"""Tests `read_cached_bridge_closures`, including real closure deserialization."""

from datetime import UTC, date, datetime
from unittest.mock import patch

from bridge_closure import LONDON_TZ, BridgeClosure, ClosedTo
from bridge_skill._cache_reading import read_cached_bridge_closures
from closure_cache import CachedBridgeClosures, serialize_bridge_closures_to_json
from tests import patch_targets
from tests.closure_data import BRIDGE_CLOSURE, FETCHED_AT
from tests.integration.alexa_lambda.bridge_skill._helpers import stub_cache_payload

_UTC_CLOSURE = BridgeClosure(
    start=datetime(2026, 6, 30, 23, 30, tzinfo=UTC),
    end=datetime(2026, 7, 1, 0, 30, tzinfo=UTC),
    closed_to=ClosedTo.EVERYONE,
)


@patch(f"{patch_targets.CACHE_READING}.boto3.client")
class TestReadCachedBridgeClosures:
    def test_utc_closure_comes_back_on_its_london_date(self, mock_boto3_client):
        payload = serialize_bridge_closures_to_json(
            [_UTC_CLOSURE],
            fetched_at=FETCHED_AT,
        )

        stub_cache_payload(mock_boto3_client, payload)

        result = read_cached_bridge_closures()

        assert result.closures[0].start.date() == date(2026, 7, 1)

    def test_utc_closure_comes_back_in_the_london_timezone(self, mock_boto3_client):
        payload = serialize_bridge_closures_to_json(
            [_UTC_CLOSURE],
            fetched_at=FETCHED_AT,
        )

        stub_cache_payload(mock_boto3_client, payload)

        result = read_cached_bridge_closures()

        assert result.closures[0].start.tzinfo is LONDON_TZ

    def test_no_closures_come_back_as_an_empty_list(self, mock_boto3_client):
        payload = serialize_bridge_closures_to_json([], fetched_at=FETCHED_AT)

        stub_cache_payload(mock_boto3_client, payload)

        result = read_cached_bridge_closures()

        assert result.closures == []

    def test_serialized_closures_and_fetch_time_come_back_unchanged(
        self,
        mock_boto3_client,
    ):
        payload = serialize_bridge_closures_to_json(
            [BRIDGE_CLOSURE],
            fetched_at=FETCHED_AT,
        )

        stub_cache_payload(mock_boto3_client, payload)

        result = read_cached_bridge_closures()

        assert result == CachedBridgeClosures(
            closures=[BRIDGE_CLOSURE],
            fetched_at=FETCHED_AT,
        )
