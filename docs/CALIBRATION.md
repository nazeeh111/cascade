# Calibration date contract

`cascade.simulation.calibrate(connection, cutoff="2023-10-01")` supports ISO
dates/datetimes strictly after 2023-01-01 and at or before 2023-10-01 UTC.
Naive timestamps mean UTC; explicit offsets are converted to UTC. Later
cutoffs are rejected to protect the frozen study's test period.

All fitted outcome priors share the same completed-flight set. Departure,
arrival and linked inbound-arrival timestamps must be strictly more than
15 minutes before the cutoff. Scheduled departure must be strictly more than
14 hours before it. Missing/unmatured arrivals are excluded rather than
assuming that the schedule buffer proves completion.

The route-degree multiplier uses schedules strictly before the earlier of
the requested cutoff and 2023-07-01. This retains the narrower pre-July scope
of the original study while supporting earlier cutoffs. Schedules and actual
tail topology remain retrospective inputs, not a claim of live availability.

The cutoff repair adapts PR1's normalization/predicate correction and adds
arrival maturity, UTC/range validation, and the route-degree boundary.
It does not import PR1's regenerated scientific artifacts. The release
reports, model evaluation and published replay remain frozen historical
outputs tied to their original source hash. They have not been rerun or
relabeled as results of this implementation.

Run the offline contract and existing simulator checks with:

```sh
python -m pytest tests/test_calibration.py tests/test_simulation.py
```

These checks use in-memory fixtures, not archived flight data.
