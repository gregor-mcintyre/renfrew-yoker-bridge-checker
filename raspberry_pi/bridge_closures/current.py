"""Fetches and parses Renfrew-Yoker bridge closures from the council website."""

import logging

from bridge_closure import BridgeClosure
from bridge_closures._fetching import fetch_webpage_text
from bridge_closures._parsing import parse_bridge_closures

_logger = logging.getLogger(__name__)


def _log(closures: list[BridgeClosure]) -> None:
    """Logs scraped bridge closures, handling empty and non-empty cases.

    Args:
        closures: The bridge closures to log, if any.
    """
    if closures:
        _logger.info(
            "Scraped the following closures from the Renfrew-Yoker bridge closures "
            "webpage within the Renfrewshire council website: %r",
            closures,
        )
    else:
        _logger.info(
            "No closures currently listed on the Renfrew-Yoker bridge closures "
            "webpage.",
        )


def get_current_bridge_closures() -> list[BridgeClosure]:
    """Fetches bridge closures currently displayed on the Renfrewshire council website.

    Returns:
        The bridge closures currently displayed on the website.
    """
    webpage_text = fetch_webpage_text()
    closures = parse_bridge_closures(webpage_text)

    _log(closures)

    return closures
