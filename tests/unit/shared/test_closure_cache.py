import json
from datetime import UTC, date
from unittest.mock import Mock, patch

from bridge_closure import LONDON_TZ, BridgeClosure
from closure_cache import (
    _parse_london_datetime,
    deserialize_bridge_closures_from_json,
    serialize_bridge_closures_to_json,
)
from tests.closure_data import BRIDGE_CLOSURE, FETCHED_AT


class TestSerializeBridgeClosuresToJSON:
    def test_serializes_the_fetched_at_timestamp_in_iso_format(self):
        result = serialize_bridge_closures_to_json([], fetched_at=FETCHED_AT)

        assert json.loads(result)["fetched_at"] == FETCHED_AT.isoformat()

    def test_no_closures_serialize_to_an_empty_array(self):
        result = serialize_bridge_closures_to_json([], fetched_at=FETCHED_AT)

        assert json.loads(result)["closures"] == []

    def test_serializes_each_closure_start_and_end_in_iso_format(self):
        result = serialize_bridge_closures_to_json(
            [BRIDGE_CLOSURE],
            fetched_at=FETCHED_AT,
        )

        assert json.loads(result)["closures"] == [
            {
                "start": BRIDGE_CLOSURE.start.isoformat(),
                "end": BRIDGE_CLOSURE.end.isoformat(),
            },
        ]


class TestParseLondonDatetime:
    def test_summer_utc_shifts_to_the_london_hour(self):
        result = _parse_london_datetime("2026-07-01T11:00:00+00:00")

        assert result.hour == 12

    def test_winter_utc_keeps_the_hour(self):
        result = _parse_london_datetime("2026-12-01T11:00:00+00:00")

        assert result.hour == 11

    def test_late_evening_utc_in_summer_moves_to_the_next_london_day(self):
        result = _parse_london_datetime("2026-06-30T23:30:00+00:00")

        assert result.date() == date(2026, 7, 1)

    def test_returns_a_datetime_in_the_london_timezone(self):
        result = _parse_london_datetime("2026-07-01T11:00:00+00:00")

        assert result.tzinfo is LONDON_TZ

    def test_returns_the_instant_that_was_parsed(self):
        result = _parse_london_datetime("2026-07-01T11:00:00+00:00")

        assert result.astimezone(UTC).hour == 11


@patch("closure_cache._parse_london_datetime")
class TestDeserializeBridgeClosuresFromJSON:
    def test_parses_the_fetched_at_timestamp(self, mock_parse_london_datetime):
        fetched_at_text = FETCHED_AT.isoformat()
        payload = json.dumps({"fetched_at": fetched_at_text, "closures": []})

        deserialize_bridge_closures_from_json(payload)

        mock_parse_london_datetime.assert_called_once_with(fetched_at_text)

    def test_no_closures_deserialize_to_an_empty_list(
        self,
        mock_parse_london_datetime,
    ):
        payload = json.dumps({"fetched_at": FETCHED_AT.isoformat(), "closures": []})

        result = deserialize_bridge_closures_from_json(payload)

        assert result.closures == []

    def test_returns_the_parsed_fetched_at_timestamp(self, mock_parse_london_datetime):
        payload = json.dumps({"fetched_at": FETCHED_AT.isoformat(), "closures": []})

        result = deserialize_bridge_closures_from_json(payload)

        assert result.fetched_at == mock_parse_london_datetime.return_value

    def test_returns_each_closure_with_its_parsed_start_and_end(
        self,
        mock_parse_london_datetime,
    ):
        payload = json.dumps(
            {
                "fetched_at": FETCHED_AT.isoformat(),
                "closures": [
                    {
                        "start": BRIDGE_CLOSURE.start.isoformat(),
                        "end": BRIDGE_CLOSURE.end.isoformat(),
                    },
                ],
            },
        )

        parsed_start = Mock()
        parsed_end = Mock()
        mock_parse_london_datetime.side_effect = {
            FETCHED_AT.isoformat(): Mock(),
            BRIDGE_CLOSURE.start.isoformat(): parsed_start,
            BRIDGE_CLOSURE.end.isoformat(): parsed_end,
        }.__getitem__

        result = deserialize_bridge_closures_from_json(payload)

        assert result.closures == [BridgeClosure(start=parsed_start, end=parsed_end)]
