# Warehouse grains and keys

All SQL timestamps are UTC `TIMESTAMP` unless a column is explicitly named local. Session timezone is UTC. `flight_date` is the BTS local origin reporting date. SQL is the source of analytical transformations; Python handles source transfer, timezone metadata, fitting, optimization and serialization.

| Relation | Grain and key | Contract |
| --- | --- | --- |
| raw_flights | One WN row in a frozen BTS monthly extract; may repeat a scheduled key | Raw strings preserved. Manifest reconciles source→filtered Parquet counts, cancellations, missing departure delays and signed delay sum. |
| raw_weather | One NOAA station report | Raw composite fields and report identity retained. |
| airports | IATA airport (`airport`) | All WN airports; eight focal flags and reviewed NOAA station IDs; IANA timezones. |
| carriers | Reporting carrier (`carrier`) | WN forecast scope plus reporting codes in the January all-carrier benchmark. |
| raw_carrier_cohorts / carrier_cohorts | (`carrier`, `airport`, `period`) | Source-reconciled January2023all-reporting-carrier counts and signed delay summaries at eight focal origins. This is selection-bias context, not a causal/full-year carrier ranking. |
| stg_flights | Scheduled flight (`flight_id`) | MD5 of date, reporting carrier, flight number, origin, destination and scheduled local departure. Exact duplicates collapse with multiplicity. Conflicting row hashes fail a test and are excluded. Snapshot refresh is atomic; corrections are never silently merged. |
| int_flight_times | `flight_id` | Source plus local→UTC conversion and explicit quality flags. Midnight 2400 rolls to the next day. Elapsed time determines destination date. DST gaps/folds and missing/invalid schedules are quarantined, not silently resolved. |
| flights | Valid `flight_id` | Signed nullable departure/arrival delays. Cancelled flights have no reconstructed completed movement; an independently recorded `observed_gate_out` remains available without consulting eventual cancellation status. Diverted arrivals are not treated as normal destination arrivals. |
| stg_weather | (`station`, `observed_at`) | Daily/monthly summaries excluded; deterministic report priority, element QC, missing sentinels→null. `available_at=observed_at+60 min` is an explicit assumption. |
| int_rotations | (`from_flight_id`, `to_flight_id`) | Immediate LEAD pair within actual reported tail; quality identifies gaps, overlaps, cancellations and diversions. |
| rotations | (`from_flight_id`, `to_flight_id`), each endpoint unique | Same airport; 20–360 min scheduled turn; observed nonnegative actual gap; completed nondiverted legs. Retrospective topology; domestic reporting can omit international legs. |
| int_airport_hours | (`airport`, `cutoff`) | Dense hourly UTC grid at eight airports. Horizon fully inside the source year. |
| int_hourly_events | (`airport`, `event_hour`) | Observed gate-outs with assumed 15 min observation latency bucketed to first usable cutoff. |
| int_cutoff_features | (`airport`, `cutoff`) | Schedule/history/backlog and retrospective next2h target. Recent 2/6h histories use availability-time windows. The backlog counts schedules without an observed gate-out, including unknown cancellations, never observed cancellation announcements. |
| network_edges | (`origin`, `dest`) | Frozen Jan–Jun scheduled-route counts and normalized inbound weights. No future actual tail edges. |
| features | (`airport`, `cutoff`) | As-of weather join with no fan-out; observations stale beyond 180 min become null. First 48h excluded. Local calendar, known schedule, observed history and upstream messages. Any unknown noncancelled departure status makes target_rate null; absent departures are not zero delay. |
| predictions | (`airport`, `cutoff`, `model`, `fold`) | Frozen chronological out-of-sample rate predictions and retrospective labels. |
| scenario_results | (`day`, `cutoff`, `policy`, parameters) | Hypothetical bounded resource experiment; actual-tail topology is retrospective. |

The final BTS schedule is assumed available before prediction; it is not a versioned historical schedule feed. Reconstructed event/NOAA availability is a simulation of feed latency, not proof of historical publication. Labels mature at least 14h after cutoff and later for very late observed departures. Cancellation announcement times are missing, so this maturity rule is an explicit retrospective assumption.

SQL tests enforce uniqueness, references, observation availability, join cardinality, rates, rotations, cancellations/diversions, and source reconciliation. Edge-case tests execute production SQL for midnight rollover, negative delay, missing outcomes, DST folds/gaps, duplicate/revised flights, weather QC and as-of publication boundaries.
