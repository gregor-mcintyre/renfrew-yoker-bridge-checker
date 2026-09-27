import logging
from unittest.mock import Mock, patch

import pytest
from curl_cffi.requests.exceptions import HTTPError, RequestException

from bridge_closures._fetching import (
    _ERROR_RESPONSE_BODY_CHARS,
    _REQUEST_TIMEOUT_SECONDS,
    _WEBPAGE_URL,
    WebpageUnavailableError,
    _raise_if_request_failed,
    fetch_webpage_text,
)
from tests import patch_targets

_FAILED_STATUS_CODE = 500


@pytest.fixture
def mock_failed_response() -> Mock:
    """A mocked `Response` from a failed request.

    `ok` is `False`, `status_code` is an error code, and `text` is not set.
    """
    return Mock(ok=False, status_code=_FAILED_STATUS_CODE)


class TestRaiseIfRequestFailed:
    def test_failed_request_logs_error_message(self, caplog, mock_failed_response):
        response_body = "Failed"

        caplog.set_level(logging.ERROR)
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
        oversized_response_body = "x" * (_ERROR_RESPONSE_BODY_CHARS + 1)

        caplog.set_level(logging.ERROR)
        mock_failed_response.text = oversized_response_body

        _raise_if_request_failed(mock_failed_response)

        assert oversized_response_body not in caplog.text
        assert "x" * _ERROR_RESPONSE_BODY_CHARS in caplog.text

    def test_failed_request_raises_http_error(self, mock_failed_response):
        mock_failed_response.text = ""
        mock_failed_response.raise_for_status.side_effect = HTTPError(
            str(_FAILED_STATUS_CODE),
        )

        with pytest.raises(HTTPError):
            _raise_if_request_failed(mock_failed_response)

    def test_successful_request_does_not_raise(self):
        mock_response = Mock(ok=True)

        _raise_if_request_failed(mock_response)

        mock_response.raise_for_status.assert_not_called()


@patch(f"{patch_targets.FETCHING}.BeautifulSoup")
@patch(f"{patch_targets.FETCHING}._raise_if_request_failed")
@patch(f"{patch_targets.FETCHING}.requests.get")
class TestFetchWebpageText:
    def test_requests_get_called_with_url_impersonation_and_timeout(
        self,
        mock_requests_get,
        mock_raise_if_request_failed,
        mock_beautiful_soup,
    ):
        fetch_webpage_text()

        mock_requests_get.assert_called_once_with(
            _WEBPAGE_URL,
            impersonate="chrome",
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )

    def test_checks_the_response_for_failure(
        self,
        mock_requests_get,
        mock_raise_if_request_failed,
        mock_beautiful_soup,
    ):
        fetch_webpage_text()

        mock_raise_if_request_failed.assert_called_once_with(
            mock_requests_get.return_value,
        )

    def test_wraps_error_from_requests_get(
        self,
        mock_requests_get,
        mock_raise_if_request_failed,
        mock_beautiful_soup,
    ):
        error_message = "Error"

        mock_requests_get.side_effect = RequestException(error_message)

        with pytest.raises(WebpageUnavailableError, match=error_message):
            fetch_webpage_text()

    def test_wraps_error_from_raise_if_request_failed(
        self,
        mock_requests_get,
        mock_raise_if_request_failed,
        mock_beautiful_soup,
    ):
        error_message = "Error"

        mock_raise_if_request_failed.side_effect = HTTPError(error_message)

        with pytest.raises(WebpageUnavailableError, match=error_message):
            fetch_webpage_text()

    def test_chains_error_to_its_cause(
        self,
        mock_requests_get,
        mock_raise_if_request_failed,
        mock_beautiful_soup,
    ):
        original_error = RequestException("Error")

        mock_requests_get.side_effect = original_error

        with pytest.raises(WebpageUnavailableError) as exc_info:
            fetch_webpage_text()

        assert exc_info.value.__cause__ is original_error

    def test_parses_response_body_as_html(
        self,
        mock_requests_get,
        mock_raise_if_request_failed,
        mock_beautiful_soup,
    ):
        fetch_webpage_text()

        mock_beautiful_soup.assert_called_once_with(
            mock_requests_get.return_value.text,
            "html.parser",
        )

    def test_extracts_text_separated_by_newlines(
        self,
        mock_requests_get,
        mock_raise_if_request_failed,
        mock_beautiful_soup,
    ):
        fetch_webpage_text()

        mock_beautiful_soup.return_value.get_text.assert_called_once_with(
            separator="\n",
        )

    def test_returns_extracted_text(
        self,
        mock_requests_get,
        mock_raise_if_request_failed,
        mock_beautiful_soup,
    ):
        result = fetch_webpage_text()

        assert result == mock_beautiful_soup.return_value.get_text.return_value
