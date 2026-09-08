"""Parses closures from text displayed on the Renfrew-Yoker bridge closures webpage."""

import calendar
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from bridge_closure import BridgeClosure

_MONTH_NUMBER_BY_NAME = {
    name: number for number, name in enumerate(calendar.month_name) if number
}
_MONTH_NAMES = "|".join(_MONTH_NUMBER_BY_NAME)
_DAY_NAMES = "|".join(calendar.day_name)

_DAY_ORDINAL_SUFFIX = r"(?:st|nd|rd|th)?"

# Matches a closure time such as "8:30am" or "9pm"
_TIME_PATTERN = r"\d{1,2}(?::\d{2})?[ap]m"

# Matches a date line ("Tuesday 8th September 2026") followed, within a short span of
# text, by a "From X to [<end date>] Y" time line. The {0,200} gap tolerates the blank
# line and indentation between the two without matching unrelated closures further down
# the page. The end-date group is optional and is only present when the end time is the
# next day. When absent, an end time earlier than the start time is treated as an
# implicit rollover past midnight instead.
_CLOSURE_PATTERN = re.compile(
    rf"(?:{_DAY_NAMES})\s+(?P<start_day>\d{{1,2}}){_DAY_ORDINAL_SUFFIX}\s+"
    rf"(?P<start_month>{_MONTH_NAMES})\s+(?P<start_year>\d{{4}})"
    r".{0,200}?"
    rf"From\s+(?P<start_time>{_TIME_PATTERN})\s+to\s+"
    rf"(?:(?:{_DAY_NAMES})\s+(?P<end_day>\d{{1,2}}){_DAY_ORDINAL_SUFFIX}\s+"
    rf"(?P<end_month>{_MONTH_NAMES})\s+(?P<end_year>\d{{4}})\s+)?"
    rf"(?P<end_time>{_TIME_PATTERN})",
    re.DOTALL,
)

_LONDON_TZ = ZoneInfo("Europe/London")


def _build_date_from_match(match: re.Match[str], prefix: str) -> date:
    """Builds a `date` from the day, month, and year of `match`.

    Args:
        match: A `_CLOSURE_PATTERN` match against the text displayed on the webpage.
        prefix: Which date to build. Either `"start"` or `"end"`.

    Returns:
        The date representing the day, month, and year from `match`.
    """
    return date(
        int(match[f"{prefix}_year"]),
        _MONTH_NUMBER_BY_NAME[match[f"{prefix}_month"]],
        int(match[f"{prefix}_day"]),
    )


def _parse_time(raw: str) -> time:
    """Parses a closure time displayed on the webpage into a `time`.

    Handles the following time formats:

        - `8:00am`
        - `10pm`

    Args:
        raw: The time as displayed on the webpage.

    Returns:
        The closure time displayed on the webpage parsed into a `time`.
    """
    normalised = raw if ":" in raw else f"{raw[:-2]}:00{raw[-2:]}"

    return datetime.strptime(normalised, "%I:%M%p").time()


def _build_end_date_from_match_if_provided(match: re.Match[str]) -> date | None:
    """Builds the end date of a closure, if one is explicitly displayed on the webpage.

    This can occur when the closure extends past midnight.

    Args:
        match: A `_CLOSURE_PATTERN` match against the text displayed on the webpage.

    Returns:
        `None` if the match had no explicit end date; otherwise `_build_date_from_match`
        with the `"end"` prefix.
    """
    if match["end_year"] is None:
        return None

    return _build_date_from_match(match, "end")


def _resolve_end_date(
    *,
    start_date: date,
    start_time: time,
    end_time: time,
    end_date: date | None,
) -> date:
    """Resolves the closure end date.

    Args:
        start_date: The start date of the closure.
        start_time: The start time of the closure.
        end_time: The end time of the closure.
        end_date: The end date of the closure, if one is explicitly displayed on the
            webpage. This can occur when the closure extends past midnight.

    Returns:
        `end_date` if provided, `start_date` advanced by one day when `end_time` is
        earlier than `start_time` (the closure runs past midnight), otherwise
        `start_date` unchanged.
    """
    if end_date is not None:
        return end_date

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
        start=start.replace(tzinfo=_LONDON_TZ),
        end=end.replace(tzinfo=_LONDON_TZ),
    )


def _build_closure_from_match(match: re.Match[str]) -> BridgeClosure:
    """Builds a `BridgeClosure` from a `_CLOSURE_PATTERN` match.

    Args:
        match: A `_CLOSURE_PATTERN` match against the text displayed on the webpage.

    Returns:
        `_build_bridge_closure_with_london_timezone` for the start and end dates and
        times from `match`.
    """
    start_date = _build_date_from_match(match, "start")
    start_time = _parse_time(match["start_time"])
    end_time = _parse_time(match["end_time"])
    end_date = _resolve_end_date(
        start_date=start_date,
        start_time=start_time,
        end_time=end_time,
        end_date=_build_end_date_from_match_if_provided(match),
    )

    return _build_bridge_closure_with_london_timezone(
        start=datetime.combine(start_date, start_time),
        end=datetime.combine(end_date, end_time),
    )


def parse_bridge_closures(webpage_text: str) -> list[BridgeClosure]:
    """Parses closures from text displayed on the Renfrew-Yoker bridge closures webpage.

    Args:
        webpage_text: The text displayed on the webpage.

    Returns:
        Closures parsed from the webpage.
    """
    return [
        _build_closure_from_match(match)
        for match in _CLOSURE_PATTERN.finditer(webpage_text)
    ]
