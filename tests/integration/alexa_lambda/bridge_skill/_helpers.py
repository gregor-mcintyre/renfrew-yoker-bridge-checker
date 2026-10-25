"""Stubs for the AWS cache shared by the bridge skill integration tests."""

from unittest.mock import Mock


def stub_cache_payload(mock_boto3_client: Mock, payload: str) -> None:
    """Makes the patched SSM client return a payload when the closures are read.

    Args:
        mock_boto3_client: The mock replacing `boto3.client`.
        payload: The JSON payload the closures parameter holds.
    """
    mock_boto3_client.return_value.get_parameter.return_value = {
        "Parameter": {"Value": payload},
    }
