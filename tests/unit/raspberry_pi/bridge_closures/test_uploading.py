import logging
from typing import cast
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from bridge_closure import BridgeClosure
from bridge_closures._uploading import (
    ClosureCacheWriteError,
    _log,
    upload_bridge_closures,
)
from closure_cache import PARAMETER_NAME
from tests import patch_target
from tests.closure_data import FETCHED_AT

_UPLOADING_MODULE = patch_target.BRIDGE_CLOSURES_PACKAGE + "._uploading"


class TestLog:
    def test_empty_list_logs_an_empty_closure_list(self, caplog):
        caplog.set_level(logging.INFO)

        _log([])

        expected_message = (
            "Uploaded an empty closure list to the Renfrew-Yoker bridge closures AWS "
            "cache."
        )
        assert expected_message in caplog.text

    def test_non_empty_list_logs_the_closures(self, caplog):
        caplog.set_level(logging.INFO)

        closures = cast(list[BridgeClosure], [Mock(), Mock()])

        _log(closures)

        expected_message = (
            "Uploaded the following closures to the Renfrew-Yoker bridge closures AWS "
            f"cache: {closures!r}"
        )
        assert expected_message in caplog.text


@patch(f"{_UPLOADING_MODULE}._log")
@patch(f"{_UPLOADING_MODULE}.serialize_bridge_closures_to_json")
@patch(f"{_UPLOADING_MODULE}.boto3.client")
class TestUploadBridgeClosures:
    def test_serializes_the_closures_with_the_fetched_at_timestamp(
        self,
        mock_boto3_client,
        mock_serialize_bridge_closures_to_json,
        mock_log,
    ):
        closures = cast(list[BridgeClosure], [Mock(), Mock()])

        upload_bridge_closures(closures, fetched_at=FETCHED_AT)

        mock_serialize_bridge_closures_to_json.assert_called_once_with(
            closures,
            fetched_at=FETCHED_AT,
        )

    def test_puts_the_serialized_closures_into_the_parameter(
        self,
        mock_boto3_client,
        mock_serialize_bridge_closures_to_json,
        mock_log,
    ):
        upload_bridge_closures([], fetched_at=FETCHED_AT)

        mock_boto3_client.return_value.put_parameter.assert_called_once_with(
            Name=PARAMETER_NAME,
            Value=mock_serialize_bridge_closures_to_json.return_value,
            Type="String",
            Overwrite=True,
        )

    def test_raises_a_closure_cache_write_error_if_the_write_fails(
        self,
        mock_boto3_client,
        mock_serialize_bridge_closures_to_json,
        mock_log,
    ):
        mock_boto3_client.return_value.put_parameter.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            "PutParameter",
        )

        with pytest.raises(ClosureCacheWriteError):
            upload_bridge_closures([], fetched_at=FETCHED_AT)

    def test_chains_the_botocore_error_that_caused_the_failure(
        self,
        mock_boto3_client,
        mock_serialize_bridge_closures_to_json,
        mock_log,
    ):
        original_error = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            "PutParameter",
        )
        mock_boto3_client.return_value.put_parameter.side_effect = original_error

        with pytest.raises(ClosureCacheWriteError) as exc_info:
            upload_bridge_closures([], fetched_at=FETCHED_AT)

        assert exc_info.value.__cause__ is original_error

    def test_logs_the_uploaded_closures(
        self,
        mock_boto3_client,
        mock_serialize_bridge_closures_to_json,
        mock_log,
    ):
        closures = cast(list[BridgeClosure], [Mock(), Mock()])

        upload_bridge_closures(closures, fetched_at=FETCHED_AT)

        mock_log.assert_called_once_with(closures)
