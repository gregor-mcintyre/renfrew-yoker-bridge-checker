"""Defines the cached format of Renfrew-Yoker bridge closures."""

import json
from datetime import datetime

from bridge_closure import BridgeClosure


def serialize_bridge_closures_to_json(
    closures: list[BridgeClosure],
    *,
    updated_at: datetime,
) -> str:
    """Serializes bridge closures into the JSON payload stored in the AWS cache.

    Args:
        closures: The bridge closures to serialize into JSON.
        updated_at: The date and time `closures` were retrieved.

    Returns:
        A JSON object containing `updated_at` and the `start` and `end` of each
        closure, each converted with `datetime.isoformat()`.
    """
    payload = {
        "updated_at": updated_at.isoformat(),
        "closures": [
            {"start": closure.start.isoformat(), "end": closure.end.isoformat()}
            for closure in closures
        ],
    }

    return json.dumps(payload)
