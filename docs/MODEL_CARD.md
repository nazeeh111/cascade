# CASCADE forecasting and scenario model card

## The operational question

At an hourly UTC cutoff, what fraction of Southwest departures scheduled from each focal airport in the next two hours will be cancelled or depart at least 15 minutes late? The denominator is scheduled departures in `[cutoff, cutoff + 2 hours)`; airport-hours with no scheduled departures are excluded. One example is an airport at 16:00 UTC predicting the scheduled 16:00–18:00 UTC cohort. The model forecasts a disruption **rate**, not individual passenger delays or the probability of an airport-wide severe event.

The focal airports are BWI, DAL, DEN, HOU, LAS, MDW, OAK and PHX. Results describe this selected carrier/network and reporting year, not all US aviation.

## What could be known at cutoff

The warehouse computes substantive features in SQL. The Python modeling layer reads the explicit query embedded in `reports/model_evaluation.json`. `availability_audit` rejects any weather or event availability timestamp after cutoff.

| Input | Availability rule and limitation |
| --- | --- |
| Scheduled departures over the next two hours, local hour, weekday, month, airport | Final BTS schedules are assumed known. BTS does not supply the historical schedule snapshots needed to verify that assumption. |
| Recent observed departure disruption rate, counts and unresolved scheduled backlog | Gate-out events become observable 15 minutes after the actual departure. This is an assumed feed latency, not a measured BTS real-time service. A backlog item is an unresolved scheduled flight; it does not assert a known cancellation. |
| Temperature, wind, visibility and observation age | Observation time plus an assumed 60-minute publication lag must be no later than cutoff. Archival revisions and true operational feed latency remain unknown. |
| Upstream airport rates | Apply a fixed pre-July scheduled-route graph to other airports' cutoff-safe lagged observations. The graph model sees aggregated neighbor messages, not future aircraft assignments. |

Realized future weather, target counts/outcomes, delay-cause fields, aircraft tails and future actual aircraft assignments never enter the feature matrix. Aircraft rotations are separately reconstructed for retrospective analysis and scenario topology.

Cancellation announcement timestamps do not exist in this extract. The 270 source flights that eventually cancelled after a recorded gate-out retain that gate-out as an observable event; the future cancellation flag cannot erase history. The separate completed-movement field remains null for cancelled flights. Final cancellations enter the target but are not treated as a known contemporaneous feature. Missing actual departure or arrival delay is not filled with zero. The departure-rate model uses negative early-departure values only through the correct `>=15` comparison; early departures remain intact in the warehouse.

Labels mature no earlier than 14 hours after cutoff and later when a target gate-out is exceptionally late, including an eventual cancellation. Every fit requires `label_available_at < fit_boundary`. The 14-hour assumption makes ordinary cancellation cohorts usable only retrospectively; it is not a verified cancellation notification time.

## Evaluation protocol

Two expanding chronological validation folds evaluate August and September 2023. HGBT settings are selected from two fixed configurations by mean validation MAE. The final October–December holdout uses a fit frozen before October 1; no final-test outcomes select the model or its parameters. Reported prediction rows retain model, cutoff, airport, fold, split, predicted rate, observed rate and target denominator.

Five models are compared:

1. **Seasonal baseline:** airport × local hour × weekday mean rate, smoothed with ten airport-prior observations. Unseen cohorts fall back to the airport mean.
2. **Rolling baseline:** most recent observed two-hour departure disruption rate, with seasonal fallback when no departure was observable.
3. **Tabular:** histogram gradient boosting with airport indicator columns, calendar, scheduled demand, observed history, backlog and weather. This model receives no network feature.
4. **Temporal residual:** the tabular prediction plus a regularized linear correction from local two/six-hour observations and normalized backlog. Corrections are learned from earlier-month **out-of-time predictions**, not residuals from fitting the same examples.
5. **Graph residual:** the same tabular base and chronological residual examples, adding upstream-minus-local and upstream-minus-base messages from the fixed directed schedule graph. This is a compact linear temporal graph model. It does not require a large neural network or PyTorch Geometric to answer whether network information adds value.

The graph contribution is the paired difference between temporal-residual and graph-residual MAE. A positive reduction favors the graph model; a negative reduction is retained as a negative finding. A circular seven-day moving-block bootstrap with 1,000 draws gives a descriptive interval that preserves short-range dependence. A limited or inconclusive effect does not justify a superiority claim.

