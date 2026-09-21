"""Defines the cached format of Renfrew-Yoker bridge closures."""

import json
from datetime import datetime

from bridge_closure import BridgeClosure

# The path of the AWS Systems Manager Parameter Store parameter the closures cache is
# written to and read from
PARAMETER_NAME = "/renfrew-yoker-bridge-checker/closures"


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
    payload = {
        "fetched_at": fetched_at.isoformat(),
        "closures": [
            {"start": closure.start.isoformat(), "end": closure.end.isoformat()}
            for closure in closures
        ],
    }

    return json.dumps(payload)
