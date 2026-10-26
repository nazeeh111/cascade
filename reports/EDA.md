# CASCADE: SQL investigation

WN domestic reporting-carrier flights, 2023; eight focal airports. A separate January all-reporting-carrier aggregate supplies carrier-selection context. No passenger or international-leg inference.

No filling missing delays with zero; incomplete next-2h labels remain null. Cancellation is a distinct event, not zero delay.

## Disruption differs within the same carrier network

**Question:** Which focal airports had the highest and lowest 2023 disruption rates?

**Denominator:** 555,335 WN departures from eight focal airports; denominator excludes unknown noncancelled departure status.

**Finding:** DEN recorded 35.9% late15-or-cancelled departures (96,164 scheduled), versus 22.1% at HOU (50,884).

**Limitation:** One carrier and reporting year; route mix, schedule and weather differ. This ranking does not measure airport management quality.

**Decision:** Use airport-specific baselines and compare within cohorts before allocating hypothetical resources.

Generating SQL: [sql/analysis/airport_cohorts.sql](../sql/analysis/airport_cohorts.sql)

## Aircraft continuity marks association, not cause

**Question:** Is a late inbound associated with a delayed next departure on validated aircraft chains?

**Denominator:** 1,160,285 immediate, validated same-tail domestic pairs with observed inbound and outbound delays; cancelled/diverted/gapped chains excluded.

**Finding:** Next departures were late15 in 80.4% of pairs after a late15 inbound, versus 14.0% after an inbound under15 minutes late.

**Limitation:** Retrospective actual tails, shared weather/airport conditions, selection on completed legs and missing international legs prevent a causal interpretation.

**Decision:** Use validated chains to investigate plausible propagation and test simulator assumptions; keep final tails out of forecasts.

Generating SQL: [sql/analysis/rotation_associations.sql](../sql/analysis/rotation_associations.sql)

## Averages conceal long tails and missing outcomes

**Question:** How much information is lost by reducing delay to a mean or filling missing arrival delays with zero?

**Denominator:** 1,438,465 deduplicated WN scheduled flights with departure-time checks passed; percentiles use non-null departure delay only.

**Finding:** Departure delay median was 1 min, mean 11.7 min, and 99th percentile 147 min. 592,247 departures were early; 17,227 arrival delays were unobserved.

**Limitation:** Cancelled and diverted flights censor arrival delay; extreme delays contribute heavily to the mean. No passenger-weighted effect is available.

**Decision:** Preserve signed early departures, report tails and cancellations alongside delay, and leave missing arrival outcomes null.

Generating SQL: [sql/analysis/overview.sql](../sql/analysis/overview.sql)

## Weather is useful context with confounding

**Question:** How does departure disruption differ under recorded higher-wind conditions?

**Denominator:** 24,140 focal departures with latest available wind ≥8 m/s, versus 524,184 other observed-weather departures; visibility <3km has a separate cohort.

**Finding:** Higher-wind cohort disruption was 41.2%, versus 28.8% in the other-observed cohort.

**Limitation:** As-of hourly observations assume 60-minute latency; QC-filtered readings can be absent. Airport, season and traffic confound the association.

**Decision:** Include observed weather as a forecast feature, then judge incremental performance on future dates rather than treating association as causal.

Generating SQL: [sql/analysis/weather_associations.sql](../sql/analysis/weather_associations.sql)

## The carrier scope is a deliberate selection

**Question:** How much of the January reporting-carrier traffic at the focal airports does the WN study cover?

**Denominator:** 80,786 scheduled departures in the January2023BTS reporting-carrier extract at the eight focal origins, including cancellations.

**Finding:** WN accounts for 43,468 of those departures (53.8%). The remaining reporting carriers have different airport, route and schedule mixes.

**Limitation:** January only; selected reporting carriers and origins, not all US operations or passenger market share. The comparison cannot isolate an airline effect.

**Decision:** Interpret the forecast as WN-network evidence and check carrier/airport composition before transferring findings to a different operation.

Generating SQL: [sql/analysis/carrier_cohorts.sql](../sql/analysis/carrier_cohorts.sql)

## Selection, censoring and negative evidence

All-carrier monthly source counts and WN scoped counts are reconciled in the source manifest. The eight-airport subset is compared with other WN origins in `monthly.sql`. Forecasting uses one carrier; the separate January carrier/airport benchmark diagnoses selection bias without isolating carrier effects. Local-hour/weekday/month cohorts are explicit in `local_seasonality.sql`.

Weather groups include missing/stale observations. Rotations exclude airport discontinuity, cancelled/diverted legs, overlaps, missing actual times and scheduled turns outside 20–360 minutes. These filters select completed operations, so chain associations do not describe the worst censored disruptions. The path examples are plausible chains, not proven delay transmission.

## Complete rerunnable tables

### airport_cohorts