MAE and RMSE are in fraction-of-departures units; multiply by 100 for percentage points. Both airport-hour MAE and departure-count-weighted MAE are reported. Severe-event recall and precision use an observed/predicted rate threshold of 0.5. Calibration compares mean predicted versus mean observed rate in ten bins; this is rate calibration, not binary event-probability calibration. Separate minimum-denominator sensitivities retain only cohorts with at least 5 or 10 scheduled departures.

The numerical model runtime uses one worker because local parallel coordination proved expensive; model configurations, seeds and evaluation are unchanged. Prediction persistence is one validated Arrow-to-SQL transaction that preserves the prior table until commit. Fit/predict wall time is reported per model. Residual-model time includes its tabular fit and chronological out-of-time residual fits. These times overlap in work and must not be summed. Full ordered feature rows and implementation bytes are hashed into the model run identity. The full rerun regenerates predictions; the public demo reads those frozen predictions.

## Recovery experiment

The scenario layer is explicitly a **retrospective, actual-tail-topology experiment**. It conditions on validated observed rotations, so it is not a deployable aircraft recovery plan. The allocator itself uses only the selected cutoff forecast, schedules assumed known, and training-period route-degree weights. Future realized delays and future weather do not enter allocator scores.

At 16:00 UTC on every held-out day, replay the remaining eight-hour schedule. Compare no service, schedule-volume priority, observed-backlog priority and a forecast-aware integer optimizer. The optimizer has four hypothetical ground-recovery teams; each airport may receive at most two. Each team serves the first two scheduled departures in the next two hours and can remove at most 15 positive simulated minutes from each served flight. All counts and capacities are explicit. A scheduled leg that eventually cancels still consumes a planned service slot, preventing hindsight from selecting only completed flights.

A completed leg's departure delay is the maximum of a training-calibrated external-delay floor and a hard incoming-aircraft readiness floor after scheduled turnaround slack. A service can reduce only the external floor by at most 15 minutes; it cannot move a departure before its simulated inbound arrival plus the assumed turn. Positive delay never falls below zero. Arrival delay adds the training route's median en-route recovery. A 12-hour schedule lookback initializes inbound state. Actual arrivals seed state only after the 15-minute observation lag. For an in-flight inbound, a known departure delay plus training route recovery predicts arrival; otherwise training priors initialize it. Future actual arrivals and departures never seed the replay. Already observed departures cannot receive a service slot.

Inherited readiness is enforced fully. Source-time inconsistencies are excluded from validated rotations and simulator calibration while remaining visible in the warehouse quality report. The baseline external component is the training airport/local-hour 65th percentile after subtracting the bounded inherited component. Forecast-rate/training-rate shock scaling is clipped to `[0.25,3]`. Holding the two-hour forecast constant over the eight-hour scenario is a scenario assumption, not a claim of eight-hour forecast accuracy.

Baseline replay is checked against completed held-out flights, reporting flight count, MAE, RMSE, bias, correlation and delay-15 recall. Cancellations and diversions are excluded from delay-minute outcomes and reported separately; there is no claim to recover cancelled flights. The baseline error must be read alongside every resource comparison. Sensitivity varies assumed minimum turnaround over 25, 35 and 45 minutes and external-shock multiplier over 0.75, 1.0 and 1.25, while preserving hard aircraft readiness.

Benefits are differences **inside this deterministic simulator**. They are not measured causal savings, airline-ready recommendations or staffing prescriptions. No passenger, crew, maintenance, gate, airspace, safety or monetary information is invented. Allocation feasibility covers the stated small hypothetical budget, not all real airline constraints.

## Reproduction and evidence

Run the repository's data/warehouse command first, followed by `python -m cascade.modeling` and `python -m cascade.simulation` from the repository root. The CLI wraps these steps. Machine-readable results are `reports/model_evaluation.json` and `reports/scenarios.json`; the latter links to the exact model run. `predictions` and `scenario_results` retain row-level audit evidence in DuckDB.

Tests cover rejected future observations/events, exclusion of target/tail fields from the feature matrix, seasonal fallback, severe/calibration denominators, slack absorption, optimizer budget/capacity constraints, nonnegative resource effects, consumed cancellation slots and rejection of future arrival seeds. These tests check contracts and consequential boundaries; actual held-out evaluation is separately recorded in the reports.
