# Release acceptance evidence

The goal objective is the release standard. The user explicitly waived its missing shared-contract reference. No paid APIs, purchases, external messages, invented passenger/crew/cost figures, or broad-superiority claims form part of this release.

| Requirement | Concrete evidence | Status |
| --- | --- | --- |
| Current dictionaries/downloads; documented scope | `docs/SOURCES.md`, source URLs/2023 directives, eight station mappings, `data/source_manifest.json` | Verified:2023WN domestic; eight focal airports, allWN legs retained |
| Resumable partitioned real-data ingestion | `cascade/ingest.py`; per-partition SHA256/atomic replacement; source/scoped totals/cancellation/delay-sum reconciliation | Full12-month+8station run complete |
| SQL/dbt staging, intermediate, marts; grains/keys | `dbt/models`, `docs/SCHEMA.md`, seed airports/carriers/weather/rotations | Full build passed 30 data tests; 32 Python regression tests |
| Times, DST, rollover, cancellations, diversions, missing tails/corrections/fanout | Production SQL and `tests/test_warehouse.py`; quality report; uncertain source-time rotations excluded | Fixture and data tests; gate-outs survive eventual cancellations; SOD/SOM weather summaries excluded; final quality counts recorded in EDA |
| Substantive SQL joins/CTEs/LAG/LEAD/windows/asof/cohorts/network | `dbt/models`, `sql/analysis`, monthly LAG and rotation LEAD | Exposed, reviewed; Python does not hide warehouse analysis |
| EXPLAIN improvement/runtime/memory/identical output | `reports/query_benchmark.json`, before/after SQL, EXPLAIN and profiler JSON | January identical SHA;3fresh-connection timings, measured buffer memory |
| Rerunnable EDA and ≥3analytical findings | `cascade/eda.py`, `sql/analysis`, `reports/EDA.md`, `eda.html`, `eda.json` | Real-source results; questions/denominators/limits/decisions |
| Fixed-horizon forecast; chronological/rolling evaluation; leakage audit | `cascade/modeling.py`, `docs/MODEL_CARD.md`, `reports/model_evaluation.json`, predictions table | Verified: Aug/Sep rolling validation, frozen Oct–Dec holdout; source/code fingerprints recorded |
| Seasonal/rolling, strong tabular, compact graph residual; network contribution | Five model comparisons and paired graph-vs-temporal test with7day block bootstrap | Verified: all five models, paired graph effect +0.175 pp;7day block interval reported |
| Calibration, error, severe recall, runtime | Per-fold model metrics; rate-calibration bins and denominator sensitivity | Verified: calibration bins cover all rows; error/recall/runtime and ≥5/≥10departure sensitivity |
| Constrained recovery simulation, heldout baseline replay, sensitivities | `cascade/simulation.py`, tests, `reports/scenarios.json` | Verified:92held-out days,178,864completed flights;708,004readiness checks;9sensitivities/day; low11.2%delay15recall retained |
| Synchronized map/timeline/drilldown/scenarios; ordinary+stress days | `web/dist`; generated real-data `data/replay.json`; browser QA evidence | Verified locally: desktop and390pxmobile, four actual days; map, cutoff, outcome and policy interactions |
| Each result links SQL/snapshot/model run | Export metadata, provenance links and frozen reports | Verified:768airport rows and96edge frames independently match DB; versioned SQL/snapshot/model links |
| Small licensed real-data quickstart | `data/quickstart`, manifest/hash selection, `DATA_LICENSE.md`, `cascade quickstart` |2.5MiB real sample; full offline warehouse passed 30 data tests |
| Measured full scale | `reports/warehouse_run.json`, manifest source counts, model/scenario runtimes, benchmark limits | Verified: source bytes/row counts, full warehouse and model/scenario runtimes, query runtime/buffer memory |
| Complete public release | Public source/tag/release, deployed public app, CI, clean-clone quickstart, public URL checks | Pending |

Independent review evidence is retained in the task's `work/evidence/independent-audit.md`. It identified consequential boundary/readiness/source consistency defects; fixes and regression tests preceded the public release. Final completion requires every pending row to be verified against the actual released revision.
