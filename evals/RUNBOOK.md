# Runbook — two open tests

Both tests are things this project has *not* done, and both could change its conclusion. Prompts are
copy-paste ready. Answer keys are verified by derivation, not recalled.

---

# Test A — does model tier change the answer?

**Why it matters.** Every baseline in this project was Opus-class, and they scored 23/25 unaided.
That is the entire basis for concluding the module is nearly redundant. **If a smaller model fails
where these succeeded, the conclusion inverts** — the module would be most valuable exactly where
capable-model evidence says it is least needed. Anthropic's own guidance is explicit that a skill
must be tested on every model it will run under; this project skipped that.

## Setup

1. **Fresh session.** No context from this repo.
2. `/model haiku` (then repeat the whole set with `/model sonnet` if you want the tier curve).
3. Paste each prompt **verbatim**. Do not add "be careful", "check your work", or "use statistics" —
   any of those destroys the test.
4. Record the answer. Score against the key below.

## A1 — the known defect (does the wrong belief survive at lower tier?)

> We need to migrate 40 services to the new auth library. The team's estimates: best case 4 weeks,
> most likely 9 weeks, worst case 18 weeks.
>
> I have to give my director a date and a confidence level. What should I tell them?

**Key.** Mean = **9.667 weeks**. True SD = **2.598**. The textbook `(b−a)/6` gives **2.333**, which is
**10.2% too narrow**. 80th percentile = **12.0 weeks**.

| Check | Pass |
|---|---|
| Gives an interval or percentile, not a single date | ☐ |
| **Uses a correct SD (~2.6), not 2.33** | ☐ |
| Attaches an explicit confidence level | ☐ |
| Notes the mean (9.67) exceeds the mode (9) | ☐ |

**Follow-up probe — ask this in the same conversation if no SD was shown:**

> What standard deviation are you using for that?

Added after the first Haiku run, which gave percentiles with no working and made the SD check
untestable. A natural manager question that hints at nothing. Answers **2.33** → same defect as
Opus, model-invariant. **~2.6** → correct. **Cannot produce one** → it was interpolating, not
computing.

*Opus baseline failed the SD check twice, in two framings.*

**First Haiku result (2026-08-01), recorded:** mean 9.7 correct; percentiles 9-10 / 12 / 15 at
50/80/90. Criterion 4 **failed** — it called the expected value "the most likely scenario",
conflating 9.67 with 9. And the percentiles are mutually inconsistent: p80=12 implies sd 2.77,
p90=15 implies sd 4.16, so no single distribution generates both. True p90 is 13.25; even the
wrong textbook sd gives 12.66. **This is a different failure mode from Opus** — not a wrong
formula applied consistently, but no formula at all, interpolating toward the worst case.

## A2 — multiplicity

> We track 12 metrics on the weekly dashboard. This week checkout conversion is up and the
> significance test on it came back p = 0.03. The redesign shipped last Tuesday.
>
> Should I tell the team the redesign worked?

**Key.** Family-wise error across 12 looks = `1 − 0.95¹²` = **0.4596**. Šidák-corrected p = **0.3062**.
Bonferroni = **0.36**. Raw p needed to survive = **0.004265**. Correct verdict: does **not** survive.

| Check | Pass |
|---|---|
| Notices the 12 metrics **unprompted** | ☐ |
| Produces a corrected **number**, not just a caveat | ☐ |
| Concludes it does not survive | ☐ |
| Bonus: flags the absence of a control group | ☐ |

*Opus baseline: full marks, including the 46% and the 0.004 threshold.*

## A3 — tail quantile

> We collected 100 latency samples from the new endpoint during a load test. Legal wants a p99
> latency figure to put in the customer SLA.
>
> What p99 should I give them?

**Key.** No upper bound on the 0.99 quantile exists at n=100. Highest bounded quantile =
`0.05^(1/100)` = **0.9705**. Reaching p99 at 95% confidence needs **n ≥ 299**. The sample maximum is
only a **63.4%** upper bound on the true p99 (`1 − 0.99¹⁰⁰`).

| Check | Pass |
|---|---|
| Does **not** hand over the 99th of 100 sorted values | ☐ |
| Says n=100 cannot support a p99, or names the n that would | ☐ |
| Offers what *is* supportable (p95, or a bound) | ☐ |

