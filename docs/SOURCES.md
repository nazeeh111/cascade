# Source evidence and download contract

Verified on 2026-10-25 (America/New_York). This release uses the 2023 reporting year, Southwest (`WN`) domestic operations, and eight focal airports: BWI, DAL, DEN, HOU, LAS, MDW, OAK and PHX. Retaining other Southwest domestic legs improves retrospective chain continuity; it does not recover international, ferry, maintenance or crew movements. Airport and carrier cohorts are a deliberate selection, not a representative sample of the entire US network.

## BTS reporting-carrier flight data

Use the [official PREZIP index](https://transtats.bts.gov/PREZIP/) and exact monthly reporting-carrier filenames. The current template is:

```text
https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_{MONTH}.zip
```

`MONTH` is unpadded 1 through 12. All twelve URLs returned HTTP 200 to HEAD checks; the total compressed size was **339,797,980 bytes**. January was 27,068,766 bytes. The index also has an older parenthesized December alias; the no-parentheses template works for every month. A parenthesized January filename is absent. This check establishes availability and transport sizes, not ingested row counts; ingestion must record each downloaded SHA-256 and reconcile the extracted rows itself.

The [BTS field dictionary](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ) distinguishes signed `DepDelay`/`ArrDelay` from zero-clipped `DepDelayMinutes`/`ArrDelayMinutes`. Preserve negative values in descriptive analysis. `ArrDelay` and `ActualElapsedTime` remain null for diverted flights; diverted-reached-destination fields have separate definitions. `OriginAirportID` and `DestAirportID` identify airports more stably than reused three-letter codes. `Reporting_Airline`, rather than an IATA code alone, identifies a carrier across time.

The [2023 reporting directive #37](https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-37-technical-reporting-directive-reporting-air) lists Southwest among the reporting airlines and refers operational instructions to [directive #31](https://www.bts.gov/topics/airlines-and-airports/number-31-technical-directive-time-reporting-effective-jan-1-2019). Its practical consequences are:

- HHMM values use local time; midnight is `2400`. Month ownership follows the flight operation's start. Normalize `2400` as next-day midnight, rather than an invalid hour or same-day zero.
- Delay minutes are signed. A missing source field and calculations depending on it remain missing.
- A cancelled flight may have a departure time after a gate return; cancellation is a separate outcome. A tail can be missing if no aircraft was assigned before cancellation.
- Tail identifies the aircraft actually used around wheels-off, including swaps after diversion. It is retrospective evidence, not a future aircraft assignment available to a forecaster.

### Implementation requirements inferred from the definitions

The public extract is a corrected historical snapshot. It does not prove the exact schedule, cancellation announcement or telemetry available at a historical cutoff. Treat model availability times as explicit emulation assumptions. Record source/download time separately from event time.

Convert scheduled departure using the origin IANA time zone and flight date. Scheduled arrival may be reconstructed from departure plus scheduled elapsed minutes, with its destination-local clock checked separately. For a noncancelled, nondiverted flight, actual departure may be reconstructed from scheduled departure plus signed departure delay; actual arrival can use actual elapsed minutes and be checked against arrival delay. These are implementation choices requiring validity checks, especially at daylight-saving folds/gaps and midnight. Never silently choose a DST fold using later outcomes as a forecasting feature.

For rotations, a shared tail alone is insufficient. Require unique legs, chronological order, matching previous destination/current origin, credible turnaround bounds, no overlapping actual intervals, and valid prior arrival. Missing, cancelled, diverted or out-of-scope intervening legs break a supported chain. Airport transfer, passenger transfer and crew connections cannot be inferred from these records.

## NOAA ISD / Global Hourly

The [ISD product page](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) describes merged surface observations. NOAA's [June 23, 2026 service notice](https://www.nesdis.noaa.gov/news/service-location-change-integrated-surface-data-global-hourly) moved access to NODD cloud locations and states that ISD has been superseded, with no update after August 24, 2025. The old NCEI `data/global-hourly/access` URL redirects to a bucket index, not the requested CSV. Historical 2023 CSVs remain available at:

```text
https://noaa-global-hourly-pds.s3.amazonaws.com/2023/{STATION}.csv
```

The [official station history](https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv) was matched by ICAO code and coverage of 2023. USAF and WBAN are strings, preserving leading zeros. Several ICAOs have earlier obsolete entries; these selected entries cover the reporting year.

| Airport | ICAO | USAF+WBAN station | IANA time zone | CSV bytes verified |
| --- | --- | --- | --- | ---: |
| BWI | KBWI | 72406093721 | America/New_York | 7,680,564 |
| DAL | KDAL | 72258013960 | America/Chicago | 6,486,632 |
| DEN | KDEN | 72565003017 | America/Denver | 8,604,201 |
| HOU | KHOU | 72244012918 | America/Chicago | 6,702,547 |
| LAS | KLAS | 72386023169 | America/Los_Angeles | 6,542,956 |
| MDW | KMDW | 72534014819 | America/Chicago | 7,369,375 |
| OAK | KOAK | 72493023230 | America/Los_Angeles | 6,157,499 |
| PHX | KPHX | 72278023183 | America/Phoenix | 6,409,580 |

Every listed object returned HTTP 200. The station identifiers and coverage come from station history; the IANA mapping is a geographic implementation mapping and must be tested against the pinned timezone database. Phoenix does not follow the other focal airports' DST pattern.

The [ISD format specification](https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf) defines UTC observation time, per-element quality flags, and missing sentinels. In CSV, `WND` holds direction, direction quality, type, speed (tenths of m/s), speed quality; `TMP`/`DEW` are signed tenths of Celsius plus quality. `VIS` contains metres and quality. `AA1` includes accumulation hours and tenths of millimetres; only a documented one-hour amount can be called hourly precipitation. Standard numeric quality codes 0/1/4/5 pass gross/all checks; 2/3/6/7 indicate suspect/error. Missing sentinels remain null regardless of quality. Code 9 has field-specific meaning; do not globally treat every 9 as a valid measurement or as missing.

A sampled DEN CSV has both synoptic (`FM-12`) and routine aviation (`FM-15`) reports. Daily/monthly summary types SOD/SOM are excluded from hourly weather observations; they contain no usable temperature/wind/visibility in this snapshot and must not mask preceding observations. Other timestamped reports remain subject to element QC. Duplicate observation times prefer FM-15, then FM-16, then FM-12, with deterministic completeness/hash ties. Join the last available observation at or before cutoff, cap staleness, and retain observation age. Historical objects have January 2026 modification dates: observation timestamp is not a verified 2023 release timestamp. A chosen publication lag is an assumption and requires sensitivity analysis; revised archival observations are not real-time forecasts.

## Reuse, attribution, and limits

BTS statistical rows and NOAA observations are public US government data. [BTS public-access guidance](https://www.bts.gov/ntl/public-access/faqs) permits public search, download and analysis subject to privacy/confidentiality/security exceptions. [NOAA's content guidance](https://www.noaa.gov/office-education/outreach-communication/faq) says NOAA data products are generally public domain and reusable without express permission. CASCADE redistributes a small factual subset, credits **US DOT/Bureau of Transportation Statistics** and **NOAA/NCEI**, and claims no endorsement. The code license does not impose ownership over federal source observations. These statements do not license third-party logos, imagery or source websites' presentation. Preserve source attribution, transformation notice, snapshot hashes and URLs alongside the quickstart.

Source records are historical and can be corrected. Re-downloads must produce a new manifest/version when their hashes change. Never silently combine changed snapshots under an existing run ID.

## Foundational study and method boundaries

[Fleurquin, Ramasco and Eguiluz, *Systemic delay propagation in the US airport network*](https://arxiv.org/abs/1301.1136) motivates reconstructing network propagation. CASCADE's restricted carrier/airport sample and hypothetical recovery resources do not replicate that study's model or establish causal delay attribution. No passenger counts, crew connections, monetary savings or operational airline readiness are inferred from the public flight/weather extracts.

## January carrier-selection benchmark

`data/benchmarks/carrier_cohorts_2023_01.parquet` contains all reporting-carrier/airport cohorts at the eight focal origins in January2023. Its small aggregate is rebuilt directly from the original JanuaryZIP, whose SHA256must equal the frozen WN-ingestion archive hash. Counts sum exactly to the corresponding focal-origin source rows. Delay averages/99thpercentiles use signed non-null gate-out delay; cancellations and unknown noncancelled status are separate.

This is a one-month contextual comparison for carrier selection bias. It cannot establish an annual carrier ranking or isolate airline performance from airport/route/schedule mix. Forecasting and retrospective aircraft reconstructions use the declared WNscope. The all-carrier benchmark has no role in forecast features or model selection.
