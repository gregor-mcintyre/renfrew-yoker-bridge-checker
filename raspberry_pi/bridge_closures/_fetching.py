"""Fetches text displayed on the Renfrew-Yoker bridge closures webpage."""

import logging

import requests
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)

_WEBPAGE_URL = (
    "https://www1.renfrewshire.gov.uk/article/14478/"
    "Check-when-Renfrew-Bridge-is-closed-to-vehicles-pedestrians-and-cyclists"
)

# The council website sits behind Cloudflare, which blocks plain `requests` traffic from
# datacenter IP ranges. This component of the project runs on a Raspberry Pi's
# residential connection. The User-Agent is a verbatim Chrome browser string -
# Cloudflare bot detection looks for real browser signatures (OS details, engine names
# like AppleWebKit/Gecko, etc.). A minimal or generic UA gets blocked; the specificity
# and redundancy (Safari/WebKit in a Chrome UA) is exactly what makes it look legitimate
_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
}

_REQUEST_TIMEOUT_SECONDS = 30
_ERROR_RESPONSE_BODY_CHARS = 300


class WebpageUnavailableError(Exception):
    """Raised when the bridge closures webpage cannot be reached."""


def _raise_if_request_failed(response: requests.Response) -> None:
    """Logs and raises an error if the response of a request indicates that it failed.

    Args:
        response: The HTTP response of the request.

    Raises:
        requests.HTTPError: If the status code of `response` indicates failure.
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
        response = requests.get(
            url,
            headers=_REQUEST_HEADERS,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )

        _raise_if_request_failed(response)
    except requests.RequestException as exc:
        raise WebpageUnavailableError(str(exc)) from exc

    # Strip HTML tags, keeping just the displayed text
    soup = BeautifulSoup(response.text, "html.parser")

    return soup.get_text(separator="\n")
