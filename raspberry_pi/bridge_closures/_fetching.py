"""Fetches text displayed on the Renfrew-Yoker bridge closures webpage."""

import logging

from bs4 import BeautifulSoup
from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException

_logger = logging.getLogger(__name__)

_WEBPAGE_URL = (
    "https://www1.renfrewshire.gov.uk/article/14478/"
    "Check-when-Renfrew-Bridge-is-closed-to-vehicles-pedestrians-and-cyclists"
)

_REQUEST_TIMEOUT_SECONDS = 30
_ERROR_RESPONSE_BODY_CHARS = 300


class WebpageUnavailableError(Exception):
    """Raised when the bridge closures webpage cannot be reached."""


def _raise_if_request_failed(response: requests.Response) -> None:
    """Logs and raises an error if the response of a request indicates that it failed.

    Args:
        response: The HTTP response of the request.

    Raises:
        HTTPError: If the status code of `response` indicates failure.
    """
    if response.ok:
        return

    _logger.error(
        (
            "Failed to reach the Renfrew-Yoker bridge closures webpage. "
            "Status code: %s. Response body = %r."
        ),
        response.status_code,
        response.text[:_ERROR_RESPONSE_BODY_CHARS],
    )

    response.raise_for_status()


def fetch_webpage_text(url: str = _WEBPAGE_URL) -> str:
    """Fetches text displayed on the Renfrew-Yoker bridge closures webpage.

    Args:
        url: The URL of the webpage to fetch text from.

    Returns:
        The text displayed on the webpage.

    Raises:
        WebpageUnavailableError: If the webpage cannot be reached.
    """
    try:
        # Passes the Cloudflare check on the council website - see README.md
        response = requests.get(
            url,
            impersonate="chrome",
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )

        _raise_if_request_failed(response)
    except RequestException as exc:
        raise WebpageUnavailableError(str(exc)) from exc

    # Strip HTML tags, keeping just the displayed text
    soup = BeautifulSoup(response.text, "html.parser")

    return soup.get_text(separator="\n")