Query: [`airport_cohorts.sql`](../sql/analysis/airport_cohorts.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "airport": "DEN",
    "n": 96164,
    "disrupted_n": 34550,
    "cancelled_n": 1286,
    "unknown_n": 0,
    "mean_dep_delay": 17.304503156319488,
    "missing_arr_n": 1470
  },
  {
    "airport": "BWI",
    "n": 71573,
    "disrupted_n": 23974,
    "cancelled_n": 663,
    "unknown_n": 0,
    "mean_dep_delay": 16.399069505145917,
    "missing_arr_n": 824
  },
  {
    "airport": "LAS",
    "n": 86582,
    "disrupted_n": 28419,
    "cancelled_n": 1013,
    "unknown_n": 0,
    "mean_dep_delay": 15.255278131535594,
    "missing_arr_n": 1189
  },
  {
    "airport": "MDW",
    "n": 77154,
    "disrupted_n": 22116,
    "cancelled_n": 1049,
    "unknown_n": 0,
    "mean_dep_delay": 13.570049134238944,
    "missing_arr_n": 1232
  },
  {
    "airport": "PHX",
    "n": 62780,
    "disrupted_n": 16399,
    "cancelled_n": 437,
    "unknown_n": 0,
    "mean_dep_delay": 11.568416157534356,
    "missing_arr_n": 567
  },
  {
    "airport": "DAL",
    "n": 71772,
    "disrupted_n": 18170,
    "cancelled_n": 1088,
    "unknown_n": 0,
    "mean_dep_delay": 11.558972037961613,
    "missing_arr_n": 1239
  },
  {
    "airport": "OAK",
    "n": 38426,
    "disrupted_n": 9157,
    "cancelled_n": 289,
    "unknown_n": 0,
    "mean_dep_delay": 10.251409096867217,
    "missing_arr_n": 342
  },
  {
    "airport": "HOU",
    "n": 50884,
    "disrupted_n": 11251,
    "cancelled_n": 356,
    "unknown_n": 0,
    "mean_dep_delay": 9.728875608501207,
    "missing_arr_n": 457
  }
]
```

### carrier_cohorts

Query: [`carrier_cohorts.sql`](../sql/analysis/carrier_cohorts.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "carrier": "WN",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 5494,
    "disrupted_n": 1384,
    "cancelled_n": 76,
    "unknown_n": 0,
    "disruption_rate": 0.2519111758281762,
    "mean_dep_delay": 12.981177338992435,
    "p99_dep_delay": 202.0
  },
  {
    "carrier": "NK",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 505,
    "disrupted_n": 142,
    "cancelled_n": 10,
    "unknown_n": 0,
    "disruption_rate": 0.2811881188118812,
    "mean_dep_delay": 19.141414141414142,
    "p99_dep_delay": 199.04000000000008
  },
  {
    "carrier": "DL",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 396,
    "disrupted_n": 47,
    "cancelled_n": 2,
    "unknown_n": 0,
    "disruption_rate": 0.11868686868686869,
    "mean_dep_delay": 3.8477157360406093,
    "p99_dep_delay": 107.76999999999992
  },
  {
    "carrier": "UA",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 261,
    "disrupted_n": 35,
    "cancelled_n": 1,
    "unknown_n": 0,
    "disruption_rate": 0.13409961685823754,
    "mean_dep_delay": 4.480769230769231,
    "p99_dep_delay": 157.0400000000011
  },
  {
    "carrier": "AA",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 229,
    "disrupted_n": 42,
    "cancelled_n": 7,
    "unknown_n": 0,
    "disruption_rate": 0.18340611353711792,
    "mean_dep_delay": 9.054054054054054,
    "p99_dep_delay": 203.84999999999988
  },
  {
    "carrier": "F9",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 184,
    "disrupted_n": 49,
    "cancelled_n": 2,
    "unknown_n": 0,
    "disruption_rate": 0.266304347826087,
    "mean_dep_delay": 16.032967032967033,
    "p99_dep_delay": 208.51999999999998
  },
  {
    "carrier": "YX",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 89,
    "disrupted_n": 9,
    "cancelled_n": 3,
    "unknown_n": 0,
    "disruption_rate": 0.10112359550561797,
    "mean_dep_delay": 2.453488372093023,
    "p99_dep_delay": 186.50000000000006
  },
  {
    "carrier": "B6",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 86,
    "disrupted_n": 18,
    "cancelled_n": 2,
    "unknown_n": 0,
    "disruption_rate": 0.20930232558139536,
    "mean_dep_delay": 2.447058823529412,
    "p99_dep_delay": 98.15999999999983
  },
  {
    "carrier": "9E",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 56,
    "disrupted_n": 11,
    "cancelled_n": 1,
    "unknown_n": 0,
    "disruption_rate": 0.19642857142857142,
    "mean_dep_delay": 7.054545454545455,
    "p99_dep_delay": 98.82000000000002
  },
  {
    "carrier": "MQ",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 51,
    "disrupted_n": 11,
    "cancelled_n": 0,
    "unknown_n": 0,
    "disruption_rate": 0.21568627450980393,
    "mean_dep_delay": 12.490196078431373,
    "p99_dep_delay": 215.0
  },
  {
    "carrier": "AS",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 31,
    "disrupted_n": 8,
    "cancelled_n": 0,
    "unknown_n": 0,
    "disruption_rate": 0.25806451612903225,
    "mean_dep_delay": 16.225806451612904,
    "p99_dep_delay": 230.0999999999999
  },
  {
    "carrier": "G4",
    "airport": "BWI",
    "period": "2023-01",
    "scheduled_n": 11,
    "disrupted_n": 1,
    "cancelled_n": 0,
    "unknown_n": 0,
    "disruption_rate": 0.09090909090909091,
    "mean_dep_delay": 2.1818181818181817,
    "p99_dep_delay": 42.70000000000002
  },
  {
    "carrier": "WN",
    "airport": "DAL",
    "period": "2023-01",
    "scheduled_n": 5823,
    "disrupted_n": 1471,
    "cancelled_n": 310,
    "unknown_n": 0,
    "disruption_rate": 0.2526189249527735,
    "mean_dep_delay": 12.245286439448876,
    "p99_dep_delay": 177.70000000000073
  },
  {
    "carrier": "DL",
    "airport": "DAL",
    "period": "2023-01",
    "scheduled_n": 107,
    "disrupted_n": 27,
    "cancelled_n": 1,
    "unknown_n": 0,
    "disruption_rate": 0.2523364485981308,
    "mean_dep_delay": 21.0,
    "p99_dep_delay": 328.70000000000016
  },
  {
    "carrier": "AS",
    "airport": "DAL",
    "period": "2023-01",
    "scheduled_n": 56,
    "disrupted_n": 13,
    "cancelled_n": 3,
    "unknown_n": 0,
    "disruption_rate": 0.23214285714285715,
    "mean_dep_delay": 2.358490566037736,
    "p99_dep_delay": 77.27999999999997
  },
  {
    "carrier": "WN",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 7263,
    "disrupted_n": 2855,
    "cancelled_n": 382,
    "unknown_n": 0,
    "disruption_rate": 0.3930882555417871,
    "mean_dep_delay": 19.1609529343405,
    "p99_dep_delay": 174.0
  },
  {
    "carrier": "UA",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 7125,
    "disrupted_n": 2078,
    "cancelled_n": 41,
    "unknown_n": 0,
    "disruption_rate": 0.29164912280701755,
    "mean_dep_delay": 19.284525320919734,
    "p99_dep_delay": 212.0
  },
  {
    "carrier": "OO",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 4198,
    "disrupted_n": 1256,
    "cancelled_n": 265,
    "unknown_n": 0,
    "disruption_rate": 0.2991900905192949,
    "mean_dep_delay": 21.45863900834809,
    "p99_dep_delay": 283.44000000000005
  },
  {
    "carrier": "F9",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 1644,
    "disrupted_n": 651,
    "cancelled_n": 58,
    "unknown_n": 0,
    "disruption_rate": 0.395985401459854,
    "mean_dep_delay": 22.49182389937107,
    "p99_dep_delay": 218.5499999999995
  },
  {
    "carrier": "DL",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 1006,
    "disrupted_n": 287,
    "cancelled_n": 14,
    "unknown_n": 0,
    "disruption_rate": 0.2852882703777336,
    "mean_dep_delay": 20.869959677419356,
    "p99_dep_delay": 295.0600000000011
  },
  {
    "carrier": "AA",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 693,
    "disrupted_n": 186,
    "cancelled_n": 15,
    "unknown_n": 0,
    "disruption_rate": 0.2683982683982684,
    "mean_dep_delay": 21.708823529411763,
    "p99_dep_delay": 308.84000000000015
  },
  {
    "carrier": "NK",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 223,
    "disrupted_n": 58,
    "cancelled_n": 7,
    "unknown_n": 0,
    "disruption_rate": 0.2600896860986547,
    "mean_dep_delay": 20.199074074074073,
    "p99_dep_delay": 447.599999999999
  },
  {
    "carrier": "B6",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 153,
    "disrupted_n": 58,
    "cancelled_n": 4,
    "unknown_n": 0,
    "disruption_rate": 0.3790849673202614,
    "mean_dep_delay": 27.335570469798657,
    "p99_dep_delay": 281.52000000000027
  },
  {
    "carrier": "AS",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 143,
    "disrupted_n": 46,
    "cancelled_n": 0,
    "unknown_n": 0,
    "disruption_rate": 0.32167832167832167,
    "mean_dep_delay": 12.41958041958042,
    "p99_dep_delay": 158.60000000000025
  },
  {
    "carrier": "G4",
    "airport": "DEN",
    "period": "2023-01",
    "scheduled_n": 12,
    "disrupted_n": 6,
    "cancelled_n": 0,
    "unknown_n": 0,
    "disruption_rate": 0.5,
    "mean_dep_delay": 18.75,
    "p99_dep_delay": 99.85000000000004
  }
]
```

