"""Chronological airport-rate forecasts; all feature extraction remains in SQL.

The graph model is a deliberately compact linear message-passing residual model,
not a claim that a large GNN is necessary. No realized aircraft assignment enters X.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import json
import time

import duckdb
import numpy as np
import pyarrow as pa
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from .ingest import atomic_text

BASE_FEATURES = ["sched_n_2h", "hour", "dow", "month", "lag_rate_2h", "lag_rate_6h", "observed_n_2h", "backlog_n", "temp_c", "wind_ms", "visibility_m", "weather_age_min"]
MODELS = ["seasonal", "rolling", "tabular", "temporal_residual", "graph_residual"]
SEVERE_THRESHOLD = 0.5
FEATURE_SQL = """
SELECT airport, cutoff, target_rate, target_n, label_available_at,
       sched_n_2h, hour, dow, month, lag_rate_2h, lag_rate_6h,
       observed_n_2h, backlog_n, temp_c, wind_ms, visibility_m,
       weather_age_min, upstream_rate, weather_available_at, max_event_available_at
FROM features WHERE target_n > 0 AND target_rate IS NOT NULL
ORDER BY cutoff, airport
"""


def json_default(x):
    if isinstance(x, (datetime, Path)):
        return str(x)
    if isinstance(x, np.generic):
        return x.item()
    raise TypeError(type(x).__name__)


def load_rows(con):
    cursor = con.execute(FEATURE_SQL)
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def availability_audit(rows):
    violations = []
    for r in rows:
        for name in ("weather_available_at", "max_event_available_at"):
            if r.get(name) is not None and r[name] > r["cutoff"]:
                violations.append((r["airport"], str(r["cutoff"]), name))
        if not 0 <= r["target_rate"] <= 1:
            violations.append((r["airport"], str(r["cutoff"]), "target range"))
    if violations:
        raise ValueError(f"Availability/range audit failed: {violations[:5]}")
    return {"rows_audited": len(rows), "future_feature_violations": 0,
            "allowed_features": BASE_FEATURES + ["airport_one_hot", "upstream_rate (graph only)"],
            "excluded": ["tail", "actual future assignments", "delay causes", "future actual weather", "target_n", "label_available_at"],
            "availability_assumptions": ["Final reported schedule treated as known; BTS has no historical schedule snapshots.", "Gate-out events assumed available 15 minutes after their occurrence, including eventual cancellations; not verified operational feed latency.", "ISD observations assumed available 60 minutes after observation; archival corrections may differ from real-time feed.", "Cancellation publication times unavailable: cancellations enter labels only; backlog is unresolved scheduled departures, not known cancellations."]}


def matrix(rows, airports):
    result = np.empty((len(rows), len(BASE_FEATURES) + len(airports)), dtype=float)
    for i, r in enumerate(rows):
        result[i, :len(BASE_FEATURES)] = [np.nan if r.get(f) is None else float(r[f]) for f in BASE_FEATURES]
        result[i, len(BASE_FEATURES):] = [float(r["airport"] == a) for a in airports]
    return result


def residual_matrix(rows, base, graph=False):
    def value(r, key, fallback):
        v = r.get(key)
        return fallback if v is None or not np.isfinite(float(v)) else float(v)
    result = []
    for r, p in zip(rows, base):
        own = value(r, "lag_rate_2h", p)
        lag6 = value(r, "lag_rate_6h", p)
        row = [own - p, lag6 - p, value(r, "backlog_n", 0) / max(1, value(r, "sched_n_2h", 1)), p]
        if graph:
            upstream = value(r, "upstream_rate", own)
            row += [upstream - own, upstream - p]
        result.append(row)
    return np.asarray(result)


def seasonal_fit(rows):
    airport, group = {}, {}
    for r in rows:
        y = float(r["target_rate"])
        a = r["airport"]
        k = (a, int(r["hour"]), int(r["dow"]))
        airport.setdefault(a, []).append(y)
        group.setdefault(k, []).append(y)
    prior = {a: float(np.mean(v)) for a, v in airport.items()}
    global_mean = float(np.mean([r["target_rate"] for r in rows]))
    smoothed = {k: (sum(v) + 10 * prior[k[0]]) / (len(v) + 10) for k, v in group.items()}
    return prior, smoothed, global_mean


def seasonal_predict(fitted, rows):
    prior, groups, global_mean = fitted
    return np.array([groups.get((r["airport"], int(r["hour"]), int(r["dow"])), prior.get(r["airport"], global_mean)) for r in rows])


def train_tabular(rows, airports, params):
    model = HistGradientBoostingRegressor(loss="squared_error", random_state=17, early_stopping=False, **params)
    model.fit(matrix(rows, airports), np.array([r["target_rate"] for r in rows]))
    return model


def residual_training(rows, airports, params, end):
    """Residual fit uses prior-month out-of-time predictions, never fitted residuals."""
    oof_rows, oof_predictions = [], []
    for month in (6, 7, 8, 9):
        start = datetime(2023, month, 1)
        stop = datetime(2023, month + 1, 1)
        if stop > end:
            continue
        tr = [r for r in rows if r["label_available_at"] < start]
        va = [r for r in rows if start <= r["cutoff"] < stop]
        if len(tr) < 100 or len(va) < 10:
            continue
        m = train_tabular(tr, airports, params)
        oof_rows.extend(va)
        oof_predictions.extend(m.predict(matrix(va, airports)))
    return oof_rows, np.asarray(oof_predictions)


def fit_predict(train, test, airports, params, end):
    if not train or not test:
        raise ValueError("Chronological split has no train or evaluation rows")
    if any(r["label_available_at"] >= end for r in train):
        raise ValueError("Unmatured label passed to training")
    timings, out = {}, {}
    t = time.perf_counter()
    seasonal = seasonal_predict(seasonal_fit(train), test)
    out["seasonal"] = seasonal
    timings["seasonal"] = time.perf_counter() - t
    t = time.perf_counter()
    out["rolling"] = np.array([p if r.get("lag_rate_2h") is None else float(r["lag_rate_2h"]) for r, p in zip(test, seasonal)])
    timings["rolling"] = time.perf_counter() - t
    t = time.perf_counter()
    base_model = train_tabular(train, airports, params)
    base = np.clip(base_model.predict(matrix(test, airports)), 0, 1)
    out["tabular"] = base
    timings["tabular"] = time.perf_counter() - t
    t = time.perf_counter()
    residual_rows, residual_base = residual_training(train, airports, params, end)
    oof_seconds = time.perf_counter() - t
    for name, graph in (("temporal_residual", False), ("graph_residual", True)):
        t = time.perf_counter()
        if len(residual_rows) >= 20:
            residual_y = np.array([r["target_rate"] for r in residual_rows]) - residual_base
            residual_model = make_pipeline(StandardScaler(), Ridge(alpha=100.0))
            residual_model.fit(residual_matrix(residual_rows, residual_base, graph), residual_y)
            correction = residual_model.predict(residual_matrix(test, base, graph))
            out[name] = np.clip(base + correction, 0, 1)
        else:
            out[name] = base.copy()
        timings[name] = timings["tabular"] + oof_seconds + time.perf_counter() - t
    return out, timings, len(residual_rows)


def metrics(y, p, weights=None):
    y, p = np.asarray(y), np.asarray(p)
    severe = y >= SEVERE_THRESHOLD
    pred_severe = p >= SEVERE_THRESHOLD
    calibration = []
    bin_ids = np.minimum(9, np.floor(np.clip(p, 0, 1) * 10).astype(int))
    for index in range(10):
        low = index / 10
        mask = bin_ids == index
        if np.any(mask):
            calibration.append({"lower": round(float(low), 1), "n": int(mask.sum()), "predicted": float(p[mask].mean()), "observed": float(y[mask].mean())})
    return {"n": int(len(y)), "mae": float(np.mean(np.abs(y - p))),
            "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
            "flight_weighted_mae": float(np.average(np.abs(y - p), weights=weights)) if weights is not None else None,
            "bias": float(np.mean(p - y)),
            "severe_events": int(severe.sum()), "severe_predicted": int(pred_severe.sum()),
            "severe_recall": float(np.mean(pred_severe[severe])) if severe.any() else None,
            "severe_precision": float(np.mean(severe[pred_severe])) if pred_severe.any() else None,
            "calibration_mae": float(sum(b["n"] * abs(b["observed"] - b["predicted"]) for b in calibration) / len(y)),
            "calibration_bins": calibration}


def network_uncertainty(rows, temporal, graph):
    """Seven-day moving-block bootstrap retains short-range temporal dependence."""
    by_day = {}
    for r, t, g in zip(rows, temporal, graph):
        day = r["cutoff"].date()
        by_day.setdefault(day, []).append(abs(r["target_rate"]-t)-abs(r["target_rate"]-g))
    daily = [by_day[d] for d in sorted(by_day)]
    if len(daily) < 14:
        return {"method": "insufficient days for seven-day moving-block bootstrap", "days": len(daily)}
    sums = np.array([sum(d) for d in daily]); counts = np.array([len(d) for d in daily])
    rng = np.random.default_rng(17)
    draws = []
    for _ in range(1000):
        ix = np.concatenate([(rng.integers(0, len(daily)) + np.arange(7)) % len(daily) for _ in range((len(daily)+6)//7)])[:len(daily)]
        draws.append(float(sums[ix].sum()/counts[ix].sum()))
    return {"method": "circular seven-day moving-block bootstrap, 1000 draws, seed17", "days": len(daily),
            "mae_reduction_95pct_interval": [float(x) for x in np.quantile(draws,[.025,.975])],
            "caution": "Descriptive resampling interval for this carrier/year; not a guarantee under regime changes."}


def persist_predictions(con,records):
    """One Arrow-to-SQL transaction preserves prior predictions until the new batch validates."""
    names=['airport','cutoff','model','prediction','target_rate','target_n','split','fold']
    schema=pa.schema([('airport',pa.string()),('cutoff',pa.timestamp('us')),('model',pa.string()),('prediction',pa.float64()),('target_rate',pa.float64()),('target_n',pa.int32()),('split',pa.string()),('fold',pa.string())])
    table=pa.Table.from_arrays([pa.array([r[i] for r in records],type=field.type) for i,field in enumerate(schema)],schema=schema)
    con.register('__cascade_prediction_batch',table)
    try:
        invalid=con.execute("select count(*) from __cascade_prediction_batch where airport is null or cutoff is null or model is null or prediction is null or not isfinite(prediction) or prediction not between 0 and 1 or target_rate is null or not isfinite(target_rate) or target_rate not between 0 and 1 or target_n is null or target_n<1").fetchone()[0]
        duplicates=con.execute('select count(*) from (select airport,cutoff,model,fold,count(*) n from __cascade_prediction_batch group by all having n<>1)').fetchone()[0]
        if invalid or duplicates:raise ValueError('Invalid prediction batch; existing predictions preserved')
        con.execute('begin')
        try:
            con.execute('create or replace table predictions as select * from __cascade_prediction_batch')
            con.execute('commit')
        except Exception:
            con.execute('rollback');raise
    finally:
        con.unregister('__cascade_prediction_batch')


def _run(db_path=Path("data/cascade.duckdb"), output_dir=Path("reports")):
    start = time.perf_counter()
    con = duckdb.connect(str(db_path))
    rows = load_rows(con)
    if not rows:
        raise ValueError("No labeled feature rows")
    audit = availability_audit(rows)
    fingerprint = hashlib.sha256()
    for r in rows:
        fingerprint.update(json.dumps(r, sort_keys=True, default=json_default).encode())
    data_sha = fingerprint.hexdigest()
    code_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    airports = sorted({r["airport"] for r in rows})
    configs = [{"max_iter": 120, "max_leaf_nodes": 15, "learning_rate": .06, "l2_regularization": 10.0},
               {"max_iter": 180, "max_leaf_nodes": 31, "learning_rate": .05, "l2_regularization": 20.0}]
    validation, evaluated_configs = [], []
    for config in configs:
        folds = []
        for month in (8, 9):
            boundary = datetime(2023, month, 1)
            end = datetime(2023, month + 1, 1)
            tr = [r for r in rows if r["label_available_at"] < boundary]
            va = [r for r in rows if boundary <= r["cutoff"] < end]
            if len(tr) < 100 or not va:
                continue
            t = time.perf_counter()
            m = train_tabular(tr, airports, config)
            p = np.clip(m.predict(matrix(va, airports)), 0, 1)
            folds.append({"month": month, "train_n": len(tr), "test_n": len(va), "mae": metrics([r["target_rate"] for r in va], p)["mae"], "runtime_seconds": time.perf_counter() - t})
        if folds:
            evaluated_configs.append({"params": config, "folds": folds, "mean_mae": float(np.mean([f["mae"] for f in folds]))})
    selected = min(evaluated_configs, key=lambda c: c["mean_mae"])["params"] if evaluated_configs else configs[0]
    prediction_records, fold_reports = [], []
    graph_uncertainty = None
    boundaries = [("validation_august", datetime(2023, 8, 1), datetime(2023, 9, 1), "validation"),
                  ("validation_september", datetime(2023, 9, 1), datetime(2023, 10, 1), "validation"),
                  ("heldout_oct_dec", datetime(2023, 10, 1), datetime(2024, 1, 1), "test")]
    for fold, boundary, end, split in boundaries:
        train = [r for r in rows if r["label_available_at"] < boundary]
        test = [r for r in rows if boundary <= r["cutoff"] < end]
        if len(train) < 100 or not test:
            continue
        print(f"Evaluating {fold}: train={len(train)} eval={len(test)}", flush=True)
        pred, timings, residual_n = fit_predict(train, test, airports, selected, boundary)
        if split == "test":
            graph_uncertainty = network_uncertainty(test, pred["temporal_residual"], pred["graph_residual"])
        fold_metrics = {}
        y = [r["target_rate"] for r in test]
        w = [r["target_n"] for r in test]
        for model, p in pred.items():
            fold_metrics[model] = {**metrics(y, p, w), "fit_predict_seconds": timings[model]}
            fold_metrics[model]["denominator_sensitivity"] = {}
            for minimum in (5, 10):
                mask = np.array(w) >= minimum
                if mask.any():
                    fold_metrics[model]["denominator_sensitivity"][str(minimum)] = metrics(np.array(y)[mask],p[mask],np.array(w)[mask])
            prediction_records.extend((r["airport"], r["cutoff"], model, float(v), float(r["target_rate"]), int(r["target_n"]), split, fold) for r, v in zip(test, p))
        fold_reports.append({"fold": fold, "split": split, "fit_before": str(boundary), "evaluation_end_exclusive": str(end), "train_rows": len(train), "evaluation_rows": len(test), "max_training_label_available_at": str(max(r["label_available_at"] for r in train)), "out_of_time_residual_rows": residual_n, "models": fold_metrics})
    persist_predictions(con,prediction_records)
    heldout = next((f for f in fold_reports if f["split"] == "test"), None)
    graph_difference = None
    selected_model = "tabular"
    if heldout:
        graph_difference = heldout["models"]["temporal_residual"]["mae"] - heldout["models"]["graph_residual"]["mae"]
        # Deployment choice is locked using validation folds only, not final test.
        valid = [f for f in fold_reports if f["split"] == "validation"]
        selected_model = min(MODELS, key=lambda m: np.mean([f["models"][m]["mae"] for f in valid])) if valid else "tabular"
    report = {"run_id": "model-2023-" + hashlib.sha256(json.dumps({"params": selected, "data_sha256": data_sha, "code_sha256": code_sha}, sort_keys=True).encode()).hexdigest()[:12],
              "feature_query_sql": FEATURE_SQL, "feature_rows_sha256": data_sha, "implementation_sha256": code_sha,
              "target": "Fraction of scheduled departures in next 2h that cancel or depart >=15 minutes late", "horizon_hours": 2,
              "severe_threshold": SEVERE_THRESHOLD, "unit": "airport-hour cutoff with at least one scheduled target departure",
              "selected_params": selected, "selected_model": selected_model, "selection_rule": "Lowest average August/September validation MAE; never selected using October-December labels",
              "tuning": evaluated_configs, "folds": fold_reports, "availability_audit": audit,
              "graph_contribution": {"comparison": "temporal_residual MAE minus graph_residual MAE, same tabular base and OOF residual rows", "heldout_mae_reduction": graph_difference, "uncertainty": graph_uncertainty, "interpretation": "Positive is an improvement; an observed negative result is retained. No claim of general superiority or significance."},
              "runtime_seconds": time.perf_counter() - start, "compute": {"numerical_workers":1,"prediction_persistence":"validated Arrow-to-SQL atomic transaction"},
              "limitations": ["One carrier and eight focal airports in 2023; excludes passenger, crew, maintenance and non-WN propagation.", "Overlapping 2h labels are serially dependent; point metrics are descriptive, without independence-based confidence claims.", "Final schedules, revised archival observations and assumed feed latencies limit deployment interpretation.", "Graph is a train-period scheduled-route adjacency and a linear temporal message residual, not observed future rotations or a large GNN.", "No severe-event probability is estimated: calibration is mean predicted versus mean observed disruption rate; severe recall uses a 0.5 rate threshold."]}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_text(output_dir / "model_evaluation.json",json.dumps(report, indent=2, default=json_default, allow_nan=False) + "\n")
    con.close()
    print(f"Model report: {output_dir / 'model_evaluation.json'}", flush=True)
    return report


def run(db_path=Path("data/cascade.duckdb"), output_dir=Path("reports")):
    with threadpool_limits(limits=1):
        return _run(db_path, output_dir)


if __name__ == "__main__":
    run()
