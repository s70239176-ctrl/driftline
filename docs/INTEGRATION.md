# Using Driftline from another contract

A consumer needs no web access, prompts, or knowledge of equivalence principles:

```python
@gl.contract_interface
class IDriftline:
    class View:
        def reliance_status(self, watch_id: int, now_ts: int, max_age_s: int) -> str: ...
        def receipt_matches(self, watch_id: int, definition_hash: str, baseline_hash: str) -> bool: ...


class CoverPool(gl.Contract):
    driftline: Address
    watch_id: u256
    pinned_definition: str
    pinned_baseline: str

    @gl.public.write
    def sell_cover(self) -> None:
        d = IDriftline(self.driftline).view()
        now = int(datetime.datetime.fromisoformat(gl.message_raw["datetime"].replace("Z", "+00:00")).timestamp())
        if d.reliance_status(int(self.watch_id), now, 7 * 86400) != "RELIABLE":
            raise gl.vm.UserError("EXPECTED: published terms are not RELIABLE")
        if not d.receipt_matches(int(self.watch_id), self.pinned_definition, self.pinned_baseline):
            raise gl.vm.UserError("EXPECTED: terms were re-baselined since this pool was configured")
        ...
```

| Status | Meaning | Typical consumer action |
|---|---|---|
| `RELIABLE` | baseline recorded, last good check within `max_age_s`, not drifted | proceed |
| `STALE` | last good check older than `max_age_s` | ask someone to call `check`, then retry |
| `BLOCKED` | latched `DRIFTED` | halt; owner must re-baseline after review |
| `UNKNOWN` | no baseline, deactivated, or 3+ consecutive unreadable checks | do not rely |

`now_ts` is supplied by the caller because views have no clock; use `gl.message_raw["datetime"]` in
the consumer's own write. Cross-contract *writes* are asynchronous; this interface is read-only on
purpose, and consumers should pull the stored result rather than trust any callback payload.

The snippet above is documentation, not an executable second contract, so the repository keeps one
canonical deployable contract.
