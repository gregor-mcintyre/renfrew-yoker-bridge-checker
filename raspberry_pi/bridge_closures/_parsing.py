"""Parses closures from text displayed on the Renfrew-Yoker bridge closures webpage.

The webpage is formatted inconsistently. Every variation seen so far is handled and
listed below. Each is a separate case, and one page can show several at once.

Page layout:

    - The closures are listed twice: once in the banner at the top of the page, then
      again in the article below it. The repeats are dropped, so each closure is
      returned once.
    - The banner ends with a `Last Updated - <date> at <time>` line. The date looks like
      a date heading, but no time range follows it, so it yields nothing.
    - The date heading is sometimes above the "will be closed" notice, and sometimes
      below it. Either way, the time ranges after it belong to it.
    - Several dates can be listed, each with its own closures.
    - A date with no closures shows either `No Closures Currently Planned` or
      `No closures currently planned`. There is no time range, so it yields nothing.

Date heading:

    - The ordinal suffix on the day is sometimes present, e.g. `Sunday 13th September
      2026`, and sometimes absent, e.g. `Friday 11 September 2026`.

Time:

    - The minutes are absent, e.g. `5pm`, or follow a colon, e.g. `6:30pm`, or follow a
      dot, e.g. `7.30am`.
    - A space sometimes precedes `am` or `pm`, e.g. `11.10 am`.

Time range:

    - A time range is sometimes prefixed with `From`, e.g. `From 5pm to 6:30pm`, and
      sometimes not, e.g. `2.10pm to 2.25pm`.
    - A date can have several time ranges, each of which is a separate closure.
    - A range whose end time is earlier than the start time runs past midnight, e.g.
      `From 11pm to 1am`, so ends on the next day.
    - A range that runs past midnight sometimes names the day of each time in
      parentheses, e.g. `11.25pm (14th) to 12.30am (15th)`. The days are ignored, as the
      end time already shows the range runs past midnight.
"""

import calendar
import re
from datetime import date, datetime, time, timedelta

from bridge_closure import LONDON_TZ, BridgeClosure

_MONTH_NUMBER_BY_NAME = {
    name: number for number, name in enumerate(calendar.month_name) if number
}
_MONTH_NAMES = "|".join(_MONTH_NUMBER_BY_NAME)
_DAY_NAMES = "|".join(calendar.day_name)

# Matches a date heading such as "Friday 11th September 2026" or "Friday 11 September
# 2026". The ordinal suffix is optional.
_DATE_HEADING = (
    rf"(?:{_DAY_NAMES})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+"
    rf"(?P<month>{_MONTH_NAMES})\s+(?P<year>\d{{4}})"
)

# Matches a closure time such as "8am", "8:30am", "9.45pm", or "11.10 am". The minutes
# are optional and can be separated by a colon or a dot, and a space can precede the
# meridiem.
_TIME = r"\d{1,2}(?:[:.]\d{2})?\s*[ap]m"

# Matches the optional day of a time in parentheses, such as " (14th)" or " (15)".
_DAY_NOTE = r"(?:\s*\(\d{1,2}(?:st|nd|rd|th)?\))?"

# Matches a "[From] X to Y" time range. The leading "From" is optional, as is the day
# in parentheses after each time.
_TIME_RANGE = (
    rf"(?:From\s+)?(?P<start_time>{_TIME}){_DAY_NOTE}"
    rf"\s+to\s+(?P<end_time>{_TIME}){_DAY_NOTE}"
)

_DATE_HEADING_OR_TIME_RANGE_PATTERN = re.compile(
    rf"(?P<date_heading>{_DATE_HEADING})|{_TIME_RANGE}",
)


def _build_date_from_match(match: re.Match[str]) -> date:
    """Builds a `date` from the day, month, and year groups of `match`.

    Args:
        match: A `_DATE_HEADING_OR_TIME_RANGE_PATTERN` match against a date heading.

    Returns:
        The date represented by the day, month, and year groups of `match`.
    """
    return date(
        int(match["year"]),
        _MONTH_NUMBER_BY_NAME[match["month"]],
        int(match["day"]),
    )


def _parse_time(raw: str) -> time:
    """Parses a closure time displayed on the webpage into a `time`.

    Handles the following time formats:

        - `8am`
        - `8:30am`
        - `10.45pm`
        - `11.10 am`

    Args:
        raw: The time as displayed on the webpage.

    Returns:
        The closure time displayed on the webpage parsed into a `time`.
    """
    normalised = "".join(raw.split()).replace(".", ":")

    if ":" not in normalised:
        normalised = f"{normalised[:-2]}:00{normalised[-2:]}"

    return datetime.strptime(normalised, "%I:%M%p").time()


def _resolve_end_date(*, start_date: date, start_time: time, end_time: time) -> date:
    """Resolves the closure end date.

    Args:
        start_date: The start date of the closure.
        start_time: The start time of the closure.
        end_time: The end time of the closure.

    Returns:
        `start_date` advanced by one day when `end_time` is earlier than `start_time`
        (the closure runs past midnight), otherwise `start_date` unchanged.
    """
    if end_time < start_time:
        return start_date + timedelta(days=1)

    return start_date


def _build_bridge_closure_with_london_timezone(
    *,
    start: datetime,
    end: datetime,
) -> BridgeClosure:
    """Builds a `BridgeClosure` with the timezone of both times set to `Europe/London`.

    Args:
        start: The date and time the bridge is closed from.
        end: The date and time the bridge reopens.

    Returns:
        A `BridgeClosure` where the timezone of both times is set to `Europe/London`.
    """
    return BridgeClosure(
        start=start.replace(tzinfo=LONDON_TZ),
        end=end.replace(tzinfo=LONDON_TZ),
    )


def _build_closure_from_match(start_date: date, match: re.Match[str]) -> BridgeClosure:
    """Builds a `BridgeClosure` from `start_date` and a time range match.

    Args:
        start_date: The date of the heading `match` was found under.
        match: A `_DATE_HEADING_OR_TIME_RANGE_PATTERN` match against a time range.

    Returns:
        `_build_bridge_closure_with_london_timezone` for `start_date`, the end date
        resolved from `match`, and the start and end times from `match`.
    """
    start_time = _parse_time(match["start_time"])
    end_time = _parse_time(match["end_time"])
    end_date = _resolve_end_date(
        start_date=start_date,
        start_time=start_time,
        end_time=end_time,
    )

    return _build_bridge_closure_with_london_timezone(
        start=datetime.combine(start_date, start_time),
        end=datetime.combine(end_date, end_time),
    )


def parse_bridge_closures(webpage_text: str) -> list[BridgeClosure]:
    """Parses closures from text displayed on the Renfrew-Yoker bridge closures webpage.

    The webpage is read in order: each date heading puts a new date in scope, and every
    time range after it is a closure on that date. A time range found before the first
    date heading has no date, so is ignored.

    The webpage lists each closure twice, so a closure already found is skipped.

    Args:
        webpage_text: The text displayed on the webpage.

    Returns:
        `_build_closure_from_match` for every distinct time range found under a date
        heading.
    """
    closures: list[BridgeClosure] = []
    start_date: date | None = None

    for match in _DATE_HEADING_OR_TIME_RANGE_PATTERN.finditer(webpage_text):
        if match["date_heading"]:
            start_date = _build_date_from_match(match)

        elif start_date is not None:
            closure = _build_closure_from_match(start_date, match)

            if closure not in closures:
                closures.append(closure)

    return closures