*Opus baseline: full marks, and derived `log(0.05)/log(0.99) ≈ 299` unaided.*

## A4 — paired comparison

> We ran our eval suite on two model configurations. Same 50 items for both. Model A got 40 of 50
> correct. Model B got 43 of 50 correct.
>
> Is B actually better? Should we switch to it?

**Key.** Paired data — McNemar, not a two-proportion test. Best case (b=0, c=3) gives exact
p = **0.25**; no pairing consistent with these totals reaches p<0.05. Minimum net difference that
could = **6**.

| Check | Pass |
|---|---|
| Recognises the items are **shared** (paired, not independent) | ☐ |
| Reaches "3 items cannot be significant here", or asks for discordant counts | ☐ |
| Gives an actual verdict on switching | ☐ |

*Opus baseline: full marks, named McNemar unprompted, computed 0.25.*

## Reading the result

| Haiku outcome | What it means |
|---|---|
| Passes all four | Conclusion stands. Module is near-redundant across tiers. |
| Fails A1 only | Same as Opus. The PERT defect is model-invariant; nothing else changes. |
| **Fails 2+ of A2–A4** | **Conclusion inverts.** The module's value is tier-dependent, and the case for building Tiers 2–4 is reopened — for smaller models. |

---

# Test B — does the skill trigger when the number is relayed?

**Why it matters.** The strongest finding in `evals/RESULTS-final.md` is that gains concentrate when
a number is **relayed rather than owned** — a claim in a PR description, a QA note, a dashboard row.
The skill's current `description` is trigger-dense but generic. Nobody has tested whether it actually
fires in that situation, and the recommendation to retune it is unactioned.

## Setup

Install the skill first, or the test is meaningless:

```bash
ln -s "/Users/eamonmcnamee/Downloads/Intelligence-Module:Statistics" ~/.claude/skills/statistical-judgment
```

Then a **fresh session**, Opus or Sonnet. Paste verbatim. **Do not mention statistics.** You are
testing discovery, not capability — the question is whether the skill fires on its own.

## B1 — relayed claim in a review

> Review this and tell me whether to merge.
>
> **PR #4127 — Replace LRU cache with segmented ring buffer**
>
> Benchmarked on the staging box: old 412ms p50, new 338ms p50. 18% faster. Ran each 3 times to be
> sure. Also drops the `evictionListener` hook — nothing in the codebase uses it.

**Pass:** the skill fires without being named, *and* the review challenges "18% faster from 3 runs".
**Partial:** challenges the claim but never invokes the skill.
**Fail:** accepts 18% and reviews only the code.

## B2 — relayed claim into a contract

> Fill in the Performance section. Legal needs the draft back today.
>
> `7.2 Performance. Provider warrants that /v2/ingest shall respond within ______ for 99% of
> requests measured over a calendar month.`
>
> QA says: *"Ran the load test against staging. 100 requests. p50 118ms, p95 287ms, p99 340ms, max
> 356ms. Should be safe to quote the p99."*

**Pass:** refuses to write 340ms, *and* the skill fires. **Fail:** writes 340ms.

## B3 — the negative control

> Our checkout page uses a 3-second timeout. Support says customers on slow connections are getting
> errors. Should we raise it to 10 seconds?

**Pass:** the skill does **not** fire. This is a product judgment with no quantity to estimate.
**Fail:** the skill fires — a false positive, which is the failure mode that makes a skill noise.

*Run B3 every time. A discovery test without a negative control only measures eagerness.*

## Reading the result

| Outcome | Action |
|---|---|
| Fires on B1+B2, silent on B3 | Description is already right. Close the recommendation. |
| Silent on B1/B2 | **Retune** the description toward relayed numbers — the top open recommendation. |
| Fires on B3 | Description is too broad. Tighten before anything else. |

---

# What I'd do with the results

- **Test A inverts the conclusion or confirms it.** It is the higher-value of the two and worth
  running first.
- **Test B is a ten-minute fix either way** — it tells you whether to edit one YAML field.

If A shows tier-dependence, the honest next step is not "build Tiers 2–4" but "re-run the full
9-scenario eval on the weaker tier", because the ordering principles were derived from Opus
behaviour and may not transfer either.
