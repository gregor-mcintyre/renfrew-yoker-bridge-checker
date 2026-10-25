"""Reads Renfrew-Yoker bridge closures from the AWS cache."""

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from closure_cache import (
    PARAMETER_NAME,
    CachedBridgeClosures,
    deserialize_bridge_closures_from_json,
)


class ClosureCacheReadError(Exception):
    """Raised when reading from the AWS cache fails."""


def read_cached_bridge_closures() -> CachedBridgeClosures:
    """Reads the bridge closures the Raspberry Pi last uploaded to the AWS cache.

    Returns:
        The cached bridge closures and the date and time they were fetched.

    Raises:
        ClosureCacheReadError: If the AWS cache cannot be read, including before the
            Raspberry Pi has uploaded to it for the first time.
    """
    try:
        response = boto3.client("ssm").get_parameter(Name=PARAMETER_NAME)
    except (BotoCoreError, ClientError) as exc:
        raise ClosureCacheReadError(str(exc)) from exc

    return deserialize_bridge_closures_from_json(response["Parameter"]["Value"])
