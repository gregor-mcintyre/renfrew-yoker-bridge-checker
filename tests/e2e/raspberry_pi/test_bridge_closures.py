"""Tests the scheduled scrape end to end, from systemd invocation to exit code."""

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parents[3]

# Refusing the connection at the proxy is the narrowest way to put the council website
# out of reach without a network. Both cases of each variable are set because `requests`
# reads the lowercase one first, so a machine-wide proxy would otherwise win.
_DEAD_PROXY = "http://127.0.0.1:1"
_ENVIRONMENT_OVERRIDES = {
    "PYTHONPATH": os.pathsep.join(["shared", "raspberry_pi"]),
    "HTTPS_PROXY": _DEAD_PROXY,
    "https_proxy": _DEAD_PROXY,
    "NO_PROXY": "",
    "no_proxy": "",
}


def _run_bridge_closures() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bridge_closures"],
        cwd=_REPO_ROOT,
        env=os.environ | _ENVIRONMENT_OVERRIDES,
        capture_output=True,
        text=True,
    )


class TestBridgeClosures:
    def test_unreachable_webpage_exits_with_code_one(self):
        result = _run_bridge_closures()

        assert result.returncode == 1

    def test_unreachable_webpage_logs_the_failure(self):
        result = _run_bridge_closures()

        expected_message = "The scheduled Renfrew-Yoker bridge closure scrape failed."
        assert expected_message in result.stderr

    def test_unreachable_webpage_logs_in_the_configured_format(self):
        result = _run_bridge_closures()

        assert "ERROR bridge_closures.cache_refresh: " in result.stderr
