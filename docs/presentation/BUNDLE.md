# One cutoff, three different claims

The original full-run replay reports DEN at 16:00 UTC on 19 October 2023: 28 scheduled departures, forecast 0.30438871555208613 and final rate 0.5357142857142857. This is a revealing underprediction, not a curated success. The final label is available 20 October at 06:00 UTC; the maximum eligible event and weather availability are 15:59 and 16:00 on 19 October. Declared observation lags remain 15/60 minutes. Archival schedules/availability assumptions limit real-time interpretation.

[Exact receipt](receipt.json) · [Wide SVG](cutoff.svg) · [Phone SVG](cutoff-mobile.svg) · [Generator](figure.py) · [Actual wide app](app-1440.png) · [True phone app](app-375.png).

The two bars share a zero to 100 percent scale. They encode rates with the same denominator 28; the raw target rate corresponds to 15 disrupted departures. No confidence interval or probability guarantee is implied. The archived four-team forecast-optimizer scenario is separately fixed at 16 UTC: DEN 2/LAS 2 and 42.4639505937339 hypothetical reduction minutes. It is not the benefit of changing the replay clock, measured savings or staffing advice. Baseline late15 recall 11.2% remains visible. No model or simulator was rerun.

## A second, explicitly different route

The bundled quickstart rebuild completed 109,423 selected-date flight records, 87,211 validated retrospective links and 64,312 hourly features, with 30 dbt tests. Those dates are discontinuous and are not the full-year population or this October 19 replay. Its [actual SQL](continuity.sql) joins one January 1 same-tail pair: ELP→SAN inbound 302 minutes late, then SAN→SMF outbound 54 minutes late; the actual ground gap is 37 minutes. These timestamps/associations do not identify the cause of either delay.

[Native CSV export](continuity.csv) · [same row as JSON](continuity.json). A fresh DuckDB connection reopens the CSV exactly. Reproduce with the pinned full repository, `uv run cascade quickstart --db /tmp/cascade-review.duckdb`, then run continuity.sql against that database using DuckDB. Do not overwrite a user's existing database. The source sample and legal notices remain in the full repository.

## Portable reader

The worked ZIP contains this case's receipt/SQL/CSV/figures, a dedicated BUNDLE.md, integrity checker and the exact buildless app with frozen replay data and local notices. Extract it; `python3 check.py` verifies all included hashes and compares the receipt to the frozen app snapshot plus the CSV to JSON. `python3 -m http.server 8080 --bind 127.0.0.1 --directory app` serves the actual current app. Use an available owned port, then open `/?day=2023-10-19&cutoff=16%3A00&airport=DEN&budget=4&policy=forecast_optimizer` on that origin. Forecast and final outcomes remain separate; reload preserves the URL state. The reader does not rerun the warehouse or infer new science from stored output.

Code MIT; BTS/NOAA-derived federal records and airportsdata/US-Atlas/font notices are preserved. No accounts, private records, source refresh or network data requests are needed. The existing live deployment is a separate older artifact; this local pass does not claim it was updated.
