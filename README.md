# Driftline

**A GenLayer Intelligent Contract that tells other contracts whether a public commitment (a terms page, policy or spec) still says what it said when they relied on it.**

Validators independently fetch the page, re-check which recorded commitments are gone, and re-judge how material the change is. Deterministic contract code turns that agreement into a latched `DRIFTED` state and a machine-readable `reliance_status` (`RELIABLE` / `STALE` / `BLOCKED` / `UNKNOWN`).

| | |
|---|---|
| Network | GenLayer Studionet (chain 61999) |
| Contract | [`0x1C7712e0C3EB5B2ec924e91846C95945cf4dfE3E`](https://explorer-studio.genlayer.com/address/0x1C7712e0C3EB5B2ec924e91846C95945cf4dfE3E) |
| Deployment tx | `0x34147ef61c8aff30f6613a8c14bd49c556d703a5afde414f60f8dfda2fec8751` (FINALIZED, MAJORITY_AGREE) |
| Source | `contracts/driftline.py`, deployed from commit `dda0588`; on-chain code SHA-256 equals the repo file |
| Tests | 103 Direct Mode, 4 Studionet integration, GenVM lint and SDK validation passing |
| Live drift | tx `0x499f87d9…ade3957`: `DRIFTED`, severity 3, evidence = the removed "never sell your personal data" clause |

Full evidence: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Overlap analysis: [DECISION.md](DECISION.md).

## Who calls it and what it decides

An insurance pool, grant DAO, or escrow that depends on someone else's published terms registers a **watch**: URL, plain-language *focus* ("data privacy and refund commitments"), and a severity threshold (MATERIAL or CRITICAL). The owner records a **baseline**; anyone can later trigger a **check**. The contract decides one thing: *does the page still honour the baseline, at or above the threshold?*

## Why GenLayer

| Alternative | Why it falls short |
|---|---|
| The relying party checks | conflict of interest; it authors the verdict |
| The publisher attests | conflict of interest the other way |
| A backend / oracle operator | single point of trust |
| A deterministic contract | cannot fetch a page or judge "was the refund promise weakened" |
| One LLM | one reader, injectable by the very page it reads |

**Delete GenLayer and** someone has to be the authority that fetches the page and decides whether the change matters.

## State machine

```
AWAITING_BASELINE --set_baseline--> STABLE --check(sev < threshold)--> STABLE
                                      |  \--check(unreachable / unclassified)--> STABLE (recorded, trust not advanced)
                                      \--check(sev >= threshold)--> DRIFTED (latched)
DRIFTED --owner set_baseline (new version, lineage kept)--> STABLE
any --owner deactivate--> inactive (reliance UNKNOWN)
```

## Nondeterministic vs deterministic

Two custom-validator `run_nondet_unsafe` calls (`set_baseline`, `check`); everything else is deterministic: access control, URL admission, cooldown (60 s), state machine, versioning and hashes, a 16-slot ring buffer, the severity floor, the freshness logic. Details: [docs/CONSENSUS.md](docs/CONSENSUS.md).

- **Grounding:** each baseline clause carries a verbatim quote every validator must find in its *own* fetch; MATERIAL+ claims need verbatim `PRESENT` text or an `ABSENT` baseline quote.
- **Must agree:** reachability, the count of missing baseline quotes, and which side of the threshold the severity falls on.
- **Fail closed:** unreachable or unparseable is never drift and never counts as reliable; a deterministic floor makes "every baseline quote gone" at least MATERIAL.

## Reuse

```python
status = IDriftline(addr).view().reliance_status(watch_id, now_ts, max_age_s)  # RELIABLE/STALE/BLOCKED/UNKNOWN
ok = IDriftline(addr).view().receipt_matches(watch_id, definition_hash, baseline_hash)
```

See [docs/INTEGRATION.md](docs/INTEGRATION.md) and [docs/SECURITY.md](docs/SECURITY.md).

## Limitations

Honest-majority validator assumption; plain HTTP GET only (no JS-rendered or personalised pages); 8000 normalised characters per page; a baseline cannot prove completeness (omitted commitments are not detected); severity is model judgement near the threshold; source CDN caching delays detection (observed live, see DEPLOYMENT.md); Studionet is a development network, not an audited production deployment. Re-baselining after drift was tested in Direct Mode but **not** shown live (see DEPLOYMENT.md).

## Verify

```bash
python -m venv .venv-test && .venv-test/Scripts/pip install -r requirements-test.txt   # POSIX: bin/
PYTHONPATH=scripts pytest tests/direct -p windows_direct_plugin   # the plugin is only needed on Windows
pip install genvm-linter && genvm-lint check contracts/driftline.py
DRIFTLINE_FIXTURE_BASE=https://raw.githubusercontent.com/s70239176-ctrl/driftline/main/fixtures \
  gltest tests/integration/ -v -s --network studionet
```

Note: the live drift scenario (`scripts/live_drift.py`) depended on `fixtures/policy_mutable.txt`, which was deliberately changed on `main` to the weakened text; `fixtures/policy_stable.txt` is unchanged and is what the integration suite uses.
