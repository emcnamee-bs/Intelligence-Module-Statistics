# L6 Behavioral Evaluation Scenarios

Seven scenarios covering the families Wave 0 and Wave 1 must serve. Each was posed to a fresh agent
with **no knowledge of this project**, no web access, and no file access — the recorded answer is the
baseline this module must beat.

**Method note.** Rubrics were written *before* the baselines were recorded, so scoring cannot be
retrofitted to whatever the agents happened to say. Baselines are stored verbatim in
`evals/baselines/`, including reasoning, so later comparisons are against what agents actually did
rather than against a remembered impression of it.

Scoring is per-criterion pass/fail, not holistic. A scenario is **passed** only if every REQUIRED
criterion is met. "Sounds thoughtful" is not a criterion — the failure mode this module targets is
*fluent, well-reasoned, confidently wrong*, which scores highly on holistic judgment.

---

## S1 — Benchmark regression · `signal-vs-noise`

> Old build: 1.02, 0.98, 1.11, 1.05, 0.99 s. New build: 1.14, 1.09, 1.21, 1.08, 1.16 s.
> Release ships tomorrow. Is the new build slower, or is this noise? Block the release?

| # | Criterion | Req |
|---|---|---|
| 1 | Quantifies the difference with an interval, not just a point estimate or a verbal verdict | REQUIRED |
| 2 | States or computes the uncertainty given n=5 per arm | REQUIRED |
| 3 | Does **not** claim significance without computing anything | REQUIRED |
| 4 | Asks what regression size would actually matter before judging (minimum interesting effect) | REQUIRED |
| 5 | Notes n=5 is small and says what n would settle it | desirable |
| 6 | Avoids asserting normality or silently assuming it | desirable |

**Target model:** `benchmark_regression_from_repeated_runs`. **Baseline to beat:** "the means differ
by 11%, so it's slower."

---

## S2 — Flaky test · `signal-vs-noise` / `evidence-sufficiency`

> Failed 2 of 60 CI runs. Nobody touched that code. Flaky, or intermittently broken? How many more
> runs to be confident?

| # | Criterion | Req |
|---|---|---|
| 1 | Gives an interval on the failure rate, not just 2/60 = 3.3% | REQUIRED |
| 2 | Answers the "how many more runs" question **with a number**, not "run it a few more times" | REQUIRED |
| 3 | Recognises that flaky-vs-broken is not distinguishable from the rate alone and says what would distinguish them | REQUIRED |
| 4 | Does not treat 2/60 as a reliable point estimate of the true rate | desirable |

**Target models:** `failure_rate_interval_from_counts`, `runs_needed_for_target_confidence`.
**Baseline to beat:** "3.3% failure rate, probably flaky, run it a few more times."

---

## S3 — Zero events observed · `tail-risk` / `duration-reliability`

> 200 days, zero data-loss incidents. Leadership wants "99.9% reliability" in a customer SLA.
> Supportable? What could we claim instead?

| # | Criterion | Req |
|---|---|---|
| 1 | Recognises that zero events does **not** mean zero rate | REQUIRED |
| 2 | Produces an actual upper bound on the incident rate | REQUIRED |
| 3 | Answers whether 99.9% specifically is supportable, with arithmetic | REQUIRED |
| 4 | Names the observation period needed to support the desired claim | desirable |
| 5 | Distinguishes the observed-reliability claim from a forward-looking SLA promise | desirable |

**Target model:** `zero_events_observed_upper_bound` (cluster C1). **Baseline to beat:** "200 days
clean, so 99.9% seems fine" — or the opposite error, refusing to quantify at all.

---

## S4 — Conflicting measurements · `synthesis`

> Three load tests: 1,200 / 1,450 / 890 req/s, all competently run. What do I tell the customer?

| # | Criterion | Req |
|---|---|---|
| 1 | Does **not** simply average to 1,180 and present it as the answer | REQUIRED |
| 2 | Addresses the spread as information, not noise to be smoothed away | REQUIRED |
| 3 | Asks whether the three runs are independent — same harness, same build, shared configuration | REQUIRED |
| 4 | Distinguishes "what we measured" from "what a customer can count on" (a low quantile, not a central estimate) | REQUIRED |
| 5 | Notes that k=3 supports very little formally, and says what it does support | desirable |

**Target models:** `combine_conflicting_estimates`, `order_statistic_interval_small_k`.
**Baseline to beat:** averaging, or picking the middle value.

---

## S5 — Duration estimate · `estimation`

> 40 services to migrate. Best 4 weeks, likely 11, worst 18. Director wants a date and a confidence.
>
> **Re-specified 2026-07-31.** The original 3/6/20 put the mode at delta=0.176, beside the
> crossover at 0.146 where the textbook PERT sd is accidentally almost right (2.2% error). The
> scenario could not detect the bug it existed to detect. At 4/11/18 the mode is near-symmetric and
> the error is the full 11.8%, in the optimistic direction. The original baseline is retained below
> for the record; a fresh baseline was recorded against the new numbers.

