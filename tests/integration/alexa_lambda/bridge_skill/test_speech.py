"""Tests `describe_bridge_closures`, including its real time and day phrasing."""

from datetime import datetime

from bridge_closure import LONDON_TZ, BridgeClosure, ClosedTo
from bridge_skill._speech import (
    _BRIDGE_NAME,
    _CLOSED_TO_WORDING,
    _NO_UPCOMING_SPEECH,
    _STALE_AFTER,
    _STALE_SPEECH,
    describe_bridge_closures,
)
from closure_cache import CachedBridgeClosures

_NOW = datetime(2026, 9, 29, 12, tzinfo=LONDON_TZ)

_OPEN_WITH_NONE_UPCOMING = f"The {_BRIDGE_NAME} is open now. {_NO_UPCOMING_SPEECH}"


class TestDescribeBridgeClosures:
    def test_stale_cache_asks_for_the_council_website_to_be_checked(self):
        cached = CachedBridgeClosures(
            closures=[
                BridgeClosure(
                    start=datetime(2026, 9, 29, 11, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 29, 12, 30, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
            ],
            fetched_at=_NOW - 2 * _STALE_AFTER,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == _STALE_SPEECH

    def test_closure_that_has_ended_is_not_mentioned(self):
        cached = CachedBridgeClosures(
            closures=[
                BridgeClosure(
                    start=datetime(2026, 9, 29, 9, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 29, 10, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
            ],
            fetched_at=_NOW,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == _OPEN_WITH_NONE_UPCOMING

    def test_closure_in_progress_says_when_the_bridge_reopens_today(self):
        cached = CachedBridgeClosures(
            closures=[
                BridgeClosure(
                    start=datetime(2026, 9, 29, 11, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 29, 12, 30, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
            ],
            fetched_at=_NOW,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == (
            f"The {_BRIDGE_NAME} is closed now, until 12:30pm. {_NO_UPCOMING_SPEECH}"
        )

    def test_closure_in_progress_says_when_the_bridge_reopens_tomorrow(self):
        cached = CachedBridgeClosures(
            closures=[
                BridgeClosure(
                    start=datetime(2026, 9, 29, 11, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 30, 1, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
            ],
            fetched_at=_NOW,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == (
            f"The {_BRIDGE_NAME} is closed now, until 1am tomorrow. "
            f"{_NO_UPCOMING_SPEECH}"
        )

    def test_closure_in_progress_is_followed_by_the_next_closure_today(self):
        cached = CachedBridgeClosures(
            closures=[
                BridgeClosure(
                    start=datetime(2026, 9, 29, 11, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 29, 12, 30, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
                BridgeClosure(
                    start=datetime(2026, 9, 29, 15, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 29, 16, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
            ],
            fetched_at=_NOW,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == (
            f"The {_BRIDGE_NAME} is closed now, until 12:30pm. "
            "It closes today from 3pm to 4pm."
        )

    def test_closure_spanning_midnight_says_the_next_day(self):
        cached = CachedBridgeClosures(
            closures=[
                BridgeClosure(
                    start=datetime(2026, 9, 30, 23, tzinfo=LONDON_TZ),
                    end=datetime(2026, 10, 1, 1, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
            ],
            fetched_at=_NOW,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == (
            f"The {_BRIDGE_NAME} is open now. "
            "It closes tomorrow from 11pm until 1am the next day."
        )

    def test_no_closures_say_the_bridge_is_open_with_none_upcoming(self):
        cached = CachedBridgeClosures(closures=[], fetched_at=_NOW)

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == _OPEN_WITH_NONE_UPCOMING

    def test_three_closures_in_a_day_are_listed_with_and_again_before_the_last(self):
        cached = CachedBridgeClosures(
            closures=[
                BridgeClosure(
                    start=datetime(2026, 9, 30, 9, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 30, 10, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
                BridgeClosure(
                    start=datetime(2026, 9, 30, 12, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 30, 13, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
                BridgeClosure(
                    start=datetime(2026, 9, 30, 15, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 30, 16, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
            ],
            fetched_at=_NOW,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == (
            f"The {_BRIDGE_NAME} is open now. "
            "It closes tomorrow from 9am to 10am, from 12pm to 1pm, "
            "and again from 3pm to 4pm."
        )

    def test_upcoming_closures_are_described_a_day_at_a_time_in_date_order(self):
        cached = CachedBridgeClosures(
            closures=[
                BridgeClosure(
                    start=datetime(2026, 9, 30, 14, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 30, 15, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
                BridgeClosure(
                    start=datetime(2026, 9, 30, 9, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 30, 12, 30, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
                BridgeClosure(
                    start=datetime(2026, 9, 29, 15, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 29, 16, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
            ],
            fetched_at=_NOW,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == (
            f"The {_BRIDGE_NAME} is open now. "
            "It closes today from 3pm to 4pm. "
            "It closes tomorrow from 9am to 12:30pm, and again from 2pm to 3pm."
        )

    def test_closures_for_different_traffic_on_one_day_are_described_in_start_order(
        self,
    ):
        cached = CachedBridgeClosures(
            closures=[
                BridgeClosure(
                    start=datetime(2026, 9, 29, 18, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 30, 6, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.VEHICLES,
                ),
                BridgeClosure(
                    start=datetime(2026, 9, 29, 15, tzinfo=LONDON_TZ),
                    end=datetime(2026, 9, 29, 16, tzinfo=LONDON_TZ),
                    closed_to=ClosedTo.EVERYONE,
                ),
            ],
            fetched_at=_NOW,
        )

        result = describe_bridge_closures(cached, now=_NOW)

        assert result == (
            f"The {_BRIDGE_NAME} is open now. "
            "It closes today from 3pm to 4pm. "
            f"It closes{_CLOSED_TO_WORDING[ClosedTo.VEHICLES]} today "
            "from 6pm until 6am the next day."
        )
