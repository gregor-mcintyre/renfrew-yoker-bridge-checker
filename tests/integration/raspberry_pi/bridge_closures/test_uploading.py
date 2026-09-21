"""Tests `upload_bridge_closures`, including real bridge closure serialization."""

import json
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from bridge_closures._uploading import ClosureCacheWriteError, upload_bridge_closures
from closure_cache import PARAMETER_NAME
from tests import patch_target
from tests.closure_data import BRIDGE_CLOSURE, FETCHED_AT

_BOTO3_CLIENT = patch_target.BRIDGE_CLOSURES_PACKAGE + "._uploading.boto3.client"


@patch(_BOTO3_CLIENT)
class TestUploadBridgeClosures:
    def test_put_parameter_client_error_raises_closure_cache_write_error(
        self,
        mock_boto3_client,
    ):
        mock_boto3_client.return_value.put_parameter.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            "PutParameter",
        )

        with pytest.raises(ClosureCacheWriteError):
            upload_bridge_closures([BRIDGE_CLOSURE], fetched_at=FETCHED_AT)

    def test_puts_the_exact_serialized_json_into_the_parameter(self, mock_boto3_client):
        upload_bridge_closures([BRIDGE_CLOSURE], fetched_at=FETCHED_AT)

        put_parameter_kwargs = (
            mock_boto3_client.return_value.put_parameter.call_args.kwargs
        )
        assert put_parameter_kwargs["Name"] == PARAMETER_NAME
        assert json.loads(put_parameter_kwargs["Value"]) == {
            "fetched_at": FETCHED_AT.isoformat(),
            "closures": [
                {
                    "start": BRIDGE_CLOSURE.start.isoformat(),
                    "end": BRIDGE_CLOSURE.end.isoformat(),
                },
            ],
        }
