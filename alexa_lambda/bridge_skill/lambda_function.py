"""Answers Alexa requests about the Renfrew-Yoker bridge closures."""

import logging
from datetime import datetime
from typing import Any, Literal, TypedDict

from bridge_closure import LONDON_TZ
from bridge_skill._cache_reading import (
    ClosureCacheReadError,
    read_cached_bridge_closures,
)
from bridge_skill._speech import _BRIDGE_NAME, describe_bridge_closures

_logger = logging.getLogger(__name__)

# Opening the skill and saying anything to it both ask for the closures, because it has
# only the one thing to say
_ANSWERED_REQUEST_TYPES = frozenset({"LaunchRequest", "IntentRequest"})

_RESPONSE_VERSION = "1.0"

_UNAVAILABLE_SPEECH = (
    f"Sorry, I can't get the {_BRIDGE_NAME} closures right now. Please try again later."
)


class OutputSpeech(TypedDict):
    """The text Alexa speaks.

    Attributes:
        type: How Alexa reads `text`, which is always `"PlainText"`.
        text: The text to speak.
    """

    type: Literal["PlainText"]
    text: str


class ResponseBody(TypedDict, total=False):
    """What Alexa does in answer to a request.

    Attributes:
        outputSpeech: The speech to say. Left out when the request needs no answer.
        shouldEndSession: If `True`, Alexa ends the session after speaking.
    """

    outputSpeech: OutputSpeech
    shouldEndSession: bool


class AlexaResponse(TypedDict):
    """The response to a request, in the JSON format the Alexa Skills Kit expects.

    Attributes:
        version: The version of the response format.
        response: What Alexa does in answer to the request.
    """

    version: str
    response: ResponseBody


def _build_response(speech: str) -> AlexaResponse:
    """Builds the response with which Alexa speaks and then ends the session.

    Args:
        speech: The text for Alexa to speak.

    Returns:
        The response that says `speech`.
    """
    return {
        "version": _RESPONSE_VERSION,
        "response": {
            "outputSpeech": {"type": "PlainText", "text": speech},
            "shouldEndSession": True,
        },
    }


def _answer_bridge_closures() -> AlexaResponse:
    """Answers whether the bridge is closed, from the cached closures.

    Returns:
        The response that says what `describe_bridge_closures` describes, or an
        apology if the AWS cache cannot be read.
    """
    try:
        cached = read_cached_bridge_closures()
    except ClosureCacheReadError:
        _logger.exception(
            "Failed to read the %s closures from the AWS cache.",
            _BRIDGE_NAME,
        )

        return _build_response(_UNAVAILABLE_SPEECH)

    speech = describe_bridge_closures(cached, now=datetime.now(LONDON_TZ))

    return _build_response(speech)


def lambda_handler(event: dict[str, Any], _context: object) -> AlexaResponse:
    """Answers a request Alexa sends to the skill.

    Args:
        event: The request in the JSON format the Alexa Skills Kit sends.
        _context: The AWS Lambda context object, which is not used.

    Returns:
        The response of `_answer_bridge_closures` to a request that opens the skill or
        asks it something. An empty response to any other request, such as the end of
        a session, which needs no answer.
    """
    if event["request"]["type"] in _ANSWERED_REQUEST_TYPES:
        return _answer_bridge_closures()

    return {"version": _RESPONSE_VERSION, "response": {}}
