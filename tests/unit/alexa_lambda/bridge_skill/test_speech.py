from datetime import date, datetime, timedelta
from unittest.mock import Mock, call, patch

import pytest

from bridge_closure import LONDON_TZ, BridgeClosure, ClosedTo
from bridge_skill._speech import (
    _BRIDGE_NAME,
    _CLOSED_TO_WORDING,
    _NO_UPCOMING_SPEECH,
    _STALE_AFTER,
    _STALE_SPEECH,
    _describe_day,
    _describe_status,
    _format_day,
    _format_reopening,
    _format_time,
    _format_window,
    _join_windows,
    describe_bridge_closures,
)
from closure_cache import CachedBridgeClosures
from tests import patch_targets

_SPEECH_MODULE = patch_targets.BRIDGE_SKILL_PACKAGE + "._speech"
_FORMAT_DAY = f"{_SPEECH_MODULE}._format_day"
_FORMAT_TIME = f"{_SPEECH_MODULE}._format_time"

_NOW = datetime(2026, 9, 29, 12, tzinfo=LONDON_TZ)

_OPEN_SPEECH = f"The {_BRIDGE_NAME} is open now."

_START_TEXT = "start time"
_END_TEXT = "end time"
_STATUS_TEXT = "status text"
_DAY_TEXT = "day text"


def _closure_starting_at(
    start: datetime,
    *,
    closed_to: ClosedTo = ClosedTo.EVERYONE,
) -> BridgeClosure:
    """Builds a closure that lasts one hour.

    Args:
        start: The date and time the closure starts.
        closed_to: Who the bridge is closed to.

    Returns:
        A closure from `start` to one hour later, closed to `closed_to`.
    """
    return BridgeClosure(
        start=start,
        end=start + timedelta(hours=1),
        closed_to=closed_to,
    )


def _stub_time_text(mock_format_time: Mock, closure: BridgeClosure) -> None:
    """Makes a mocked `_format_time` return different text for each time of a closure.

    Args:
        mock_format_time: The mock replacing `_format_time`.
        closure: The closure whose start and end are told apart.
    """
    mock_format_time.side_effect = {
        closure.start: _START_TEXT,
        closure.end: _END_TEXT,
    }.__getitem__


class TestFormatTime:
    def test_midnight_renders_as_12am(self):
        result = _format_time(datetime(2026, 9, 29, 0))

        assert result == "12am"

    def test_noon_renders_as_12pm(self):
        result = _format_time(datetime(2026, 9, 29, 12))

        assert result == "12pm"

    def test_full_hour_leaves_out_the_minutes(self):
        result = _format_time(datetime(2026, 9, 29, 10))

        assert result == "10am"

    def test_single_digit_minutes_are_zero_padded(self):
        result = _format_time(datetime(2026, 9, 29, 9, 5))

        assert result == "9:05am"

    def test_afternoon_uses_a_12_hour_clock(self):
        result = _format_time(datetime(2026, 9, 29, 15, 30))

        assert result == "3:30pm"

    def test_renders_the_hour_and_minutes(self):
        result = _format_time(datetime(2026, 9, 29, 8, 55))

        assert result == "8:55am"


class TestFormatDay:
    def test_same_day_renders_today(self):
        today = date(2026, 9, 29)

        result = _format_day(today, today=today)

        assert result == "today"

    def test_next_day_renders_tomorrow(self):
        result = _format_day(date(2026, 9, 30), today=date(2026, 9, 29))

        assert result == "tomorrow"

    def test_first_of_next_month_renders_tomorrow(self):
        result = _format_day(date(2026, 10, 1), today=date(2026, 9, 30))

        assert result == "tomorrow"


@patch(_FORMAT_DAY)
@patch(_FORMAT_TIME)
class TestFormatReopening:
    def test_same_day_returns_only_the_time(self, mock_format_time, mock_format_day):
        result = _format_reopening(_NOW + timedelta(minutes=30), now=_NOW)

        assert result == mock_format_time.return_value

    def test_same_day_names_no_day(self, mock_format_time, mock_format_day):
        _format_reopening(_NOW + timedelta(minutes=30), now=_NOW)

        mock_format_day.assert_not_called()

    def test_formats_the_reopening_time(self, mock_format_time, mock_format_day):
        reopens_at = _NOW + timedelta(days=1)

        _format_reopening(reopens_at, now=_NOW)

        mock_format_time.assert_called_once_with(reopens_at)

    def test_formats_the_reopening_day_relative_to_today(
        self,
        mock_format_time,
        mock_format_day,
    ):
        reopens_at = _NOW + timedelta(days=1)

        _format_reopening(reopens_at, now=_NOW)

        mock_format_day.assert_called_once_with(reopens_at.date(), today=_NOW.date())

    def test_returns_the_time_followed_by_the_day(
        self,
        mock_format_time,
        mock_format_day,
    ):
        result = _format_reopening(_NOW + timedelta(days=1), now=_NOW)

        expected = f"{mock_format_time.return_value} {mock_format_day.return_value}"
        assert result == expected


