# Tier 1 gate — FAILED

Run 2026-07-31 after building the three highest fact-density models. Rubrics (S9–S11) were written
and committed before any arm launched.

## Result: zero criterion-level gain

| Scenario | Baseline | With module | Delta |
|---|---|---|---|
| S9 multiplicity | **3/3** | 3/3 | **0** |
| S10 quantile | **3/3** | 3/3 | **0** |
| S11 McNemar | **3/3** | 3/3 | **0** |

Compare Wave 0, where every arm gained: 3/4 → 4/4 across S1, S5 and S8.

**Every Tier 1 baseline scored full marks unaided**, and each reproduced its target model's central
output from first principles:

- **S9**: computed `1 − 0.95¹² = 46%` family-wise error and a Bonferroni threshold of 0.004. Both
  verified correct. That is what `multiplicity_correction_for_search` returns.
- **S10**: *"Your sample maximum is only a 63% confidence upper bound on the true p99. It's a 95%
  upper bound on the true **p97**, not p99."* Verified: `0.05^(1/100) = 0.9705`, and
  `1 − 0.99¹⁰⁰ = 0.634`. That is `quantile_confidence_from_order_statistics`'s headline fact,
  derived unaided and with more supporting detail than the model gives.
- **S11**: *"the most favorable possible case is b=0, c=3... p = 0.25. That's the ceiling."* Named
  McNemar unprompted. That is `mcnemar_paired_comparison`'s headline fact.

**The fact-density hypothesis is refuted by the first three models built on it.**

## What the module did add, and why it did not count

All three with-module arms were better in ways the rubric did not measure: exact corrected values
rather than threshold comparisons, the "12 is a floor, not the count" observation, the net-difference-
of-6 threshold, sizing to 400–500 eval items, and composition hazards surfaced verbatim.

Two mechanisms are worth recording as validated:

- **`NO CONFIDENT MATCH` was used correctly in the field.** The S9 arm routed the no-control-group
  question, got no match, and concluded *"this isn't a question statistics decides."* The
  false-positive control functioned as information rather than as a failure.
- The S9 arm **declined to run the E-value** because it requires an already-adjusted estimate.

Better precision on an answer the agent already had right is a real but small thing, and it is not
what the criteria measured or what the tokens were spent for.

## The pattern across all six measured scenarios

| Scenario | Δ | What the baseline missed |
|---|---|---|
| S5 | **+1** | Used `(b−a)/6`. **Held a specific wrong belief.** |
| S1 | **+1** | Never asked how many runs would settle it. |
| S8 | **+1** | Noticed the 3-run claim, filed it as "not fatal on its own". |
| S9 | 0 | Nothing. |
| S10 | 0 | Nothing. |
| S11 | 0 | Nothing. |

Fact-density does not separate these. Two things do.

### 1. Derivable versus recalled

Šidák (`1−0.95¹²`), the McNemar bound (`2·0.5³`) and the quantile cap (`0.99¹⁰⁰`) are each two lines
of elementary probability. A capable model reconstructs them on demand, so a script only makes the
same answer faster.

The beta-PERT variance is different in kind. It is not reconstructed — it is **recalled, and recalled
wrong**, with no internal signal that anything is off. No amount of reasoning fixes a wrong belief
the reasoner has no reason to doubt.

### 2. Adjacent versus central — the stronger predictor

Sort the six by whether the statistical issue **is** the question or sits **beside** it:

| | Question asked | Statistical issue | Δ |
|---|---|---|---|
| S1 | "Is it slower?" | how many runs would settle it | beside → **+1** |
| S5 | "What date do I commit to?" | your sd formula is wrong | beside → **+1** |
| S8 | "Should I merge this PR?" | the perf claim is unsupported | beside → **+1** |
| S9 | "Did the redesign work?" | twelve metrics | **is the question** → 0 |
| S10 | "What p99 do I quote?" | you cannot have one | **is the question** → 0 |
| S11 | "Is B better?" | three items cannot be significant | **is the question** → 0 |

Six for six. When the statistical problem *is* the question, a capable agent engages with it directly
and gets there. When the agent is answering something else — merging a PR, committing to a date,
judging a benchmark — the statistical issue is a detour it must choose to take, and that is where the
module changes the answer.

This also explains S8, which was designed to test embedding and produced a gain, and it explains why
S1 gained despite being a posed question: the agent answered *the question asked* correctly and
simply never reframed to the planning question beside it.

## Implication — and it is uncomfortable

**A model cannot know whether it is adjacent. Only the trigger can.** If adjacency is what predicts
gain, then the value is concentrated in the skill's *description*, its triggering, and the router —
the machinery that makes an agent stop mid-task and consider a detour — rather than in the size of
the model library.

That inverts the project's working assumption. It says the next marginal token is better spent on
**discovery** than on **models**, and it predicts that Tiers 2–4 as ordered would produce more ties.

## Recommendation

**Do not build Tiers 2–4 as ordered.** The gate exists to stop exactly this, and it fired.

1. **Keep the seven models.** Three earned their place in Wave 0; three more are correct, cheap and
   tested, and add precision even where they did not move a criterion. Nothing here argues for
   deleting them.
2. **Reorder what remains around adjacency, not fact-density.** Prioritise models that fire while the
   agent is doing something else — reviewing a PR, writing an estimate into a doc, sizing work,
   answering a user. Deprioritise models that answer a question someone explicitly asked, because the
   evidence says the agent will answer it correctly unaided.
3. **Prioritise limb (b) — corrections to wrong beliefs — over limb (a).** `three_point_estimate_to_range`
   is the only model in the project with an unambiguous, repeatable, mechanism-explained gain. Find
   the other formulas agents reliably recall wrong. That is a research question the sweep never
   asked, because it was looking for models rather than for errors.
4. **Test the adjacency hypothesis before building on it.** It is derived from six scenarios, three of
   which were designed to test something else. The cheap test: re-run S9, S10 and S11 with the
   statistical question *embedded* in a larger task, as S8 was. If baselines degrade there and the
   module holds, adjacency is confirmed and it becomes the ordering principle.

Step 4 costs six agent runs and no code. It should happen before any further model is written.
