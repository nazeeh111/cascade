# Independent review and regression evidence

A source reviewer verified all 12 BTS archives and 8 NOAA station objects and read the 2023 reporting directives/ISD format. A separate implementation reviewer used production-SQL fixtures, current source, real warehouse queries and an independent timestamp-based replay reference.

Review exposed and fixed:

- Exact 15-minute cutoff equality omitted an unresolved scheduled flight from the backlog until the next hour. A production-SQL fixture now covers the equality boundary.
- Floating calibration boundaries could omit predictions exactly on 0.6. Integer bin IDs now count every evaluation row; boundary regression checks 0 through 1.
- Attenuated inherited delay and post-readiness service reduction could produce impossible aircraft timing. The simulator now enforces inbound arrival plus assumed minimum turn as a hard floor; service reduces only the external floor.
- In-flight inbound state needed initialization. A 12-hour schedule lookback plus cutoff-observable departures/arrivals and training priors now initializes it. Unavailable future outcomes are excluded; known departed legs cannot receive service.
- Source clock inconsistencies affected 58 previously validated rotation links. Flagged source rows remain in flight/quality reports; all affected rotation endpoints are now excluded.
- Undirected map edges previously discarded the reverse-direction count. Both directions are now aggregated and identified in tooltips.
- Cutoff-aware timeline initially displayed final outcomes. This mode now hides final outcomes and forecasts made after the cursor; final-outcome mode explicitly reveals the retrospective comparison.

Final independent checks against the current data before the last metadata-only report-label regeneration:

| Check | Observed evidence |
| --- | --- |
| Source/feature audit | 1,438,465 flights; 69,688 feature rows; 0 future weather/event observations; 0 unknown nonempty target cohorts |
| Rotation clock policy | 0 flagged-source endpoints among 1,160,285 validated links |
| App fidelity |All 768 exported airport records and 96 edge frames exactly matched warehouse values; ordinary/stress selection matched documented quantiles/top 2 |
| Model calculations |Recomputed MAE/RMSE/severe recall matched all 5 held-out model reports; all 15 fold/model calibration counts complete |
| Independent simulator reference |29,580 timestamp-readiness checks over 4 showcase days × 4 policies; 0 per-flight or aggregate differences |
| Future-outcome perturbation |Replacing unavailable future departure/arrival delays with 99999 changed 0 simulated predictions |
| Regression suite | 23 tests passed; full/quickstart dbt each passed 27 data tests |

The graph comparison label was clarified to “temporal residual MAE minus graph residual MAE”; numerical formulas were unchanged and complete reports were regenerated to match final implementation hashes. Publication, browser interaction, clean-clone and CI evidence are recorded separately in `RELEASE.md`.

The low baseline replay delay15 recall of 11.1% is a material retained limitation. Physical/resource correctness does not establish airline readiness or causal benefits.