### chains

Query: [`chains.sql`](../sql/analysis/chains.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "flight_date": "2023-12-24",
    "tail": "N257WN",
    "flight1": "4ca6eb9d0be50da7a1fe74941c2b034a",
    "flight2": "3f8bf04e0898dcec5f77021151c7ac6d",
    "flight3": "099dea0051fc96b43622593aa753aac1",
    "path": "MCI \u2192 MDW \u2192 ALB \u2192 BWI",
    "dep1": 309.0,
    "arr1": 425.0,
    "dep2": 633.0,
    "arr2": 639.0,
    "dep3": 635.0,
    "turn1": 55,
    "turn2": 40
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N565WN",
    "flight1": "3a2d1b481765fdd9c04de90a829fa986",
    "flight2": "a99bb63cf4316623ba6945af2fbc9d2e",
    "flight3": "7a3113732ad13d11a1e53eb6a90987f6",
    "path": "MDW \u2192 MCI \u2192 LGA \u2192 ATL",
    "dep1": 402.0,
    "arr1": 405.0,
    "dep2": 420.0,
    "arr2": 442.0,
    "dep3": 459.0,
    "turn1": 40,
    "turn2": 40
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N219WN",
    "flight1": "c09c2e90b61e6a32734136c3d4ca185c",
    "flight2": "20fa6169d35e123fc69e5bf6234dcca2",
    "flight3": "831450af5af158555eaa8a8440c684a5",
    "path": "MSP \u2192 MDW \u2192 OMA \u2192 HOU",
    "dep1": 275.0,
    "arr1": 399.0,
    "dep2": 425.0,
    "arr2": 419.0,
    "dep3": 442.0,
    "turn1": 60,
    "turn2": 40
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N1808U",
    "flight1": "06259384f652d4d0ce68c2b44149c951",
    "flight2": "07c2fd90bd3b7038f7a0fbdf6526ba01",
    "flight3": "866fc43e13ee733cbb07e7760accf93a",
    "path": "MDW \u2192 CLE \u2192 BNA \u2192 TPA",
    "dep1": 379.0,
    "arr1": 378.0,
    "dep2": 372.0,
    "arr2": 364.0,
    "dep3": 180.0,
    "turn1": 45,
    "turn2": 245
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N8301J",
    "flight1": "c86bb6ff64b1d61fbd2b1efef73da401",
    "flight2": "ae168951cd293eace29daf1f48829c2f",
    "flight3": "a926357f69292b9ea35c49703949e4bc",
    "path": "MDW \u2192 SDF \u2192 BWI \u2192 CHS",
    "dep1": 390.0,
    "arr1": 374.0,
    "dep2": 402.0,
    "arr2": 390.0,
    "dep3": 261.0,
    "turn1": 45,
    "turn2": 350
  },
  {
    "flight_date": "2023-10-22",
    "tail": "N8801Q",
    "flight1": "76af498d9b29b98cc961b2933f0a24ed",
    "flight2": "a555265f70f83fa384c314eb4bd6afe5",
    "flight3": "5f65fc164fee0d6089e4fd0490de8325",
    "path": "ABQ \u2192 DAL \u2192 HOU \u2192 ATL",
    "dep1": 391.0,
    "arr1": 373.0,
    "dep2": 127.0,
    "arr2": 123.0,
    "dep3": 120.0,
    "turn1": 320,
    "turn2": 55
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N8694E",
    "flight1": "642ed8407cd1e7d0d55d00cdc9b57e70",
    "flight2": "78fc909ef585f67684e60badd7e92d44",
    "flight3": "40a046672357255035da19ff6812b0e8",
    "path": "MDW \u2192 STL \u2192 DAL \u2192 COS",
    "dep1": 382.0,
    "arr1": 369.0,
    "dep2": 383.0,
    "arr2": 391.0,
    "dep3": 506.0,
    "turn1": 45,
    "turn2": 55
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N1808U",
    "flight1": "07c2fd90bd3b7038f7a0fbdf6526ba01",
    "flight2": "866fc43e13ee733cbb07e7760accf93a",
    "flight3": "5b2363e1444cc2a21619dfac64cf242d",
    "path": "CLE \u2192 BNA \u2192 TPA \u2192 IND",
    "dep1": 372.0,
    "arr1": 364.0,
    "dep2": 180.0,
    "arr2": 183.0,
    "dep3": 169.0,
    "turn1": 245,
    "turn2": 50
  },
  {
    "flight_date": "2023-10-24",
    "tail": "N447WN",
    "flight1": "e75d45ebc3069fa0679bc45bee6fa5e6",
    "flight2": "73e0919e5f4fbedd7ad84fd4052c2c58",
    "flight3": "8ad6c3a36e24718998b3dffae61b5ead",
    "path": "DAL \u2192 IAH \u2192 LAS \u2192 SAN",
    "dep1": 325.0,
    "arr1": 364.0,
    "dep2": 364.0,
    "arr2": 347.0,
    "dep3": 323.0,
    "turn1": 40,
    "turn2": 60
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N8647A",
    "flight1": "cf69d70b348f9bbfbb1dc60fe8d436c4",
    "flight2": "61ca099e4c7b161ac8842364ed79aa5a",
    "flight3": "b94bc9e19ef6b3170217dc825db1fb78",
    "path": "MDW \u2192 STL \u2192 ATL \u2192 PBI",
    "dep1": 359.0,
    "arr1": 349.0,
    "dep2": 368.0,
    "arr2": 392.0,
    "dep3": 94.0,
    "turn1": 55,
    "turn2": 355
  },
  {
    "flight_date": "2023-10-29",
    "tail": "N7842A",
    "flight1": "2ee46ff8b8f9e17a642422cbcb2f5445",
    "flight2": "9dad0aaf7fb00729d171b960103a2a28",
    "flight3": "765726f559fc340ef512d4cd2056a76b",
    "path": "DEN \u2192 SAN \u2192 SJC \u2192 SNA",
    "dep1": 313.0,
    "arr1": 347.0,
    "dep2": 347.0,
    "arr2": 336.0,
    "dep3": 338.0,
    "turn1": 35,
    "turn2": 35
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N8322X",
    "flight1": "1e9f31a567d5776db16671a7530fb916",
    "flight2": "a0f876f9f3a1a8f43998c0cb3751db5e",
    "flight3": "56675b048128110483cb6f6ba7c86d3b",
    "path": "MDW \u2192 ATL \u2192 AUS \u2192 ELP",
    "dep1": 323.0,
    "arr1": 344.0,
    "dep2": 370.0,
    "arr2": 370.0,
    "dep3": 451.0,
    "turn1": 45,
    "turn2": 45
  },
  {
    "flight_date": "2023-12-03",
    "tail": "N934WN",
    "flight1": "cf7e33f76ed985626d45c55af559f248",
    "flight2": "3d3b3a72c5038144b3097e5e190bb22c",
    "flight3": "69889d45cd296aa1ac9e3dfa93817671",
    "path": "AUS \u2192 SAN \u2192 PHX \u2192 MDW",
    "dep1": 364.0,
    "arr1": 341.0,
    "dep2": 279.0,
    "arr2": 276.0,
    "dep3": 74.0,
    "turn1": 120,
    "turn2": 235
  },
  {
    "flight_date": "2023-10-22",
    "tail": "N8801Q",
    "flight1": "3b574a273b57ad93beb2935822ee5e2d",
    "flight2": "76af498d9b29b98cc961b2933f0a24ed",
    "flight3": "a555265f70f83fa384c314eb4bd6afe5",
    "path": "AUS \u2192 ABQ \u2192 DAL \u2192 HOU",
    "dep1": 338.0,
    "arr1": 340.0,
    "dep2": 391.0,
    "arr2": 373.0,
    "dep3": 127.0,
    "turn1": 45,
    "turn2": 320
  },
  {
    "flight_date": "2023-10-12",
    "tail": "N8623F",
    "flight1": "9123b52cb7f7528778ef71b22ccd8f1c",
    "flight2": "b3b322bf702e5cf69de2ef4b9bd23c89",
    "flight3": "8f3e22c492b560836757ea80dd71d3bc",
    "path": "TPA \u2192 CMH \u2192 FLL \u2192 DAL",
    "dep1": 279.0,
    "arr1": 340.0,
    "dep2": 338.0,
    "arr2": 326.0,
    "dep3": 306.0,
    "turn1": 50,
    "turn2": 60
  },
  {
    "flight_date": "2023-10-29",
    "tail": "N7842A",
    "flight1": "9dad0aaf7fb00729d171b960103a2a28",
    "flight2": "765726f559fc340ef512d4cd2056a76b",
    "flight3": "3ddc1b54abdb8f3b7a966ef538d5c9c4",
    "path": "SAN \u2192 SJC \u2192 SNA \u2192 DEN",
    "dep1": 347.0,
    "arr1": 336.0,
    "dep2": 338.0,
    "arr2": 336.0,
    "dep3": 334.0,
    "turn1": 35,
    "turn2": 40
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N8509U",
    "flight1": "d2d53db5f0d860b87da3054ce651e60c",
    "flight2": "0aa5fdab38fa30bf931176077b97479c",
    "flight3": "4700769898073910f7901df8e001f252",
    "path": "MDW \u2192 ATL \u2192 TPA \u2192 FLL",
    "dep1": 335.0,
    "arr1": 329.0,
    "dep2": 323.0,
    "arr2": 321.0,
    "dep3": 352.0,
    "turn1": 50,
    "turn2": 45
  },
  {
    "flight_date": "2023-12-23",
    "tail": "N442WN",
    "flight1": "767a3bcad93c55ce7c622e7f9c74ef72",
    "flight2": "065c3974e305fe3602b08d1ef462262b",
    "flight3": "f15e46698e8ce2ff1e588000db52a5d5",
    "path": "ORD \u2192 AUS \u2192 ORD \u2192 PHX",
    "dep1": 319.0,
    "arr1": 323.0,
    "dep2": 337.0,
    "arr2": 326.0,
    "dep3": 320.0,
    "turn1": 55,
    "turn2": 60
  },
  {
    "flight_date": "2023-10-07",
    "tail": "N937WN",
    "flight1": "38b453a1203ea4afc1c44765a379a26b",
    "flight2": "5f6f480fa92da779b2aaa9b46cc1db3e",
    "flight3": "c35247e6c329fecb3b8f6963dd341960",
    "path": "SAN \u2192 LAS \u2192 AUS \u2192 DEN",
    "dep1": 327.0,
    "arr1": 321.0,
    "dep2": 65.0,
    "arr2": 44.0,
    "dep3": 48.0,
    "turn1": 310,
    "turn2": 40
  },
  {
    "flight_date": "2023-12-24",
    "tail": "N8306H",
    "flight1": "aeccf116cf3d7f89d13b511ebe160dc7",
    "flight2": "d55b85d6f965f37b563a9039862704a1",
    "flight3": "afe74c4aa4a3792b3fc3793e933c0c6e",
    "path": "MDW \u2192 TUL \u2192 AUS \u2192 HRL",
    "dep1": 338.0,
    "arr1": 319.0,
    "dep2": 303.0,
    "arr2": 283.0,
    "dep3": 276.0,
    "turn1": 50,
    "turn2": 55
  }
]
```

### distribution

Query: [`distribution.sql`](../sql/analysis/distribution.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "delay_bin": "0_to_14",
    "n": 480651
  },
  {
    "delay_bin": "15_to_59",
    "n": 273691
  },
  {
    "delay_bin": "180_plus",
    "n": 8218
  },
  {
    "delay_bin": "60_to_179",
    "n": 69401
  },
  {
    "delay_bin": "cancelled",
    "n": 14325
  },
  {
    "delay_bin": "early",
    "n": 592179
  }
]
```

