# Decision record: why Driftline

## Portfolio collision map (owner's local GenLayer projects)

| Project | Core trust question | Same lane as Driftline? |
|---|---|---|
| Credo | Is this identity creditworthy (proof-of-control + policy tiers)? | No: identity/standing, not document change |
| Chargeback | Did an agent's spend match its mandate? | No: one-shot spend veto |
| CharterKeeper | Does an action conform to an organisation's charter? | No: action conformance; the charter is fixed, not watched |
| OpenNotum | Does public web evidence support a case claim? | No: one-shot attestation of a claim, no baseline or change state |
| RfpFit | Which bid fits a brief? | No |
| UptimeSLA | Is an endpoint up? (status classes) | Adjacent only in "watch a URL"; question is availability, not meaning |
| Stagehold | Does a photo satisfy a payment gate? | No |
| Meridian | Cross-chain escrow dispute judge | No |

## Candidates considered (12), scored 0-10 on the prompt's criteria (summary column)

| # | Candidate | Verdict |
|---|---|---|
| 1 | **Semantic drift of a public commitment (Driftline)** | **Selected (best overall)** |
| 2 | Source-independence / syndication detector for corroboration | Strong, but needs multi-URL fixtures and a clustering prompt; deferred |
| 3 | Dependency reliance (is a third-party API/package still safe to depend on) | Overlaps Driftline's reliance view; a consumer of it, not a rival |
| 4 | Evidence firewall (is a page safe to feed another model) | Good, but output is a classification with no accumulating state |
| 5 | Appeal / re-examination registry | Needs an upstream primitive to appeal; not standalone |
| 6 | Agent behavioural conformance | Overlaps UptimeSLA plus Chargeback |
| 7 | Acceptance-spec for a live artifact | Overlaps RfpFit |
| 8 | Causal-responsibility judge | Hard to test live with stable evidence |
| 9 | Duplicate/originality check | Heuristic-heavy (see prompt 41.8); weak determinism story |
| 10 | Policy permit/deny oracle | Overlaps CharterKeeper |
| 11 | Staleness registry for accepted facts | Subsumed by Driftline's freshness view |
| 12 | Generic claim attestation | Overlaps OpenNotum |

Driftline wins on novelty against the portfolio, clear independent evidence (a public URL that
validators fetch themselves), a machine-readable output, and live testability from committed fixtures.

## Selected primitive

**Driftline**: a stateful registry of watches. Each binds a public HTTPS document to an immutable
focus and severity threshold, records a grounded baseline, and lets anyone trigger consensus-witnessed
`check`s that either keep the watch STABLE or latch it DRIFTED. Downstream contracts read
`reliance_status`.

## Delete-GenLayer test

Without GenLayer someone has to be the authority that fetches the page, decides whether wording
changes "matter", and writes the verdict: the party relying on the commitment (conflict of interest)
or the party who published it (conflict of interest) or a neutral backend operator (single point of
trust). A deterministic contract cannot fetch a page or judge "was the refund promise weakened".
Validators each fetch the page, re-check the deterministic facts, and independently re-judge severity,
so no single reader or model authors the verdict.

## Three unrelated consumers (no change to the core contract)

1. **Lending/insurance contract** that prices cover against a protocol's published terms: refuses new
   policies when `reliance_status != RELIABLE`.
2. **DAO grant program** paying on a published criteria document: pauses payouts when the criteria
   page drifts, forcing a vote.
3. **Escrow whose release conditions cite a published spec/SLA page**: pins `receipt_matches` to the
   baseline it was signed against and refuses to settle against a different one.

## Hardest technical risk

Model nondeterminism on "how material is this change". Mitigation: validators must agree only on the
threshold-class (`severity >= min_severity`), the deterministic facts (which baseline quotes are gone)
must match exactly, and evidence is grounded verbatim in each validator's own fetch. A deterministic
floor forces at least MATERIAL when every baseline quote has vanished, so a model cannot call a
replaced page "unchanged".

## Why standalone

One contract, no funds, no frontend, a small read interface, and consensus is the only thing that can
turn "the web page changed" into "the commitment changed".
