"""Bounded schedule/rotation replay, explicitly a hypothetical retrospective experiment.

Actual tail topology is an oracle reconstruction. Forecast-aware allocation uses
only model forecasts, schedules and training route weights, never future delays.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
import math
import time

import duckdb
import numpy as np
from ortools.sat.python import cp_model

DEFAULT_BUDGET = 4
DEFAULT_TURN = 35.0
MINUTES_PER_SERVICE = 15.0
FLIGHTS_PER_TEAM = 2
MAX_TEAMS_PER_AIRPORT = 2
POLICIES = ["volume", "backlog", "forecast_optimizer"]


def bounded_propagation(exogenous, previous_arrival_delay, scheduled_gap, alpha, min_turn=DEFAULT_TURN):
    """Enforce actual-tail readiness; alpha scales only the external shock floor."""
    inherited = 0.0 if previous_arrival_delay is None else max(0., previous_arrival_delay + min_turn - scheduled_gap)
    return max(0., alpha * exogenous, inherited)


def allocate(scores, capacity, budget=DEFAULT_BUDGET, optimize=False):
    """Allocate integer teams with total/per-airport/eligible-flight constraints."""
    if budget < 0:
        raise ValueError("Budget cannot be negative")
    if optimize:
        m = cp_model.CpModel()
        choices = {}
        for a in sorted(capacity):
            cap = min(MAX_TEAMS_PER_AIRPORT, max(0, int(capacity[a])))
            for k in range(cap):
                choices[a, k] = m.NewBoolVar(f"team_{a}_{k}")
                if k:
                    m.Add(choices[a, k] <= choices[a, k - 1])
        m.Add(sum(choices.values()) <= budget)
        # Scores are expected handled-delay reduction with a training-route multiplier.
        # A tiny deterministic tie term does not change the 0.001-minute score precision.
        objective = []
        for i, ((a, k), var) in enumerate(sorted(choices.items())):
            marginal = scores[a][k] if isinstance(scores[a], list) else scores[a]
            objective.append((round(float(marginal) * 1000) * 10000 + (100 - i)) * var)
        m.Maximize(sum(objective))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 2
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 17
        status = solver.Solve(m)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError("Recovery resource problem was infeasible")
        return {a: sum(solver.Value(v) for (aa, _), v in choices.items() if aa == a) for a in sorted(capacity)}
    remaining = budget
    result = {a: 0 for a in sorted(capacity)}
    for a in sorted(scores, key=lambda a: (-float(scores[a]), a)):
        take = min(remaining, MAX_TEAMS_PER_AIRPORT, max(0, int(capacity.get(a, 0))))
        result[a] = take
        remaining -= take
        if remaining == 0:
            break
    return result


def gate_out_observable(flight,cutoff):
    event=flight.get("observed_gate_out",flight.get("actual_dep"))
    return event is not None and event+timedelta(minutes=15)<=cutoff


def handled_flights(flights, allocation, cutoff):
    """Serve the first scheduled legs; unknown cancellations consume a slot too."""
    eligible = defaultdict(list)
    for f in flights:
        if cutoff <= f["sched_dep"] < cutoff + timedelta(hours=2) and not gate_out_observable(f,cutoff):
            eligible[f["origin"]].append(f)
    handled = set()
    for a, teams in allocation.items():
        ordered = sorted(eligible[a], key=lambda f: (f["sched_dep"], f["flight_id"]))
        handled.update(f["flight_id"] for f in ordered[:teams * FLIGHTS_PER_TEAM])
    return handled


def replay(flights, exogenous, route_recovery, rate_scale, cutoff, allocation=None, alpha=1.0, min_turn=DEFAULT_TURN, diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else {}
    handled = handled_flights(flights, allocation or {}, cutoff)
    arrivals, predictions = {}, {}
    for f in sorted(flights, key=lambda f: (f["sched_dep"], f["flight_id"])):
        # Missing/cancelled/diverted legs are outside delay-minute benefit claims.
        if f["cancelled"] or f["diverted"]:
            continue
        fid = f["flight_id"]
        a = f["origin"]
        hour = f["local_hour"]
        base = exogenous.get((a, hour), exogenous.get((a, -1), exogenous.get(("*", -1),0.)))
        base *= rate_scale.get(a, 1.)
        prev = f.get("from_flight_id")
        incoming = arrivals.get(prev)
        # Seed only a prior arrival whose event would already be observable.
        if incoming is None and f.get("prev_actual_arr") is not None and f["prev_actual_arr"] + timedelta(minutes=15) <= cutoff:
            incoming = f["prev_arr_delay"]
        if incoming is None and f.get("prev_sched_dep") is not None:
            # Initialize an in-flight/overdue inbound using only observed departure or training prior.
            pa=f["prev_origin"]; ph=f["prev_local_hour"]
            prior=exogenous.get((pa,ph),exogenous.get((pa,-1),exogenous[("*",-1)]))*rate_scale.get(pa,1.)*alpha
            if f.get("prev_actual_dep") is not None and f["prev_actual_dep"]+timedelta(minutes=15)<=cutoff:
                prior=float(f["prev_dep_delay"])
                diagnostics["observed_departure_seeds"]=diagnostics.get("observed_departure_seeds",0)+1
            else:
                diagnostics["training_prior_seeds"]=diagnostics.get("training_prior_seeds",0)+1
            incoming=prior+route_recovery.get((pa,f["origin"]),route_recovery.get(("*","*"),0.))
        gap = f["sched_gap_min"] if f.get("sched_gap_min") is not None else 99999.
        external_floor = max(0., alpha * base - (MINUTES_PER_SERVICE if fid in handled else 0.))
        delay = bounded_propagation(external_floor, incoming, gap, 1., min_turn)
        # Departed-by-cutoff events are known; resources cannot alter them.
        if f.get("actual_dep") is not None and f["actual_dep"] + timedelta(minutes=15) <= cutoff:
            delay = max(0., float(f["dep_delay"]))
        predictions[fid] = delay
        enroute = route_recovery.get((a, f["dest"]), route_recovery.get(("*", "*"), 0.))
        duration = (f["sched_arr"] - f["sched_dep"]).total_seconds()/60 if f.get("sched_arr") is not None else 1e6
        arrivals[fid] = max(delay + enroute, delay - duration + 1.)
        if f.get("actual_arr") is not None and f["actual_arr"]+timedelta(minutes=15)<=cutoff:
            arrivals[fid]=float(f["arr_delay"])
        already_known=f.get("actual_dep") is not None and f["actual_dep"]+timedelta(minutes=15)<=cutoff
        if incoming is not None and not already_known:
            diagnostics["readiness_checks"]=diagnostics.get("readiness_checks",0)+1
            if delay+1e-7 < max(0.,incoming+min_turn-gap):
                raise AssertionError("Simulated departure precedes inbound aircraft readiness")
    # Earlier legs initialize the state; only future scheduled legs enter outcome comparisons.
    future_ids={f["flight_id"] for f in flights if f["sched_dep"]>=cutoff}
    predictions={fid:v for fid,v in predictions.items() if fid in future_ids}
    return predictions, handled


def dict_rows(con, sql, params=None):
    cur = con.execute(sql, params or [])
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def calibrate(con, cutoff="2023-10-01"):
    """Fit only completed flights mature before the locked test boundary."""
    con.execute("""CREATE OR REPLACE TEMP VIEW sim_train AS
        SELECT f.*, r.sched_gap_min, r.inbound_arr_delay,
               extract(hour FROM timezone(f.origin_tz, timezone('UTC', f.sched_dep)))::INTEGER AS local_hour
        FROM flights f LEFT JOIN rotations r ON r.to_flight_id=f.flight_id
        WHERE NOT f.cancelled AND NOT f.diverted AND f.dep_delay IS NOT NULL
          AND NOT f.arrival_inconsistent AND NOT f.scheduled_arr_clock_inconsistent AND NOT f.actual_dep_clock_inconsistent
          AND f.actual_dep + INTERVAL '15 minutes' < TIMESTAMP '2023-10-01'
          AND f.sched_dep < TIMESTAMP '2023-10-01' - INTERVAL '14 hours'
    """)
    alpha = 1.0  # Hard aircraft readiness cannot be weakened by an association slope.
    rows = con.execute("""SELECT origin, local_hour,
        quantile_cont(greatest(0,dep_delay-?*greatest(coalesce(inbound_arr_delay,0)+35-coalesce(sched_gap_min,99999),0)),.65)
        FROM sim_train GROUP BY GROUPING SETS ((origin,local_hour),(origin),())""", [alpha]).fetchall()
    exog = {(a or "*", h if h is not None else -1): float(v or 0.) for a, h, v in rows}
    recovery = {(a or "*", b or "*"): float(v or 0.) for a, b, v in con.execute("""SELECT origin,dest,median(arr_delay-dep_delay)
        FROM sim_train WHERE arr_delay IS NOT NULL GROUP BY GROUPING SETS ((origin,dest),())""").fetchall()}
    rates = dict(con.execute("SELECT origin,avg((dep_delay>=15)::INTEGER)::DOUBLE FROM sim_train GROUP BY origin").fetchall())
    # Route-degree multiplier is computed only from pre-test schedules.
    degrees = dict(con.execute("""SELECT origin, count(DISTINCT dest)::DOUBLE FROM flights
        WHERE sched_dep < TIMESTAMP '2023-07-01' GROUP BY origin""").fetchall())
    maxdegree = max(degrees.values(), default=1.)
    degrees = {a: 1. + v / maxdegree for a, v in degrees.items()}
    train_n = con.execute("SELECT count(*) FROM sim_train").fetchone()[0]
    return alpha, exog, recovery, rates, degrees, train_n


def run(db_path=Path("data/cascade.duckdb"), output_dir=Path("reports")):
    t0 = time.perf_counter()
    output_dir = Path(output_dir)
    model_report_path = output_dir / "model_evaluation.json"
    model_report = json.loads(model_report_path.read_text())
    selected_model = model_report["selected_model"]
    con = duckdb.connect(str(db_path))
    alpha, exog, recovery, rates, degree, train_n = calibrate(con)
    focal = [r[0] for r in con.execute("SELECT airport FROM airports WHERE focal ORDER BY airport").fetchall()]
    dates = [r[0] for r in con.execute("SELECT DISTINCT CAST(cutoff AS DATE) AS d FROM predictions WHERE split='test' ORDER BY d").fetchall()]
    if not dates:
        raise ValueError("No held-out model predictions; run modeling before simulation")
    daily = []
    all_errors, all_actual, all_base = [], [], []
    scenario_records = []
    checked_scenarios = 0
    checked_departures = 0
    checked_readiness = 0
    for d in dates:
        cutoff = datetime.combine(d, datetime.min.time()) + timedelta(hours=16)
        horizon_end = cutoff + timedelta(hours=8)
        flights = dict_rows(con, """SELECT f.flight_id,f.origin,f.dest,f.sched_dep,f.sched_arr,f.actual_dep,f.observed_gate_out,f.actual_arr,f.dep_delay,f.arr_delay,f.cancelled,f.diverted,
            extract(hour FROM timezone(f.origin_tz, timezone('UTC',f.sched_dep)))::INTEGER AS local_hour,
            r.from_flight_id,r.sched_gap_min,p.actual_arr AS prev_actual_arr,p.arr_delay AS prev_arr_delay,
            p.sched_dep as prev_sched_dep,p.actual_dep as prev_actual_dep,p.dep_delay as prev_dep_delay,
            p.origin as prev_origin,
            extract(hour from timezone(p.origin_tz,timezone('UTC',p.sched_dep)))::integer as prev_local_hour
            FROM flights f LEFT JOIN rotations r ON r.to_flight_id=f.flight_id
            LEFT JOIN flights p ON p.flight_id=r.from_flight_id
            WHERE f.sched_dep >= ? AND f.sched_dep < ? ORDER BY f.sched_dep,f.flight_id""", [cutoff-timedelta(hours=12),horizon_end])
        feature = {r["airport"]: r for r in dict_rows(con, "SELECT airport,backlog_n,sched_n_2h FROM features WHERE cutoff=?", [cutoff])}
        forecast = dict(con.execute("SELECT airport,prediction FROM predictions WHERE model=? AND cutoff=? AND split='test'", [selected_model,cutoff]).fetchall())
        # If midnight-UTC schedule is empty at a focal airport, train prior supplies a declared fallback.
        forecast = {a: float(forecast.get(a, rates.get(a, .2))) for a in focal}
        counts = {a: sum(f["origin"] == a and cutoff <= f["sched_dep"] < cutoff + timedelta(hours=2) and not gate_out_observable(f,cutoff) for f in flights) for a in focal}
        capacity = {a: min(MAX_TEAMS_PER_AIRPORT, math.ceil(counts[a] / FLIGHTS_PER_TEAM)) for a in focal}
        # Fixed forecast-driven shock scaling, clipped to prevent extrapolation explosions.
        scales = {a: min(3., max(.25, forecast[a] / max(.05, rates.get(a, .2)))) for a in focal}
        allocations = {
            "none": {a: 0 for a in focal},
            "volume": allocate(counts, capacity),
            "backlog": allocate({a: float(feature.get(a, {}).get("backlog_n") or 0) for a in focal}, capacity),
            "forecast_optimizer": allocate({a: [forecast[a] * min(FLIGHTS_PER_TEAM, max(0, counts[a]-k*FLIGHTS_PER_TEAM)) * MINUTES_PER_SERVICE * degree.get(a,1.) for k in range(capacity[a])] for a in focal}, capacity, optimize=True)
        }
        base_diag={}
        base, _ = replay(flights, exog,recovery,scales,cutoff,alpha=alpha,diagnostics=base_diag)
        evaluable = [f for f in flights if f["flight_id"] in base and f["dep_delay"] is not None]
        y = np.array([max(0., f["dep_delay"]) for f in evaluable])
        p = np.array([base[f["flight_id"]] for f in evaluable])
        all_errors.extend((p-y).tolist()); all_actual.extend(y.tolist()); all_base.extend(p.tolist())
        replay_metrics = {"n_completed_flights": len(evaluable), "mae_minutes": float(np.mean(np.abs(p-y))) if len(y) else None,
                          "bias_minutes": float(np.mean(p-y)) if len(y) else None,
                          "observed_positive_departure_minutes": float(y.sum()), "simulated_positive_departure_minutes": float(p.sum()),
                          "excluded_cancelled": sum(bool(f["cancelled"]) for f in flights if f["sched_dep"]>=cutoff), "excluded_diverted": sum(bool(f["diverted"]) for f in flights if f["sched_dep"]>=cutoff), "initialization":base_diag}
        policies = {}
        for policy, allocation in allocations.items():
            diag={}
            result, handled = replay(flights, exog,recovery,scales,cutoff,allocation,alpha,diagnostics=diag)
            checked_readiness += diag.get("readiness_checks",0)
            checked_scenarios += 1
            checked_departures += len(result)
            if any(v < 0 or not math.isfinite(v) for v in result.values()):
                raise AssertionError("Nonfinite or negative simulated departure delay")
            total = sum(result.values())
            benefit = sum(base.values()) - total
            if benefit < -1e-7:
                raise AssertionError("A bounded reduction increased network delay")
            if sum(allocation.values()) > DEFAULT_BUDGET:
                raise AssertionError("Budget exceeded")
            policies[policy] = {"allocation": allocation,"simulated_departure_delay_minutes": total,
                                "simulated_reduction_minutes": max(0.,benefit), "served_scheduled_legs": len(handled),
                                "served_completed_legs": sum(fid in result for fid in handled),
                                "budget_used": sum(allocation.values())}
            scenario_records.append((d,cutoff,policy,alpha,DEFAULT_TURN,sum(base.values()),total,max(0.,benefit),json.dumps(allocation)))
        sensitivity = []
        for turn in (25.,35.,45.):
            for propagation in (.75, 1.0, 1.25):
                no, _ = replay(flights,exog,recovery,scales,cutoff,alpha=propagation,min_turn=turn)
                yes, _ = replay(flights,exog,recovery,scales,cutoff,allocations["forecast_optimizer"],propagation,turn)
                sensitivity.append({"min_turn_minutes": turn,"external_shock_multiplier": propagation,"simulated_reduction_minutes": max(0., sum(no.values())-sum(yes.values()))})
        daily.append({"date": str(d),"cutoff": str(cutoff),"horizon_end": str(horizon_end),"forecast_model": selected_model,
                      "forecast": forecast,"replay": replay_metrics,"policies": policies,"sensitivity": sensitivity})
    errors = np.array(all_errors); y = np.array(all_actual); p = np.array(all_base)
    severe = y >= 15
    overall = {"heldout_days": len(dates),"completed_flight_predictions": len(errors),
               "mae_minutes": float(np.abs(errors).mean()), "bias_minutes": float(errors.mean()),
               "rmse_minutes": float(np.sqrt((errors**2).mean())),
               "delay15_recall": float((p[severe]>=15).mean()) if severe.any() else None,
               "pearson_correlation": float(np.corrcoef(y,p)[0,1]) if np.std(y)>0 and np.std(p)>0 else None,
               "use_limit": "This replay error describes model mismatch. Resource outcomes are exploratory and must be read alongside this error; no airline readiness or causal savings claim."}
    con.execute("CREATE OR REPLACE TABLE scenario_results (day DATE,cutoff TIMESTAMP,policy VARCHAR,alpha DOUBLE,min_turn_minutes DOUBLE,baseline_delay_minutes DOUBLE,scenario_delay_minutes DOUBLE,reduction_minutes DOUBLE,allocation_json VARCHAR)")
    con.executemany("INSERT INTO scenario_results VALUES (?,?,?,?,?,?,?,?,?)", scenario_records)
    aggregate = {policy: {"mean_daily_simulated_reduction_minutes": float(np.mean([d["policies"][policy]["simulated_reduction_minutes"] for d in daily])),
                           "total_simulated_reduction_minutes": float(sum(d["policies"][policy]["simulated_reduction_minutes"] for d in daily))} for policy in allocations}
    report = {"run_id": "scenario-2023-" + hashlib.sha256((model_report["run_id"] + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()).encode()).hexdigest()[:12], "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "model_run_id": model_report["run_id"], "experiment": "Retrospective actual-tail topology, forecast-driven shocks, bounded hypothetical ground-recovery teams",
              "budget": DEFAULT_BUDGET, "maximum_teams_per_airport": MAX_TEAMS_PER_AIRPORT,"flights_served_per_team": FLIGHTS_PER_TEAM,
              "maximum_delay_reduction_per_served_flight_minutes": MINUTES_PER_SERVICE,
              "forecast_interval_hours": 2,"replay_horizon_hours": 8,"cutoff_utc_hour": 16,
              "calibration": {"train_before": "2023-10-01", "train_completed_flights": train_n,"external_shock_multiplier": alpha,"minimum_turn_minutes": DEFAULT_TURN,
                              "exogenous_delay": "65th percentile of nonnegative observed departure delay after subtracting bounded inherited-delay component, by airport/local hour",
                              "enroute_recovery": "Training median arrival delay minus departure delay per route",
                              "shock_scale": "Selected model next-2h rate / training airport delayed-departure rate, clipped [.25,3], held fixed over 8h scenario"},
              "baseline_replay": overall,"policy_summary": aggregate,"days": daily,
              "invariants": {"scenarios_checked": checked_scenarios, "departure_predictions_checked": checked_departures, "aircraft_readiness_checks":checked_readiness,"aircraft_readiness_violations":0, "budget_exceeded": 0,"negative_simulated_departure_delay": 0,"resource_increases_delay": 0},
              "limitations": ["Actual-tail topology and final cancellations/diversions are known retrospectively. This is an oracle-topology scenario experiment, not a deployable aircraft recovery plan.",
                             "Allocator scores use forecasts, final schedules assumed known and pre-July route degree only; no future realized delays or future weather.",
                             "Cancellations and diversions are excluded from delay-minute outcomes, but a resource slot aimed at such a final scheduled leg is consumed. No recovered cancellations are claimed.",
                             "No passenger, crew, maintenance, gate, airspace or safety constraint data. Teams and 15-minute service are hypothetical, not staffing prescriptions.",
                             "The 2h forecast is held constant over an 8h replay only as a scenario assumption, not an evaluated 8h forecast.",
                             "Benefits are differences within this deterministic simulator, not estimated causal savings. Large baseline errors limit operational interpretation.",
                             "Aircraft readiness is a hard timing floor, including under service. The sensitivity multiplier scales exogenous shocks only, never physical inbound availability."],
              "runtime_seconds": time.perf_counter()-t0}
    output_dir.mkdir(parents=True,exist_ok=True)
    (output_dir/"scenarios.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    con.close()
    print(f"Scenario report: {output_dir/'scenarios.json'} ({len(dates)} heldout days)",flush=True)
    return report


if __name__ == "__main__":
    run()