### local_seasonality

Query: [`local_seasonality.sql`](../sql/analysis/local_seasonality.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 1,
    "n": 143,
    "disrupted_n": 12,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 2,
    "n": 76,
    "disrupted_n": 2,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 3,
    "n": 181,
    "disrupted_n": 11,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 4,
    "n": 300,
    "disrupted_n": 11,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 5,
    "n": 228,
    "disrupted_n": 12,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 6,
    "n": 238,
    "disrupted_n": 7,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 7,
    "n": 284,
    "disrupted_n": 25,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 8,
    "n": 214,
    "disrupted_n": 16,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 9,
    "n": 80,
    "disrupted_n": 5,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 10,
    "n": 176,
    "disrupted_n": 8,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 11,
    "n": 256,
    "disrupted_n": 17,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 0,
    "month": 12,
    "n": 295,
    "disrupted_n": 22,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 1,
    "n": 285,
    "disrupted_n": 24,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 2,
    "n": 220,
    "disrupted_n": 4,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 3,
    "n": 287,
    "disrupted_n": 13,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 4,
    "n": 318,
    "disrupted_n": 15,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 5,
    "n": 422,
    "disrupted_n": 21,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 6,
    "n": 284,
    "disrupted_n": 14,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 7,
    "n": 405,
    "disrupted_n": 26,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 8,
    "n": 286,
    "disrupted_n": 20,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 9,
    "n": 227,
    "disrupted_n": 8,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 10,
    "n": 397,
    "disrupted_n": 21,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 11,
    "n": 257,
    "disrupted_n": 18,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 1,
    "month": 12,
    "n": 236,
    "disrupted_n": 19,
    "unknown_n": 0
  },
  {
    "local_hour": 5,
    "weekday": 2,
    "month": 1,
    "n": 264,
    "disrupted_n": 24,
    "unknown_n": 0
  }
]
```

### monthly

Query: [`monthly.sql`](../sql/analysis/monthly.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "source_month": "2023-01",
    "focal": false,
    "n": 68962,
    "cancelled_n": 1831,
    "disrupted_n": 15248,
    "unknown_n": 0,
    "mean_departure_minutes": 10.740187027220204,
    "p99_departure_minutes": 187.0,
    "disruption_rate": 0.22110727647110004,
    "previous_month_rate": null,
    "month_rate_change": null
  },
  {
    "source_month": "2023-01",
    "focal": true,
    "n": 43468,
    "cancelled_n": 1403,
    "disrupted_n": 12544,
    "unknown_n": 0,
    "mean_departure_minutes": 14.16130412052659,
    "p99_departure_minutes": 178.0,
    "disruption_rate": 0.2885801049047575,
    "previous_month_rate": null,
    "month_rate_change": null
  },
  {
    "source_month": "2023-02",
    "focal": false,
    "n": 62235,
    "cancelled_n": 1181,
    "disrupted_n": 10961,
    "unknown_n": 0,
    "mean_departure_minutes": 6.055857596698654,
    "p99_departure_minutes": 107.0,
    "disruption_rate": 0.17612276050453923,
    "previous_month_rate": 0.22110727647110004,
    "month_rate_change": -0.044984515966560806
  },
  {
    "source_month": "2023-02",
    "focal": true,
    "n": 39220,
    "cancelled_n": 962,
    "disrupted_n": 9933,
    "unknown_n": 0,
    "mean_departure_minutes": 9.88596514149834,
    "p99_departure_minutes": 113.0,
    "disruption_rate": 0.25326364099949006,
    "previous_month_rate": 0.2885801049047575,
    "month_rate_change": -0.03531646390526744
  },
  {
    "source_month": "2023-03",
    "focal": false,
    "n": 72943,
    "cancelled_n": 695,
    "disrupted_n": 18096,
    "unknown_n": 0,
    "mean_departure_minutes": 11.615812563140924,
    "p99_departure_minutes": 149.0,
    "disruption_rate": 0.24808412047763323,
    "previous_month_rate": 0.17612276050453923,
    "month_rate_change": 0.071961359973094
  },
  {
    "source_month": "2023-03",
    "focal": true,
    "n": 45054,
    "cancelled_n": 421,
    "disrupted_n": 13683,
    "unknown_n": 0,
    "mean_departure_minutes": 13.76188342816182,
    "p99_departure_minutes": 137.0,
    "disruption_rate": 0.3037022239978692,
    "previous_month_rate": 0.25326364099949006,
    "month_rate_change": 0.05043858299837917
  },
  {
    "source_month": "2023-04",
    "focal": false,
    "n": 71751,
    "cancelled_n": 709,
    "disrupted_n": 19070,
    "unknown_n": 0,
    "mean_departure_minutes": 12.77659559496165,
    "p99_departure_minutes": 156.0,
    "disruption_rate": 0.2657802678708311,
    "previous_month_rate": 0.24808412047763323,
    "month_rate_change": 0.01769614739319786
  },
  {
    "source_month": "2023-04",
    "focal": true,
    "n": 44195,
    "cancelled_n": 540,
    "disrupted_n": 14786,
    "unknown_n": 0,
    "mean_departure_minutes": 16.263884753681605,
    "p99_departure_minutes": 155.0,
    "disruption_rate": 0.33456273334087566,
    "previous_month_rate": 0.3037022239978692,
    "month_rate_change": 0.030860509343006437
  },
  {
    "source_month": "2023-05",
    "focal": false,
    "n": 75380,
    "cancelled_n": 344,
    "disrupted_n": 15784,
    "unknown_n": 0,
    "mean_departure_minutes": 8.961341648676742,
    "p99_departure_minutes": 122.58999999999651,
    "disruption_rate": 0.2093924117803131,
    "previous_month_rate": 0.2657802678708311,
    "month_rate_change": -0.056387856090517996
  },
  {
    "source_month": "2023-05",
    "focal": true,
    "n": 47141,
    "cancelled_n": 279,
    "disrupted_n": 13691,
    "unknown_n": 0,
    "mean_departure_minutes": 13.33046706637933,
    "p99_departure_minutes": 135.0,
    "disruption_rate": 0.29042659256273734,
    "previous_month_rate": 0.33456273334087566,
    "month_rate_change": -0.04413614077813832
  },
  {
    "source_month": "2023-06",
    "focal": false,
    "n": 73260,
    "cancelled_n": 393,
    "disrupted_n": 21785,
    "unknown_n": 0,
    "mean_departure_minutes": 15.291624358516973,
    "p99_departure_minutes": 174.0,
    "disruption_rate": 0.2973655473655474,
    "previous_month_rate": 0.2093924117803131,
    "month_rate_change": 0.08797313558523429
  },
  {
    "source_month": "2023-06",
    "focal": true,
    "n": 45991,
    "cancelled_n": 315,
    "disrupted_n": 17235,
    "unknown_n": 0,
    "mean_departure_minutes": 19.290761048000526,
    "p99_departure_minutes": 169.0,
    "disruption_rate": 0.3747472331543128,
    "previous_month_rate": 0.29042659256273734,
    "month_rate_change": 0.08432064059157546
  },
  {
    "source_month": "2023-07",
    "focal": false,
    "n": 77589,
    "cancelled_n": 633,
    "disrupted_n": 24199,
    "unknown_n": 0,
    "mean_departure_minutes": 17.019565047938265,
    "p99_departure_minutes": 189.27000000000407,
    "disruption_rate": 0.31188699429042777,
    "previous_month_rate": 0.2973655473655474,
    "month_rate_change": 0.014521446924880388
  },
  {
    "source_month": "2023-07",
    "focal": true,
    "n": 48880,
    "cancelled_n": 558,
    "disrupted_n": 19812,
    "unknown_n": 0,
    "mean_departure_minutes": 21.936439625920716,
    "p99_departure_minutes": 188.0,
    "disruption_rate": 0.4053191489361702,
    "previous_month_rate": 0.3747472331543128,
    "month_rate_change": 0.030571915781857417
  },
  {
    "source_month": "2023-08",
    "focal": false,
    "n": 76720,
    "cancelled_n": 1256,
    "disrupted_n": 18587,
    "unknown_n": 0,
    "mean_departure_minutes": 10.266540367239871,
    "p99_departure_minutes": 138.0,
    "disruption_rate": 0.2422705943691345,
    "previous_month_rate": 0.31188699429042777,
    "month_rate_change": -0.06961639992129326
  },
  {
    "source_month": "2023-08",
    "focal": true,
    "n": 48944,
    "cancelled_n": 808,
    "disrupted_n": 15377,
    "unknown_n": 0,
    "mean_departure_minutes": 13.887102803738317,
    "p99_departure_minutes": 134.0,
    "disruption_rate": 0.31417538411245505,
    "previous_month_rate": 0.4053191489361702,
    "month_rate_change": -0.09114376482371517
  },
  {
    "source_month": "2023-09",
    "focal": false,
    "n": 71852,
    "cancelled_n": 361,
    "disrupted_n": 14190,
    "unknown_n": 0,
    "mean_departure_minutes": 8.823911948981875,
    "p99_departure_minutes": 140.0,
    "disruption_rate": 0.19748928352725045,
    "previous_month_rate": 0.2422705943691345,
    "month_rate_change": -0.04478131084188405
  },
  {
    "source_month": "2023-09",
    "focal": true,
    "n": 46018,
    "cancelled_n": 299,
    "disrupted_n": 12337,
    "unknown_n": 0,
    "mean_departure_minutes": 12.350337830450659,
    "p99_departure_minutes": 136.0,
    "disruption_rate": 0.2680907470989613,
    "previous_month_rate": 0.31417538411245505,
    "month_rate_change": -0.046084637013493746
  },
  {
    "source_month": "2023-10",
    "focal": false,
    "n": 78733,
    "cancelled_n": 153,
    "disrupted_n": 15967,
    "unknown_n": 0,
    "mean_departure_minutes": 8.646337273664253,
    "p99_departure_minutes": 124.0,
    "disruption_rate": 0.20279933445950238,
    "previous_month_rate": 0.19748928352725045,
    "month_rate_change": 0.005310050932251925
  },
  {
    "source_month": "2023-10",
    "focal": true,
    "n": 49855,
    "cancelled_n": 134,
    "disrupted_n": 13457,
    "unknown_n": 0,
    "mean_departure_minutes": 12.181339231852,
    "p99_departure_minutes": 129.0,
    "disruption_rate": 0.2699227760505466,
    "previous_month_rate": 0.2680907470989613,
    "month_rate_change": 0.001832028951585296
  },
  {
    "source_month": "2023-11",
    "focal": false,
    "n": 75192,
    "cancelled_n": 155,
    "disrupted_n": 11974,
    "unknown_n": 0,
    "mean_departure_minutes": 5.82004744010021,
    "p99_departure_minutes": 99.58999999999651,
    "disruption_rate": 0.1592456644323864,
    "previous_month_rate": 0.20279933445950238,
    "month_rate_change": -0.043553670027115965
  },
  {
    "source_month": "2023-11",
    "focal": true,
    "n": 47309,
    "cancelled_n": 89,
    "disrupted_n": 9221,
    "unknown_n": 0,
    "mean_departure_minutes": 7.5495319977976365,
    "p99_departure_minutes": 98.0,
    "disruption_rate": 0.19491005939673212,
    "previous_month_rate": 0.2699227760505466,
    "month_rate_change": -0.07501271665381448
  },
  {
    "source_month": "2023-12",
    "focal": false,
    "n": 78513,
    "cancelled_n": 433,
    "disrupted_n": 15738,
    "unknown_n": 0,
    "mean_departure_minutes": 8.553550848976874,
    "p99_departure_minutes": 131.0,
    "disruption_rate": 0.20045088074586373,
    "previous_month_rate": 0.1592456644323864,
    "month_rate_change": 0.041205216313477316
  },
  {
    "source_month": "2023-12",
    "focal": true,
    "n": 49260,
    "cancelled_n": 373,
    "disrupted_n": 11960,
    "unknown_n": 0,
    "mean_departure_minutes": 10.314795876626032,
    "p99_departure_minutes": 116.0,
    "disruption_rate": 0.24279334145351197,
    "previous_month_rate": 0.19491005939673212,
    "month_rate_change": 0.04788328205677986
  }
]
```