@patch(f"{_SPEECH_MODULE}._format_reopening")
class TestDescribeStatus:
    def test_no_closures_say_the_bridge_is_open(self, mock_format_reopening):
        result = _describe_status([], now=_NOW)

        assert result == _OPEN_SPEECH

    def test_closure_that_has_ended_says_the_bridge_is_open(
        self,
        mock_format_reopening,
    ):
        closure = _closure_starting_at(_NOW - timedelta(hours=3))

        result = _describe_status([closure], now=_NOW)

        assert result == _OPEN_SPEECH

    def test_closure_still_to_come_says_the_bridge_is_open(
        self,
        mock_format_reopening,
    ):
        closure = _closure_starting_at(_NOW + timedelta(hours=1))

        result = _describe_status([closure], now=_NOW)

        assert result == _OPEN_SPEECH

    def test_closure_ending_now_says_the_bridge_is_open(self, mock_format_reopening):
        closure = _closure_starting_at(_NOW - timedelta(hours=1))

        result = _describe_status([closure], now=_NOW)

        assert result == _OPEN_SPEECH

    def test_closure_starting_now_says_the_bridge_is_closed(
        self,
        mock_format_reopening,
    ):
        closure = _closure_starting_at(_NOW)

        result = _describe_status([closure], now=_NOW)

        expected = (
            f"The {_BRIDGE_NAME} is closed now, until "
            f"{mock_format_reopening.return_value}."
        )
        assert result == expected

    def test_formats_the_end_of_the_closure_in_progress(self, mock_format_reopening):
        past = _closure_starting_at(_NOW - timedelta(hours=3))
        in_progress = _closure_starting_at(_NOW - timedelta(minutes=30))
        upcoming = _closure_starting_at(_NOW + timedelta(hours=3))

        _describe_status([past, in_progress, upcoming], now=_NOW)

        mock_format_reopening.assert_called_once_with(in_progress.end, now=_NOW)

    @pytest.mark.parametrize("closed_to", [ClosedTo.VEHICLES, ClosedTo.PEDESTRIANS])
    def test_closure_for_some_traffic_says_who_the_bridge_is_closed_to(
        self,
        mock_format_reopening,
        closed_to,
    ):
        closure = _closure_starting_at(
            _NOW - timedelta(minutes=30),
            closed_to=closed_to,
        )

        result = _describe_status([closure], now=_NOW)

        expected = (
            f"The {_BRIDGE_NAME} is closed{_CLOSED_TO_WORDING[closed_to]} now, until "
            f"{mock_format_reopening.return_value}."
        )
        assert result == expected

    def test_says_the_bridge_is_closed_until_it_reopens(self, mock_format_reopening):
        closure = _closure_starting_at(_NOW - timedelta(minutes=30))

        result = _describe_status([closure], now=_NOW)

        expected = (
            f"The {_BRIDGE_NAME} is closed now, until "
            f"{mock_format_reopening.return_value}."
        )
        assert result == expected


@patch(_FORMAT_TIME)
class TestFormatWindow:
    def test_closure_starting_tomorrow_and_ending_the_day_after_says_the_next_day(
        self,
        mock_format_time,
    ):
        start = datetime(2026, 9, 30, 22, tzinfo=LONDON_TZ)
        closure = BridgeClosure(
            start=start,
            end=start + timedelta(hours=3),
            closed_to=ClosedTo.EVERYONE,
        )

        _stub_time_text(mock_format_time, closure)

        result = _format_window(closure, today=_NOW.date())

        assert result == f"from {_START_TEXT} until {_END_TEXT} the next day"

    def test_closure_starting_today_and_ending_tomorrow_says_tomorrow(
        self,
        mock_format_time,
    ):
        start = datetime(2026, 9, 29, 22, tzinfo=LONDON_TZ)
        closure = BridgeClosure(
            start=start,
            end=start + timedelta(hours=3),
            closed_to=ClosedTo.EVERYONE,
        )

        _stub_time_text(mock_format_time, closure)

        result = _format_window(closure, today=_NOW.date())

        assert result == f"from {_START_TEXT} until {_END_TEXT} tomorrow"

    def test_formats_the_start_and_end_times(self, mock_format_time):
        closure = _closure_starting_at(_NOW)

        _stub_time_text(mock_format_time, closure)

        _format_window(closure, today=_NOW.date())

        assert mock_format_time.call_args_list == [
            call(closure.start),
            call(closure.end),
        ]

    def test_returns_the_start_and_end_times(self, mock_format_time):
        closure = _closure_starting_at(_NOW)

        _stub_time_text(mock_format_time, closure)

        result = _format_window(closure, today=_NOW.date())

        assert result == f"from {_START_TEXT} to {_END_TEXT}"


