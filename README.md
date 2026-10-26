# CASCADE

**Reconstruct disruption. Forecast network pressure. Test a bounded recovery idea.**

CASCADE connects US public flight and weather records to an inspectable two-hour departure-disruption forecast and a constrained recovery experiment. SQL and dbt build the warehouse; statistical models and a small integer optimizer operate on explicit, versioned tables.

[Live replay](https://cascade-flight-intelligence.nazeeh1.chatgpt.site) · [Source dictionaries](docs/SOURCES.md) · [SQL investigation](reports/EDA.md) · [Model card](docs/MODEL_CARD.md) · [Acceptance evidence](docs/ACCEPTANCE.md)

The 2023 study retains **1,438,465 Southwest domestic flights** for aircraft continuity and focuses forecasts on **BWI, DAL, DEN, HOU, LAS, MDW, OAK and PHX**. This is a historical research replay with declared information-availability assumptions. Recovery outcomes are simulated minutes, not causal savings or airline staffing instructions.

![CASCADE real-data network replay](docs/images/replay.png)

## Reproduce

Python 3.12 and [uv](https://docs.astral.sh/uv/) are the recommended local runtime. No API key, account, paid service or source download is needed for the bundled quickstart.

```bash
git clone https://github.com/nazeeh111/cascade.git
cd cascade
uv sync --frozen --python 3.12
uv run pytest -q
uv run cascade quickstart
uv run cascade serve
```

Open the loopback URL printed by `serve`. The app reads a frozen full-run replay; the quickstart separately rebuilds the warehouse from a **2.5 MiB licensed real-data subset**. The sample's selected dates are discontinuous and cannot support annual scientific claims. Its exact selection, per-file rows and checksums are in [data/quickstart/manifest.json](data/quickstart/manifest.json). `quickstart` uses a separate DuckDB file and preserves the full warehouse.

Rebuild all 2023 source data, models, scenarios and the app export:

```bash
uv run cascade full
# Resume already-downloaded, hash-verified partitions:
uv run cascade full --skip-ingest
# Run individual inspectable stages:
uv run cascade warehouse
uv run cascade eda
uv run cascade model
uv run cascade simulate
uv run cascade benchmark
uv run cascade export
uv run cascade verify
```

Source downloads are public and resumable by completed partition. Incomplete bytes never replace a valid partition. The ingestion manifest records hashes of original ZIP/CSV bytes and filtered Parquet, retrieval time, source/scoped counts, cancellations, missing departure delay and signed delay sums. `uv run cascade ingest --refresh` explicitly refreshes sources and preserves changed prior Parquet/manifest bytes under content-addressed `data/history` paths. Manifest writes are atomic; corrupt or incomplete markers trigger a safe re-fetch. A changed snapshot produces a new model data fingerprint and requires regenerated outputs.

## What the system does

- **Warehouse:** raw public snapshots → dbt staging → UTC flights and quality flags → validated retrospective rotations → cutoff-safe airport features and fixed training-period network edges. See [table grains and keys](docs/SCHEMA.md).
- **Investigation:** substantive SQL joins, CTEs, LAG/LEAD, rolling windows, as-of weather, local seasonality, censoring and cohort analysis. Each published finding carries its question, denominator, limitation and decision implication. Read [the evidence notebook](reports/EDA.md) or [its chart view](reports/eda.html).
- **Forecast:** at each hourly UTC cutoff, predict the fraction of scheduled departures in the following two hours that cancel or depart at least 15 minutes late. Compare seasonal, recent-observation, gradient-boosted tabular, temporal residual and graph residual models on chronological dates.
- **Recovery lab:** replay held-out schedules with retrospective actual-tail topology, hard aircraft readiness, an explicit small resource budget and forecast-aware allocation versus simple rules. Check baseline replay error and parameter sensitivity before interpreting any simulated difference.
- **Replay app:** select ordinary or high-disruption held-out days; move the cutoff; inspect the geographic network and airport drilldown; reveal final outcomes separately. Recovery scenarios use a clearly marked 16:00 UTC experiment, independent of the cursor. Source hashes, SQL and model-run reports remain linked.

## What the evidence says

The **tabular** model was selected by mean August/September validation MAE. Final October–December evaluation contains **13,492 labeled airport-hour cutoffs** over **92 days**. The following rates describe the selected WN network, with the declared archival availability assumptions.

| Model | MAE (pp) | RMSE (pp) | Rate-calibration error (pp) | Severe recall | Fit/predict (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| seasonal | 14.62 | 18.69 | 6.96 | 22.2% | 0.49 |
| rolling | 12.22 | 16.65 | 5.41 | 39.5% | 0.15 |
| tabular | 10.21 | 13.83 | 1.68 | 39.1% | 7.42 |
| temporal residual | 10.08 | 13.82 | 0.99 | 36.3% | 20.57 |
| graph residual | 9.91 | 13.63 | 1.30 | 36.3% | 20.42 |

A severe case has an observed late15-or-cancelled rate of at least 50%; recall uses the same threshold on predictions. Rate calibration is not an event probability. Residual timings include their tabular and out-of-time fits, so overlapping timings must not be added.

The graph residual reduces held-out MAE by **0.175 pp** versus the temporal residual (seven-day block-bootstrap descriptive 95% interval: **0.101–0.242 pp**). This is a restricted-network result, not broad superiority. Model selection remains based on validation, including when final-test rankings differ. [Complete calibration, folds and denominator sensitivities](reports/model_evaluation.json).

Reproducible SQL findings include:

- DEN recorded 35.9% late15-or-cancelled departures (96,164 scheduled), versus 22.1% at HOU (50,884). [Question, denominator and limits](sql/analysis/airport_cohorts.sql).
- Next departures were late15 in 80.4% of pairs after a late15 inbound, versus 14.0% after an inbound under15 minutes late. [Question, denominator and limits](sql/analysis/rotation_associations.sql).
- Departure delay median was 1 min, mean 11.7 min, and 99th percentile 147 min. 592,247 departures were early; 17,227 arrival delays were unobserved. [Question, denominator and limits](sql/analysis/overview.sql).
- Among 80,786 scheduled January departures at the eight focal origins, WN accounts for 43,468 departures (53.8%). The remaining reporting carriers have different airport, route and schedule mixes. [Question, denominator and limits](sql/analysis/carrier_cohorts.sql).

[Full SQL investigation and chart notebook](reports/EDA.md), including weather, seasonality, selection bias and cancellation censoring.

## Scale and query performance

The measured ingestion scanned **6,847,899 all reporting-carrier source rows**, retaining **1,438,465 WN flights**. Eight stations supplied **93,148 source reports**, deduplicated to **90,084 observations**. The warehouse creates **69,688 hourly feature rows** and **1,160,285 validated retrospective links**.

Original downloads totaled **395,751,334 bytes**; scoped flight/weather Parquet totaled **21,019,683 bytes**. Stage wall times on the development Mac were ingestion **531.6s** (initial download), full warehouse **225.4s**, model evaluation **52.8s**, and recovery evaluation **131.7s**. These are separately observed local stage measurements, with cache/host effects, not a throughput guarantee or a single uninterrupted end-to-end timing.

A January eight-airport weather query compares range-join-plus-ranking with ASOF. Both return the same SHA-256 result. Three fresh-connection repetitions measured **134.8×** median speedup and **86.8%** lower DuckDB peak buffer memory. This is a subset improvement; buffer memory is not process RSS. Inspect [before/after SQL](sql), [EXPLAIN/profile evidence](reports/query_benchmark.json) and [warehouse measurements](reports/warehouse_run.json).

## Recovery validation

The deterministic positive-delay baseline (early departures scored as zero, signed values preserved in the warehouse) was replayed on **178,864 completed flights across 92 held-out days**: MAE **11.29 min**, RMSE **25.44 min**, and bias **-4.92min**. Its delay15 recall was only **11.2%**. This underrepresentation of tail events materially limits operational interpretation.

At a four-team hypothetical budget, mean daily simulated reduction was **22.6 min** for schedule-volume priority, **26.8 min** for backlog priority and **31.5 min** for the forecast-aware optimizer. These are internal simulator differences, not measured causal savings or an optimal real airline plan. All nine turnaround/shock sensitivities and day-level errors remain visible in [scenarios.json](reports/scenarios.json).

## Boundaries that matter

Final BTS schedules are assumed known before cutoff; historical schedule versions are unavailable. Recorded gate-out events have an assumed 15-minute observation lag and NOAA observations an assumed 60-minute publication lag. Corrected archival records may differ from what a real-time feed showed. Cancellation announcement times are absent; labels mature retrospectively and cancellation status never enters the cutoff feature matrix. Eventual cancellation also cannot erase a gate-out already observed at cutoff.

Actual aircraft assignments are used only for retrospective chains and scenario topology. International/ferry/maintenance movements, passengers, crew legality, gates and airspace restrictions are missing. Same-tail association is not proof of propagation cause. The simulator enforces its stated bounds; those are a small hypothetical experiment, not all real airline constraints. Baseline replay error and negative/inconclusive model comparisons are retained.

## Layout and provenance

| Path | Purpose |
| --- | --- |
| `cascade/ingest.py` | Atomic, hash-verified source partitions and reconciliation |
| `dbt/models`, `dbt/tests` | Substantive SQL transformations and data contracts |
| `sql/analysis` | Rerunnable exploratory questions and cohorts |
| `cascade/modeling.py` | Chronological baseline/tabular/graph comparisons |
| `cascade/simulation.py` | Bounded resource optimization and held-out replay |
| `web/dist` | Buildless, dependency-free browser app and frozen replay |
| `data/source_manifest.json` | Original-source provenance and run scale |
| `data/quickstart` | Small attributed real-data sample |
| `reports` | Scientific results, query profiles, evidence and verification |

Code: MIT. Federal source records: public domain with attribution. Airport metadata: airportsdata MIT. See [DATA_LICENSE.md](DATA_LICENSE.md). No endorsement by airlines, airports, BTS or NOAA is claimed.
