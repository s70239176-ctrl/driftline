"""Staged live evidence on Studionet for the one path pytest cannot run: material drift.

The drift path needs a page that changes at a fixed URL, so it is staged around a git push of
fixtures/policy_mutable.txt:

  python scripts/live_drift.py deploy      # deploy canonical contract, register watch, record baseline (page = v1)
  # ... overwrite fixtures/policy_mutable.txt with fixtures/policy_mutable_v2.txt, commit, push ...
  python scripts/live_drift.py check       # expect DRIFTED (latched, evidence = the removed no-sale clause)
  python scripts/live_drift.py rebaseline  # owner records v2 as a new baseline (version 2, STABLE)
  python scripts/live_drift.py recheck     # expect STABLE against the new baseline

Needs DRIFTLINE_FIXTURE_BASE. Run with `gltest`'s Python (see requirements-test.txt) from the repo root.
State (address, tx hashes) is kept in artifacts/live_state.json (git-ignored); copy it into
docs/DEPLOYMENT.md. The deployer is the genlayer-test default Studionet account; no key is read or printed.
"""
import json
import os
import sys
import time

from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded

BASE = os.environ["DRIFTLINE_FIXTURE_BASE"].rstrip("/")
FOCUS = "Data privacy and refund commitments to customers"
STATE = "artifacts/live_state.json"
WAIT = {"wait_interval": 10000, "wait_retries": 40}
TX = {"consensus_max_rotations": 3, **WAIT}


def load():
    with open(STATE, encoding="utf-8") as f:
        return json.load(f)


def save(st):
    os.makedirs("artifacts", exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2)


def attach(st):
    factory = get_contract_factory(contract_file_path="driftline.py")
    return factory.build_contract(st["address"], account=get_default_account())


def send(st, label, call):
    r = call.transact(**TX)
    ok = tx_execution_succeeded(r)
    st.setdefault("txs", []).append(
        {"label": label, "hash": r.get("hash") or r.get("id"), "status": r.get("status_name") or str(r.get("status")), "ok": ok}
    )
    save(st)
    print(label, "->", st["txs"][-1])
    assert ok, f"{label} did not succeed"


def main(stage):
    if stage == "deploy":
        factory = get_contract_factory(contract_file_path="driftline.py")
        acct = get_default_account()
        receipt = factory.deploy_contract_tx(account=acct, consensus_max_rotations=3, **WAIT)
        assert tx_execution_succeeded(receipt)
        from gltest.utils import extract_contract_address  # noqa: PLC0415

        st = {"deployer": acct.address, "address": extract_contract_address(receipt), "txs": [
            {"label": "deploy", "hash": receipt.get("hash") or receipt.get("id"),
             "status": receipt.get("status_name") or str(receipt.get("status")), "ok": True}]}
        save(st)
        print("deployed", st)
        c = attach(st)
        send(st, "register_watch", c.register_watch(args=[f"{BASE}/policy_mutable.txt", FOCUS, 2]))
        send(st, "set_baseline v1", c.set_baseline(args=[1]))
        print(c.get_watch(args=[1]).call())
        return
    st = load()
    c = attach(st)
    if stage in ("check", "recheck"):
        time.sleep(65)  # check cooldown is 60 s of chain time
        send(st, stage, c.check(args=[1]))
        print(c.get_watch(args=[1]).call())
        w = c.get_watch(args=[1]).call()
        print(c.get_observation(args=[1, w["obs_count"]]).call())
    elif stage == "rebaseline":
        send(st, "set_baseline v2", c.set_baseline(args=[1]))
        print(c.get_watch(args=[1]).call())
        print(c.get_baseline(args=[1]).call())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