class TestJoinWindows:
    def test_single_window_is_returned_unchanged(self):
        result = _join_windows(["first"])

        assert result == "first"

    def test_three_windows_put_and_again_before_the_last(self):
        result = _join_windows(["first", "second", "third"])

        assert result == "first, second, and again third"

    def test_two_windows_are_joined_with_and_again(self):
        result = _join_windows(["first", "second"])

        assert result == "first, and again second"


@patch(f"{_SPEECH_MODULE}._join_windows")
@patch(f"{_SPEECH_MODULE}._format_window")
@patch(_FORMAT_DAY)
class TestDescribeDay:
    def test_formats_the_day_of_the_first_closure_relative_to_today(
        self,
        mock_format_day,
        mock_format_window,
        mock_join_windows,
    ):
        first = _closure_starting_at(_NOW)
        second = _closure_starting_at(_NOW + timedelta(hours=3))

        _describe_day([first, second], today=_NOW.date())

        mock_format_day.assert_called_once_with(first.start.date(), today=_NOW.date())

    def test_formats_the_window_of_every_closure(
        self,
        mock_format_day,
        mock_format_window,
        mock_join_windows,
    ):
        first = _closure_starting_at(_NOW)
        second = _closure_starting_at(_NOW + timedelta(hours=3))

        _describe_day([first, second], today=_NOW.date())

        assert mock_format_window.call_args_list == [
            call(first, today=_NOW.date()),
            call(second, today=_NOW.date()),
        ]

    def test_joins_the_windows_of_every_closure(
        self,
        mock_format_day,
        mock_format_window,
        mock_join_windows,
    ):
        closures = [
            _closure_starting_at(_NOW),
            _closure_starting_at(_NOW + timedelta(hours=3)),
        ]

        mock_format_window.side_effect = ["first window", "second window"]

        _describe_day(closures, today=_NOW.date())

        mock_join_windows.assert_called_once_with(["first window", "second window"])

    @pytest.mark.parametrize("closed_to", [ClosedTo.VEHICLES, ClosedTo.PEDESTRIANS])
    def test_closures_for_some_traffic_say_who_the_bridge_closes_to(
        self,
        mock_format_day,
        mock_format_window,
        mock_join_windows,
        closed_to,
    ):
        closure = _closure_starting_at(_NOW, closed_to=closed_to)

        result = _describe_day([closure], today=_NOW.date())

        expected = (
            f"It closes{_CLOSED_TO_WORDING[closed_to]} {mock_format_day.return_value} "
            f"{mock_join_windows.return_value}."
        )
        assert result == expected

    def test_describes_the_day_and_the_joined_windows(
        self,
        mock_format_day,
        mock_format_window,
        mock_join_windows,
    ):
        closure = _closure_starting_at(_NOW)

        result = _describe_day([closure], today=_NOW.date())

        expected = (
            f"It closes {mock_format_day.return_value} "
            f"{mock_join_windows.return_value}."
        )
        assert result == expected


