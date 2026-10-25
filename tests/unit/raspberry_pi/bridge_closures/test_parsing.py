import re
from datetime import date, datetime, time, timedelta
from unittest.mock import ANY, Mock, call, patch

import pytest

from bridge_closure import ClosedTo
from bridge_closures._parsing import (
    _CLOSURE_LISTING_PATTERN,
    _build_bridge_closure_with_london_timezone,
    _build_closure_from_match,
    _build_date_from_match,
    _parse_time,
    _resolve_closed_to,
    _resolve_end_date,
    parse_bridge_closures,
)
from tests import closures_webpage_text, patch_targets
from tests.closure_data import BRIDGE_CLOSURE

_PARSING_MODULE = patch_targets.BRIDGE_CLOSURES_PACKAGE + "._parsing"

_ROLLOVER_START_TIME = "11pm"
_ROLLOVER_END_TIME = "1am"
_IMPLICIT_ROLLOVER_TIME_RANGE = f"From {_ROLLOVER_START_TIME} to {_ROLLOVER_END_TIME}"
_WEEKDAY_NOTED_TIME_RANGE = "6.00pm Saturday to 6.00am Sunday"

_START_DATE = date(2026, 9, 15)

_VEHICLES_ONLY_NOTICE = "The bridge will be closed to vehicular traffic as follows:"


def _first_match(displayed_text: str) -> re.Match[str]:
    """Matches `_CLOSURE_LISTING_PATTERN` against `displayed_text`.

    Args:
        displayed_text: Text displayed on the webpage containing a date heading or a
            time range.

    Returns:
        The first `_CLOSURE_LISTING_PATTERN` match against `displayed_text`.
    """
    match = _CLOSURE_LISTING_PATTERN.search(displayed_text)

    assert match is not None

    return match


@pytest.mark.parametrize(
    "date_heading",
    [
        pytest.param(closures_webpage_text.DATE_HEADING, id="ordinal-suffix"),
        pytest.param("Tuesday 15 September 2026", id="no-ordinal-suffix"),
    ],
)
def test_build_date_from_match_returns_the_date(date_heading):
    match = _first_match(date_heading)

    result = _build_date_from_match(match)

    assert result == _START_DATE


class TestResolveClosedTo:
    def test_neither_vehicles_nor_pedestrians_returns_everyone(self):
        result = _resolve_closed_to("cyclists ")

        assert result == ClosedTo.EVERYONE

    @pytest.mark.parametrize(
        "traffic",
        [
            pytest.param("road ", id="road"),
            pytest.param("vehicular ", id="vehicular"),
            pytest.param("vehicles and cyclists ", id="vehicles-and-cyclists"),
        ],
    )
    def test_vehicles_without_pedestrians_returns_vehicles(self, traffic):
        result = _resolve_closed_to(traffic)

        assert result == ClosedTo.VEHICLES

    @pytest.mark.parametrize(
        "traffic",
        [
            pytest.param("pedestrian ", id="pedestrian"),
            pytest.param("pedestrians and cyclists ", id="pedestrians-and-cyclists"),
        ],
    )
    def test_pedestrians_without_vehicles_returns_pedestrians(self, traffic):
        result = _resolve_closed_to(traffic)

        assert result == ClosedTo.PEDESTRIANS

    @pytest.mark.parametrize(
        "traffic",
        [
            pytest.param("both road and pedestrian ", id="road-and-pedestrian"),
            pytest.param("pedestrian & road ", id="pedestrian-and-road"),
        ],
    )
    def test_vehicles_and_pedestrians_returns_everyone(self, traffic):
        result = _resolve_closed_to(traffic)

        assert result == ClosedTo.EVERYONE


@pytest.mark.parametrize(
    ("raw", "expected_time"),
    [
        pytest.param("8am", time(8), id="hour-only"),
        pytest.param("8:30am", time(8, 30), id="colon-minutes"),
        pytest.param("10.45pm", time(22, 45), id="dot-minutes"),
        pytest.param("11.10 am", time(11, 10), id="spaced-meridiem"),
    ],
)
def test_parse_time_returns_the_time(raw, expected_time):
    result = _parse_time(raw)

    assert result == expected_time


