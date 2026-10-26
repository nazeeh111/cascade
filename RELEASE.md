# CASCADE v0.1.0

Released 26 October 2026. This release reconstructs 2023 Southwest domestic flight disruption, forecasts the next two hours at eight airports, and evaluates a bounded hypothetical recovery experiment.

- [Public replay](https://cascade-flight-intelligence.nazeeh1.chatgpt.site)
- [Public source and licensed real-data quickstart](https://github.com/nazeeh111/cascade)
- [Versioned release and source/data archives](https://github.com/nazeeh111/cascade/releases/tag/v0.1.0)
- [Fresh-runtime CI evidence](https://github.com/nazeeh111/cascade/actions/runs/40401916903)
- [Current release checks](https://github.com/nazeeh111/cascade/actions)

## Verified scope

The full local warehouse contains 1,438,465 WN flights, 90,084 deduplicated hourly weather observations, 69,688 feature rows and 1,160,285 validated retrospective aircraft links. Its 13 dbt models and 30 data tests passed. The local file/data verifier passed 2,073 checks against the full warehouse; 32 Python regression tests passed.

Public CI checked out source revision `847634e525e33b4e7d1ba61a96cdd0d9d4783b72`, installed pinned dependencies in a fresh Python 3.12 Ubuntu environment, passed all 32 Python tests, rebuilt 109,423 real flights with all 30 dbt data tests, passed 507 portable evidence/snapshot checks, checked browser JavaScript syntax and built the static deployment. The portable run deliberately lacks the full annual database; it does not claim to repeat the full local run. Subsequent release documentation does not alter scientific code, source snapshots or browser assets.

The public host serves all eight source assets without authentication. JavaScript, CSS and JSON match the checked source response bytes. HTML matches after removing only the host-injected Cloudflare challenge script. Per-asset hashes and anonymous HTTP checks are in [reports/public_http.json](reports/public_http.json). The application was deployed through Sites version 1 from the tested source revision; public access was confirmed independently of deployment status. Later versions retain the identical application asset hashes while sealing release documentation.

Live browser checks covered an ordinary held-out day, the high-disruption 24 December day, airport selection, synchronized cutoff movement, explicit final-outcome mode and allocation strategy changes, with no browser console errors. The current source was also inspected at 390-pixel mobile width, with no horizontal document overflow. Saved views are in [docs/images](docs/images).

Independent audit recomputed every metric in 15 fold/model combinations, matched all 768 exported airport rows and 96 edge frames, and rebuilt 16 showcase-day policy replays using an independent timestamp reference. All 29,580 aircraft-readiness checks and per-flight results matched. Perturbing unavailable future outcomes changed none of 30,380 simulated predictions. [Review and fixes](reports/REVIEW.md).

## Scientific identities

| Artifact | Identity |
| --- | --- |
| Source manifest SHA-256 | `14d51bf7707dec51f348f943a35ec4b7c10feff92536d156921623146eab8e84` |
| Model | `model-2023-3285fe6404fb` |
| Scenario | `scenario-2023-3fe0a2e6fd1b` |
| Ordered labeled features SHA-256 | `d8cfbf428deb045bbd4c16a4c6a62cd65b91af0e1ebc87762186d841b18e8dec` |

The final weather cleanup excludes SOD/SOM daily/monthly summaries. The affected 2,892 airport-hour frames contain no scheduled targets; the labeled-feature fingerprint remains unchanged. Gate-outs on eventually cancelled flights remain observable independently of final cancellation status.

## Reproduce and interpret

Follow the [README quickstart](README.md#reproduce). The bundled data comprise 16 attributed real Parquet partitions totaling 2,609,720 bytes. No source download or API key is needed. The full-year rebuild uses the documented public BTS and NOAA downloads; measured full-run stage timings and original-byte hashes remain published. Release archives include the source and quickstart; the separate data archive includes its manifest and license notices. SHA-256 checksums accompany downloadable assets.

The tabular model remains the validation-selected forecast. The graph residual improves final held-out MAE over the temporal residual by 0.175 percentage points, a restricted-network descriptive result. The simulator's late15 recall is only 11.2%, with 11.29-minute baseline MAE. Actual-tail scenario topology uses hindsight. Hypothetical team effects, archival availability assumptions, missing international/crew/maintenance/passenger constraints and cancellation censoring limit interpretation. Simulated minutes are not measured causal savings or airline-ready advice. These limitations are retained in the interface, model card and evaluation reports.

Code is MIT; federal public records and airport metadata carry the notices in [DATA_LICENSE.md](DATA_LICENSE.md). No separately billed service is required to reproduce the work.
