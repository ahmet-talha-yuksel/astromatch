# Scientific validation

The contract requires meter elevations/distances, row-major ordering, explicit datum and
CRS, and a sample-center physical window. Validation rejects missing real-data
provenance, malformed metadata, inconsistent windows, invalid NoData masks, non-finite
values and unsafe display ranges. NoData is excluded from statistics and produces no
vertices or bridging triangles.

Comparison medians use valid source elevations. Relative mode subtracts those medians
for display only; source values remain unchanged. A common physical world scale and
shared relative color range are used. Absolute mode warns when datums differ.
Exaggeration is display-only.

Tests cover dimensions, spacing, ordering, rectangular/negative/flat terrain, NoData,
exaggeration, relative references, shared scale/range behavior, provenance/CRS/datum
failures, invalid similarity inputs and missing candidate links. Browser checks cover
controls, loading errors, NoData, stale requests and page errors when dependencies are
available. Synthetic fixtures are not measurements; real-data validation is blocked.

