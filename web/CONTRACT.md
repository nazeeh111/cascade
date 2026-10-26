# CASCADE replay data contract

Buildless app, served with `python -m http.server --directory web/dist`. It fetches `data/replay.json`; static source is index.html, styles.css, app.js. No external fonts, tiles, scripts, or paid services. Parent owns data export and publishing.

```json
{
  "meta": {
    "repository_url": "https://github.com/nazeeh111/cascade",
    "source_snapshot": "manifest-id-or-sha256",
    "model_run": "run-id",
    "forecast_model": "model-name",
    "sql_url": "https://...",
    "source_url": "https://...",
    "model_url": "https://...",
    "scenario_url": "https://...",
    "analysis_url": "https://...",
    "generated_at": "UTC ISO datetime",
    "flight_count": 123
  },
  "airports": [{"airport":"DEN","name":"Denver International","lat":39.86,"lon":-104.67,"timezone":"America/Denver"}],
  "days": [{
    "date":"2023-10-01",
    "label":"ORDINARY DAY",
    "kind":"ordinary",
    "frames":[{
      "cutoff":"2023-10-01T18:00:00Z",
      "airports":[{"airport":"DEN","scheduled":12,"observed_rate":0.2,"prediction":0.3,"target_rate":0.25,"backlog":5,"weather":{"temp_c":12,"wind_ms":3,"visibility_m":16000,"age_min":65}}],
      "edges":[{"origin":"DEN","dest":"LAS","flights":3}]
    }],
    "scenarios":[{"budget":2,"policy":"optimizer","baseline_delay_min":120,"scenario_delay_min":105,"benefit_min":15,"allocations":{"DEN":2},"cutoff":"2023-10-01T18:00:00Z","resource_description":"...","note":"..."}]
  }],
  "models":{"summary":"Evidence-based comparison statement","metrics":[{"model":"tabular","split":"test","mae":0.1,"rmse":0.15,"severe_recall":0.4,"runtime_seconds":1.2}]},
  "findings":[{"title":"...","question":"...","denominator":"...","finding":"...","limitation":"...","decision":"...","sql_url":"https://..."}],
  "provenance":[{"label":"Source snapshots","url":"https://..."}]
}
```

Numbers in the schema above illustrate types only, never production data. All production numerical content comes from parent export.

Required: `airports` and nonempty `days[].frames`. Forecast and outcome rates are fractions 0..1. Missing values must be `null`, not zero. `cutoff` timestamps must be UTC ISO. `scheduled` is the target denominator for each airport's next 2h. Weighted network rates exclude rows missing that specific rate. `backlog` is known schedule-minus-observed-departure proxy. Edge flight counts must be defined by generating SQL; edge endpoints must be focal airports. Edges may instead be supplied once per day or globally. Day scenarios may instead be global `scenarios` rows with date.

Default cutoff is 18:00 UTC when present; otherwise middle frame. Query parameters day, cutoff, airport, view restore a view. Map and airport rows are keyboard selectable; native controls support keyboard day/time/budget/policy changes. Forecast and final outcome modes remain visually and textually distinct. Playback pauses when tab is hidden. No unavailable observation is synthesized.

Design: paper and slate operational atlas, green / amber / coral stress bins, quiet geographic grid, compact monospace timing. All source links have safe URL handling and inserted data is escaped. Public source URL is configurable in metadata.
