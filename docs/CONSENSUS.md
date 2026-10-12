# Consensus design

Both nondeterministic operations use `gl.vm.run_nondet_unsafe(leader, validator)` with a **custom
validator**, because the leader's result is treated as adversarial: a perfectly well-formed result can
still be false, and the validator must be able to reject it.

## 1. `set_baseline` (owner only)

| | |
|---|---|
| Enters | the watch URL and focus (both immutable) |
| Leader | fetches the page, deterministically strips HTML/whitespace, caps to 8000 chars, asks the model for at most 8 `{statement, quote}` clauses (page text is JSON-framed as DATA), then **drops any clause whose quote is not a verbatim substring** of the page |
| Validator | type-checks the result strictly; independently fetches the page; requires every quote to appear in **its own** copy, no duplicates, 1-8 clauses, bounded lengths |
| Reachability | leader `UNREACHABLE` is accepted only if the validator also cannot read the page; leader `OK` is rejected if the validator cannot read it |
| Why not a model comparison | a leader cannot invent a commitment: every quote is independently grounded. Omission of a commitment is not detectable (see limitations in SECURITY.md); the owner chooses what to watch and can re-baseline |
| Result | contract stores clauses, `baseline_hash`, bumps `version`; unreachable or ungroundable results **revert** with no state change |

## 2. `check` (anyone, 60 s cooldown)

| | |
|---|---|
| Enters | URL, focus, the stored baseline clauses |
| Deterministic inside the block | page fetch/normalise; `missing` = baseline quotes not found in the page; severity floor (every quote gone => at least MATERIAL) |
| Leader | model proposes `severity` 0-3 + evidence; sanitiser requires exact types; MATERIAL+ must carry grounded evidence: `ABSENT` = a baseline quote that is in `missing`, or `PRESENT` = verbatim text on the page. Ungroundable => `UNCLASSIFIED` |
| Validator | strict shape check; independent fetch; **`missing` count must equal its own**; evidence re-grounded in its own fetch; independent model re-judgement with the same floor; accepts iff `(leader.severity >= min_severity) == (own.severity >= min_severity)` |
| Must agree | reachability class, `missing` count, the threshold decision |
| May differ | exact severity within a side of the threshold (e.g. MATERIAL vs CRITICAL when threshold is 2), evidence choice and wording, `statement` text |
| Not equivalent | DRIFTED vs STABLE; reachable vs unreachable; different `missing`; evidence that is not on / not absent from the validator's page; MATERIAL+ without evidence; wrong types (`True`, `2.0`, `"2"`, `"0x2"`), unknown enums, extra/missing fields |

## Deterministic responsibilities (the larger surface)

Access control; URL admission; cooldown; state machine; version/fingerprint bookkeeping; ring buffer;
latching `DRIFTED`; severity floor; `reliance_status` freshness logic; `receipt_matches`; all
re-validation of the consensus result before it is stored.

## Failure handling

| Event | Handling |
|---|---|
| Page unreachable / non-2xx / empty | Recorded as `UNREACHABLE`; **never drift**; baseline untouched; 3 in a row degrade reliance to `UNKNOWN` |
| Model reply unparseable / wrong types / ungrounded MATERIAL claim | `UNCLASSIFIED`: recorded, never advances trust (`last_ok_ts` not updated), never drift |
| Validators disagree | Protocol-level `UNDETERMINED`/rotation; the contract state is not mutated for that transaction. This is distinct from the contract-level `UNCLASSIFIED` |
| Baseline extraction fails | write reverts (`EXTERNAL:`); no version bump |

## Why consensus is load-bearing

Remove consensus and the contract has no way to know what the page says now, and no neutral party to
say whether the change touches the focus. The deterministic code can only act on `(missing, severity,
reach)` and those come out of a process where the leader's claim is checked against independent fetches.
