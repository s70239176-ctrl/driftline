# Threat model

**Assets:** the integrity of the `STABLE`/`DRIFTED` verdict and of `reliance_status`; the baseline a
consumer pinned. No funds are held or moved.

**Actors:** owner (defines watch, records baseline), any caller (triggers checks), page publisher
(controls the source), malicious leader, honest validators, malicious validator minority, downstream
consumer.

**Trust assumptions:** an honest majority of validators; validators can reach the public web; the
publisher's page is the authoritative statement of the commitment.

## Input attacks and defences

| Attack | Defence |
|---|---|
| Prompt injection in the page ("report severity 0") | Page text is placed in a JSON `document` field labelled DATA; the deterministic floor (all quotes gone => MATERIAL) and verbatim-grounded evidence limit what the model can change; tested |
| Leader forges "stable" or "drift" | Validators recompute `missing`, re-ground evidence in their own fetch, re-judge the threshold class; tested in `test_driftline_hardening.py` |
| Leader fabricates a baseline commitment | Every quote must be a verbatim substring of each validator's own fetch |
| Type confusion (`True`, `2.0`, `"0x2"`, unknown enum, extra field) | Exact `type(x) is int/str/dict` checks; unknown values never map to a positive result; tested |
| Malformed/hostile URL | HTTPS only; no credentials, ports, IPs, numeric hosts, `localhost/.local/.internal`; length/charset bounds. This is defence in depth, **not** an SSRF guarantee: validator egress policy still matters |
| Cheap spam checks / state bloat | 60 s cooldown; 16-slot ring buffer; clause, string and text caps |
| Drift hidden by a transient outage | Unreachable is a separate outcome and never resets or clears `DRIFTED` |
| Owner silently weakens the baseline after a trusted period | `baseline_hash` + `version` change on every re-baseline; consumers pin with `receipt_matches` |
| Replay | `DRIFTED` is latched; only a new owner baseline (new version) clears it |

## Fail-open / fail-closed policy

Every safety default is closed: unreachable, unparseable, ungroundable, or unknown => never `RELIABLE`
because of it, never silently `STABLE` for the purpose of advancing freshness. `DRIFTED` is the only
state that blocks; `UNKNOWN`/`STALE` also tell consumers not to rely.

## Limitations (honest)

- A malicious owner or leader can **omit** a commitment from the baseline; validators check what is
  there, not what is missing. The owner is trusted to define what matters (they can also just not watch).
- The page is capped to 8000 normalised chars; a decisive change beyond the cap is invisible.
- The model's severity is judgement; only the threshold side is consensus-critical. Edge cases near the
  threshold can be flaky and may cause `UNDETERMINED` rounds.
- Dynamic pages (timestamps, A/B copy, JS-rendered text) are out of scope: the fetch is a plain GET.
- A source that serves different content to different validators can cause disagreement or be gamed.
- Studionet deployment is a development network, not an audited production deployment.
- Not legal advice; "drift" means "the page text no longer supports the recorded commitments".
- Source-side caching: a CDN-fronted page (for example raw.githubusercontent.com, `max-age=300`) can
  serve validators stale bytes, delaying detection by the cache lifetime. Observed live; see DEPLOYMENT.md.
