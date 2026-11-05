"""Synthetic tests for count-only egress-probe validation."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "official" / "fm_local"))

import check_network_probe as probe  # noqa: E402


RELAY = "http://10.0.2.2:12345/api/version"


def report(**overrides):
    rows = {url: {"reachable": False, "http_code": "000", "detail": "private diagnostic"}
            for url in probe.EXTERNAL_URLS}
    rows[RELAY] = {"reachable": True, "http_code": "200", "detail": "private diagnostic"}
    rows.update(overrides)
    return rows


def test_only_relay_reachable_passes():
    result = probe.evaluate(
        report(), task=probe.PROBE_TASK, harness="codex", relay_url=RELAY, raw_sha256="a" * 64
    )
    assert result["status"] == "pass"
    assert result["checked_host_count"] == 5
    assert result["relay_reachable"] is True
    assert result["vendor_reachable"] == result["other_reachable"] == 0
    assert "private diagnostic" not in str(result)


def test_vendor_reachability_fails_closed():
    result = probe.evaluate(
        report(**{"https://api.anthropic.com": {"reachable": True}}),
        task=probe.PROBE_TASK,
        harness="claude-code",
        relay_url=RELAY,
        raw_sha256="b" * 64,
    )
    assert result["status"] == "fail"
    assert result["vendor_reachable"] == 1


def test_non_relay_public_host_reachability_fails():
    result = probe.evaluate(
        report(**{"https://example.com": {"reachable": True}}),
        task=probe.PROBE_TASK,
        harness="codex",
        relay_url=RELAY,
        raw_sha256="c" * 64,
    )
    assert result["status"] == "fail"
    assert result["other_reachable"] == 1


def test_missing_host_and_relay_failure_fail_closed():
    rows = report()
    rows.pop("https://api.openai.com")
    rows[RELAY] = {"reachable": False}
    result = probe.evaluate(
        rows, task=probe.PROBE_TASK, harness="codex", relay_url=RELAY, raw_sha256="d" * 64
    )
    assert result["status"] == "fail"


def test_wrong_policy_task_fails_closed():
    result = probe.evaluate(
        report(), task="apex-eurogrid-curtailment", harness="codex", relay_url=RELAY,
        raw_sha256="e" * 64,
    )
    assert result["status"] == "fail"