@patch(f"{_SPEECH_MODULE}._describe_day", return_value=_DAY_TEXT)
@patch(f"{_SPEECH_MODULE}._describe_status", return_value=_STATUS_TEXT)
class TestDescribeBridgeClosures:
    def test_stale_cache_returns_the_stale_speech(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        cached = CachedBridgeClosures(
            closures=[],
            fetched_at=_NOW - _STALE_AFTER - timedelta(seconds=1),
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == _STALE_SPEECH

    def test_stale_cache_describes_nothing(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        cached = CachedBridgeClosures(
            closures=[_closure_starting_at(_NOW + timedelta(hours=1))],
            fetched_at=_NOW - _STALE_AFTER - timedelta(seconds=1),
        )

        describe_bridge_closures(cached, now=_NOW)

        mock_describe_status.assert_not_called()
        mock_describe_day.assert_not_called()

    def test_cache_exactly_an_hour_old_is_not_stale(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        cached = CachedBridgeClosures(
            closures=[],
            fetched_at=_NOW - _STALE_AFTER,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result != _STALE_SPEECH

    def test_describes_the_status_of_every_closure(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        cached = CachedBridgeClosures(
            closures=[
                _closure_starting_at(_NOW - timedelta(hours=3)),
                _closure_starting_at(_NOW + timedelta(hours=3)),
            ],
            fetched_at=_NOW,
        )

        describe_bridge_closures(cached, now=_NOW)

        mock_describe_status.assert_called_once_with(cached.closures, now=_NOW)

    def test_closure_already_started_is_not_upcoming(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        cached = CachedBridgeClosures(
            closures=[
                _closure_starting_at(_NOW - timedelta(hours=3)),
                _closure_starting_at(_NOW),
            ],
            fetched_at=_NOW,
        )

        describe_bridge_closures(cached, now=_NOW)

        mock_describe_day.assert_not_called()

    def test_closure_starting_after_tomorrow_is_not_described(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        day_after_tomorrow = datetime(2026, 10, 1, tzinfo=LONDON_TZ)
        cached = CachedBridgeClosures(
            closures=[_closure_starting_at(day_after_tomorrow)],
            fetched_at=_NOW,
        )

        describe_bridge_closures(cached, now=_NOW)

        mock_describe_day.assert_not_called()

    def test_no_upcoming_closures_say_none_are_listed(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        cached = CachedBridgeClosures(closures=[], fetched_at=_NOW)

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == f"{mock_describe_status.return_value} {_NO_UPCOMING_SPEECH}"

    def test_closure_starting_late_tomorrow_is_described(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        late_tomorrow = _closure_starting_at(
            datetime(2026, 9, 30, 23, 59, tzinfo=LONDON_TZ),
        )
        cached = CachedBridgeClosures(closures=[late_tomorrow], fetched_at=_NOW)

        describe_bridge_closures(cached, now=_NOW)

        mock_describe_day.assert_called_once_with([late_tomorrow], today=_NOW.date())

    def test_groups_closures_starting_on_the_same_day(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        first = _closure_starting_at(_NOW + timedelta(hours=1))
        second = _closure_starting_at(_NOW + timedelta(hours=3))
        cached = CachedBridgeClosures(closures=[first, second], fetched_at=_NOW)

        describe_bridge_closures(cached, now=_NOW)

        mock_describe_day.assert_called_once_with([first, second], today=_NOW.date())

    def test_closures_on_one_day_for_different_traffic_are_described_separately(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        first = _closure_starting_at(_NOW + timedelta(hours=1))
        second = _closure_starting_at(
            _NOW + timedelta(hours=2),
            closed_to=ClosedTo.VEHICLES,
        )
        third = _closure_starting_at(_NOW + timedelta(hours=3))
        cached = CachedBridgeClosures(closures=[first, second, third], fetched_at=_NOW)

        describe_bridge_closures(cached, now=_NOW)

        assert mock_describe_day.call_args_list == [
            call([first], today=_NOW.date()),
            call([second], today=_NOW.date()),
            call([third], today=_NOW.date()),
        ]

    def test_sorts_the_closures_of_a_day_by_start(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        earlier = _closure_starting_at(_NOW + timedelta(hours=1))
        later = _closure_starting_at(_NOW + timedelta(hours=3))
        cached = CachedBridgeClosures(closures=[later, earlier], fetched_at=_NOW)

        describe_bridge_closures(cached, now=_NOW)

        mock_describe_day.assert_called_once_with([earlier, later], today=_NOW.date())

    def test_describes_each_day_in_date_order(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        sooner = _closure_starting_at(_NOW + timedelta(hours=3))
        later = _closure_starting_at(_NOW + timedelta(days=1))
        cached = CachedBridgeClosures(closures=[later, sooner], fetched_at=_NOW)

        describe_bridge_closures(cached, now=_NOW)

        assert mock_describe_day.call_args_list == [
            call([sooner], today=_NOW.date()),
            call([later], today=_NOW.date()),
        ]

    def test_joins_the_status_and_each_day_with_spaces(
        self,
        mock_describe_status,
        mock_describe_day,
    ):
        cached = CachedBridgeClosures(
            closures=[
                _closure_starting_at(_NOW + timedelta(hours=3)),
                _closure_starting_at(_NOW + timedelta(days=1)),
            ],
            fetched_at=_NOW,
        )

        mock_describe_day.side_effect = ["first day", "second day"]

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == f"{mock_describe_status.return_value} first day second day"
