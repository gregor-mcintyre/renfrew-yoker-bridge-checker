"""Tests `get_current_bridge_closures`, including real fetch and parse behaviour."""

from unittest.mock import patch

import pytest
from curl_cffi.requests import exceptions

from bridge_closures._current import get_current_bridge_closures
from bridge_closures._fetching import WebpageUnavailableError
from tests import patch_targets
from tests.closure_data import BRIDGE_CLOSURE
from tests.integration.raspberry_pi.bridge_closures._helpers import (
    PAGE_WITH_CLOSURE,
    PAGE_WITHOUT_CLOSURE,
    build_response,
)


@patch(f"{patch_targets.FETCHING}.requests.get")
class TestGetCurrentBridgeClosures:
    def test_unreachable_webpage_raises_webpage_unavailable_error(
        self,
        mock_requests_get,
    ):
        mock_requests_get.side_effect = exceptions.ConnectionError(
            "Webpage unavailable",
        )

        with pytest.raises(WebpageUnavailableError):
            get_current_bridge_closures()

    def test_error_status_raises_webpage_unavailable_error(self, mock_requests_get):
        mock_requests_get.return_value = build_response(status_code=503)

        with pytest.raises(WebpageUnavailableError):
            get_current_bridge_closures()

    def test_no_closures_on_webpage_returns_empty_list(self, mock_requests_get):
        mock_requests_get.return_value = build_response(PAGE_WITHOUT_CLOSURE)

        result = get_current_bridge_closures()

        assert result == []

    def test_closure_on_webpage_returns_the_parsed_closure(
        self,
        mock_requests_get,
    ):
        mock_requests_get.return_value = build_response(PAGE_WITH_CLOSURE)

        result = get_current_bridge_closures()

        assert result == [BRIDGE_CLOSURE]
