# Data rights and provenance

The bundled quickstart is a real subset of US federal government flight statistics (Bureau of Transportation Statistics, Reporting Carrier On-Time Performance,2023) and weather observations (NOAA NCEI, Integrated Surface Database/Global Hourly,2023). These US government source records are public domain under17USC§105. No claim is made to airline, airport or NOAA endorsement. Data may be revised and are supplied without warranty.

- BTS source/data guide: https://www.transtats.bts.gov/ontime/ . Monthly URLs, checksums, retrieval timestamps, source/scoped row counts and aggregate reconciliations are in `data/source_manifest.json`.
- NOAA ISD: https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database . Current public distribution uses https://noaa-global-hourly-pds.s3.amazonaws.com/2023/ . Element quality flags and assumed availability are documented in `docs/SOURCES.md`.
- US government copyright rule: https://www.copyright.gov/title17/92chap1.html#105 . NOAA reuse guidance: https://www.noaa.gov/disclaimer . BTS reuse guidance: https://www.bts.gov/bts-site-policies . Review the original sites for their current notices.

The tiny `data/benchmarks` carrier-cohort Parquet is also derived from the same federal January2023source, with its own manifest and original-archive checksum.

`data/quickstart/manifest.json` declares the exact date selection, per-file row counts and SHA-256 hashes. It is a discontinuous functional sample, not the full-year analytical population. The full scoped Parquet files are rebuilt with `cascade ingest`; downloads use only public source URLs, without accounts or keys. Original monthly ZIP/CSV bytes are hashed during ingestion and processed in disposable temporary storage. Hash-verified WN Parquet partitions and per-source manifests remain local for resumable builds.

Airport coordinates, names and IANA timezone identifiers come from the `airportsdata` Python package (MIT): https://github.com/mborsetti/airportsdata . Its upstream airport metadata has separate provenance described in that project. The airport metadata is distributed under the MIT terms below; CASCADE's code/derived selections use the repository MIT license.

## airportsdata license

The MIT License (MIT)

Copyright (c) 2020- Mike Borsetti <mike@borsetti.com>

This project includes data from https://github.com/mwgg/Airports Copyright
(c) 2014 mwgg

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