class TestResolveEndDate:
    def test_end_time_before_start_time_advances_by_one_day(self):
        result = _resolve_end_date(
            start_date=_START_DATE,
            start_time=time(23),
            end_time=time(1),
        )

        assert result == _START_DATE + timedelta(days=1)

    def test_end_time_after_start_time_returns_start_date(self):
        result = _resolve_end_date(
            start_date=_START_DATE,
            start_time=time(8, 30),
            end_time=time(10),
        )

        assert result == _START_DATE


def test_build_bridge_closure_with_london_timezone_sets_london_timezone_on_both_times():
    start = datetime(2026, 9, 15, 9)
    end = datetime(2026, 9, 15, 12, 30)

    result = _build_bridge_closure_with_london_timezone(
        start=start,
        end=end,
        closed_to=BRIDGE_CLOSURE.closed_to,
    )

    assert result == BRIDGE_CLOSURE


@patch(f"{_PARSING_MODULE}._build_bridge_closure_with_london_timezone")
@patch(f"{_PARSING_MODULE}._resolve_end_date")
@patch(f"{_PARSING_MODULE}._parse_time")
def test_build_closure_from_match_delegates_each_step_and_returns_the_built_closure(
    mock_parse_time,
    mock_resolve_end_date,
    mock_build_bridge_closure,
):
    start_time = time(23)
    end_time = time(1)
    resolved_end_date = date(2026, 9, 16)
    closed_to = Mock()

    mock_parse_time.side_effect = [start_time, end_time]
    mock_resolve_end_date.return_value = resolved_end_date

    match = _first_match(_IMPLICIT_ROLLOVER_TIME_RANGE)

    result = _build_closure_from_match(_START_DATE, match, closed_to=closed_to)

    assert mock_parse_time.call_args_list == [
        call(_ROLLOVER_START_TIME),
        call(_ROLLOVER_END_TIME),
    ]
    mock_resolve_end_date.assert_called_once_with(
        start_date=_START_DATE,
        start_time=start_time,
        end_time=end_time,
    )
    mock_build_bridge_closure.assert_called_once_with(
        start=datetime(2026, 9, 15, 23),
        end=datetime(2026, 9, 16, 1),
        closed_to=closed_to,
    )

    assert result == mock_build_bridge_closure.return_value


