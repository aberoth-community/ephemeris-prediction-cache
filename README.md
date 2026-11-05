# ephemeris-prediction-cache

Run `python cache_generator.py` with `aberoth_ephemeris` installed to generate
prediction JSON files in `predictions/scrolls/` and `predictions/moon_phases/`.
Each file contains the library's timestamped events for one UTC calendar month.
Its filename is the month's starting Unix epoch in milliseconds, for example
`1735689600000.json` for January 2025. Month ranges include their start and
exclude the start of the following month. The generated range covers the full
months containing four days before the current time through 100 calendar years
after it. Both scroll and moon-phase predictions cover the same range.

Each successful generation replaces the previous JSON predictions in both folders,
including files for months outside the new range.
