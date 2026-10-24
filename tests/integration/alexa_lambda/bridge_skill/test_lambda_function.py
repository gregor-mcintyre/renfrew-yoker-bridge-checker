"""Tests `lambda_handler`, including real cache reading and speech wording."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from bridge_closure import BridgeClosure
from bridge_skill._speech import _BRIDGE_NAME, _NO_UPCOMING_SPEECH, _STALE_SPEECH
from bridge_skill.lambda_function import (
    _RESPONSE_VERSION,
    _UNAVAILABLE_SPEECH,
    lambda_handler,
)
from closure_cache import serialize_bridge_closures_to_json
from tests import patch_targets
from tests.closure_data import BRIDGE_CLOSURE, FETCHED_AT
from tests.integration.alexa_lambda.bridge_skill._helpers import stub_cache_payload

_LAUNCH_EVENT = {"request": {"type": "LaunchRequest"}}


@patch(f"{patch_targets.LAMBDA_FUNCTION}.datetime")
@patch(f"{patch_targets.CACHE_READING}.boto3.client")
class TestLambdaHandler:
    def test_request_needing_no_answer_returns_an_empty_response(
        self,
        mock_boto3_client,
        mock_datetime,
    ):
        event = {"request": {"type": "SessionEndedRequest"}}

        result = lambda_handler(event, Mock())

        assert result == {"version": _RESPONSE_VERSION, "response": {}}

    def test_request_needing_no_answer_leaves_the_cache_unread(
        self,
        mock_boto3_client,
        mock_datetime,
    ):
        event = {"request": {"type": "SessionEndedRequest"}}

        lambda_handler(event, Mock())

        mock_boto3_client.assert_not_called()

    def test_unreadable_cache_apologises_and_ends_the_session(
        self,
        mock_boto3_client,
        mock_datetime,
    ):
        mock_boto3_client.return_value.get_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound", "Message": "Not found"}},
            "GetParameter",
        )

        result = lambda_handler(_LAUNCH_EVENT, Mock())

        assert result == {
            "version": _RESPONSE_VERSION,
            "response": {
                "outputSpeech": {"type": "PlainText", "text": _UNAVAILABLE_SPEECH},
                "shouldEndSession": True,
            },
        }

    def test_stale_cache_asks_for_the_council_website_to_be_checked(
        self,
        mock_boto3_client,
        mock_datetime,
    ):
        payload = serialize_bridge_closures_to_json(
            [BRIDGE_CLOSURE],
            fetched_at=FETCHED_AT,
        )

        stub_cache_payload(mock_boto3_client, payload)
        mock_datetime.now.return_value = FETCHED_AT + timedelta(hours=2)

        result = lambda_handler(_LAUNCH_EVENT, Mock())

        assert result == {
            "version": _RESPONSE_VERSION,
            "response": {
                "outputSpeech": {"type": "PlainText", "text": _STALE_SPEECH},
                "shouldEndSession": True,
            },
        }

    def test_utc_closure_is_spoken_on_its_london_date(
        self,
        mock_boto3_client,
        mock_datetime,
    ):
        utc_closure = BridgeClosure(
            start=datetime(2026, 9, 15, 23, 30, tzinfo=UTC),
            end=datetime(2026, 9, 16, 0, 30, tzinfo=UTC),
        )
        payload = serialize_bridge_closures_to_json(
            [utc_closure],
            fetched_at=FETCHED_AT,
        )

        stub_cache_payload(mock_boto3_client, payload)
        mock_datetime.now.return_value = FETCHED_AT

        result = lambda_handler(_LAUNCH_EVENT, Mock())

        spoken = (
            f"The {_BRIDGE_NAME} is open now. "
            "It closes tomorrow from 12:30am to 1:30am."
        )
        assert result == {
            "version": _RESPONSE_VERSION,
            "response": {
                "outputSpeech": {"type": "PlainText", "text": spoken},
                "shouldEndSession": True,
            },
        }

    def test_intent_request_speaks_the_upcoming_closure(
        self,
        mock_boto3_client,
        mock_datetime,
    ):
        event = {
            "request": {
                "type": "IntentRequest",
                "intent": {"name": "GetBridgeClosuresIntent"},
            },
        }
        tomorrow_closure = BridgeClosure(
            start=BRIDGE_CLOSURE.start + timedelta(days=1),
            end=BRIDGE_CLOSURE.end + timedelta(days=1),
        )
        payload = serialize_bridge_closures_to_json(
            [tomorrow_closure],
            fetched_at=FETCHED_AT,
        )

        stub_cache_payload(mock_boto3_client, payload)
        mock_datetime.now.return_value = FETCHED_AT

        result = lambda_handler(event, Mock())

        spoken = (
            f"The {_BRIDGE_NAME} is open now. It closes tomorrow from 9am to 12:30pm."
        )
        assert result == {
            "version": _RESPONSE_VERSION,
            "response": {
                "outputSpeech": {"type": "PlainText", "text": spoken},
                "shouldEndSession": True,
            },
        }

    def test_launch_request_speaks_when_the_closed_bridge_reopens(
        self,
        mock_boto3_client,
        mock_datetime,
    ):
        payload = serialize_bridge_closures_to_json(
            [BRIDGE_CLOSURE],
            fetched_at=FETCHED_AT,
        )

        stub_cache_payload(mock_boto3_client, payload)
        mock_datetime.now.return_value = FETCHED_AT

        result = lambda_handler(_LAUNCH_EVENT, Mock())

        spoken = (
            f"The {_BRIDGE_NAME} is closed now, until 12:30pm. {_NO_UPCOMING_SPEECH}"
        )
        assert result == {
            "version": _RESPONSE_VERSION,
            "response": {
                "outputSpeech": {"type": "PlainText", "text": spoken},
                "shouldEndSession": True,
            },
        }