@patch(f"{_PARSING_MODULE}._resolve_closed_to")
@patch(f"{_PARSING_MODULE}._build_closure_from_match")
@patch(f"{_PARSING_MODULE}._build_date_from_match")
class TestParseBridgeClosures:
    def test_no_date_heading_returns_empty_list(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
    ):
        result = parse_bridge_closures(
            closures_webpage_text.NO_CLOSURES_LINE_CAPITALISED,
        )

        assert result == []

    def test_ignores_a_time_range_before_the_first_date_heading(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
    ):
        result = parse_bridge_closures(closures_webpage_text.TIME_RANGE)

        assert result == []

    @pytest.mark.parametrize(
        "no_closures_line",
        [
            pytest.param(
                closures_webpage_text.NO_CLOSURES_LINE_CAPITALISED,
                id="capitalised",
            ),
            pytest.param(
                closures_webpage_text.NO_CLOSURES_LINE_LOWERCASE,
                id="lowercase",
            ),
        ],
    )
    def test_date_heading_without_time_range_returns_empty_list(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
        no_closures_line,
    ):
        result = parse_bridge_closures(
            f"{closures_webpage_text.DATE_HEADING}\n\n{no_closures_line}",
        )

        assert result == []

    def test_builds_no_closure_from_the_last_updated_line(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
    ):
        webpage_text = (
            f"{closures_webpage_text.DATE_HEADING}"
            f"\n{closures_webpage_text.TIME_RANGE}"
            f"\n{closures_webpage_text.LAST_UPDATED_LINE}"
        )

        parse_bridge_closures(webpage_text)

        mock_build_closure_from_match.assert_called_once()

    @pytest.mark.parametrize(
        "webpage_text",
        [
            pytest.param(
                f"<h3>{closures_webpage_text.DATE_HEADING}</h3>"
                f"\n  <p>\n{closures_webpage_text.TIME_RANGE}</p>",
                id="markup-between-heading-and-range",
            ),
            pytest.param(
                f"{closures_webpage_text.DATE_HEADING}"
                f"\n\n{closures_webpage_text.CLOSURE_NOTICE}"
                f"\n\n{closures_webpage_text.TIME_RANGE}",
                id="heading-before-notice",
            ),
            pytest.param(
                f"{closures_webpage_text.CLOSURE_NOTICE}"
                f"\n\n{closures_webpage_text.DATE_HEADING}"
                f"\n\n{closures_webpage_text.TIME_RANGE}",
                id="heading-after-notice",
            ),
        ],
    )
    def test_known_layout_returns_the_closure(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
        webpage_text,
    ):
        result = parse_bridge_closures(webpage_text)

        assert result == [mock_build_closure_from_match.return_value]

    @pytest.mark.parametrize(
        "time_range",
        [
            pytest.param(closures_webpage_text.TIME_RANGE, id="with-from"),
            pytest.param("8am to 9am", id="without-from"),
            pytest.param("From 8.00am to 9.00pm", id="dot-minutes"),
            pytest.param("From 11.10 am to 1.00pm", id="spaced-meridiem"),
            pytest.param("11.25pm (14th) to 12.30am (15th)", id="day-notes"),
            pytest.param(_WEEKDAY_NOTED_TIME_RANGE, id="weekday-notes"),
            pytest.param("12:40pm - 1:10pm", id="hyphen-separator"),
            pytest.param("12:40pm – 1:10pm", id="en-dash-separator"),
        ],
    )
    def test_known_time_range_format_returns_the_closure(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
        time_range,
    ):
        result = parse_bridge_closures(
            f"{closures_webpage_text.DATE_HEADING}\n\n{time_range}",
        )

        assert result == [mock_build_closure_from_match.return_value]

    def test_closure_listed_twice_is_returned_once(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
    ):
        section = (
            f"{closures_webpage_text.DATE_HEADING}\n{closures_webpage_text.TIME_RANGE}"
        )

        result = parse_bridge_closures(f"{section}\n{section}")

        assert result == [mock_build_closure_from_match.return_value]

    @pytest.mark.parametrize(
        "first_time_range",
        [
            pytest.param(closures_webpage_text.TIME_RANGE, id="no-day-notes"),
            pytest.param(_WEEKDAY_NOTED_TIME_RANGE, id="weekday-notes"),
        ],
    )
    def test_assigns_each_time_range_to_the_date_heading_above_it(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
        first_time_range,
    ):
        first_date = Mock()
        second_date = Mock()
        webpage_text = (
            f"{closures_webpage_text.DATE_HEADING}"
            f"\n{first_time_range}\n"
            f"{'Wednesday 16th September 2026'}"
            f"\n{_IMPLICIT_ROLLOVER_TIME_RANGE}"
        )

        mock_build_date_from_match.side_effect = [first_date, second_date]

        parse_bridge_closures(webpage_text)

        assert mock_build_closure_from_match.call_args_list == [
            call(first_date, ANY, closed_to=ANY),
            call(second_date, ANY, closed_to=ANY),
        ]

    def test_builds_one_closure_per_time_range_under_a_date_heading(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
    ):
        first_closure = Mock()
        second_closure = Mock()
        webpage_text = (
            f"{closures_webpage_text.DATE_HEADING}"
            f"\n{closures_webpage_text.TIME_RANGE}"
            f"\n{_IMPLICIT_ROLLOVER_TIME_RANGE}"
        )

        mock_build_closure_from_match.side_effect = [first_closure, second_closure]

        result = parse_bridge_closures(webpage_text)

        assert result == [first_closure, second_closure]

    def test_page_title_is_not_a_notice(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
    ):
        webpage_text = (
            "Check when Renfrew Bridge is closed to vehicles, pedestrians, and cyclists"
            f"\n{closures_webpage_text.DATE_HEADING}"
            f"\n{closures_webpage_text.TIME_RANGE}"
        )

        parse_bridge_closures(webpage_text)

        mock_resolve_closed_to.assert_not_called()

    def test_closure_before_any_notice_applies_to_everyone(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
    ):
        parse_bridge_closures(
            f"{closures_webpage_text.DATE_HEADING}\n{closures_webpage_text.TIME_RANGE}",
        )

        mock_build_closure_from_match.assert_called_once_with(
            ANY,
            ANY,
            closed_to=ClosedTo.EVERYONE,
        )

    @pytest.mark.parametrize(
        ("notice", "traffic"),
        [
            pytest.param(
                closures_webpage_text.CLOSURE_NOTICE,
                "both road and pedestrian ",
                id="road-and-pedestrian",
            ),
            pytest.param(
                "The bridge will be closed to pedestrian & road traffic:",
                "pedestrian & road ",
                id="pedestrian-and-road",
            ),
            pytest.param(_VEHICLES_ONLY_NOTICE, "vehicular ", id="vehicular"),
        ],
    )
    def test_notice_resolves_who_the_bridge_is_closed_to_from_its_traffic_words(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
        notice,
        traffic,
    ):
        parse_bridge_closures(notice)

        mock_resolve_closed_to.assert_called_once_with(traffic)

    def test_notice_on_the_same_line_as_a_time_range_returns_the_closure(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
    ):
        webpage_text = (
            f"{closures_webpage_text.DATE_HEADING}"
            "\nThe bridge will be closed to vehicles "
            f"{closures_webpage_text.TIME_RANGE}"
        )

        result = parse_bridge_closures(webpage_text)

        assert result == [mock_build_closure_from_match.return_value]

    @pytest.mark.parametrize(
        "webpage_text",
        [
            pytest.param(
                f"{closures_webpage_text.DATE_HEADING}"
                f"\n{_VEHICLES_ONLY_NOTICE}"
                f"\n{closures_webpage_text.TIME_RANGE}",
                id="heading-before-notice",
            ),
            pytest.param(
                f"{_VEHICLES_ONLY_NOTICE}"
                f"\n{closures_webpage_text.DATE_HEADING}"
                f"\n{closures_webpage_text.TIME_RANGE}",
                id="heading-after-notice",
            ),
        ],
    )
    def test_notice_applies_to_the_closure_after_it(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
        webpage_text,
    ):
        parse_bridge_closures(webpage_text)

        mock_build_closure_from_match.assert_called_once_with(
            ANY,
            ANY,
            closed_to=mock_resolve_closed_to.return_value,
        )

    def test_later_notice_replaces_an_earlier_one(
        self,
        mock_build_date_from_match,
        mock_build_closure_from_match,
        mock_resolve_closed_to,
    ):
        first_closed_to = Mock()
        second_closed_to = Mock()
        webpage_text = (
            f"{_VEHICLES_ONLY_NOTICE}"
            f"\n{closures_webpage_text.DATE_HEADING}"
            f"\n{closures_webpage_text.TIME_RANGE}"
            f"\n{closures_webpage_text.CLOSURE_NOTICE}"
            f"\n{_IMPLICIT_ROLLOVER_TIME_RANGE}"
        )

        mock_resolve_closed_to.side_effect = [first_closed_to, second_closed_to]

        parse_bridge_closures(webpage_text)

        assert mock_build_closure_from_match.call_args_list == [
            call(ANY, ANY, closed_to=first_closed_to),
            call(ANY, ANY, closed_to=second_closed_to),
        ]
