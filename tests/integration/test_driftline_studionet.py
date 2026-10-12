"""Real-consensus Studionet tests. Each test deploys its own disposable contract.

Run:  DRIFTLINE_FIXTURE_BASE=https://raw.githubusercontent.com/<owner>/<repo>/main/fixtures \
      gltest tests/integration/ -v -s --network studionet

The pages are committed fixtures served by raw.githubusercontent.com, so validators fetch
the same public bytes. The material-drift path needs a page that changes at a fixed URL, so it
lives in scripts/live_drift.py (a staged runbook), not here.
"""
import os
import time

import pytest
from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded

BASE = os.environ.get("DRIFTLINE_FIXTURE_BASE", "").rstrip("/")
FOCUS = "Data privacy and refund commitments to customers"
GAP_S = 65
# Studionet's gateway rate-limits (~30 req/min): poll slowly so a run does not trip it.
WAIT = {"wait_interval": 10000, "wait_retries": 30}
TX = {"consensus_max_rotations": 3, **WAIT}

pytestmark = pytest.mark.skipif(not BASE, reason="set DRIFTLINE_FIXTURE_BASE to the raw fixtures URL")


def _deploy():
    factory = get_contract_factory(contract_file_path="driftline.py")
    return factory.deploy(account=get_default_account(), consensus_max_rotations=3, **WAIT)


def _register(c, name, min_sev=2):
    r = c.register_watch(args=[f"{BASE}/{name}", FOCUS, min_sev]).transact(**TX)
    assert tx_execution_succeeded(r)
    assert c.get_watch(args=[1]).call()["url"].endswith(name)  # setup really created state
    return 1


def test_deploy_and_public_surface():
    c = _deploy()
    wid = _register(c, "policy_stable.txt")
    w = c.get_watch(args=[wid]).call()
    assert w["status"] == "AWAITING_BASELINE" and w["version"] == 0 and len(w["definition_hash"]) == 64
    assert c.reliance_status(args=[wid, 1_800_000_000, 3600]).call() == "UNKNOWN"


def test_live_baseline_then_stable_check():
    c = _deploy()
    wid = _register(c, "policy_stable.txt")
    r = c.set_baseline(args=[wid]).transact(**TX)
    assert tx_execution_succeeded(r)
    w = c.get_watch(args=[wid]).call()
    assert w["status"] == "STABLE" and w["version"] == 1 and len(w["baseline_hash"]) == 64
    quotes = [x["quote"] for x in c.get_baseline(args=[wid]).call()]
    assert quotes and all(q in open("fixtures/policy_stable.txt", encoding="utf-8").read() for q in quotes)

    time.sleep(GAP_S)
    r = c.check(args=[wid]).transact(**TX)
    assert tx_execution_succeeded(r)
    o = c.get_observation(args=[wid, 1]).call()
    assert o["outcome"] == "STABLE" and o["missing"] == 0 and o["severity"] < 2
    assert c.is_drifted(args=[wid]).call() is False
    assert c.is_reliable(args=[wid, w["baseline_ts"] + 10, 3600]).call() is True


def test_live_unreadable_source_fails_closed():
    c = _deploy()
    wid = _register(c, "no_such_fixture.txt")  # raw.githubusercontent.com answers 404
    r = c.set_baseline(args=[wid]).transact(**TX)
    assert not tx_execution_succeeded(r)
    w = c.get_watch(args=[wid]).call()
    assert w["version"] == 0 and w["status"] == "AWAITING_BASELINE"
    assert c.reliance_status(args=[wid, 1_800_000_000, 3600]).call() == "UNKNOWN"


def test_live_check_before_baseline_rejected():
    c = _deploy()
    wid = _register(c, "policy_stable.txt")
    r = c.check(args=[wid]).transact(**TX)
    assert not tx_execution_succeeded(r)
    assert c.get_watch(args=[wid]).call()["obs_count"] == 0
