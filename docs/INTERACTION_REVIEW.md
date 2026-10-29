# CASCADE interaction review

Scope: refine the released aviation atlas while preserving the v0.1.0 scientific snapshots, SQL, model and simulator. Review began from clean revision 892c3e19b4905cfd3a89a9c1c7e14d05f7728f4a. Native browser checks were performed during 27-29 October 2026. An independent source review identified the focus/history/selection and empty-state gaps; the follow-up review found no remaining concrete regression after its nullable-frame guard was fixed.

| Screen / interaction | Observed verification |
| --- | --- |
| Replay days | All four days at 16:00 UTC, forecast/final modes: Nov 17 20.0/15.0%, Dec 16 14.8/19.2%, Oct 19 26.4/50.5%, Dec 24 34.0/45.1%. |
| Airports | All eight map controls select with Enter; sidebar selects DEN. Drilldown and selected airport stay synchronized. |
| Playback | Focused map airport survives seven redraws; playback stops at 23:00; Replay starts at 00:00; Home and endpoint disabling work. |
| Time interpretation | 23:00 to 01:00 explicitly marks next day; DEN at 00:00 UTC Dec 24 shows 17:00 MST Dec 23; October MDT and November/December MST checked. |
| URL / history | Back and Forward restore day/rate; reload restores recovery policy; day changes retain cutoff and a supported policy; malformed hash and invalid parameters do not hide the app. |
| Empty overnight interval | Zero scheduled departures remains unavailable rather than 0%; next scheduled interval moves Nov 17 08:00 to 10:00 and focuses the slider. |
| Recovery lab | All four strategy buttons synchronize dropdown, allocation, delay reduction and URL. Nov 17 reductions: 0.0, 39.9, 46.5 and 44.4 min. No intervention explicitly says no resources allocated. Scenario stays fixed at 16:00 when replay cursor changes. Single evaluated budget is read-only. |
| Evidence | All five finding disclosures open and close with Enter; denominators and limitations remain present. |
| Narrow model table | Keyboard arrow scrolling works; model names remain sticky while metrics scroll. |
| Scope / provenance | Four method articles and nine provenance links remain readable; mobile footer reaches Scope & limits. |
| Responsive layout | 320, 390, 768 and 1440px: page width matches viewport; replay, recovery, evidence, method, provenance and footer remain within bounds. |
| Loading / failure | Local controlled delayed-response and HTTP 503 fixtures show status/error screens. Retry successfully restores a real snapshot. These fixtures were never included in published assets. |
| Missing exported results | Local fixture with removed scenarios/findings/metrics shows explicit empty copy and disables unavailable controls. |

The test fixtures altered only task-local responses. Published scientific data remains the original real-data export. Targeted text contrast checks cover the muted text token on its three common light backgrounds. No claim of every assistive technology or browser combination is made.

Regression checks: 32 Python tests and the full-data 2,073-check verifier passed; JavaScript syntax, content fingerprints, static packaging and whitespace checks passed. Exact published revision and CI/deployment evidence are retained in the task release-evidence folder.
