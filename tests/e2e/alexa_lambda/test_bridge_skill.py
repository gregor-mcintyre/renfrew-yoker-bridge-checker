"""Tests the Alexa skill end to end, from its deployment zip to the response."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import boto3
import pytest

_REPO_ROOT = Path(__file__).parents[3]
_REQUESTS_DIRECTORY = Path(__file__).parent / "requests"
_DEPLOYMENT_ZIP = _REPO_ROOT / "build" / "alexa_lambda.zip"
_INTERACTION_MODEL = _REPO_ROOT / "alexa_lambda" / "interaction_model.json"

_PARAMETER_NAME = "/renfrew-yoker-bridge-checker/closures"
_FUNCTION_NAME = "renfrew-yoker-bridge-checker-alexa"

_BRIDGE_STATUS_START = "The Renfrew-Yoker bridge is "
_OPEN_SPEECH = f"{_BRIDGE_STATUS_START}open now. No upcoming closures are listed."

# Names the profile the scrape runs under; the live tests' own profile is read-only
_SCRAPE_PROFILE_VARIABLE = "SCRAPE_AWS_PROFILE"

# Calls the handler as AWS Lambda does, with only the read of the cache faked
_ANSWER_SCRIPT = """
import json
import sys
from datetime import UTC, datetime
from unittest.mock import patch

from bridge_skill.lambda_function import lambda_handler

with open(sys.argv[1]) as request_file:
    event = json.load(request_file)

cache = json.dumps({"fetched_at": datetime.now(UTC).isoformat(), "closures": []})

with patch("boto3.client") as mock_client:
    mock_client.return_value.get_parameter.return_value = {
        "Parameter": {"Value": cache},
    }
    response = lambda_handler(event, None)

print(response["response"]["outputSpeech"]["text"])
"""


@pytest.fixture(scope="module")
def unpacked_zip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Builds the deployment zip with the documented command and unpacks it.

    Args:
        tmp_path_factory: The factory of the temporary directory to unpack into.

    Returns:
        The directory holding the unpacked zip, which is how Lambda unpacks it.
    """
    subprocess.run(
        [sys.executable, "alexa_lambda/deployment_zip.py"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    directory = tmp_path_factory.mktemp("alexa_lambda")

    with ZipFile(_DEPLOYMENT_ZIP) as archive:
        archive.extractall(directory)

    return directory


def _answer_from_unpacked_zip(directory: Path, request_file: str) -> str:
    """Runs the handler in the unpacked zip the way AWS Lambda does.

    Args:
        directory: The directory holding the unpacked zip, which is the only place the
            handler can import from.
        request_file: The name of the file in the requests directory holding the
            request Alexa sends.

    Returns:
        What the handler says.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            _ANSWER_SCRIPT,
            str(_REQUESTS_DIRECTORY / request_file),
        ],
        cwd=directory,
        env=os.environ | {"PYTHONPATH": str(directory)},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    return result.stdout.strip()


class TestBridgeSkill:
    # The virtualenv has its own `tzdata`, so the answers below would pass without it
    def test_zip_holds_the_time_zone_database(self, unpacked_zip):
        london = unpacked_zip / "tzdata" / "zoneinfo" / "Europe" / "London"

        assert london.is_file()

    def test_interaction_model_names_the_skill_renfrew_yoker_bridge(self):
        model = json.loads(_INTERACTION_MODEL.read_text())

        assert model["interactionModel"]["languageModel"]["invocationName"] == (
            "renfrew yoker bridge"
        )

    @pytest.mark.parametrize(
        "request_file",
        ["launch_request.json", "get_bridge_closures_intent_request.json"],
    )
    def test_request_speaks_that_the_bridge_is_open(self, unpacked_zip, request_file):
        result = _answer_from_unpacked_zip(unpacked_zip, request_file)

        assert result == _OPEN_SPEECH


def _build_scrape_environment() -> dict[str, str]:
    """Builds the environment the scrape runs in, apart from the live test profile.

    Returns:
        The environment of this process with `AWS_PROFILE` replaced by the value of
        the variable named `_SCRAPE_PROFILE_VARIABLE`, or left out if that is unset,
        so the scrape runs under the default profile. `PYTHONPATH` is set to the roots
        the scrape imports from.
    """
    environment = {
        name: value for name, value in os.environ.items() if name != "AWS_PROFILE"
    }
    environment["PYTHONPATH"] = os.pathsep.join(["shared", "raspberry_pi"])

    if _SCRAPE_PROFILE_VARIABLE in os.environ:
        environment["AWS_PROFILE"] = os.environ[_SCRAPE_PROFILE_VARIABLE]

    return environment


@pytest.fixture(scope="class")
def scrape_started_at() -> datetime:
    """Runs the documented scrape, which writes a fresh cache to the AWS account.

    Returns:
        The moment the scrape started.
    """
    started_at = datetime.now(UTC)

    result = subprocess.run(
        [sys.executable, "-m", "bridge_closures"],
        cwd=_REPO_ROOT,
        env=_build_scrape_environment(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    return started_at


@pytest.fixture(scope="class")
def cache_fetched_at() -> datetime:
    """Reads when the closures in the deployed AWS cache were fetched.

    Returns:
        The date and time the cached closures were fetched.
    """
    response = boto3.client("ssm").get_parameter(Name=_PARAMETER_NAME)
    cached = json.loads(response["Parameter"]["Value"])

    return datetime.fromisoformat(cached["fetched_at"])


@pytest.fixture(scope="class")
def deployed_answer() -> str:
    """Asks the deployed Lambda function to answer a request that opens the skill.

    Returns:
        What the function says.
    """
    invocation = boto3.client("lambda").invoke(
        FunctionName=_FUNCTION_NAME,
        Payload=(_REQUESTS_DIRECTORY / "launch_request.json").read_bytes(),
    )
    response = json.loads(invocation["Payload"].read())

    return str(response["response"]["outputSpeech"]["text"])


@pytest.mark.live
@pytest.mark.usefixtures("scrape_started_at")
class TestDeployedSkill:
    def test_cache_holds_the_fetch_the_scrape_just_made(
        self,
        scrape_started_at,
        cache_fetched_at,
    ):
        assert cache_fetched_at >= scrape_started_at

    def test_answer_says_whether_the_bridge_is_open_or_closed(self, deployed_answer):
        assert deployed_answer.startswith(_BRIDGE_STATUS_START)