### overview

Query: [`overview.sql`](../sql/analysis/overview.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "n": 1438465,
    "cancelled_n": 14325,
    "diverted_n": 2902,
    "missing_tail_n": 74,
    "missing_dep_delay_n": 14055,
    "missing_arr_delay_n": 17227,
    "early_departure_n": 592247,
    "mean_dep_delay": 11.717483028060741,
    "median_dep_delay": 1.0,
    "p90_dep_delay": 38.0,
    "p99_dep_delay": 147.0,
    "max_dep_delay": 775.0,
    "inconsistent_actual_arrival_n": 25,
    "inconsistent_scheduled_arrival_n": 31,
    "inconsistent_actual_departure_n": 0
  }
]
```

### quality

Query: [`quality.sql`](../sql/analysis/quality.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "kind": "flight_time",
    "reason": "valid",
    "n": 1438465
  },
  {
    "kind": "rotation",
    "reason": "inconsistent_source_timestamps",
    "n": 104
  },
  {
    "kind": "rotation",
    "reason": "discontinuous_airport",
    "n": 26781
  },
  {
    "kind": "rotation",
    "reason": "actual_overlap",
    "n": 12
  },
  {
    "kind": "rotation",
    "reason": "cancelled",
    "n": 11234
  },
  {
    "kind": "rotation",
    "reason": "diverted",
    "n": 5038
  },
  {
    "kind": "rotation",
    "reason": "valid",
    "n": 1160285
  },
  {
    "kind": "rotation",
    "reason": "scheduled_gap",
    "n": 234082
  },
  {
    "kind": "weather_report",
    "reason": "FM-12",
    "n": 9295
  },
  {
    "kind": "weather_report",
    "reason": "FM-15",
    "n": 70058
  },
  {
    "kind": "weather_report",
    "reason": "FM-16",
    "n": 10692
  },
  {
    "kind": "weather_report",
    "reason": "SY-MT",
    "n": 39
  },
  {
    "kind": "weather_summary_excluded",
    "reason": "SOM",
    "n": 96
  },
  {
    "kind": "weather_summary_excluded",
    "reason": "SOD",
    "n": 2920
  }
]
```

