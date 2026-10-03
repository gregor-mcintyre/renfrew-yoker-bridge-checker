from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from bridge_skill._cache_reading import (
    ClosureCacheReadError,
    read_cached_bridge_closures,
)
from closure_cache import PARAMETER_NAME
from tests import patch_targets

_READ_ERRORS = [
    pytest.param(
        ClientError(
            {"Error": {"Code": "ParameterNotFound", "Message": "Not found"}},
            "GetParameter",
        ),
        id="client_error",
    ),
    pytest.param(NoCredentialsError(), id="botocore_error"),
]


@patch(f"{patch_targets.CACHE_READING}.deserialize_bridge_closures_from_json")
@patch(f"{patch_targets.CACHE_READING}.boto3.client")
class TestReadCachedBridgeClosures:
    def test_creates_an_ssm_client(
        self,
        mock_boto3_client,
        mock_deserialize_bridge_closures_from_json,
    ):
        read_cached_bridge_closures()

        mock_boto3_client.assert_called_once_with("ssm")

    def test_gets_the_closures_parameter(
        self,
        mock_boto3_client,
        mock_deserialize_bridge_closures_from_json,
    ):
        read_cached_bridge_closures()

        mock_boto3_client.return_value.get_parameter.assert_called_once_with(
            Name=PARAMETER_NAME,
        )

    def test_deserializes_the_value_of_the_parameter(
        self,
        mock_boto3_client,
        mock_deserialize_bridge_closures_from_json,
    ):
        parameter_value = Mock()

        mock_boto3_client.return_value.get_parameter.return_value = {
            "Parameter": {"Value": parameter_value},
        }

        read_cached_bridge_closures()

        mock_deserialize_bridge_closures_from_json.assert_called_once_with(
            parameter_value,
        )

    @pytest.mark.parametrize("error", _READ_ERRORS)
    def test_read_error_raises_a_closure_cache_read_error(
        self,
        mock_boto3_client,
        mock_deserialize_bridge_closures_from_json,
        error,
    ):
        mock_boto3_client.return_value.get_parameter.side_effect = error

        with pytest.raises(ClosureCacheReadError):
            read_cached_bridge_closures()

    @pytest.mark.parametrize("error", _READ_ERRORS)
    def test_read_error_chains_the_error_that_caused_it(
        self,
        mock_boto3_client,
        mock_deserialize_bridge_closures_from_json,
        error,
    ):
        mock_boto3_client.return_value.get_parameter.side_effect = error

        with pytest.raises(ClosureCacheReadError) as exc_info:
            read_cached_bridge_closures()

        assert exc_info.value.__cause__ is error

    @pytest.mark.parametrize("error", _READ_ERRORS)
    def test_read_error_carries_the_message_of_the_error(
        self,
        mock_boto3_client,
        mock_deserialize_bridge_closures_from_json,
        error,
    ):
        mock_boto3_client.return_value.get_parameter.side_effect = error

        with pytest.raises(ClosureCacheReadError) as exc_info:
            read_cached_bridge_closures()

        assert str(exc_info.value) == str(error)

    def test_returns_the_deserialized_closures(
        self,
        mock_boto3_client,
        mock_deserialize_bridge_closures_from_json,
    ):
        result = read_cached_bridge_closures()

        assert result == mock_deserialize_bridge_closures_from_json.return_value
