"""Defines the cached format of Renfrew-Yoker bridge closures."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from bridge_closure import LONDON_TZ, BridgeClosure

# The path of the AWS Systems Manager Parameter Store parameter the closures cache is
# written to and read from
PARAMETER_NAME = "/renfrew-yoker-bridge-checker/closures"


@dataclass
class CachedBridgeClosures:
    """Bridge closures held in the AWS cache.

    Attributes:
        closures: The bridge closures held in the cache.
        fetched_at: The date and time `closures` were fetched from the council website.
    """

    closures: list[BridgeClosure]
    fetched_at: datetime


class _SerializedBridgeClosure(TypedDict):
    """A bridge closure in the format the cache holds it in.

    Attributes:
        start: The date and time the closure starts, in ISO 8601 format.
        end: The date and time the closure ends, in ISO 8601 format.
    """

    start: str
    end: str


class _SerializedBridgeClosures(TypedDict):
    """Bridge closures in the format the cache holds them in.

    Attributes:
        fetched_at: The date and time the closures were fetched from the council
            website, in ISO 8601 format.
        closures: The closures.
    """

    fetched_at: str
    closures: list[_SerializedBridgeClosure]


def serialize_bridge_closures_to_json(
    closures: list[BridgeClosure],
    *,
    fetched_at: datetime,
) -> str:
    """Serializes bridge closures into the JSON payload stored in the AWS cache.

    Args:
        closures: The bridge closures to serialize into JSON.
        fetched_at: The date and time `closures` were fetched from the council
            website.

    Returns:
        A JSON object containing `fetched_at` and the `start` and `end` of each
        closure, each converted with `datetime.isoformat()`.
    """
    payload: _SerializedBridgeClosures = {
        "fetched_at": fetched_at.isoformat(),
        "closures": [
            {"start": closure.start.isoformat(), "end": closure.end.isoformat()}
            for closure in closures
        ],
    }

    return json.dumps(payload)


def _parse_london_datetime(value: str) -> datetime:
    """Parses an ISO 8601 timestamp into the `Europe/London` timezone.

    Args:
        value: The timestamp to parse, including its UTC offset.

    Returns:
        The instant `value` names, in the `Europe/London` timezone. Parsing alone
        leaves a fixed UTC offset, which would put a date near a clock change on the
        wrong side of midnight.
    """
    return datetime.fromisoformat(value).astimezone(LONDON_TZ)


def deserialize_bridge_closures_from_json(payload: str) -> CachedBridgeClosures:
    """Deserializes the JSON payload stored in the AWS cache into bridge closures.

    Reverses `serialize_bridge_closures_to_json`. The payload is only ever written by
    that function, so a malformed one is not handled.

    Args:
        payload: The JSON object to deserialize.

    Returns:
        The closures and the fetch time held in `payload`, each in the `Europe/London`
        timezone.
    """
    data: _SerializedBridgeClosures = json.loads(payload)

    return CachedBridgeClosures(
        closures=[
            BridgeClosure(
                start=_parse_london_datetime(closure["start"]),
                end=_parse_london_datetime(closure["end"]),
            )
            for closure in data["closures"]
        ],
        fetched_at=_parse_london_datetime(data["fetched_at"]),
    )
