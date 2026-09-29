import logging
from unittest.mock import patch

import pytest

from bridge_closure import LONDON_TZ
from bridge_closures._fetching import WebpageUnavailableError
from bridge_closures._uploading import ClosureCacheWriteError
from bridge_closures.cache_refresh import main, refresh_closure_cache
from tests import patch_targets

_REFRESH_ERRORS = [
    pytest.param(WebpageUnavailableError("Unreachable"), id="webpage_unavailable"),
    pytest.param(ClosureCacheWriteError("Access denied"), id="cache_write_failure"),
]


@patch(f"{patch_targets.CACHE_REFRESH}.upload_bridge_closures")
@patch(f"{patch_targets.CACHE_REFRESH}.get_current_bridge_closures")
@patch(f"{patch_targets.CACHE_REFRESH}.datetime")
class TestRefreshClosureCache:
    def test_stamps_the_fetch_time_in_the_london_timezone(
        self,
        mock_datetime,
        mock_get_current_bridge_closures,
        mock_upload_bridge_closures,
    ):
        refresh_closure_cache()

        mock_datetime.now.assert_called_once_with(LONDON_TZ)

    def test_scrapes_the_current_closures(
        self,
        mock_datetime,
        mock_get_current_bridge_closures,
        mock_upload_bridge_closures,
    ):
        refresh_closure_cache()

        mock_get_current_bridge_closures.assert_called_once_with()

    def test_uploads_the_scraped_closures_with_the_fetch_time(
        self,
        mock_datetime,
        mock_get_current_bridge_closures,
        mock_upload_bridge_closures,
    ):
        refresh_closure_cache()

        mock_upload_bridge_closures.assert_called_once_with(
            mock_get_current_bridge_closures.return_value,
            fetched_at=mock_datetime.now.return_value,
        )


@patch(f"{patch_targets.CACHE_REFRESH}.refresh_closure_cache")
@patch(f"{patch_targets.CACHE_REFRESH}.logging.basicConfig")
class TestMain:
    def test_configures_logging(self, mock_basic_config, mock_refresh_closure_cache):
        main()

        mock_basic_config.assert_called_once_with(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    def test_refreshes_the_closure_cache(
        self,
        mock_basic_config,
        mock_refresh_closure_cache,
    ):
        main()

        mock_refresh_closure_cache.assert_called_once_with()

    @pytest.mark.parametrize("error", _REFRESH_ERRORS)
    def test_refresh_error_returns_one(
        self,
        mock_basic_config,
        mock_refresh_closure_cache,
        error,
    ):
        mock_refresh_closure_cache.side_effect = error

        result = main()

        assert result == 1

    @pytest.mark.parametrize("error", _REFRESH_ERRORS)
    def test_refresh_error_logs_the_failure(
        self,
        mock_basic_config,
        mock_refresh_closure_cache,
        error,
        caplog,
    ):
        caplog.set_level(logging.ERROR)
        mock_refresh_closure_cache.side_effect = error

        main()

        expected_message = "The scheduled Renfrew-Yoker bridge closure scrape failed."
        assert expected_message in caplog.text

    def test_successful_refresh_returns_zero(
        self,
        mock_basic_config,
        mock_refresh_closure_cache,
    ):
        result = main()

        assert result == 0
