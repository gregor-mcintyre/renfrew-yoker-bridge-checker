import re
from datetime import date, datetime, time, timedelta
from unittest.mock import Mock, call, patch

from bridge_closure import BridgeClosure
from bridge_closures._parsing import (
    _CLOSURE_PATTERN,
    _LONDON_TZ,
    _build_bridge_closure_with_london_timezone,
    _build_closure_from_match,
    _build_date_from_match,
    _build_end_date_from_match_if_provided,
    _parse_time,
    _resolve_end_date,
    parse_bridge_closures,
)
from tests.unit.raspberry_pi.bridge_closures import _patch_targets

_PARSING_MODULE = _patch_targets.BRIDGE_CLOSURES_PACKAGE + "._parsing"
_BUILD_DATE_FROM_MATCH = f"{_PARSING_MODULE}._build_date_from_match"
_BUILD_CLOSURE_FROM_MATCH = f"{_PARSING_MODULE}._build_closure_from_match"

_DATE_LINE = "Tuesday 8th September 2026"
_SAME_DAY_TEXT = f"{_DATE_LINE}\n\n    From 11am to 12:30pm"
_IMPLICIT_ROLLOVER_TEXT = f"{_DATE_LINE}\n\n    From 11pm to 1am"
_EXPLICIT_END_DATE_TEXT = (
    f"{_DATE_LINE}\n\n    From 11pm to Wednesday 9th September 2026 1am"
)

_START_DATE = date(2026, 9, 8)


def _closure_match(displayed_text: str) -> re.Match[str]:
    """Matches `_CLOSURE_PATTERN` against `displayed_text` asserting a closure is found.

    Args:
        displayed_text: Text displayed on the webpage for a single bridge closure.

    Returns:
        The `_CLOSURE_PATTERN` match against `displayed_text`.
    """
    match = _CLOSURE_PATTERN.search(displayed_text)

    assert match is not None

    return match


class TestBuildDateFromMatch:
    def test_start_prefix_returns_start_date(self):
        match = _closure_match(_EXPLICIT_END_DATE_TEXT)

        assert _build_date_from_match(match, "start") == date(2026, 9, 8)

    def test_end_prefix_returns_end_date(self):
        match = _closure_match(_EXPLICIT_END_DATE_TEXT)

        assert _build_date_from_match(match, "end") == date(2026, 9, 9)


class TestParseTime:
    def test_hour_only_returns_time_on_the_hour(self):
        assert _parse_time("8am") == time(8)

    def test_hour_and_minutes_returns_time(self):
        assert _parse_time("9:30pm") == time(21, 30)


class TestBuildEndDateFromMatchIfProvided:
    @patch(_BUILD_DATE_FROM_MATCH)
    def test_match_without_end_date_returns_none(self, mock_build_date_from_match):
        match = _closure_match(_SAME_DAY_TEXT)

        result = _build_end_date_from_match_if_provided(match)

        assert result is None

    @patch(_BUILD_DATE_FROM_MATCH)
    def test_match_with_end_date_returns_the_built_date(
        self,
        mock_build_date_from_match,
    ):
        match = _closure_match(_EXPLICIT_END_DATE_TEXT)

        result = _build_end_date_from_match_if_provided(match)

        mock_build_date_from_match.assert_called_once_with(match, "end")
        assert result == mock_build_date_from_match.return_value


class TestResolveEndDate:
    def test_explicit_end_date_is_returned_unchanged(self):
        end_date = date(2026, 9, 9)

        result = _resolve_end_date(
            start_date=_START_DATE,
            start_time=time(23),
            end_time=time(1),
            end_date=end_date,
        )

        assert result == end_date

    def test_end_time_before_start_time_advances_one_day(self):
        result = _resolve_end_date(
            start_date=_START_DATE,
            start_time=time(23),
            end_time=time(1),
            end_date=None,
        )

        assert result == _START_DATE + timedelta(days=1)

    def test_end_time_after_start_time_returns_start_date(self):
        result = _resolve_end_date(
            start_date=_START_DATE,
            start_time=time(8, 30),
            end_time=time(10),
            end_date=None,
        )

        assert result == _START_DATE