| # | Criterion | Req |
|---|---|---|
| 1 | Produces a distribution or interval, not a single date | REQUIRED |
| 2 | If it uses PERT, uses a **correct** variance — `(μ−a)(b−μ)/7`, not `((b−a)/6)²` | REQUIRED |
| 3 | Attaches an explicit confidence level to whatever date it gives | REQUIRED |
| 4 | Addresses the right-skew: mean 7.2 weeks exceeds the 6-week mode, and the committed date should not be the mode | REQUIRED |
| 5 | Mentions reference-class / outside-view correction or the planning fallacy | desirable |

**Target model:** `three_point_estimate_to_range`. **Baseline to beat:** "(3 + 4×6 + 20)/6 ≈ 7.8
weeks, call it 8." Watch specifically for the textbook `(b−a)/6` standard deviation — it is **11.8%
too narrow** at symmetric modes and wrong at every mode but two (`RESEARCH.md` §1.37).

---

## S6 — Self-calibration · `calibration`

> Said "90% confident" 20 times; right 13. Overconfident? By how much? 20 doesn't feel like many.

| # | Criterion | Req |
|---|---|---|
| 1 | Computes the gap: 65% observed vs 90% stated | REQUIRED |
| 2 | Puts an interval on the observed 13/20 rather than treating 65% as exact | REQUIRED |
| 3 | Answers the "is 20 enough?" question **with an analysis**, not a shrug | REQUIRED |
| 4 | Does not incorrectly dismiss n=20 as too small — a 25-point gap is detectable at this n (`RESEARCH.md` §1.8) | REQUIRED |
| 5 | Gives a concrete adjustment rule for future statements | desirable |

**Target models:** `overconfidence_gap_from_prediction_log`, `calibration_sample_size_check`.
**Baseline to beat:** "13/20 is 65% versus 90%, so yes overconfident, but 20 is too small to say
much." Criterion 4 exists because that dismissal is the *expected* baseline failure and it is wrong.

---

## S7 — Is more measurement worth it · `decision`

> Choosing library A vs B. 70% confident B is better. Being wrong costs ~2 weeks rework.
> Benchmarking costs 2 days. Benchmark, or just pick?

| # | Criterion | Req |
|---|---|---|
| 1 | Compares the **value** of the information against its **cost**, numerically | REQUIRED |
| 2 | Recognises the loss is asymmetric and one-sided — the 30% branch is what carries the cost | REQUIRED |
| 3 | Reaches a decision rather than listing considerations | REQUIRED |
| 4 | Notes that a 2-day benchmark may not resolve the question, so its value is bounded by EVPI, not equal to it | desirable |
| 5 | Considers reversibility — how expensive is switching later? | desirable |

**Target model:** `value_of_information_reachability`. **Baseline to beat:** qualitative
pros-and-cons ending in "it depends on how risk-averse you are." This scenario is the gate itself
(spec §5); if the module cannot beat the baseline here, the gate is not worth its tokens.

---

## S8 — The question nobody asked · embedded

> Added 2026-07-31. Every other scenario hands the agent an explicit judgment question with the
> numbers laid out and no competing work. Real situations are not like that: the statistical
> question is implicit, and the agent is busy with something else. **This scenario tests whether the
> baselines' strong performance survives when nobody points at the statistics.**
>
> If the baseline degrades here, the module's value proposition is restored. If it does not, Wave 1
> should shrink substantially. That makes S8 the single most decision-relevant scenario in the set.

The task given is a code review, not a statistics question. A performance claim based on three runs
per arm is embedded in the PR description, where it reads as supporting evidence rather than as
something to check.

| # | Criterion | Req |
|---|---|---|
| 1 | Notices that the performance claim rests on 3 runs per arm at all | REQUIRED |
| 2 | Does not accept "18% faster" as established | REQUIRED |
| 3 | Recognises that p<0.05 is unreachable at n=3 per arm, or asks how many runs would be needed | REQUIRED |
| 4 | Still completes the actual code review it was asked for | REQUIRED |
| 5 | Quantifies what would settle it rather than only expressing doubt | desirable |

**Target models:** `minimum_attainable_p_for_design`, `benchmark_runs_needed`.
**The failure this looks for:** treating an embedded number as a fact because the task framing did
not invite scrutiny of it.

---

## Scoring record

| Scenario | Baseline REQUIRED met | With module | Delta |
|---|---|---|---|
| S1 | pending | — | — |
| S2 | pending | — | — |
| S3 | pending | — | — |
| S4 | pending | — | — |
| S5 | pending | — | — |
| S6 | pending | — | — |
| S7 | pending | — | — |

**Honest expectation:** baselines will score well on fluency and poorly on criteria requiring an
actual number. The interesting result is not the aggregate — it is *which* criteria fail, because
those are the only ones the module has any business existing to fix. A criterion the baseline already
passes is a criterion where a script adds cost and no judgment.
