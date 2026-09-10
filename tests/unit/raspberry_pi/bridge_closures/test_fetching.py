import logging
from unittest.mock import Mock, patch

import pytest
import requests

from bridge_closures._fetching import (
    _ERROR_RESPONSE_BODY_CHARS,
    _REQUEST_HEADERS,
    _REQUEST_TIMEOUT_SECONDS,
    _WEBPAGE_URL,
    WebpageUnavailableError,
    _raise_if_request_failed,
    fetch_webpage_text,
)
from tests.unit.raspberry_pi.bridge_closures import _patch_targets

_FETCHING_MODULE = _patch_targets.BRIDGE_CLOSURES_PACKAGE + "._fetching"
_REQUESTS_GET = f"{_FETCHING_MODULE}.requests.get"
_BEAUTIFUL_SOUP = f"{_FETCHING_MODULE}.BeautifulSoup"

_FAILED_STATUS_CODE = 500


@pytest.fixture
def mock_failed_response():
    """A mocked `requests.Response` from a failed request.

    `ok` is `False`, `status_code` is an error code, and `text` is not set.
    """
    return Mock(ok=False, status_code=_FAILED_STATUS_CODE)


@pytest.fixture
def mock_successful_response():
    """A mocked `requests.Response` from a successful request.

    `ok` is `True` and `text` is not set.
    """
    return Mock(ok=True)


class TestRaiseIfRequestFailed:
    def test_failed_request_logs_error_message(self, caplog, mock_failed_response):
        caplog.set_level(logging.ERROR)

        response_body = "Failed"

        mock_failed_response.text = response_body

        _raise_if_request_failed(mock_failed_response)

        expected_error_message = (
            "Failed to reach the Renfrew-Yoker bridge closures webpage. "
            f"Status code: {_FAILED_STATUS_CODE}. Response body = {response_body!r}."
        )
        assert expected_error_message in caplog.text

    def test_failed_request_log_truncates_response_body(
        self,
        caplog,
        mock_failed_response,
    ):
        caplog.set_level(logging.ERROR)

        oversized_response_body = "x" * (_ERROR_RESPONSE_BODY_CHARS + 1)

        mock_failed_response.text = oversized_response_body

        _raise_if_request_failed(mock_failed_response)

        assert oversized_response_body not in caplog.text
        assert "x" * _ERROR_RESPONSE_BODY_CHARS in caplog.text

    def test_failed_request_raises_http_error(self, mock_failed_response):
        mock_failed_response.text = ""
        mock_failed_response.raise_for_status.side_effect = requests.HTTPError(
            str(_FAILED_STATUS_CODE),
        )

        with pytest.raises(requests.HTTPError):
            _raise_if_request_failed(mock_failed_response)

    def test_successful_request_does_not_raise(self):
        mock_response = Mock(ok=True)

        _raise_if_request_failed(mock_response)

        mock_response.raise_for_status.assert_not_called()


class TestFetchWebpageText:
    @patch(_BEAUTIFUL_SOUP)
    @patch(_REQUESTS_GET)
    def test_requests_get_called_with_correct_url_headers_and_timeout(
        self,
        mock_requests_get,
        mock_beautiful_soup,
        mock_successful_response,
    ):
        mock_requests_get.return_value = mock_successful_response

        fetch_webpage_text()

        mock_requests_get.assert_called_once_with(
            _WEBPAGE_URL,
            headers=_REQUEST_HEADERS,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )

    @patch(_BEAUTIFUL_SOUP)
    @patch(_REQUESTS_GET)
    def test_mozilla_in_request_headers_user_agent(
        self,
        mock_requests_get,
        mock_beautiful_soup,
        mock_successful_response,
    ):
        mock_requests_get.return_value = mock_successful_response

        fetch_webpage_text()

        assert "Mozilla" in mock_requests_get.call_args.kwargs["headers"]["User-Agent"]

    @patch(_REQUESTS_GET)
    def test_wraps_error_from_requests_get(self, mock_requests_get):
        error_message = "Error"

        mock_requests_get.side_effect = requests.RequestException(error_message)

        with pytest.raises(WebpageUnavailableError, match=error_message):
            fetch_webpage_text()

    @patch(f"{_FETCHING_MODULE}._raise_if_request_failed")
    @patch(_REQUESTS_GET)
    def test_wraps_error_from_raise_if_request_failed(
        self,
        mock_requests_get,
        mock_raise_if_request_failed,
        mock_failed_response,
    ):
        error_message = "Error"

        mock_raise_if_request_failed.side_effect = requests.HTTPError(error_message)

        with pytest.raises(WebpageUnavailableError, match=error_message):
            fetch_webpage_text()

    @patch(_REQUESTS_GET)
    def test_chains_error_to_its_cause(self, mock_requests_get):
        original_error = requests.ConnectionError("Error")

        mock_requests_get.side_effect = original_error

        with pytest.raises(WebpageUnavailableError) as exc_info:
            fetch_webpage_text()

        assert exc_info.value.__cause__ is original_error

    @patch(_BEAUTIFUL_SOUP)
    @patch(_REQUESTS_GET)
    def test_parses_response_body_as_html(
        self,
        mock_requests_get,
        mock_beautiful_soup,
        mock_successful_response,
    ):
        html_displayed_on_page = "<p>Bridge closed</p>"

        mock_successful_response.text = html_displayed_on_page
        mock_requests_get.return_value = mock_successful_response

        fetch_webpage_text()

        mock_beautiful_soup.assert_called_once_with(
            html_displayed_on_page,
            "html.parser",
        )

    @patch(_BEAUTIFUL_SOUP)
    @patch(_REQUESTS_GET)
    def test_returns_extracted_text(
        self,
        mock_requests_get,
        mock_beautiful_soup,
        mock_successful_response,
    ):
        mock_requests_get.return_value = mock_successful_response
        mock_get_text = mock_beautiful_soup.return_value.get_text

        result = fetch_webpage_text()

        mock_get_text.assert_called_once_with(separator="\n")
        assert result == mock_get_text.return_value