def test_build_bridge_closure_with_london_timezone_sets_zone_on_both_times():
    start = datetime(2026, 9, 8, 23)
    end = datetime(2026, 9, 9, 1)

    result = _build_bridge_closure_with_london_timezone(start=start, end=end)

    assert result == BridgeClosure(
        start=start.replace(tzinfo=_LONDON_TZ),
        end=end.replace(tzinfo=_LONDON_TZ),
    )


@patch(f"{_PARSING_MODULE}._build_bridge_closure_with_london_timezone")
@patch(f"{_PARSING_MODULE}._build_end_date_from_match_if_provided")
@patch(f"{_PARSING_MODULE}._resolve_end_date")
@patch(f"{_PARSING_MODULE}._parse_time")
@patch(_BUILD_DATE_FROM_MATCH)
def test_build_closure_from_match_delegates_each_step_and_returns_the_built_closure(
    mock_build_date_from_match,
    mock_parse_time,
    mock_resolve_end_date,
    mock_build_end_date_from_match_if_provided,
    mock_build_bridge_closure,
):
    start_date = date(2026, 9, 8)
    start_time = time(23)
    end_time = time(1)
    resolved_end_date = date(2026, 9, 9)

    mock_build_date_from_match.return_value = start_date
    mock_parse_time.side_effect = [start_time, end_time]
    mock_resolve_end_date.return_value = resolved_end_date

    match = _closure_match(_IMPLICIT_ROLLOVER_TEXT)

    result = _build_closure_from_match(match)

    mock_build_date_from_match.assert_called_once_with(match, "start")
    assert mock_parse_time.call_args_list == [call("11pm"), call("1am")]
    mock_build_end_date_from_match_if_provided.assert_called_once_with(match)
    mock_resolve_end_date.assert_called_once_with(
        start_date=start_date,
        start_time=start_time,
        end_time=end_time,
        end_date=mock_build_end_date_from_match_if_provided.return_value,
    )
    mock_build_bridge_closure.assert_called_once_with(
        start=datetime(2026, 9, 8, 23),
        end=datetime(2026, 9, 9, 1),
    )
    assert result == mock_build_bridge_closure.return_value


class TestParseBridgeClosures:
    @patch(_BUILD_CLOSURE_FROM_MATCH)
    def test_returns_empty_list_when_no_closure_is_matched(
        self,
        mock_build_closure_from_match,
    ):
        page_text = f"{_DATE_LINE}\n\n    No Closures Currently Planned."

        result = parse_bridge_closures(page_text)

        assert result == []

    @patch(_BUILD_CLOSURE_FROM_MATCH)
    def test_tolerates_markup_between_the_date_and_time_lines(
        self,
        mock_build_closure_from_match,
    ):
        page_text = f"{_DATE_LINE}</td><td>\n  <span>\nFrom 9am to 12:30pm"

        result = parse_bridge_closures(page_text)

        assert result == [mock_build_closure_from_match.return_value]

    @patch(_BUILD_CLOSURE_FROM_MATCH)
    def test_matches_a_closure_with_an_explicit_end_date_line(
        self,
        mock_build_closure_from_match,
    ):
        result = parse_bridge_closures(_EXPLICIT_END_DATE_TEXT)

        assert result == [mock_build_closure_from_match.return_value]

    @patch(_BUILD_CLOSURE_FROM_MATCH)
    def test_builds_one_closure_per_match_in_page_order(
        self,
        mock_build_closure_from_match,
    ):
        first_closure = Mock()
        second_closure = Mock()
        page_text = f"{_SAME_DAY_TEXT}\n{_DATE_LINE}\n\n    From 9am to 10:30am"

        mock_build_closure_from_match.side_effect = [first_closure, second_closure]

        result = parse_bridge_closures(page_text)

        assert result == [first_closure, second_closure]
