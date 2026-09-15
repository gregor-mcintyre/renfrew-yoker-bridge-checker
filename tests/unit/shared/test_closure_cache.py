import json
from datetime import datetime

from bridge_closure import LONDON_TZ, BridgeClosure
from closure_cache import serialize_bridge_closures_to_json

_UPDATED_AT = datetime(2026, 9, 15, 12, tzinfo=LONDON_TZ)


class TestSerializeBridgeClosuresToJSON:
    def test_serializes_the_updated_at_timestamp_in_iso_format(self):
        result = serialize_bridge_closures_to_json([], updated_at=_UPDATED_AT)

        assert json.loads(result)["updated_at"] == _UPDATED_AT.isoformat()

    def test_no_closures_serialize_to_an_empty_array(self):
        result = serialize_bridge_closures_to_json([], updated_at=_UPDATED_AT)

        assert json.loads(result)["closures"] == []

    def test_serializes_each_closure_start_and_end_in_iso_format(self):
        closure = BridgeClosure(
            start=datetime(2026, 9, 15, 9, tzinfo=LONDON_TZ),
            end=datetime(2026, 9, 15, 12, 30, tzinfo=LONDON_TZ),
        )

        result = serialize_bridge_closures_to_json([closure], updated_at=_UPDATED_AT)

        assert json.loads(result)["closures"] == [
            {"start": closure.start.isoformat(), "end": closure.end.isoformat()},
        ]
