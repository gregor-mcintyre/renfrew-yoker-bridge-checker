"""Refreshes the Renfrew-Yoker bridge closures cached in AWS."""

import logging
from datetime import datetime

from bridge_closure import LONDON_TZ
from bridge_closures._current import get_current_bridge_closures
from bridge_closures._fetching import WebpageUnavailableError
from bridge_closures._uploading import ClosureCacheWriteError, upload_bridge_closures

_logger = logging.getLogger(__name__)


def refresh_closure_cache() -> None:
    """Scrapes the current bridge closures and uploads them to the AWS cache."""
    fetched_at = datetime.now(LONDON_TZ)

    closures = get_current_bridge_closures()

    upload_bridge_closures(closures, fetched_at=fetched_at)


def main() -> int:
    """Runs a scheduled cache refresh, reporting failure through the exit code.

    Returns:
        `0` if the closures reached the AWS cache, `1` if the council website was
        unreachable or the cache could not be written.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        refresh_closure_cache()
    except (WebpageUnavailableError, ClosureCacheWriteError) as exc:
        _logger.error(
            "The scheduled Renfrew-Yoker bridge closure scrape failed. %s",
            exc,
        )

        return 1

    return 0
