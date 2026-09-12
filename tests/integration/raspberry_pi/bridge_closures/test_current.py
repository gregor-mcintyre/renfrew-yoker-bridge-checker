"""Tests `get_current_bridge_closures`, including real fetch and parse behaviour."""

from datetime import datetime
from unittest.mock import patch

import pytest
import requests

from bridge_closure import BridgeClosure
from bridge_closures._fetching import WebpageUnavailableError
from bridge_closures._parsing import _LONDON_TZ
from bridge_closures.current import get_current_bridge_closures
from tests import closures_webpage_text, patch_target

_PAGE_WITHOUT_CLOSURE = f"""
<div class="article">
  <h3>{closures_webpage_text.DATE_HEADING}</h3>
  <p>{closures_webpage_text.NO_CLOSURES_LINE}</p>
</div>
"""

_CLOSURE_NOTICE = (
    "The Renfrew Bridge will be closed to both road and pedestrian traffic during the "
    "following times:"
)

_PAGE_WITH_CLOSURE = f"""
<div class="article">
  <h3>{closures_webpage_text.DATE_HEADING}</h3>
  <p>{_CLOSURE_NOTICE}</p>
  <p>{closures_webpage_text.TIME_RANGE}</p>
</div>
"""


def _build_response(body: str = "", *, status_code: int = 200) -> requests.Response:
    """Builds a `requests.Response` for the patched `requests.get` to return.

    Args:
        body: The HTML response body.
        status_code: The HTTP status code of the response.

    Returns:
        A `requests.Response` with `body` as its content and `status_code` as its
        status.
    """
    response = requests.Response()
    response.status_code = status_code
    response._content = body.encode()

    return response


@patch(patch_target.BRIDGE_CLOSURES_PACKAGE + "._fetching.requests.get")
class TestGetCurrentBridgeClosures:
    def test_unreachable_webpage_raises_webpage_unavailable_error(
        self,
        mock_requests_get,
    ):
        mock_requests_get.side_effect = requests.ConnectionError("Webpage unavailable")

        with pytest.raises(WebpageUnavailableError):
            get_current_bridge_closures()

    def test_error_status_raises_webpage_unavailable_error(self, mock_requests_get):
        mock_requests_get.return_value = _build_response(status_code=503)

        with pytest.raises(WebpageUnavailableError):
            get_current_bridge_closures()

    def test_no_closures_on_webpage_returns_empty_list(self, mock_requests_get):
        mock_requests_get.return_value = _build_response(_PAGE_WITHOUT_CLOSURE)

        result = get_current_bridge_closures()

        assert result == []

    def test_closure_on_webpage_returns_the_parsed_closure(
        self,
        mock_requests_get,
    ):
        mock_requests_get.return_value = _build_response(_PAGE_WITH_CLOSURE)

        result = get_current_bridge_closures()

        assert result == [
            BridgeClosure(
                start=datetime(2026, 9, 12, 9, tzinfo=_LONDON_TZ),
                end=datetime(2026, 9, 12, 12, 30, tzinfo=_LONDON_TZ),
            ),
        ]
