"""Describes Renfrew-Yoker bridge closures as sentences for Alexa to speak."""

from datetime import date, datetime, timedelta
from itertools import groupby

from bridge_closure import BridgeClosure
from closure_cache import CachedBridgeClosures

# How old the cache can be before it is no longer trusted
_STALE_AFTER = timedelta(hours=1)

_BRIDGE_NAME = "Renfrew-Yoker bridge"

_STALE_SPEECH = (
    "I haven't been able to check Renfrewshire Council's website for "
    f"{_BRIDGE_NAME} closures recently, so please check it directly."
)
_NO_UPCOMING_SPEECH = "No upcoming closures are listed."


def _format_time(value: datetime) -> str:
    """Renders the time of a datetime as a spoken 12-hour clock time.

    Args:
        value: The datetime to render the time of.

    Returns:
        A time such as `"8:55am"`, with the minutes left out on the hour, for example,
        `"10am"`.
    """
    hour = value.hour % 12 or 12
    meridiem = "am" if value.hour < 12 else "pm"

    if value.minute == 0:
        return f"{hour}{meridiem}"

    return f"{hour}:{value.minute:02d}{meridiem}"


def _format_day(day: date, *, today: date) -> str:
    """Renders a date as a spoken phrase relative to today.

    Args:
        day: The date to render, which is today or tomorrow.
        today: The current date.

    Returns:
        `"today"` if `day` is `today`, otherwise `"tomorrow"`.
    """
    if day == today:
        return "today"

    return "tomorrow"


def _format_reopening(reopens_at: datetime, *, now: datetime) -> str:
    """Renders when a bridge that is closed now reopens.

    Args:
        reopens_at: The date and time the bridge reopens.
        now: The current date and time.

    Returns:
        The time the bridge reopens, for example, `"12:30pm"`, followed by the day when
        that is not today, for example, `"1am tomorrow"`. The day is worded by
        `_format_day`.
    """
    reopening_day = reopens_at.date()
    reopening_time = _format_time(reopens_at)

    if reopening_day == now.date():
        return reopening_time

    return f"{reopening_time} {_format_day(reopening_day, today=now.date())}"


def _describe_status(closures: list[BridgeClosure], *, now: datetime) -> str:
    """Describes whether the bridge is closed now.

    Args:
        closures: The bridge closures to look through.
        now: The current date and time.

    Returns:
        A sentence saying the bridge is open, or closed until the time that
        `_format_reopening` gives.
    """
    current_closure = next(
        (closure for closure in closures if closure.start <= now < closure.end),
        None,
    )

    if current_closure is None:
        return f"The {_BRIDGE_NAME} is open now."

    reopening = _format_reopening(current_closure.end, now=now)

    return f"The {_BRIDGE_NAME} is closed now, until {reopening}."


def _format_window(closure: BridgeClosure) -> str:
    """Renders the times a closure runs from and to.

    Args:
        closure: The closure to render.

    Returns:
        A phrase such as `"from 8:55am to 10am"`. A closure that ends on the next day
        reads `"from 11pm until 1am the next day"`.
    """
    start = _format_time(closure.start)
    end = _format_time(closure.end)

    if closure.end.date() == closure.start.date():
        return f"from {start} to {end}"

    return f"from {start} until {end} the next day"


def _join_windows(windows: list[str]) -> str:
    """Joins the times of the closures on one day into a spoken list.

    Args:
        windows: The times of each closure, as `_format_window` words them.

    Returns:
        The times separated by commas, with `", and again "` in front of the last when
        there are several, such as `"from 9am to 10am, from 12pm to 1pm, and again from
        3pm to 4pm"`.
    """
    *earlier_windows, last_window = windows

    if not earlier_windows:
        return last_window

    return f"{', '.join(earlier_windows)}, and again {last_window}"


def _describe_day(closures: list[BridgeClosure], *, today: date) -> str:
    """Describes every closure that starts on one day in a single sentence.

    Args:
        closures: The closures to describe. All of them start on the same date.
        today: The current date.

    Returns:
        A sentence naming the day as `_format_day` words it, followed by the closures
        as `_join_windows` joins them, such as `"It closes tomorrow from 9am to 12:30pm,
        and again from 2pm to 3pm."`.
    """
    day = _format_day(closures[0].start.date(), today=today)
    windows = [_format_window(closure) for closure in closures]

    return f"It closes {day} {_join_windows(windows)}."


def describe_bridge_closures(cached: CachedBridgeClosures, *, now: datetime) -> str:
    """Describes cached bridge closures as the sentences Alexa speaks.

    Args:
        cached: The cached bridge closures to describe.
        now: The current date and time.

    Returns:
        A request to check the council website instead, if `cached` was fetched too
        long before `now` to be trusted. Otherwise the sentence `_describe_status`
        gives, followed by the sentence `_describe_day` gives for each of today and
        tomorrow with a closure still to come, in date order, or by
        `_NO_UPCOMING_SPEECH` if there is none. Closures that have ended, or that start
        after tomorrow, are not mentioned.
    """
    if now - cached.fetched_at > _STALE_AFTER:
        return _STALE_SPEECH

    status = _describe_status(cached.closures, now=now)
    tomorrow = now.date() + timedelta(days=1)

    # It is not known that the council webpage can list closures beyond tomorrow, so
    # tomorrow is the furthest `_format_day` can word
    upcoming_closures = sorted(
        (
            closure
            for closure in cached.closures
            if closure.start > now and closure.start.date() <= tomorrow
        ),
        key=lambda closure: closure.start,
    )

    day_sentences = [
        _describe_day(list(day_closures), today=now.date())
        for _, day_closures in groupby(
            upcoming_closures,
            key=lambda closure: closure.start.date(),
        )
    ]

    return " ".join([status, *(day_sentences or [_NO_UPCOMING_SPEECH])])
