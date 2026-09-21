"""Uploads Renfrew-Yoker bridge closures to the AWS cache."""

import logging
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from bridge_closure import BridgeClosure
from closure_cache import PARAMETER_NAME, serialize_bridge_closures_to_json

_logger = logging.getLogger(__name__)


class ClosureCacheWriteError(Exception):
    """Raised when writing to the AWS cache fails."""


def _log(closures: list[BridgeClosure]) -> None:
    """Logs closures uploaded to the AWS cache, handling empty and non-empty cases.

    Args:
        closures: The bridge closures uploaded to the AWS cache, if any.
    """
    if closures:
        _logger.info(
            "Uploaded the following closures to the Renfrew-Yoker bridge closures AWS "
            "cache: %r",
            closures,
        )
    else:
        _logger.info(
            "Uploaded an empty closure list to the Renfrew-Yoker bridge closures AWS "
            "cache.",
        )


def upload_bridge_closures(
    closures: list[BridgeClosure],
    *,
    fetched_at: datetime,
) -> None:
    """Uploads bridge closures to the AWS cache.

    Args:
        closures: The bridge closures to upload.
        fetched_at: The date and time `closures` were fetched from the council website,
            so a stale cache can be flagged later.

    Raises:
        ClosureCacheWriteError: If `closures` cannot be written to the AWS cache.
    """
    payload = serialize_bridge_closures_to_json(closures, fetched_at=fetched_at)

    try:
        boto3.client("ssm").put_parameter(
            Name=PARAMETER_NAME,
            Value=payload,
            Type="String",
            Overwrite=True,
        )
    except (BotoCoreError, ClientError) as exc:
        raise ClosureCacheWriteError(str(exc)) from exc

    _log(closures)
