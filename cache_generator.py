"""Generate monthly prediction files. All timestamps are UTC milliseconds."""

import calendar
from datetime import datetime, timezone
import inspect
import json
import math
from pathlib import Path
import time
from tempfile import TemporaryDirectory

from aberoth_ephemeris import Ephemeris

MS_PER_DAY = 86_400_000
FORECAST_YEARS = 100
OUTPUT_DIR = Path(__file__).resolve().parent / "predictions"


def month_start(timestamp):
    """Return the UTC start of the calendar month containing timestamp."""
    date = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
    return datetime(date.year, date.month, 1, tzinfo=timezone.utc)


def next_month(date):
    if date.month == 12:
        return date.replace(year=date.year + 1, month=1)
    return date.replace(month=date.month + 1)


def epoch_ms(date):
    return calendar.timegm(date.utctimetuple()) * 1000


def save_monthly_predictions(events, start, end, directory):
    """Write one JSON array per UTC month in the half-open range [start, end)."""
    directory.mkdir(parents=True, exist_ok=True)
    events = sorted(events, key=lambda event: event[0])
    index = 0
    month = month_start(start)
    while epoch_ms(month) < end:
        following = next_month(month)
        boundary = epoch_ms(following)
        month_events = []
        while index < len(events) and events[index][0] < boundary:
            if events[index][0] >= epoch_ms(month):
                month_events.append(events[index])
            index += 1
        (directory / f"{epoch_ms(month)}.json").write_text(
            json.dumps(month_events, indent=4) + "\n", encoding="utf-8"
        )
        month = following


def replace_predictions(scroll_events, moon_events, start, end, output_dir):
    """Stage both sets before replacing JSON files from the previous run."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir, prefix=".predictions-") as temp_dir:
        staging_dir = Path(temp_dir)
        for name, events in (("scrolls", scroll_events), ("moon_phases", moon_events)):
            save_monthly_predictions(events, start, end, staging_dir / name)

        for name in ("scrolls", "moon_phases"):
            destination = output_dir / name
            destination.mkdir(parents=True, exist_ok=True)
            staged_files = list((staging_dir / name).glob("*.json"))
            new_names = {path.name for path in staged_files}
            for path in staged_files:
                path.replace(destination / path.name)
            for path in destination.glob("*.json"):
                if path.name not in new_names:
                    path.unlink()


def formatTime(milliseconds: int) -> str:
    """Takes in a length of time in milliseconds and formats it into h:m:s:ms format.

    Parameters
    ---------
        milliseconds: `int`
            The length of time to be formatted
    Returns
    ---------
        `str`
        The length of time in the format f"{hours:.0f}h {minutes:.0f}m {seconds:.0f}s {ms}ms"
    """
    # Convert milliseconds to seconds
    seconds = milliseconds // 1000
    # Calculate hours, minutes and seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    ms = milliseconds % 1000
    # Return formatted time string
    return f"{hours:.0f}h {minutes:.0f}m {seconds:.0f}s {ms}ms"

def main():
    startTime = time.time_ns() // 1_000_000
    now = round(time.time() * 1000)
    # Include the entire previous UTC month and a 100-year forecast.
    current_month = month_start(now)
    start = epoch_ms(month_start(epoch_ms(current_month) - 1))
    end_month = current_month.replace(year=current_month.year + FORECAST_YEARS)
    end = epoch_ms(next_month(end_month))
    num_moon_cycles = math.ceil((end - start) / (MS_PER_DAY * 3))

    # Ephemeris expects this sibling directory even in installations that omit it.
    package_dir = Path(inspect.getfile(Ephemeris)).resolve().parent
    (package_dir.parent / "UpdateWebServer").mkdir(exist_ok=True)

    print("Calculating 100 years of predictions; this may take a while...", flush=True)
    ephemeris = Ephemeris(
        start=start,
        end=end,
        numMoonCycles=num_moon_cycles,
        discordTimestamps=False,
        multiProcess=True,
        numCores=None,
        varFile=None,
    )

    moon_events = ephemeris.moonCyclesCache
    while not moon_events or moon_events[-1][0] < end:
        num_moon_cycles *= 2
        print(f"Extending moon predictions to {num_moon_cycles} cycles...", flush=True)
        moon_events = ephemeris.createLunarCalendar(start, num_moon_cycles)

    print(f"Saving monthly predictions to {OUTPUT_DIR}...", flush=True)
    replace_predictions(ephemeris.scrollEventsCache, moon_events, start, end, OUTPUT_DIR)
    print("Monthly predictions saved; old JSON files replaced.", flush=True)

    stopTime = time.time_ns() // 1_000_000
    print(
        f"{ephemeris.numCores} cores; Execution time: {formatTime(stopTime-startTime)}"
    )


if __name__ == "__main__":
    main()