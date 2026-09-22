"""Tests `refresh_closure_cache`, including real parsing and serialization."""

import json
from unittest.mock import patch

import pytest
import requests

from bridge_closures._fetching import WebpageUnavailableError
from bridge_closures.cache_refresh import refresh_closure_cache
from tests import patch_target
from tests.closure_data import BRIDGE_CLOSURE, FETCHED_AT
from tests.integration.raspberry_pi.bridge_closures._helpers import (
    PAGE_WITH_CLOSURE,
    PAGE_WITHOUT_CLOSURE,
    build_response,
)


@patch(patch_target.BRIDGE_CLOSURES_PACKAGE + ".cache_refresh.datetime")
@patch(patch_target.BRIDGE_CLOSURES_PACKAGE + "._uploading.boto3.client")
@patch(patch_target.BRIDGE_CLOSURES_PACKAGE + "._fetching.requests.get")
class TestRefreshClosureCache:
    def test_unreachable_webpage_leaves_the_cache_unwritten(
        self,
        mock_requests_get,
        mock_boto3_client,
        mock_datetime,
    ):
        mock_requests_get.side_effect = requests.ConnectionError("Webpage unavailable")

        with pytest.raises(WebpageUnavailableError):
            refresh_closure_cache()

        mock_boto3_client.return_value.put_parameter.assert_not_called()

    def test_no_closures_on_the_webpage_caches_an_empty_closure_list(
        self,
        mock_requests_get,
        mock_boto3_client,
        mock_datetime,
    ):
        mock_requests_get.return_value = build_response(PAGE_WITHOUT_CLOSURE)
        mock_datetime.now.return_value = FETCHED_AT

        refresh_closure_cache()

        put_parameter_kwargs = (
            mock_boto3_client.return_value.put_parameter.call_args.kwargs
        )
        assert json.loads(put_parameter_kwargs["Value"]) == {
            "fetched_at": FETCHED_AT.isoformat(),
            "closures": [],
        }

    def test_closure_on_the_webpage_reaches_the_cached_payload(
        self,
        mock_requests_get,
        mock_boto3_client,
        mock_datetime,
    ):
        mock_requests_get.return_value = build_response(PAGE_WITH_CLOSURE)
        mock_datetime.now.return_value = FETCHED_AT

        refresh_closure_cache()

        put_parameter_kwargs = (
            mock_boto3_client.return_value.put_parameter.call_args.kwargs
        )
        assert json.loads(put_parameter_kwargs["Value"]) == {
            "fetched_at": FETCHED_AT.isoformat(),
            "closures": [
                {
                    "start": BRIDGE_CLOSURE.start.isoformat(),
                    "end": BRIDGE_CLOSURE.end.isoformat(),
                },
            ],
        }