### rotation_associations

Query: [`rotation_associations.sql`](../sql/analysis/rotation_associations.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "cohort": "inbound_late15",
    "n": 226042,
    "outbound_late_rate": 0.8042222241884251,
    "mean_outbound_minutes": 43.40105821042107,
    "median_scheduled_turn_minutes": 45.0
  },
  {
    "cohort": "inbound_under15",
    "n": 934243,
    "outbound_late_rate": 0.13972488956299378,
    "mean_outbound_minutes": 4.632497112635578,
    "median_scheduled_turn_minutes": 45.0
  }
]
```

### weather_associations

Query: [`weather_associations.sql`](../sql/analysis/weather_associations.sql). Full result: [`eda.json`](eda.json).

```json
[
  {
    "weather_group": "missing_or_stale",
    "n": 258,
    "disrupted_n": 69,
    "unknown_n": 0,
    "mean_dep_delay": 11.244186046511627
  },
  {
    "weather_group": "other_observed",
    "n": 524184,
    "disrupted_n": 150865,
    "unknown_n": 0,
    "mean_dep_delay": 13.196879465953783
  },
  {
    "weather_group": "visibility_below_3km",
    "n": 6753,
    "disrupted_n": 3145,
    "unknown_n": 0,
    "mean_dep_delay": 30.052073288331727
  },
  {
    "weather_group": "wind_at_least_8mps",
    "n": 24140,
    "disrupted_n": 9957,
    "unknown_n": 0,
    "mean_dep_delay": 22.19263876521223
  }
]
```
