# L6 Baseline Results — agents WITHOUT the module

Recorded 2026-07-31. Seven scenarios, one fresh agent each, no web access, no file access, no
knowledge of this project. Rubrics in `evals/scenarios.md` were written **before** these were
recorded.

**Headline: the baselines passed 23 of 25 REQUIRED criteria.** This is a much stronger result than
the project's premise assumed, and it changes the value proposition. Read §Implications.

---

## Scoring

| Scenario | REQUIRED met | Verdict |
|---|---|---|
| S1 benchmark regression | 3 / 4 | Correct Welch t-test computed unaided |
| S2 flaky test | 3 / 3 | Correct Wilson interval computed unaided |
| S3 zero events | 3 / 3 | Correct rule of three; found a deeper problem than the rubric anticipated |
| S4 conflicting measurements | 4 / 4 | Explicitly refused to average; reframed better than the target model would have |
| S5 duration estimate | 3 / 4 | **Used the wrong PERT variance formula** |
| S6 calibration | 4 / 4 | Exact binomial and Wilson interval, both verified correct to 3 dp |
| S7 value of information | 3 / 3 | Ran the EV calculation, then correctly argued past it |
| **Total** | **23 / 25** | |

---

## S1 — Benchmark regression · 4/5

**What it computed, verbatim:** means 1.030 / 1.136, SDs 0.052 / 0.053, difference +0.106 s (10.3%),
`t ≈ 3.17, df = 8, p ≈ 0.013`, 95% CI on the slowdown `[0.03s, 0.18s]`, plus a Mann–Whitney check at
p ≈ 0.03.

**I verified every one of these by hand. They are correct.** Mean 5.15/5 = 1.030 and 5.68/5 = 1.136;
pooled-ish Welch t = 0.106 / √(0.00275/5 + 0.00283/5) = 3.17; two-sided p at df 8 ≈ 0.013.

- ✅ 1 interval not point · ✅ 2 uncertainty at n=5 · ✅ 3 no unsupported significance claim
- ❌ **4 did not ask what size of regression would matter** before judging. It raised the product
  question only at the end, after already reaching a statistical verdict.
- ✅ 5 flagged n=5, prescribed 15–20 interleaved runs · ✅ 6 ran a non-parametric cross-check rather
  than assuming normality

**Notable:** it identified that the statistics only rule out run-to-run noise, not systematic
measurement error (thermal throttling, ordering, cache state), and that "no amount of analysis on
these 10 numbers can detect that." That is a correct and non-obvious point which no model in the
catalog would have made.

## S2 — Flaky test · 4/4

**Verbatim:** "2/60 = 3.3%, Wilson 95% CI **[0.9%, 11.4%]**." Verified correct (Wilson centre 0.0614,
half-width 0.0522). Gave ~300 clean runs for a <1% upper bound via the rule of three, and 400–800
runs to distinguish 1% from 5%.

All four REQUIRED met. **It then argued that more runs is the wrong instrument** — that two failure
artifacts beat 500 additional pass/fail bits, and that "statistics cannot answer that question." That
is a correct value-of-information argument reached qualitatively, and it is the argument spec §5
proposes to make numerically.

## S3 — Zero events · 5/5

Applied the rule of three correctly (`3/200` → 98.5% lower bound at day granularity) and computed
that 99.9% at day granularity needs ~3,000 incident-free days ≈ 8.2 years. Verified correct.

**It found a problem the rubric did not anticipate**: "99.9%" is undefined until the denominator is
fixed, and produced a table showing the same 200 days supports 98.5% per-day, 99.94% per-hour, or
99.999%+ per-operation. Also flagged that the rule of three assumes i.i.d. trials while data-loss
incidents cluster around deploys — a correct and material objection to the very model we planned to
ship for this scenario.

## S4 — Conflicting measurements · 4/4

**Verbatim:** "Do not average the three. 1,180 req/s is a number with no referent; it's the arithmetic
mean of three different experiments, not three samples of one quantity."

All four REQUIRED met with no arithmetic at all. It diagnosed the spread as evidence that the
measured quantity is ill-defined, enumerated the likely causes (load generator saturation, different
points on the load curve, keepalive, coordinated omission), and recommended committing below the
lowest observation.

**This is a negative result for the synthesis family.** The rubric's target models
(`combine_conflicting_estimates`, `order_statistic_interval_small_k`) would have produced a pooled
estimate with an interval — which is *worse* than what the baseline did, because pooling presumes the
three numbers estimate one quantity, and the baseline's central insight is that they do not.

## S5 — Duration estimate · 4/5 — **the one real arithmetic failure**

**Verbatim:** "Expected: (3 + 4×6 + 20)/6 = ~7.8 weeks · Std dev: **(20−3)/6 = ~2.8 weeks** · P80 ≈
10.2, P90 ≈ 11.5"

That is exactly the `RESEARCH.md` §1.37 bug: `(b−a)/6` is not the standard deviation of the
distribution whose mean is `(a+4m+b)/6`.

**But the harm here is small, and that is a flaw in my scenario design, not a reprieve for the
formula.** With a = 3, m = 6, b = 20, the mode sits at δ = (6−3)/17 = 0.176 — very close to the
crossover δ = 0.146 where the wrong formula happens to be right. True SD is
`√[(7.833−3)(20−7.833)/7]` = 2.90 vs the 2.83 it used: **2.2% off**, not 11.8%.

**Action: S5 must be re-specified with a near-symmetric mode** (e.g. 4 / 11 / 18), where the error is
the full 11.8% and lands in the optimistic direction. As posed, S5 cannot detect the bug it exists to
detect — the same failure mode as P2, an underpowered test read as a pass.

