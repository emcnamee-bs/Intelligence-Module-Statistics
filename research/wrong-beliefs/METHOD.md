# Wrong-belief study — method

**Research question:** which quantitative formulas, thresholds and validity conditions do capable
agents state confidently and get wrong?

This is not the question the 13-territory sweep asked. That one asked which statistical models exist
and would help, produced 310 candidates, and yielded mostly ties against unaided baselines
(`evals/RESULTS-final.md`). Four of nine scenarios gained, and only one — the beta-PERT standard
deviation — had a *mechanism* explaining why the agent could not self-correct.

That mechanism is the target here. A wrong belief is not a gap in knowledge; it is knowledge that is
wrong, held with no internal signal that anything is off. Reasoning does not repair it, because the
reasoner has no reason to doubt.

## Why the obvious methods fail

**Asking a model what it gets wrong.** If it knew, it would not get it wrong. Self-report finds only
the errors already corrected.

**Having a model verify another model's answer.** Same base model, same wrong belief — the verifier
confirms the error. This is `RESEARCH.md` §1.16 (pseudo-replication) applied to methodology, and it
is the failure that made four of the sweep's findings wrong.

**Giving the elicitation agent a calculator.** Does not help and is not the point. **The beta-PERT
error survives having a calculator**, because the error is in *which formula*, not in the arithmetic.
Tools protect against slips, not against confident wrong recall.

## Design

**Phase 1 — Elicit.** Fresh agents, no knowledge of this project, given natural working tasks that
require producing specific numbers. No hint that anything is being tested, no instruction to verify.
Realistic framing: the kind of quick practical question a colleague asks.

**Phase 2 — Verify independently.** Every quantitative claim checked by **derivation or simulation
in code**, never by recall and never by a second opinion. A claim is only marked wrong when the
correct value has been derived from first principles.

**Phase 3 — Classify.** Distinguish four things that look alike:

| Class | Description | Does the module help? |
|---|---|---|
| **WRONG-RECALL** | A formula or constant stated confidently and incorrectly | **Yes — this is the target** |
| **CONTEXT-WRONG** | Correct formula, invalid in the situation given (validity conditions ignored) | Yes, if the condition is checkable |
| **CONVENTION** | A defensible convention stated as if it were a fact (Cohen's d = 0.5 is "medium") | Weakly — a caveat, not a correction |
| **SLIP** | Arithmetic error the agent would catch on rereading | No — not a stable belief |

Only WRONG-RECALL and CONTEXT-WRONG justify a model. The Wave 0 finding is that these are the only
categories where an agent cannot rescue itself.

**Phase 4 — Confirm stability.** A belief found once may be a slip. Any candidate error is re-probed
in a *different* framing with a fresh agent. Only errors that reproduce across framings count, since
a stable wrong belief is the thing worth building against — and a one-off is noise.

## Domains probed

Chosen because each is somewhere agents produce numbers in ordinary engineering work, and each has
folklore attached:

1. Estimation and project planning
2. Experiment design and A/B testing
3. Performance, latency and queueing
4. Reliability and availability
5. ML and eval measurement

## Success criterion

The sweep's output was a catalogue. This study's output should be a **defect list**: specific,
reproduced, independently verified claims that capable agents get wrong, each with the correct value
and its derivation. A defect list of five real entries is worth more than another 300 models.

Registered before running: I expect most flagged items to be CONVENTION or SLIP rather than
WRONG-RECALL, and I expect the WRONG-RECALL rate to be low — single digits out of ~40 probes. If it
is zero beyond PERT, the honest conclusion is that PERT was a one-off and the module is finished.
