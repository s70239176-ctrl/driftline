# Submission copy

**Category:** Standalone Intelligent Contract
**Title:** Driftline: consensus-witnessed semantic drift of a public commitment
**Repository:** https://github.com/s70239176-ctrl/driftline
**Canonical Studionet address:** `0x1C7712e0C3EB5B2ec924e91846C95945cf4dfE3E`
**Explorer (genlayer-explorer-contract):** https://explorer-studio.genlayer.com/address/0x1C7712e0C3EB5B2ec924e91846C95945cf4dfE3E
**Deployment tx:** `0x34147ef61c8aff30f6613a8c14bd49c556d703a5afde414f60f8dfda2fec8751` (FINALIZED, MAJORITY_AGREE)
**Deployment source:** commit `dda0588`, `contracts/driftline.py` blob `5c6aa7bb…`; on-chain code SHA-256 equals the repo file
**Evidence doc:** https://github.com/s70239176-ctrl/driftline/blob/main/docs/DEPLOYMENT.md

## Portal description (under 1000 characters)

Driftline is a standalone GenLayer Intelligent Contract that tells other contracts whether a public commitment (terms, policy, spec) still says what it said when they relied on it. Validators independently fetch the page, re-check which recorded commitments vanished, and re-judge severity; a malicious leader is rejected if its evidence is not found in the validator's own copy. Deterministic code owns the state machine, versioned baselines, a latched DRIFTED state and reliance_status (RELIABLE/STALE/BLOCKED/UNKNOWN). Unreachable or unparseable pages fail closed. Verified: 103 Direct Mode tests, GenVM lint/SDK validation, 4 Studionet integration tests, a FINALIZED Studionet deployment, and a live DRIFTED verdict on a weakened terms page.

(Length verified under 1000 characters before submission.)

## Reviewer fast path

See README "Verify". Live evidence table: docs/DEPLOYMENT.md. The full DRIFTED -> owner re-baseline -> STABLE cycle is shown live on watch #3.
