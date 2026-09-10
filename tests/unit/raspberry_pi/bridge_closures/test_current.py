import logging
from typing import cast
from unittest.mock import Mock, patch

from bridge_closure import BridgeClosure
from bridge_closures.current import _log, get_current_bridge_closures
from tests.unit.raspberry_pi.bridge_closures import _patch_targets

_CURRENT_MODULE = _patch_targets.BRIDGE_CLOSURES_PACKAGE + ".current"


class TestLog:
    def test_empty_list_logs_no_closures(self, caplog):
        caplog.set_level(logging.INFO)

        _log([])

        expected_message = (
            "No closures currently listed on the Renfrew-Yoker bridge closures webpage."
        )
        assert expected_message in caplog.text

    def test_non_empty_list_logs_the_closures(self, caplog):
        caplog.set_level(logging.INFO)

        closures = cast(list[BridgeClosure], [Mock(), Mock()])

        _log(closures)

        expected_message = (
            "Scraped the following closures from the Renfrew-Yoker bridge closures "
            f"webpage within the Renfrewshire council website: {closures!r}"
        )
        assert expected_message in caplog.text


@patch(f"{_CURRENT_MODULE}._log")
@patch(f"{_CURRENT_MODULE}.parse_bridge_closures")
@patch(f"{_CURRENT_MODULE}.fetch_webpage_text")
class TestGetCurrentBridgeClosures:
    def test_fetches_the_webpage_text(
        self,
        mock_fetch_webpage_text,
        mock_parse_bridge_closures,
        mock_log,
    ):
        get_current_bridge_closures()

        mock_fetch_webpage_text.assert_called_once_with()

    def test_parses_the_fetched_webpage_text(
        self,
        mock_fetch_webpage_text,
        mock_parse_bridge_closures,
        mock_log,
    ):
        get_current_bridge_closures()

        mock_parse_bridge_closures.assert_called_once_with(
            mock_fetch_webpage_text.return_value,
        )

    def test_logs_the_parsed_closures(
        self,
        mock_fetch_webpage_text,
        mock_parse_bridge_closures,
        mock_log,
    ):
        get_current_bridge_closures()

        mock_log.assert_called_once_with(mock_parse_bridge_closures.return_value)

    def test_returns_the_parsed_closures(
        self,
        mock_fetch_webpage_text,
        mock_parse_bridge_closures,
        mock_log,
    ):
        result = get_current_bridge_closures()

        assert result == mock_parse_bridge_closures.return_value
