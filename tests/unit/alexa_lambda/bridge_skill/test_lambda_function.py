import logging
from unittest.mock import Mock, patch

import pytest

from bridge_closure import LONDON_TZ
from bridge_skill._cache_reading import ClosureCacheReadError
from bridge_skill._speech import _BRIDGE_NAME
from bridge_skill.lambda_function import (
    _ANSWERED_REQUEST_TYPES,
    _RESPONSE_VERSION,
    _UNAVAILABLE_SPEECH,
    _answer_bridge_closures,
    _build_response,
    lambda_handler,
)
from tests import patch_targets

_NO_ANSWER_REQUEST_TYPES = ["SessionEndedRequest", "CanFulfillIntentRequest"]


def test_build_response_says_the_speech_and_ends_the_session():
    speech = "Spoken text."

    result = _build_response(speech)

    assert result == {
        "version": _RESPONSE_VERSION,
        "response": {
            "outputSpeech": {"type": "PlainText", "text": speech},
            "shouldEndSession": True,
        },
    }


@patch(f"{patch_targets.LAMBDA_FUNCTION}._build_response")
@patch(f"{patch_targets.LAMBDA_FUNCTION}.describe_bridge_closures")
@patch(f"{patch_targets.LAMBDA_FUNCTION}.datetime")
@patch(f"{patch_targets.LAMBDA_FUNCTION}.read_cached_bridge_closures")
class TestAnswerBridgeClosures:
    def test_reads_the_cached_closures(
        self,
        mock_read_cached_bridge_closures,
        mock_datetime,
        mock_describe_bridge_closures,
        mock_build_response,
    ):
        _answer_bridge_closures()

        mock_read_cached_bridge_closures.assert_called_once_with()

    def test_reads_the_clock_in_the_london_timezone(
        self,
        mock_read_cached_bridge_closures,
        mock_datetime,
        mock_describe_bridge_closures,
        mock_build_response,
    ):
        _answer_bridge_closures()

        mock_datetime.now.assert_called_once_with(LONDON_TZ)

    def test_describes_the_cached_closures_at_the_current_time(
        self,
        mock_read_cached_bridge_closures,
        mock_datetime,
        mock_describe_bridge_closures,
        mock_build_response,
    ):
        _answer_bridge_closures()

        mock_describe_bridge_closures.assert_called_once_with(
            mock_read_cached_bridge_closures.return_value,
            now=mock_datetime.now.return_value,
        )

    def test_builds_a_response_with_the_description(
        self,
        mock_read_cached_bridge_closures,
        mock_datetime,
        mock_describe_bridge_closures,
        mock_build_response,
    ):
        _answer_bridge_closures()

        mock_build_response.assert_called_once_with(
            mock_describe_bridge_closures.return_value,
        )

    def test_read_error_logs_the_failure(
        self,
        mock_read_cached_bridge_closures,
        mock_datetime,
        mock_describe_bridge_closures,
        mock_build_response,
        caplog,
    ):
        caplog.set_level(logging.ERROR)
        mock_read_cached_bridge_closures.side_effect = ClosureCacheReadError("Denied")

        _answer_bridge_closures()

        expected_message = (
            f"Failed to read the {_BRIDGE_NAME} closures from the AWS cache."
        )
        assert expected_message in caplog.text

    def test_read_error_describes_nothing(
        self,
        mock_read_cached_bridge_closures,
        mock_datetime,
        mock_describe_bridge_closures,
        mock_build_response,
    ):
        mock_read_cached_bridge_closures.side_effect = ClosureCacheReadError("Denied")

        _answer_bridge_closures()

        mock_describe_bridge_closures.assert_not_called()

    def test_read_error_builds_the_unavailable_response(
        self,
        mock_read_cached_bridge_closures,
        mock_datetime,
        mock_describe_bridge_closures,
        mock_build_response,
    ):
        mock_read_cached_bridge_closures.side_effect = ClosureCacheReadError("Denied")

        _answer_bridge_closures()

        mock_build_response.assert_called_once_with(_UNAVAILABLE_SPEECH)

    def test_read_error_returns_the_built_response(
        self,
        mock_read_cached_bridge_closures,
        mock_datetime,
        mock_describe_bridge_closures,
        mock_build_response,
    ):
        mock_read_cached_bridge_closures.side_effect = ClosureCacheReadError("Denied")

        result = _answer_bridge_closures()

        assert result == mock_build_response.return_value

    def test_returns_the_built_response(
        self,
        mock_read_cached_bridge_closures,
        mock_datetime,
        mock_describe_bridge_closures,
        mock_build_response,
    ):
        result = _answer_bridge_closures()

        assert result == mock_build_response.return_value


@patch(f"{patch_targets.LAMBDA_FUNCTION}._answer_bridge_closures")
class TestLambdaHandler:
    @pytest.mark.parametrize("request_type", _NO_ANSWER_REQUEST_TYPES)
    def test_request_needing_no_answer_returns_an_empty_response(
        self,
        mock_answer_bridge_closures,
        request_type,
    ):
        event = {"request": {"type": request_type}}

        result = lambda_handler(event, Mock())

        assert result == {"version": _RESPONSE_VERSION, "response": {}}

    @pytest.mark.parametrize("request_type", _NO_ANSWER_REQUEST_TYPES)
    def test_request_needing_no_answer_answers_nothing(
        self,
        mock_answer_bridge_closures,
        request_type,
    ):
        event = {"request": {"type": request_type}}

        lambda_handler(event, Mock())

        mock_answer_bridge_closures.assert_not_called()

    @pytest.mark.parametrize("request_type", sorted(_ANSWERED_REQUEST_TYPES))
    def test_request_asking_for_the_closures_answers_them(
        self,
        mock_answer_bridge_closures,
        request_type,
    ):
        event = {"request": {"type": request_type}}

        lambda_handler(event, Mock())

        mock_answer_bridge_closures.assert_called_once_with()

    @pytest.mark.parametrize("request_type", sorted(_ANSWERED_REQUEST_TYPES))
    def test_request_asking_for_the_closures_returns_the_answer(
        self,
        mock_answer_bridge_closures,
        request_type,
    ):
        event = {"request": {"type": request_type}}

        result = lambda_handler(event, Mock())

        assert result == mock_answer_bridge_closures.return_value
