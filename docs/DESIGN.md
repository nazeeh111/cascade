# CASCADE interface refresh

The interface uses an aviation-atlas direction: a calm paper canvas, a dark geographic workspace, locally hosted Manrope typography, and clear green/amber/coral rate encoding. The map and the selected airport carry the visual emphasis; interpretation and provenance remain close to the results.

## Presentation and interaction

- A structured replay toolbar separates day selection, prediction cutoff and forecast/final-outcome mode. Versioned CSS/JS URLs refresh returning visitors' cached assets.
- Summary cards pair disruption rate with scheduled volume and the known backlog proxy. Their values still come from the same frozen scientific export.
- Census-derived state outlines replace the schematic background. Airport coordinates and the projection are unchanged. Selected routes have stronger contrast; rate colors and volume-driven node sizes retain their meaning.
- The airport panel includes a rate gauge, ranked airport controls and lagged weather context. Missing rates use a dashed unavailable gauge, rather than resembling a true zero.
- The timeline shades times after the selected cutoff and fills only available forecast segments. Future forecasts and final outcomes remain hidden in cutoff mode. Resize handling redraws the compact chart.
- Recovery allocation controls and baseline limitations remain explicit. The simulator's low 11.2% late15 recall, hindsight topology and noncausal resource effects are still visible.
- Findings show their question, result, decision implication and generating SQL. Denominators and limitations are available in clearly labeled disclosures. The model table marks the validation-selected model.

## Assets and accessibility

Manrope and US Atlas geography are served locally; licenses and SHA-256 provenance live in `web/dist/assets`. No external font, map service or JavaScript dependency is required. Geography can be regenerated with `python scripts/build_geography.py`. The rest of the app is buildless.

Native buttons/selects, keyboard-selectable map nodes, visible focus rings, larger airport row targets, explicit mode labels, an unavailable state, reduced-motion support and responsive reflow are retained. The wide model comparison uses its own horizontal scroll area on small screens. Browser verification covers desktop and narrow/mobile layouts, actual day/airport/cutoff changes, final-outcome separation, scenario policies, missing rates and finding disclosures.

Scientific data, model/scenario identities and generating SQL remain the v0.1.0 study. This refresh changes the interface and its geographic/typographic assets.

## Interaction refinement

The [interaction review](INTERACTION_REVIEW.md) records the complete replay, recovery, evidence and failure-state pass. Recovery selections now survive reload/history; playback retains keyboard focus; fixed budgets, empty intervals and midnight boundaries are explicit. Model names remain visible while narrow-screen metrics scroll. Secondary text uses #526b70, with measured contrast of 5.68:1 on white, 5.13:1 on paper and 4.78:1 on the pale green panel. This is a targeted contrast check, not a claim of a complete accessibility certification.

Browser assets use SHA-256-derived query fingerprints. Run `python scripts/version_web_assets.py` after CSS/JS edits; the publication build checks that they match.
