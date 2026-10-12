# Canonical Studionet deployment and live evidence

| | |
|---|---|
| Date | 2026-10-12 |
| Network | GenLayer Studionet (hosted), chain id 61999 |
| RPC | https://studio.genlayer.com/api |
| Deployment method | `genlayer-test` Studio Mode (`ContractFactory.deploy_contract_tx`, `scripts/live_drift.py deploy`) |
| Deployer (public address) | `0x2E63c021C16Bf0835eaa594e5DD078d1D6101F7e` (ephemeral per-session key from `get_default_account()`; not retained, so watch #1 has no recoverable owner) |
| Canonical contract | `0x1C7712e0C3EB5B2ec924e91846C95945cf4dfE3E` |
| Explorer | https://explorer-studio.genlayer.com/address/0x1C7712e0C3EB5B2ec924e91846C95945cf4dfE3E |
| Deployment tx | `0x34147ef61c8aff30f6613a8c14bd49c556d703a5afde414f60f8dfda2fec8751` |
| Lifecycle / consensus | FINALIZED / MAJORITY_AGREE (queried via `eth_getTransactionByHash`) |
| Contract source | `contracts/driftline.py`, git blob `5c6aa7bb4083ab87010e7d7eba4daccc7eddf06a` |
| Deployment source commit | `dda0588` (the file has not changed in any later commit) |
| Source parity | SHA-256 of the on-chain code (`gen_getContractCode`) equals SHA-256 of `contracts/driftline.py` (`60d6a5ee…f9af`, 25873 bytes); the file has no CR bytes |
| Tooling | Python 3.12.10, genlayer-test 0.29.2, genlayer-py 0.16.3, cloudpickle 3.1.2, genvm-linter 0.11.0 |

## Live transactions on the canonical contract

All 15 transactions on the canonical contract were FINALIZED with MAJORITY_AGREE when last queried.

| Scenario | Action | Tx | Stored / observed result |
|---|---|---|---|
| setup | `register_watch(policy_mutable.txt, focus, 2)` | `0xebc646891817bc378434acc467e48ea9296daaf56845ec5f9e26727afa7c6e56` | watch #1 created, `AWAITING_BASELINE` |
| baseline | `set_baseline(1)` (page v1) | `0xbc738f4b11533eaef63292cc5298b2fcccb402ca6469e5ba8a941e7b693702cd` | `STABLE`, version 1, baseline hash `b8c89c89…8f5c` |
| success (stale CDN) | `check(1)` after the fixture was pushed | `0xda2510fe6524732992a251d756db00d56f231df3d5039f557ccae11d2a449d10` | `STABLE`, `missing 0`: validators fetched the CDN-cached v1 page (see note) |
| **negative: material drift** | `check(1)` after the cache expired | `0x499f87d99ddba6639dd17f31c30407ad5a3d63e3e67581272cec93627ade3957` | **`DRIFTED`**, severity 3, evidence `ABSENT`: "We will never sell your personal data to third parties.", `missing 1`; watch status latched `DRIFTED` |
| fail closed: access control | `set_baseline(1)` from a different account | `0x5415184b1242801d2c200746da59346f8c7c659b682e810643666628f22ee64d` | reverted `EXPECTED: only the owner may do this`; all validators agreed; state unchanged |
| fail closed: latch | `check(1)` while `DRIFTED` | `0x9a1ecfc279b22e18331bc856b2de718cb8eb5e3b622216573bc863eaf5b91177` | reverted (a drifted watch cannot be re-checked back to stable) |
| lifecycle | `register_watch` #2 (stable page) | `0xd9a997c6d217cffd24401e9926574e274964f24f1382061a6d41b3a014173f49` | created |
| lifecycle | `set_baseline(2)` | `0x3003e170e9b4a37679497956842e292b09a0ed9ad9dfb52a1149d847a0dd3a1e` | `reliance_status` = `RELIABLE` |
| lifecycle | `deactivate(2)` (owner, persistent throwaway key) | `0x35c0a9dc667b1fd0fa81db066505d7067cdd69ddb0d772649895f2f3eb40972e` | `reliance_status` = `UNKNOWN` |
| recovery: setup | `register_watch` #3 (owner = persistent throwaway key, page `policy_recover.txt`) | `0x2e7be828357521a10a711a4f1e6b5dfcc77df80d528bac3dd79aaf63c7138b76` | created |
| recovery: baseline | `set_baseline(3)` (page v1) | `0x125953f0a6b238a50484283632bf06c8d8f41fd7dee7019df465e751af752deb` | `STABLE`, version 1, baseline hash `3cf9e1b5…40c2` |
| **recovery: drift** | `check(3)` after the page was weakened and the CDN cache expired | `0x29259fe26cb8e14b7a7ac84c484f59dd3444421e67096e10282e09764204435e` | **`DRIFTED`**, severity 2, evidence `ABSENT` = the removed no-sale clause, `missing 1` |
| **recovery: re-baseline** | `set_baseline(3)` by the owner (page now v2) | `0xcfaa6a17dfe34b99c035549c84703588d132103ea0330d2a8f1f6cd3dc98d3e8` | version 2, `STABLE`, baseline hash `b712cd6a…af64`, `prev_baseline_hash` = `3cf9e1b5…40c2` (lineage kept), definition hash unchanged |
| **recovery: re-check** | `check(3)` against the new baseline | `0x1ec70d35d26f2d985710ca113affbdb15b88dc536740a9b4a9da46852d0c0fe6` | `STABLE`, `missing 0`, observation recorded against version 2 |

**CDN note.** raw.githubusercontent.com serves with `Cache-Control: max-age=300`. The first check ran
about four minutes after the fixture push and read the cached old page, so it correctly reported
`STABLE`. The contract reports what validators actually fetch; the second check, after expiry, detected
the drift. Real consumers should expect source-cache latency.

**Watch #1 owner note.** Watch #1 was registered by an ephemeral per-session key that was not kept, so the
re-baseline attempt from a different account was (correctly) rejected. Re-baselining after drift is
demonstrated live on watch #3 instead, which is owned by a persistent throwaway key (`.dev-key`, git-ignored).

## Test results

| Gate | Result |
|---|---|
| Direct Mode `pytest tests/direct -p windows_direct_plugin` | 103 passed, 0 failed, 0 skipped (~33 s), `check_pickling = True` |
| `genvm-lint lint` / `check` | passed; 13 methods (9 view, 4 write) |
| Studionet integration `gltest tests/integration/ -v -s --network studionet` | 4 passed (860 s). An earlier full run before the connection shim had 2 passed / 2 failed with client-side `ConnectTimeout`s; tests 2, 3, 4 each passed when run alone |
| Supplemental `genvm-lint typecheck` | not run |

Disposable contracts deployed by the integration tests are **not** the canonical deployment.

## Host-only workarounds (not contract changes)

- `scripts/windows_direct_plugin.py`: defers one temp-file unlink in genlayer-test 0.29.2's Direct Mode
  loader, which otherwise fails on Windows before any contract code runs. Committed, optional, test-only.
- `tests/integration/conftest.py`: forces IPv4 and retries *connection* failures for Python's `requests`
  against studio.genlayer.com, which intermittently timed out on this host while `curl` did not.
  Committed, test-only.