Everything else passed: it flagged that the mean (7.8) exceeds the mode (6), committed to P80 rather
than P50, gave the skew a causal reading, and proposed a diverse pilot cohort to convert elicited
estimates into measured throughput.

## S7 — Value of information · 5/5

**Verbatim:** "picking blind costs 0.30 × 10 days = 3 expected days of rework. The benchmark costs 2
days guaranteed. Benchmark wins by a day." Then refined it with detection reliability: "0.30 × 0.85 ×
10 = 2.55 days saved against 2 days spent," minus a false-positive branch, netting "between slightly
positive and zero."

All five REQUIRED met. It then made a move the target model cannot: observing that when EV is near
break-even the EV calculation should not decide, and that the cheaper play is to **buy an option
rather than information** — put the library behind a seam so rework costs 1 day instead of 10,
collapsing expected loss to 0.3 days.

**This is the gate scenario, and the baseline beat the planned tool on it.**

## S6 — Self-calibration · 4/4 — **the most damaging result for the premise**

**Verbatim:** "getting 13 or fewer out of 20 has probability **0.24%** (binomial, one-sided)" ·
"with n=20 the significance threshold is 15 — 16/20 would have told you nothing (p = 0.13)" ·
"95% Wilson interval is roughly **43% to 82%**" · "When you feel 90%, say 70%."

**I checked all four numbers computationally. Every one is exactly right:**

| Claim | Verified |
|---|---|
| P(X ≤ 13 \| n=20, p=0.9) = 0.24% | 0.002386 ✓ |
| Rejection threshold at k = 15 | smallest k with P ≥ 0.05 is 16 ✓ |
| 16/20 gives p = 0.13 | 0.1330 ✓ |
| Wilson 95% = [43%, 82%] | [0.433, 0.819] ✓ |

An agent with no tools computed a binomial CDF and a Wilson score interval correctly to three
decimal places.

It also **independently derived `RESEARCH.md` §1.8** — billed in the sweep as one of the most valuable
findings — arguing unprompted that the user's instinct about small n "is right in general but wrong
here, and it's worth understanding why: the null is extreme." That finding cost a full territory
agent to produce. The baseline reached it in one pass.

Beyond the rubric it caught two things the planned models would not have: a multiple-comparisons
problem ("is 90% your only bin, or your worst bin?") and a data-provenance problem ("who scored the
outcomes? self-scoring bias runs generous") — the latter being precisely the
`data_provenance_required` field in spec §7.

---

## Implications — the premise needs revising

The spec's success criterion 1 reads: *"An agent facing a judgment call it would otherwise answer with
'probably' reaches for the module... and states a defensible number instead."*

**Seven of seven baselines already stated defensible numbers.** They computed Welch t-tests, Wilson
intervals, the rule of three, PERT percentiles and expected-value comparisons unaided and — with one
exception — correctly. Three of them reframed the problem more usefully than the model we planned to
ship for that scenario. The "agent says *probably* and moves on" failure the project is built around
did not occur once.

### What this does not mean

It does not mean the module is worthless. Four things survive intact:

1. **The known-wrong formulas.** S5 used the textbook PERT SD. That is a real error, reproduced
   faithfully from training data, and it will recur every time. A script fixes it permanently.
2. **The arithmetic floors** (`RESEARCH.md` §1.29). No baseline mentioned that p < 0.05 is unreachable
   at n₁=n₂=3, or that a 95% distribution-free median CI first exists at n=6. An agent cannot know
   what it has not been told.
3. **Reliability at scale.** I hand-verified ten computations across seven scenarios and they were all right. That is ten easy
   cases with clean inputs and no competing task. It is evidence that the *strongest* version of the
   baseline is strong — not that the median invocation mid-task under token pressure is.
4. **Consistency.** The baseline's quality varied by scenario in ways that don't track difficulty.
   Scripts don't have good and bad days.

### What it does mean

**The value proposition is not "agents can't do statistics."** They can. It is narrower and should be
stated narrowly:

> Agents compute correct statistics *when they stop and try*, but they use formulas that are
> sometimes wrong, don't know the arithmetic floors, and cannot verify their own arithmetic. The
> module makes the right answer cheap and repeatable rather than contingent on the agent choosing to
> be careful this time.

That is a real but much smaller claim than the spec makes, and it does not obviously justify 30
models at +87% tokens.

### Three caveats against over-reading this

1. **The questions were clean and well-posed.** Each baseline was handed an explicit judgment question
   with the numbers laid out, no competing task, no token pressure, and an implicit signal that
   careful reasoning was wanted. Real situations are mid-task with the statistical question *implicit*.
   This is a genuine reason baselines may overstate field performance — but it is a hypothesis, not a
   defence, and testing it requires embedding the question inside a larger task.
2. **These agents share a base model with the eventual user** (`RESEARCH.md` §1.16). The baseline is
   not an independent yardstick.
3. **I verified the arithmetic myself, on six easy cases.** That is not a measurement of accuracy rate.

### Actions

- **A1.** Re-specify S5 with a near-symmetric mode so it can actually detect the PERT bug.
- **A2.** Add S8: the same statistical question embedded *inside* a larger task, to test caveat 1.
  If the baseline degrades there, the value proposition is restored; if it doesn't, Wave 1 should
  shrink substantially.
- **A3.** Revise spec §1 success criteria to the narrower claim above before building anything.
- **A4.** Re-examine the synthesis family. S4 suggests the honest answer to conflicting sources is
  often "these don't measure the same thing," which pooling models actively obscure.
- **A5.** Treat the Wave 1 target of ~30 models as **unjustified pending A2**. Build Wave 0's four
  pilots, re-run the evals, and let the measured delta set the size of Wave 1.
