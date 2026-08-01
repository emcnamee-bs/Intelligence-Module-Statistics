# Consolidated evaluation — nine scenarios, eighteen arms

All rubrics written and committed before their arms ran. No rubric was modified after a result.

## The complete table

| Scenario | Framing | Baseline | With module | Δ |
|---|---|---|---|---|
| S5 duration estimate | posed | 3/4 | **4/4** | **+1** |
| S1 benchmark regression | posed | 3/4 | **4/4** | **+1** |
| S8 PR review | embedded | 3/4 | **4/4** | **+1** |
| S9E weekly post | embedded | 3/4 | **4/4** | **+1** |
| S9 multiplicity | posed | 3/3 | 3/3 | 0 |
| S10 quantile | posed | 3/3 | 3/3 | 0 |
| S11 paired eval | posed | 3/3 | 3/3 | 0 |
| S10E contract clause | embedded | 4/4 | 4/4 | 0 |
| S11E release notes | embedded | 4/4 | 4/4 | 0 |

**Four gains, five ties, zero regressions.**

## Both ordering hypotheses were wrong

**Fact-density** (from Wave 0) predicted the three highest-fact-density models would gain most. All
three tied. Refuted.

**Adjacency** (from the Tier 1 failure) predicted baselines would degrade whenever the statistic was
embedded rather than posed. Two of three embedded baselines held at full marks — including the
contract clause, where the baseline derived `log(0.05)/log(0.99) ≈ 299` unaided while QA was telling
it the number was safe to quote. Refuted.

## What actually fits all nine

The module gains **only where the baseline misses a criterion**, and baselines miss in exactly two
situations:

**1. The agent holds a specific wrong belief.** S5: the beta-PERT standard deviation is recalled, and
recalled wrong, with no internal signal that anything is off. Reasoning cannot repair a belief the
reasoner has no reason to doubt. This is the only category with a *mechanism* guaranteeing the agent
cannot self-correct.

**2. The number is relayed rather than owned.** S8 and S9E: the statistic is supporting context the
agent could pass through without endorsing — a perf claim in a PR description, a dashboard row going
into a cheerful post. Scrutiny is optional there, and under a competing deliverable it degrades: the
S9E baseline *noticed* the multiplicity but stopped short of computing it, asserting "adjusted, it
doesn't clear" where the posed baseline had produced 0.004.

S1 is the boundary case: the agent answered the question asked correctly and never reframed to the
planning question beside it.

**Where baselines do not miss:** when the statistical problem *is* the task (S9, S10, S11), or when
the deliverable **forces the agent to personally endorse the number** (S10E, S11E). Writing 340ms
into a contract with service credits attached *is* an endorsement. Handing customer success a quality
claim *is* an endorsement. Under ownership, capable agents scrutinise properly and need nothing.

That rule fits nine of nine. It is also much narrower than anything claimed earlier in this project.

## What the ties still showed

Ties are not nothing, but they are not what the tokens were spent for:

- **S10E**: both arms refused the 340ms. Only the module arm noticed that **even the observed p95 of
  287ms is not the defensible p95 bound** — that bound is the 99th-smallest value, ~350ms — and so
  changed the clause from a p99 to a p95 warranty. A real correction the baseline missed, on a
  criterion the rubric did not have.
- **S9**: `NO CONFIDENT MATCH` was used correctly in the field. The agent routed the no-control-group
  question, got no match, and concluded *"this isn't a question statistics decides."*
- **S11E**: the agent cited SKILL.md's own limitation — *"the skill explicitly says not to use it for
  arithmetic I can do"* — and computed Wilson intervals itself. **The honest-limitation framing
  prevented waste**, which is the behaviour it was written for.

## Recommendation: stop at seven models

The library is close to saturated for a capable agent. Nine of nine posed baselines and two of three
embedded baselines scored full marks, several by reproducing this project's own headline formulas
from first principles. Building Tiers 2–4 would be building where the measurement says there is no
gap, and the gate exists to prevent exactly that.

**Keep:** all seven models. Four earned gains; three tie but add precision, cost little, and never
regressed anything.

**Do next, in order:**

1. **Hunt wrong beliefs, not models.** Limb (b) is the only category with a mechanism. The research
   sweep never asked "which formulas do agents reliably recall wrong?" — it asked "which models
   exist?" Those are different questions, and only the first predicts value. This is a research task,
   not a build task, and it is the highest-value thing left.
2. **Retune triggering toward relayed numbers.** The SKILL.md description should fire on *"you are
   about to repeat a number someone else supplied"* — a PR description, a QA note, a dashboard row, a
   ticket. That is where the measured gains live. It is a description change, not a model.
3. **Do not build Tiers 2–4 as scoped.** `discovery_saturation` and `capture_recapture_remaining`
   remain interesting because no baseline was ever tested on them, but they should be evaluated
   before they are built, not after.

## Caveats that limit all of this

1. **n = 1 per arm.** Eighteen single samples. No percentage claim is supportable and none is made.
2. **Same base model in both arms.** The baseline is not an independent yardstick.
3. **I wrote the rubrics and the module.** Rubrics predate their baselines, which controls the worst
   version of this but not all of it.
4. **Two scenarios had design defects I introduced** — S5's original mode sat beside the crossover
   where the bug is invisible, and S9E's ship date is ambiguous against its measurement window (both
   agents caught the latter). Corrected and recorded rather than quietly fixed.
5. **Token cost was never measured directly.** Module arms used 6–11 tool calls. Against four gains
   in nine scenarios, the honest summary is that this module earns its cost in a minority of
   situations and should be triggered narrowly rather than broadly — which is what recommendation 2
   is for.
