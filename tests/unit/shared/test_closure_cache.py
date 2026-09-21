import json

from closure_cache import serialize_bridge_closures_to_json
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
