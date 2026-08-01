# Review 04 — Coverage Audit

**Question asked:** not "are the 310 chosen models good" but **"what is missing, and what was wrongly discarded."**

Method: 55 concrete agent situations brainstormed *before* consulting the catalog, then checked one by
one against the 310 ranked rows. Then all 266 cut-list entries read for bad reasoning. Then a
duplicate hunt against RESEARCH.md §2.2's three named identity clusters.

**Contents**
1. [Headline](#1-headline)
2. [Situation-first gap analysis](#2-situation-first-gap-analysis)
3. [The structural finding: four territories that were never commissioned](#3-the-structural-finding)
4. [Wrongly-cut audit](#4-wrongly-cut-audit)
5. [Missed identity clusters](#5-missed-identity-clusters)
6. [Family balance](#6-family-balance)
7. [Over-representation and where Wave 1 should cut depth](#7-over-representation)
8. [Recommendations](#8-recommendations)

---

## 1. Headline

Three findings dominate.

**(a) The sweep's coverage gaps are not random — they cluster in the places where territories deferred
to each other.** Thirteen territories were commissioned. Their cross-territory tables collectively
defer work to at least **six territories that do not exist**: a regression territory, an effect-size
territory, a multiple-testing territory, a measurement-agreement territory, a distribution-comparison
territory, and a prediction/coverage territory. Models cut with the reason "belongs to X" where X was
never staffed are not deferred — they are **deleted**. This accounts for roughly half the gaps below,
including the single most common comparison an agent runs (two evaluators / two judges / two labelled
sets and their agreement) and the single most common fit an agent performs (a straight line through a
dozen points, with an interval).

**(b) The catalog is over-fitted to "the agent has a dataset."** Of 310 rows, I count fewer than a
dozen whose SITUATION phrasings describe an *agent-workflow* predicament rather than a data-analysis
one. Nothing is phrased as "should I ask the user before proceeding", "have I read enough of this
codebase to answer", "is one more subagent worth the tokens", "am I going in circles". The mathematics
for most of these already exists in territory 10 (EVPI, Weitzman, reservation stopping) — it is the
*retrieval index* that will fail, and RESEARCH.md §0.6 already identified retrieval as the failure mode
that kills skill libraries. This is a phrasing gap, not a model gap, but it is the one most likely to
make the module unused.

**(c) RESEARCH.md §2.2 undercounted the identity clusters by roughly a factor of four.** It names
three. I find at least nine more, two of which (exact discrete-tail inversion; design-effect /
effective sample size) each span *more territories than C1 does*. The spec's commitment to one
implementation per cluster is right; the cluster list it is committing against is incomplete enough
that the dedup pass as currently scoped will miss most of the duplication.

---

## 2. Situation-first gap analysis

55 situations were generated blind. 40 are adequately covered and are not listed. The 15 below have
**no adequate model in the 310**, ordered by (frequency × margin over unaided guessing).

### G1. Capture–recapture: "two reviewers found 5 and 4 bugs, 2 overlap — how many are left?"

**Phrasings:** "how many bugs are still in this PR" · "two tools flagged overlapping issues, what's the
total" · "I found 3 problems in the first pass and 1 new one in the second — am I done" · "estimate
what I haven't found yet"

**Status:** absent from all 13 territories. No mention of capture–recapture, Lincoln–Petersen, or
Chapman anywhere in 6,000 lines. Territory 09 #22 (Goel–Okumoto software reliability growth) is
shipped *with a hostile posture and a hard refusal*, and the National Academies citation used to
refuse it does not apply here — capture–recapture is not extrapolation, it is estimation from an
overlap the agent has already observed.

**Why it matters:** this is the defect-estimation method that actually works at agent scale, and the
input is data an agent generates by default (two review passes, two linters, two test suites, a human
review plus an automated one). Chapman's estimator `N̂ = (n₁+1)(n₂+1)/(m+1) − 1` is one line, is
bias-corrected for small samples, and has a closed-form variance. The unaided answer — "we found 7
distinct issues, so there were 7" — is wrong in a known direction and by a knowable amount.

**Feasibility:** EASY. Arithmetic plus a log-normal CI on N̂. Multi-source (k > 2) needs a
log-linear model and should be refused.

### G2. Discovery saturation / coverage: "the last five pages added nothing new — can I stop?"

**Phrasings:** "have I found all the call sites" · "how many distinct error signatures are there" ·
"will one more grep turn anything up" · "am I done searching" · "how much of this codebase have I
actually seen" · "how many unique failure modes exist"

**Status:** absent. No Good–Turing, no Chao1, no species-richness estimator, no coverage estimator
anywhere. Territory 06's stopping rules answer "have I sampled enough to *estimate a mean*", which is
a different question from "have I seen enough to have *enumerated the categories*".

**Why it matters:** this is arguably the most frequent quantitative question in an agent's actual
working loop and it currently has no arithmetic behind it at all. Good–Turing is startlingly cheap:
the estimated probability mass of *unseen* categories is `f₁/N` (singletons over total observations).
Chao1's lower bound on true richness is `S_obs + f₁²/(2f₂)`. Both are exact-ish, distribution-free,
and one line each. An agent that has grepped 40 files, found 12 distinct call patterns, and seen 7 of
them exactly once should be told that ~17% of the pattern mass is still unobserved — and it currently
cannot be.

**Feasibility:** EASY. Counting only. Refusals: non-exchangeable search order (grep results are
ordered by directory, not randomly — the agent must have sampled, not enumerated); `f₂ = 0` (Chao1
undefined, use the bias-corrected form).

### G3. Inter-rater / inter-judge agreement

**Phrasings:** "three LLM judges rated these 20 outputs — do they agree?" · "how reliable is my rubric"
· "does the model's labelling match the human's beyond chance" · "two reviewers disagree, is that
normal" · "is my eval consistent"

**Status:** **cut in territory 08** — "Cohen's κ / Bland–Altman agreement — measures inter-rater or
inter-method agreement, not synthesis of a common quantity. **Belongs to a measurement-agreement
territory.**" No such territory exists. This is a cut into a void.

**Why it matters:** LLM-as-judge is the dominant evaluation pattern, and the first question about any
judge is whether it agrees with itself, with another judge, or with a human — beyond chance. Raw
percent agreement is the naive answer and it is *badly* wrong when the label distribution is skewed
(two judges that both say "pass" 90% of the time agree 82% of the time by chance alone). Cohen's κ,
Fleiss' κ for k>2 raters, Krippendorff's α for missing data and ordinal labels, and ICC for continuous
scores are all stdlib-trivial. Territory 04 already ships the exact 2×2 machinery κ needs.

**Feasibility:** EASY (κ, Fleiss, percent-agreement-vs-chance). MODERATE (Krippendorff's α with
ordinal/interval distance metrics, bootstrap CI). Known refusals to encode: κ's prevalence and bias
paradoxes — κ can be near zero when agreement is 95% if one category dominates, and the tool must
print P_o, P_e and the marginal distributions alongside κ or the number misleads.

### G4. Ranking from pairwise judgments (Bradley–Terry / Elo)

**Phrasings:** "I have 20 pairwise A-vs-B preferences over 6 candidates — rank them" · "arena-style
comparison" · "which output is best when I only compared them two at a time" · "are these rankings
distinguishable or is the order noise"

**Status:** **cut in territory 10** — "Dueling bandits / preference-based bandits — right model when
only pairwise comparisons are available, **which is a genuine agent situation (LLM-judge
comparisons)**, but the sample complexity at 2–20 options is prohibitive."

**The cut is aimed at the wrong object.** The sample-complexity objection applies to the *adaptive
allocation* problem (which pair should I compare next). The *estimation* problem — given the pairwise
wins I already have, produce a ranking with uncertainty — is a 30-line logistic fit with no sample
complexity issue at all, and it is the situation that actually arises. Nothing else in the catalog
converts pairwise preferences into a ranking; territory 04's rank methods all assume scored, not
compared, items.

**Feasibility:** MODERATE. Bradley–Terry MLE by MM/minorization (a fixed-point iteration, ~15 lines,
provably monotone, no optimizer). CIs by the observed information or by a bootstrap over comparisons.
Refuse when the comparison graph is disconnected (some item never compared to the rest — the MLE
diverges) and when any item is undefeated (separation; needs a Haldane/Firth prior).

### G5. Paired binary comparison — McNemar

**Phrasings:** "prompt A got 40/50 and prompt B got 43/50 on the same items" · "did the new model fix
more than it broke" · "same test suite, two configs, which passes more" · "we changed one thing and 6
tests started passing and 3 started failing"

**Status:** no row anywhere. Territory 04 #8 (sign test / exact binomial) is *mathematically identical*
to exact McNemar — it is the binomial test on the discordant pairs — but its SITUATION phrasings are
all about paired *continuous* measurements ("did the before/after change do anything"), so an agent
holding two accuracy counts on the same items will never retrieve it. Territory 06 #9 and territory 13
#5 both cover *unpaired* two-proportion comparison, which is the wrong test here and throws away the
pairing.

**Why it matters:** this is plausibly the single most common comparison an agent performs, and using
the unpaired test on paired data is not merely inefficient — it can miss a real effect entirely
(when both configs pass 80% of items but disagree on which 20%, the unpaired test sees nothing and
McNemar sees everything). The fix is cheap: this is a **routing and phrasing gap on an existing model**,
not a missing model. But the discordant-pair extraction (`b`, `c` from the 2×2) and the refusal when
the agent supplies only marginal counts (in which case the paired test is *not computable* and the tool
must say so and ask for the per-item results) are real additions.

**Feasibility:** EASY. `math.comb`. The critical refusal: **marginal totals alone are insufficient** —
40/50 and 43/50 does not determine `b` and `c`, and any tool that proceeds is fabricating.

### G6. Blocked k-sample comparison — Friedman

**Phrasings:** "three configs across the same 20 benchmarks" · "four prompts on the same eval set" ·
"compare five models over the same test cases" · "which of these variants is best, measured on
identical inputs"

**Status:** **cut in territory 04**, which flagged its own doubt: *"Friedman test — borderline; k≥3
repeated conditions on the same blocks does occur (same benchmark suite, 3 configs). Cut from the top
26 but the closest thing to a 27th row."*

**The doubt was correct.** Territory 04 *ranks* Kruskal–Wallis (#19) for k-group comparison, which
assumes independent groups. Applying it to the same-items-many-configs design — the normal design for
any agent evaluation — discards the blocking and loses most of the power. This sits squarely in
RESEARCH.md §1.2's `naive_answer_is_wrong` category: the available ranked model gives a *worse* answer
than the cut one, on the more common design.

**Feasibility:** EASY. Rank within blocks, `Q = 12/(nk(k+1))·ΣR_j² − 3n(k+1)`; exact null by
enumeration for small n,k, permutation otherwise (permute within blocks, which is the correct
exchangeability structure). Post-hoc via Nemenyi or a within-block permutation max-T.

### G7. Two-sample distributional comparison / drift detection

**Phrasings:** "has the input distribution changed since the upgrade" · "are these two latency
distributions the same shape or just shifted" · "is my sample representative" · "did the data drift" ·
"the mean is the same but it feels different"

**Status:** **cut in territory 13** — "Two-sample KS / Cramér–von Mises as a distribution-change
detector — **belongs to the distribution-comparison territory**; listed as a cross-territory
dependency." Again, no such territory.

Territory 04 correctly and forcefully cuts KS *as a normality gatekeeper* (§ cut list: near-zero power
at n<15, and an agent reads non-rejection as confirmation). That argument does not transfer to the
two-sample use, where the question is symmetric and there is no "assumption confirmed" failure mode.
Territory 12 #16 covers KL divergence but only for aligned *discrete* distributions with a smoothing
guard. Nothing handles continuous two-sample comparison, and nothing handles the shape-vs-location
distinction at all.

**Why it matters:** "the distribution changed but the mean didn't" is a real and frequent situation
(latency bimodality after a cache change, output-length distribution shift after a prompt change,
error-type mix shift after a dependency bump), and every location-comparison tool in the catalog is
blind to it. Territory 13 #8's change-type discriminator includes a variance-change model but only for
a single series over time, not for two samples.

**Feasibility:** EASY. Two-sample KS with an *exact* permutation null (no asymptotic Kolmogorov
series needed — permute the pooled labels, recompute D). Cramér–von Mises and Anderson–Darling
likewise. Wasserstein-1 between two empirical samples is a sorted-difference sum, one line, and is
interpretable in the data's own units (unlike KS's D). Population Stability Index for binned data.

### G8. Simple regression, correlation with an interval, and R×C association

**Phrasings:** "does file size predict build time" · "fit a line through these 15 points and give me
the slope with an interval" · "what's the correlation and how sure am I" · "predict y for a new x with
a range" · "is failure type associated with environment"

**Status:** systematically deferred to a **regression territory that was never commissioned**.
Territory 02's cross-territory table is explicit: *"Every estimator here (#3, #7, #11, #18, #22, #23)
sits on the same OLS core. **Build it once, in the regression territory**, and have causal tools import
it."* Territory 03 says *"Do not duplicate the OLS implementation."* Territory 04 splits ownership:
*"regression owns OLS and diagnostics; this territory owns the robust fitters."* Territory 12 defers
"deviance residual diagnostics, Cook's distance, leverage" to "regression diagnostics territory."

The consequence: OLS exists as an *internal component* of Theta, ITS, DiD, Egger's test, and the
change-type discriminator, but there is **no agent-facing row** for the most basic quantitative
question there is. An agent asking "is there a relationship between these two columns" gets Theil–Sen
(T04 #17, framed as a *trend over time*, not a bivariate relationship) or nothing.

Same structure for correlation: territory 06 #22 ships *sample size for a correlation*, territory 04
buries an exact Kendall null inside Theil–Sen's CI, but no row answers "here are 12 (x,y) pairs, what's
r and how uncertain is it." And for R×C contingency: territory 04 owns the exact 2×2, territory 12 has
a G-test embedded in the MI row, but "5 failure categories × 3 environments — is there an association"
has no owner and no row.

**Feasibility:** EASY–MODERATE. Simple OLS with a t-based slope CI and a *prediction* interval
(distinct from the confidence interval on the mean — the same conflation territory 01 §1.36 flags for
Bayesian posteriors applies verbatim here and is worth carrying over). Pearson r with Fisher-z CI;
Spearman/Kendall with exact permutation nulls at agent n. R×C G-test with a permutation null (avoids
the expected-cell-count problem entirely).

### G9. Direct standardization / Simpson's-paradox reversal check

**Phrasings:** "region A has a higher error rate than B, but the traffic mix is different" · "the
overall rate went up but every segment went down" · "is this difference just composition" ·
"adjust for the fact that the two groups aren't comparable" · "our average got worse but nothing got
worse"

**Status:** no row. Territory 02 #2 (back-door criterion) answers *what to adjust for* given a declared
DAG but computes no adjusted estimate; #9 (propensity weighting) computes one but needs unit-level data
and n ≥ 50; #5 (regression to the mean) is a different phenomenon.

**Why it matters:** the input is a stratified count table — the most common shape of data an agent
actually holds from a dashboard, a log aggregation, or a test-suite summary — and the naive answer
(compare the crude rates) can be *reversed in sign*, which is territory 02's own
`naive_answer_is_wrong` criterion for Wave 1 priority. Direct standardization to a common reference
population is elementary arithmetic; an explicit reversal detector ("the crude comparison and every
stratum-specific comparison disagree in sign") is a boolean over the same table.

**Feasibility:** EASY. Weighted sums plus a delta-method or bootstrap SE on the standardized
difference. Mantel–Haenszel gives a pooled ratio with an exact-ish variance and a homogeneity test
(Breslow–Day) for whether pooling is legitimate at all.

### G10. Empirical scaling exponent — "is this O(n²)?"

**Phrasings:** "does this scale linearly" · "the runtime looks quadratic, is it" · "will this still work
at 10× the input" · "fit a complexity class to these timings" · "extrapolate the runtime"

**Status:** no row. Territory 12 covers model comparison generically (AICc across candidates) and
territory 04 covers robust slopes, but the specific composition — fit log(t) vs log(n), get the
exponent with a CI, compare against the candidate set {1, n log n, n², n³}, and refuse to extrapolate
beyond a stated factor — is not assembled anywhere. Territory 03 #13 (threshold crossing) has the
right refusal doctrine ("if the slope CI contains zero, refuse to print a date") and is the closest
analogue.

**Why it matters:** it is a coding agent's most common quantitative question about its own artifact,
the data (4–8 timing points at doubling sizes) is trivially constructed, and the unaided answer
("it went from 1s to 4.2s when I doubled n, so it's quadratic") is a single-ratio estimate with no
error bar that a constant-factor or a cache-cliff can invert.

**Feasibility:** EASY. Log-log OLS or Theil–Sen for the exponent; AICc across the candidate class set;
refuse extrapolation beyond ~1 doubling past the largest measured n. The interesting refusal:
**a cache cliff or a phase transition breaks the power law**, and it presents as a single high-leverage
point — route to territory 04's leverage check.

### G11. Online FDR over an unbounded stream of repeated checks

**Phrasings:** "I run this check every hour forever — how do I not drown in false alarms" · "how many
of my alerts this month were real" · "I keep testing the same thing on new data"

**Status:** **cut in territory 06** — "Online FDR (LORD, SAFFRON, alpha-investing) — belongs in the
multiple-testing territory; cross-reference only." No multiple-testing territory exists. Territory 13
§4.8 identifies it as *"precisely the monitoring situation... **underused and directly implementable in
stdlib** (it is a running alpha-wealth ledger)"* — and then does not rank it, because 06 owned it.

The two territories that ship batch FDR (T12 #8, T13 #14) both assume a fixed, finite, simultaneous set
of p-values. Neither is defined over an unbounded stream, which is the monitoring case. So the
territory that identified the need deferred to the territory that cut it.

**Feasibility:** EASY. LORD++ is a running wealth ledger: start with `W₀ = α·(1−...)`, spend
`α_t` at each test, refund on each rejection. ~25 lines.

### G12. PERT-network merge bias / max-of-k parallel workstreams

**Phrasings:** "five things have to finish before we ship — when does the last one land" · "parallel
workstreams, what's the completion date" · "the critical path says 3 weeks, is that right" · "when do
all of these converge"

**Status:** no row. Territory 03 #11 handles a *single* three-point task (and correctly fixes the
variance bug, §1.37), then cites Roos & den Hertog to the effect that **"network topology and variance
magnitude are what move the answer"** — and no model addresses topology. Territory 11 #10 (scenario
mixture) handles mixtures, not maxima.

**Why it matters:** `E[max(X₁..X_k)] ≫ max(E[X₁..X_k])`, and the gap grows with k and with the spread.
This is *the* reason multi-workstream projects are late, it is completely invisible to the agent's
mental model (which sums or maxes the point estimates), and it is exactly the same arithmetic as
territory 05 #9's fan-out tail amplification — see cluster **C5** below. One implementation, two
framings.

**Feasibility:** EASY by Monte Carlo (`random` ships everything needed, §1.19), and closed-form for the
independent-normal case. Refusal: correlated workstreams (shared people, shared dependency) make the
independent max wildly optimistic — require a correlation or refuse.

### G13. Finite-population / hypergeometric audit sampling

**Phrasings:** "I checked 20 of 1000 records and found no errors" · "how many should I audit" · "what
fraction of these files do I need to review" · "sample size for a spot check"

**Status:** partially covered and quietly wrong. Rule of three (C1) is *binomial* — it assumes sampling
with replacement from an infinite population. When the agent samples 20 of 1000 records, or 5 of 40
files, the finite-population correction matters and the hypergeometric bound is tighter and exact.
Territory 06's cross-territory note flags "confidence sequences for sampling *without* replacement
(arXiv:2006.04347)" as relevant and nothing picks it up.

**Feasibility:** EASY. Exact hypergeometric tail via `math.comb`; the LTPD / acceptance-number planner
is an integer search.

### G14. Ordinal outcomes and ordered alternatives

**Phrasings:** "does quality improve monotonically with context length" · "severity levels 1–5, did they
shift" · "ratings went from mostly-3 to mostly-4, is that real" · "is there a dose-response with
temperature"

**Status:** cut twice, both times as "rare." Territory 04: *"Jonckheere–Terpstra, Page's trend test,
Quade test — ordered-alternative and blocked designs are rare in agent judgment work."* Territory 07:
*"Ranked Probability Score for ordered categories — real but rare."* Territory 01 #18 lists "ordinal
categories treated as nominal (throws away the ordering)" as a *refusal condition* while offering no
ordinal model to route to.

**The "rare" judgment is wrong.** Ordered alternatives across a monotone knob — context length,
temperature, model size, batch size, thread count, retry count, sample count — are among the most
common designed experiments an agent runs, and the ordered-alternative test is substantially more
powerful than the unordered one precisely because it uses the ordering the agent already knows about.
Severity/priority/rating scales are the second most common non-numeric outcome after pass/fail.

**Feasibility:** EASY. Jonckheere–Terpstra is a sum of pairwise Mann–Whitney counts; exact null by the
same DP that territory 04 already builds for cluster C3. Page's L for the blocked version. RPS is two
lines given cumulative sums.

### G15. Lee bounds for differential attrition (territory 02's own regret)

Territory 02 flags this itself: *"Lee bounds for attrition/selection — genuinely cheap (trimming bounds,
closed form) and stdlib-easy. Cut only because it requires differential attrition between arms — a
narrow situation for an agent — but it is the strongest candidate for later re-inclusion."*

**The "narrow" judgment is wrong, because the agent's version of attrition is timeouts and crashes.**
"Of 50 runs, 8 timed out in arm A and 2 in arm B" is not a narrow situation — it is the *default*
condition of any benchmark, eval, or A/B on a real system, and it silently breaks every comparison in
territories 04, 06, and 13. The dropped runs are not missing at random: they are disproportionately the
slow ones, so dropping them biases both arms toward optimism and biases the *comparison* toward
whichever arm dropped more.

Lee bounds trim the better-retained arm down to the worse arm's retention rate from each end, producing
a sharp identified interval that requires only monotonicity. Closed form, `sorted()` and two indices.
This should be re-included, and it should be wired as a **composition hazard** into every two-sample
row: *"you reported 50 and 50 runs but 42 and 48 completed — the comparison you asked for is not
identified; here are the bounds."*

### Situations checked and found adequately covered (not listed above)

Flaky-vs-broken (T13 #5), zero-failure bounds (T05 #1, T09 #2), benchmark regression (T13 #2/#3),
when-to-stop-sampling (T06 #1/#2), ETA from partial progress (T09 #7), completion-date Monte Carlo
(T03 #9), combining disagreeing sources (T08), calibration of stated confidence (T07), timeout choice
as a newsvendor problem (T01 #4), did-my-change-cause-it (T02), trend detection (T03 #12, T13 #9),
p99 uncertainty (T05 #2), scanning many metrics (T13 #14), option choice under uncertainty (T10),
Fermi propagation (T11 #2/#3), three-point duration (T03 #11), give-up thresholds (T09 #8, T10 #6),
inspection paradox (T09 #13), Little's Law (T03 #19), queueing blow-up (T03 #21), base rates
(T11 #4), rare-count significance (T13 #4), retry-vs-restart under hazard shape (T09 #5/#8),
sample size for an eval (T06 #3/#9), prior from a hunch (T01 #11, T11 #1), reference-class correction
(T03 #8, T11 #6), interval-width overconfidence (T11 #5), value of asking one more question
(T10 #1/#22 — mathematically, though not by phrasing), which unknown to resolve first (T10 #24,
T11 #11), budget allocation across candidates (T10 #4/#14), SLO burn rate (T13 #22), MTBF from
censored exposure (T09 #1), competing exit causes (T09 #17), interval-censored polling data (T09 #20),
recurrent incidents (T09 #15), post-hoc pattern discounting (T12 #2/#4), overfitting a model choice
(T12 #9), surprise accounting (T12 #7), and evidence pooling under unknown dependence (T08 #7).

---

## 3. The structural finding

Six territories are referenced as owners in the cross-territory tables and do not exist:

| Referenced owner | Referenced by | What fell through |
|---|---|---|
| **Regression** | T02, T03, T04, T12 | Simple/multiple OLS, slope CIs, prediction intervals, leverage, Cook's distance, R², Fieller. G8. |
| **Effect size** | T04, T06 | Cohen's d / Hedges' g, d↔r↔OR conversion, "what counts as meaningful". Every model that demands a declared minimum-interesting effect has no tool to help state one. |
| **Multiple testing** | T02, T04, T06, T12, T13 | Recovered by accident — T12 #8 and T13 #14 both ship BH/Holm independently (a duplicate). Online FDR fell through entirely. G11. |
| **Measurement / agreement** | T02, T08 | κ, α, ICC, attenuation correction, test–retest reliability. G3. T02 also parked regression-to-the-mean's second entry point here. |
| **Distribution comparison / GoF** | T05, T13 | Two-sample KS/CvM/AD/Wasserstein/PSI. G7. |
| **Prediction / coverage** | T01, T07 | Conformal prediction — though T03, T04, and T09 each independently ranked it, so this one was *over*-recovered rather than lost. |

The pattern is mechanical: a territory encounters a model, judges it out of scope, and names a
plausible owner. No one owned the list of owners. **Recommendation: before Wave 1, run a
"deferred-to" sweep — grep every cross-territory table for a named territory, check it against the
list of 13, and adopt or explicitly kill every orphan.** This is a mechanical check that would have
caught G3, G7, G8, and G11 in an hour.

---

## 4. Wrongly-cut audit

All 266 cut entries read. The great majority are well-reasoned — the cuts for gradient-requiring
methods, matrix-heavy methods, and methods needing n in the thousands are correct and consistent.
Below are the ones cut for bad reasons, grouped by failure mode.

### 4a. Cut in one territory, ranked highly in another (unreconciled contradictions)

These matter most, because the sweep produced *two opposite verdicts on the same model* and nothing
adjudicates.

| Model | Cut by | Ranked by | Adjudication |
|---|---|---|---|
| **Weitzman Pandora's box / house-selling with recall** | **T06**: "beautiful online-algorithms theory, but the input (a known value distribution plus a recall/cost structure) is **almost never available to an agent**" | **T10 #4 (fourth of 25)** and **T10 #23**: "a *provably optimal* policy for **the exact situation an agent is in** when triaging approaches, and almost nobody in the decision-analysis mainstream uses it" | **T10 wins.** T06's premise is false — the agent supplies the inspection cost and a prior over candidate value, which is exactly what territory 11 exists to elicit. This is the most consequential wrong cut after Lee bounds. |
| **Secretary problem / 37% rule** | **T10**: "its no-recall, ordinal-only, known-N assumptions almost never hold for an agent, which can usually recall earlier candidates. #23 dominates it in practice" | **T06 #19** | **T10 wins.** The two territories cut each other's stopping model; T10's reasoning is the better one in both directions. Net: **ship Weitzman/reservation, drop secretary.** T06 #19 and #20 (Bruss' odds algorithm) should both be demoted — Bruss solves "stop on the last success", a specific objective T06 itself flags as needing verification that it's the actual goal. |
| **Fisher's method for pooling** | **T06**: cut deliberately "**because** they are invalid under the optional-continuation pattern agents actually use. Worth an explicit 'don't do this' note" | **T08 #9** | **T06 wins**, and RESEARCH.md §1.6 already logged this as a hard refuse. T08 #9 should be demoted to a refusal-with-redirect. Currently the catalog ships both a model and its own prohibition. |
| **Cooke's classical model** | **T01**: "an agent essentially never [has seed questions] at decision time." **T11**: "Requires a battery of calibration questions with known answers, plus a *panel*. A single agent has neither." | **T08 #17**: "the agent *can* construct seed questions — **this is the one heavyweight method whose data requirement an agent can genuinely satisfy** by asking sub-agents questions it already knows the answer to" | **Unresolved and needs a decision.** T08's argument is clever but collides head-on with P6 (pseudo-replication): sub-agents on one base model are not a panel, and scoring them on seed questions measures the base model k times. T08's own #11 would then discount them to k_eff ≈ 1. **I judge T01/T11 correct; T08 #17 should be cut**, and its slot given to G3 (agreement), which is what "how much do my sub-agents actually differ" really needs. |
| **VaR backtesting (Kupiec, Christoffersen)** | **T05**: "require a long history of *out-of-sample forecasts*, which an agent making a one-off judgment does not have" | **T07 #9 (Kupiec) and T07 #22 (Christoffersen)** | **T07 wins.** T05 and T07 hold opposite models of whether the agent accumulates a prediction log — T07's whole existence depends on it, and §1.8 established that ~20 resolved predictions suffice. T05's cut is fine *for its own territory* but the reasoning generalizes wrongly and should not be repeated. |
| **Safe / anytime-valid log-rank** | **T06**: "real and elegant, but **agents almost never have censored time-to-event data**" | **T09, entire territory**: "censoring is not an edge case here; **it is the normal case**, and the single largest accuracy win in the whole territory is simply refusing to throw away the in-flight observations" | **T09 wins decisively.** T06's factual premise is contradicted by the territory that studied it. The sequential version of the log-rank is a genuine gap for "should I keep this canary running". |
| **Bayes-factor sequential design (Schönbrodt–Wagenmakers)** | **T06**: "largely isomorphic to e-values under a prior; keeping both invites the agent to pick whichever is more favorable" | **T01 #12** | **T06 wins on the reasoning** ("invites the agent to shop for a favourable answer" is a first-class design concern this project should adopt generally), but T01 #12 bundles it with assurance and BFDA operating characteristics, which are genuinely useful. Keep T01 #12, drop the standalone thresholds, adopt T06's anti-shopping principle as a library-wide rule. |
| **Grubbs' test** | **T04**: "assume normality, which is the exact assumption in doubt... **Explicitly anti-recommend**" | **T08 #22** (refusal-first) and **T13 #21 (GESD = iterated Grubbs)** | **T04's objection applies to all three** and is not addressed by either T08 or T13 (T13 #21 does list "refuse on visibly skewed data", which is a partial answer). Three territories, three positions, no reconciliation. Recommend: ship GESD only, with T04's normality objection as a printed precondition, and cut T08 #22 (whose stated value is entirely its refusal, which T04's resolution guard already provides). |
| **Cluster/ICC design effect** | **T06**: "narrow; the useful kernel (inflate n by `1+(m−1)ρ`...) is **a one-line warning attached to #3, not its own tool**" | **T08 #11** ships exactly `k_eff = k/(1+ρ(k−1))` as a ranked model, and RESEARCH.md §1.16 calls the underlying concern "**the module's single highest-leverage guard**" | **T08 wins.** Same formula, demoted in one territory and elevated to flagship in another. See cluster **C6**. |

### 4b. Cut as "belongs to territory X" where X does not exist

Already tabulated in §3. The four that are real losses: **inter-rater agreement** (T08), **two-sample
distribution comparison** (T13), **online FDR** (T06), and the entire **regression / effect-size**
surface (T02, T03, T04, T06, T12). All four were cut for a *filing* reason, not a substantive one —
nobody argued they were low-value or infeasible.

### 4c. Cut as "too niche" where the situation is actually common

| Cut | Cut by | Why the niche judgment is wrong |
|---|---|---|
| **Lee bounds** | T02 (self-flagged as regretted) | The agent's attrition is *timeouts and crashed runs*, which is universal, not narrow. See G15. |
| **Friedman test** | T04 (self-flagged as "the closest thing to a 27th row") | Same-items-many-configs is the normal agent eval design, and the ranked alternative (Kruskal–Wallis) is the wrong test for it. See G6. |
| **Jonckheere–Terpstra / Page's trend / ordered alternatives** | T04 ("rare in agent judgment work") | Monotone knobs (context length, temperature, k, threads, retries) are the most common designed experiment an agent runs. See G14. |
| **Ranked Probability Score** | T07 ("real but rare") | Severity/priority/star ratings are the commonest ordinal outcome. Same blind spot as above, in a second territory. |
| **Dueling / pairwise preference** | T10 ("revisit if a pairwise-judgement use case appears") | The use case has appeared — it is the dominant LLM eval pattern. And the cheap estimation half was never considered. See G4. |
| **Fault trees / reliability block diagrams** | T09: "this is arithmetic on independent probabilities, **which an agent does correctly unaided**" | Flatly contradicted by T05 #9, which exists *because* agents get `1−(1−q)^k` wrong at scale, and by T08 #11, which exists because agents compound correlated evidence. The claim that agents do independent-probability composition correctly is the one empirical assertion in the sweep I would bet against. Also a near-duplicate of T05 #9 (cluster C5). |
| **Cure / mixture-cure models** | T09 (cut with explicit regret) | "Some of these jobs never finish" is common, but T09's identification argument (needs a clear KM plateau with substantial follow-up) is sound. **Correctly cut**; listed here only to record that I checked the regret and disagree with re-including it. |

### 4d. Cut on a false feasibility claim

**KSG k-nearest-neighbour mutual information** (T12): *"genuinely implementable (O(n²) at agent n) but
**needs a digamma function that `math` does not provide**... Revisit if a digamma lands in the numerics
layer."* But **T09 #23 states digamma is "implementable in ~15 lines by recurrence + asymptotic
series"** and needs it anyway for the gamma MLE. The stated blocker is false, the function is already
required by another territory, and the consequence of the cut is that **continuous-variable dependence
detection is entirely absent** from the catalog (T12 #12 handles categorical only, and requires the
agent to choose bins, which T12 itself flags as a refusal condition). Recommend: add digamma to the
numerics core (it is cheaper than either incomplete beta or incomplete gamma) and reinstate KSG behind
an n ≥ 100 gate.

### 4e. Cuts I checked and endorse

For the record, so the audit is falsifiable: the cuts of causal discovery (T02), deep-learning
forecasters and foundation models (T03), Shapiro–Wilk-as-gatekeeper (T04), automatic outlier deletion
(T04), non-stationary GEV and Danielsson double-bootstrap (T05), post-hoc power (T06), Hosmer–Lemeshow
and AUROC-as-calibration (T07), trim-and-fill / p-curve / fail-safe N (T08), MIL-HDBK-217 and
3-parameter Weibull (T09), AHP / TOPSIS / info-gap / prospect theory (T10), anchoring-correction
models (T11), Kolmogorov complexity and NML (T12), and the entire learned-anomaly-detector family
(T13) are all correct, well-argued, and in several cases better-argued than the corresponding
inclusions. The sweep's cut-list discipline is generally a strength; the failures are concentrated in
*filing* decisions and in *frequency* judgments about agent behaviour, not in statistical judgment.

---

## 5. Missed identity clusters

RESEARCH.md §2.2 names three (C1 `n ≥ ln α/ln p`; C2 marginal EVSI = marginal cost; C3 exact rank
nulls by DP). All three are real. Below are nine more, ordered by how much duplicated code they
represent. **Two of them span more territories than C1 does.**

### C4 — Exact discrete-tail inversion (the largest cluster in the sweep)

**The identity:** every exact interval and exact test on a count or a proportion is *bisection on a
binomial, Poisson, or hypergeometric CDF*, and the Beta/Gamma duality makes all three the same two
special functions.

**Appears as:** Clopper–Pearson upper limit (T05 #1); Garwood exact Poisson CI (T05 #15); exponential
MTBF χ² interval (T09 #1 — **T09 itself notes "the exponential MTBF interval *is* the Garwood exact
Poisson rate interval"**); Clopper–Pearson/Jeffreys reliability interval (T09 #16); exact Poisson rate
check (T13 #4); Clopper–Pearson/Wilson/Jeffreys flake rate (T13 #5); exact conditional binomial
two-rate test (T13 #13); Wilson/Jeffreys recalibration cells (T07 #5); exact binomial coverage test
(T07 #9); Beta-Binomial posterior interval (T01 #1 — numerically identical to the Jeffreys interval);
exact binomial / sign test (T04 #8); logit-transformed proportion pooling (T08 #20); exact
beta-binomial Bayes factor (T12 #14); Fisher / Boschloo (T04 #18).

**Span: eleven territories.** C1 is the `k = 0` special case of this cluster. RESEARCH.md found the
special case and missed the general one. Territories 05, 07, 09, and 13 each independently flag
"share the binomial-CDF primitive; do not duplicate it" in their overlap tables — four independent
warnings that never reached §2.2.

**Consequence if missed:** at least six separate implementations of a bisection-on-a-discrete-CDF, each
with its own edge cases at k=0, k=n, and α near the boundary. This is the highest-risk duplication in
the project because the edge cases are exactly where the module's headline refusals fire.

### C5 — `1 − (1−p)^k`: the at-least-once / max-of-k family

**The identity:** one expression, and its inverse `p = 1 − (1−P)^(1/k)`.

**Appears as:** fan-out tail amplification (T05 #9, "each service has a 10ms p99 — what's the request
p99 across 50 of them"); return-period-to-horizon conversion (T05 #5, "a 1-in-100 event has a 26%
chance in 30 periods") — **these two are the same formula, ranked as separate rows four apart in the
same territory**; Šidák multiplicity correction (T12 #2, `p_adj = 1 − (1−p)^m`) — **the identical
expression under a name sharing no vocabulary with either**; search-corrected surprisal (T12 #7,
`−log₂p − log₂m`, the log form); reruns-needed-to-expose-a-flake (T13 §3.7, the inverse); the rule of
three (C1, the `k=0`/`P=α` corner); system reliability composition (T09, cut); PERT-network merge bias
(G12, the continuous analogue).

**Span: four territories, plus one gap and one cut.** The vocabulary divergence is total — "tail at
scale", "return period", "Šidák correction", "reruns to confidence", and "rule of three" share no
words — which is precisely why §2.2 missed it and precisely why the *router* must index it under all
five phrasings.

### C6 — Design effect / effective sample size

**The identity:** divide n by a correlation-induced inflation factor before believing any interval.

**Appears as:** Kish design effect `1 + ρ(k−1)` (T08 #11, the pseudo-replication discount);
cluster-randomization inflation `1 + (m−1)ρ` (T06, **cut** as "a one-line warning"); autocorrelation
`n_eff = n(1−ρ)/(1+ρ)` (T13 #16); Hamed–Rao Mann–Kendall variance correction (T03 #12, T13 #9 — the
same correction, ranked twice); extremal index `θ·N_u` (T05 #17); LOO fold correlation (T12 #10,
Bates–Hastie–Tibshirani); the exchangeability gate (T04 #23); block-permutation block length
`≈ 2(1+ρ)/(1−ρ)` (T13 #6).

**Span: six territories.** Given that RESEARCH.md P6 names pseudo-replication as "the dominant
violation when combining sources" and §1.16 calls it "the module's single highest-leverage guard",
having the same correction implemented six times under six names — and *cut* in one of them — is the
most strategically important miss in the dedup list.

### C7 — Test inversion by 1-D root-find (the confidence-interval engine)

**The identity:** "invert a test or a profile likelihood over a scalar by bisection to get an
interval." Territory 02 flags it explicitly and no one picks it up: *"Anderson–Rubin CI — an instance
of the general 'invert a test to get a confidence set' pattern, **which is worth generalizing** (it also
gives exact CIs for binomial proportions, etc.)"*

**Appears as:** Anderson–Rubin CI (T02 #18); Weibull shape profile CI (T09 #5); Cox profile-likelihood
CI (T09 #19); GEV return-level profile deviance (T05 #18); changepoint location CI (T13 #6); Bayes
factor robustness region (T01 #10); Fieller's theorem for threshold-crossing (T03 #13); mixture-CDF
quantile inversion (T08 #2, T11 #10); betting-CS endpoint bisection (T06 §2.2); mSPRT inverted CI
(T06 §2.3); GPD/Clopper–Pearson bisections (C4).

**Span: eight territories.** One ~30-line Brent/bisection utility with a monotonicity guard and a
bracketing helper serves all of them. Currently each row describes its own root-find.

### C8 — Logit-affine: extremizing, temperature scaling, and log pooling are one operation

**The identity:** `p' = σ(a·logit(p) + b)`. Everything else in this list is a choice of `a` and `b`
and a story about where they came from.

**Appears as:** logarithmic opinion pooling (T01 #19, `b`-only with weights); geometric mean of odds
(T08 #6, identical); extremizing (T01 #19, T08 #6, T11 #21 — `a > 1`); Bayesian log-odds accumulation
(T08 #11, T11 #17 — additive in `b`); Bayes from prior + LR (T11 #4 — the `k=1` case); logistic /
Platt / Cox recalibration (T07 #7 — `a` and `b` both fitted, and T07 notes it is "one model, three
names"); **temperature scaling (T07 #8, `a = 1/T`)**.

**The surprising part:** **extremizing and temperature scaling are the same one-parameter operation
with reciprocal parameters and opposite intent.** Extremizing multiplies the logit by `a > 1` to sharpen
an under-confident crowd; temperature scaling divides it by `T > 1` to soften an over-confident model.
They live in territories 08/11 and 07 respectively with zero cross-reference, and the library is about
to ship both — one of which pushes probabilities out and the other pulls them in — with no shared
guard against applying both. Given P6 (correlated agents must not be extremized) and §1.8 (LLMs are
measurably overconfident), an agent that extremizes its own sub-agents and then temperature-scales the
result is a real and reachable failure.

**Span: four territories, eight rows, one primitive.**

### C9 — Brier / log score and the REL–RES–UNC decomposition

Straight duplication, no reinterpretation needed: **T07 #3** (Brier + Murphy 3-way decomposition) and
**T11 #19** (Brier/log score + calibration–resolution decomposition) are the same model with the same
formula. **T08 #15**'s "diversity decomposition" is the same decomposition again — T08 says so
outright ("The diversity decomposition in row #15 *is* the Brier decomposition"). **T07 #2** (CORP) is
the modern binning-free version of the same object.

Similarly **T07 #9/#10** (coverage test + Winkler interval score) and **T11 #20** (interval coverage +
Winkler) are verbatim duplicates across two territories; and pinball loss appears at **T07 #14** and
**T01 #4**.

**Span: three territories, six duplicated rows.** These are the easiest wins in the dedup pass because
there is no vocabulary divergence at all — the same names are used.

### C10 — Isotonic regression / PAVA

**T07 #2** (CORP decomposition) and **T07 #17** (isotonic recalibration) are two ranked rows in the
same territory driven by the same PAVA loop — T07 notes #17's "in-sample fit is also the exact quantity
subtracted in the CORP MCB term". **T01 #15** (empirical-Bayes shrinkage of group rates) solves the
adjacent problem with different math. **T10 #24** (EVPPI by sorted-window conditional expectation,
"optimal segmentation à la Sadatsafavi") is isotonic-adjacent. One 25-line PAVA serves three rows.

### C11 — The arithmetic-floor / minimum-attainable-p engine

**The identity:** "is any conclusion reachable at this n, before we compute anything?"

**Appears as:** the exact-resolution guard (T04 #1, which explicitly calls itself "the refusal engine");
permutation min-p refusal (T12 #3); randomization-inference min-p with few clusters (T02 #15); synthetic
control's `1/(J+1)` donor floor (T02 #14); sign-test min-p at k=3 (T08 #12); Grubbs' max attainable
statistic at k=3 (T08 #22); the quantile wall `n ≥ ln α/ln p` (T05 §2.2 — which is C1); conformal's
`n ≥ (1−α)/α` floor (T04 #13); MDE inversion (T13 #3, T06 #4); the calibration power ladder (T07 #12).

**Span: six territories.** T04 already recognises it as one engine that other tools call as a
precondition. RESEARCH.md doesn't list it as a cluster despite §1.29 tabulating seven of its
instances. Given that this is arguably the module's signature capability, it should be one module with
one registry entry per design, not ten scattered refusals.

### C12 — E-processes / betting martingales

Five territories independently rank a "running product of likelihood ratios, reject at `1/α`" row:
**T04 #26**, **T06 #1/#2/#15**, **T01 #12**, **T12 #17**, plus **T13 §4.1** (e-detectors). RESEARCH.md
discusses e-values extensively (§1.5, §1.6, §1.7) but never lists them as an *implementation* cluster,
so five territories will each build the same accumulator.

### Also worth noting (smaller)

- **Hill estimator / power-law tail**: T04 #20 (gated n≥200), T05 #14, T05 #22, T09 #18. Four rows,
  one estimator; T09 flags it, §2.2 doesn't.
- **MAD-with-zero-fallback robust z**: T04 #15/#16, T13 #1/#18, T08 #19. §1.33 spotted two of the
  three convergences; it is three.
- **Regression to the mean**: T02 #5 and T03 #8 (reference-class shrinkage) are the same shrinkage
  arithmetic — T03 says so ("K&T's `class_mean + ρ·(inside − class_mean)` is literally shrinkage
  toward a prior mean") — and T01 #15 (James–Stein) is the third instance.
- **Page–Hinkley ≡ CUSUM** (T13 cut list) — an identity that *was* correctly caught. Good precedent.

---

## 6. Family balance

The 12 families map imperfectly onto the 13 territories. Assessment of whether each can support a
credible Wave 1 slice:

| Family | Territory | Ranked rows | Rows usable at agent scale in Wave 1 | Verdict |
|---|---|---|---|---|
| signal-vs-noise | 04, 13 | 50 | ~20 | Thick. Over-served if anything. |
| estimation | 01, 04, 11 | 74 | ~30 | Thick. |
| forecasting | 03 | 23 | **6** | **Thin in practice** — see below. |
| causal | 02 | 24 | **6** | **Thin in practice** — see below. |
| evidence-sufficiency | 06 | 25 | ~15 | Thick and cheap (§1.5). Best-positioned family. |
| synthesis | 08 | 23 | ~14 | Adequate. |
| monitoring | 13 | 24 | ~16 | Thick. |
| tail-risk | 05 | 24 | ~12 | Adequate, but 50% is refusal machinery. |
| decision | 10 | 25 | ~12 | Thick, over-deep in bandits. |
| calibration | 07 | 23 | **4** | **Thinnest. Blocked on data, not mathematics.** |
| duration-reliability | 09 | 23 | ~15 | Thick. |
| model-choice | 12 | 22 | ~10 | Adequate. |

### Calibration is the one family that cannot support a conventional Wave 1 slice

Not because the research under-served it — territory 07 is one of the two or three strongest reports in
the sweep, and §1.8's finding that N ≈ 11–25 suffices for calibration-in-the-large is the single most
promotable result of the whole pass. The problem is that **every row is blocked on a prediction log
that does not exist**, and T07's own §4.1 ladder is explicit: N < 10 → nothing; N = 10–24 → rows 1, 4,
12, 20 only.

So the Wave 1 deliverable for this family is **not four models. It is a logging protocol** — an
append-only format, a pre-registration discipline ("the confidence must be written before resolution"),
a task-class tag (T07 §4.2 item 4), and an elicitation-protocol field (§1.10's
`data_provenance_required`) — with four small models attached. If Wave 1 ships the models without the
protocol, the models will have nothing to run on for weeks and will be judged useless. If it ships the
protocol first, the family becomes the module's flagship by Wave 2. **This should be an explicit
sequencing decision, not an accident.**

### Forecasting and causal are thin for the same reason: their ranked depth is in the wrong tier

**Forecasting**: 23 rows, but rows 14–23 need n ≥ 10–20 or MUST-CONSTRUCT-DATA. At the agent's modal
series length of 5–12 points the family collapses to six rows — the MASE gate (#1), naive baselines
(#7), Theta (#2), damped trend (#3), simple combination (#4), and empirical/conformal intervals (#5).
All six are trivial. That is a credible slice, and it is honest, but the spec should not promise a
forecasting *family* when it is really "six functions and a gate". Note that the family's genuine
strength is its gate: §1.39's MASE ≥ 1 → print the naive forecast is the cleanest instance of P9 in
the sweep.

**Causal**: 24 rows, but 11 of them (#9, #11, #12, #14, #18, #21, #22, #23, #24, and partly #10, #15)
need panel or unit-level data an agent essentially never holds. The Wave 1 slice is the six no-data /
INLINE rows: E-value (#1), back-door + good/bad control (#2), regression to the mean (#5), Manski/MTR
bounds (#6), probability of necessity (#8), and Oster's δ (#13). This is a *sensitivity-analysis*
family, not an estimation family, and territory 02 is right that this inversion is the correct ranking
(§1.3). The spec should name the family accordingly — calling it "causal inference" will make an agent
expect estimators it will not get, which is its own kind of miscalibration.

### No family is thin because of under-research

Every thin family is thin because of *input-tier* mismatch, not because the territory agent missed
material. The research quality is uniformly high; the problem is that the ranked tables mix INLINE and
MUST-CONSTRUCT-DATA rows in one ordering, which makes families look deeper than their shippable core.
**Recommendation: add a "Wave 1 shippable" column keyed on input tier before the registry is written,
and rank within tier.**

---

## 7. Over-representation

Where Wave 1 should cut depth to buy the breadth in §2.

| Family | Cut | Rationale | Rows freed |
|---|---|---|---|
| **Causal (02)** | All 11 panel/unit-level estimators (#9, #11, #12, #14, #18, #21, #22, #23, #24, and defer #10, #15) | The agent does not have panels. Territory 02's own ranking already puts sensitivity above estimation; Wave 1 should make that structural. | **11** |
| **Tail risk (05)** | Rows 10, 11, 12, 13, 14, 16, 18, 21, 22, 23, 24 | All gate at n ≥ 150 raw / 30 exceedances / 25 blocks / 500 for auto-threshold. §1.14's own finding (Δξ needs ~1,570 exceedances) says ξ is "a sign, not a number" at agent scale. Shipping eleven GPD/GEV/Hill rows that refuse is expensive theatre. | **11** |
| **Decision / bandits (10)** | Four of six bandit rows (#7 *or* #8, keep one; cut #11, #13, #14, #25) and three of five MCDA rows (#16, #17, #18) | T10 says it itself: "at agent scale... the horizon is far too short for the log-*n* asymptotics that make UCB and Thompson sampling famous", and "#9's dominance screen already settled it (don't run MCDA you don't need)". Six bandits and five MCDA variants for a horizon that voids their guarantees. | **7** |
| **Model choice (12)** | Defer #6 (BIC-as-BF), #11 (Vuong), #19 (MDL), #10 (LOO-CV) | At n < 20 with 2–3 candidates, AICc + the AIC/BIC disagreement detector (#22) + the split-LRT (#4) cover the decision space; the rest will agree with AICc or refuse. Vuong is explicitly refused for nested models and size-distorted for overlapping ones. | **4** |
| **Robust (04)** | Collapse #10, #11, #12 into one gate + one method | §1.27 demotes the bootstrap to Wave 2 behind refusals; three ranked bootstrap rows contradict that decision. HulC (#22) is the measured replacement. | **2** |
| **Bayesian (01)** | Reclassify #13, #14, #21, #22, #25, #26 as infrastructure, not models | Grid, MCMC, Laplace, PSIS-LOO, stacking, and SBC are engine and test, not agent-facing rows. §1.35 already moves MCMC out of the critical path. They should not consume family budget or registry entries. | **6 (reclassified)** |

**Net: roughly 35 rows of depth freed, against ~15 uncovered situations to add.** The trade is
comfortably positive and the added rows are systematically *cheaper* than the removed ones — capture–
recapture, Good–Turing, κ, McNemar, Friedman, Simpson standardization, and the at-least-once family are
all EASY, INLINE, and need no special functions, whereas most of the cut depth needs GPD fits, panel
data, or asymptotics that do not bite.

---

## 8. Recommendations

Ordered by expected value.

1. **Run a mechanical "deferred-to" sweep before the registry is written.** Grep every cross-territory
   table for a named owning territory; check each against the list of 13; adopt or explicitly kill
   every orphan. Would have caught G3, G7, G8, G11 in an hour. (§3)

2. **Add the nine missed identity clusters to §2.2 and re-scope the dedup pass around twelve, not
   three.** C4 (exact discrete-tail inversion, 11 territories) and C6 (design effect, 6 territories)
   are each larger than C1. C8 (extremize ≡ inverse temperature scaling) is a correctness hazard, not
   just duplication. (§5)

3. **Add the fifteen uncovered situations, prioritising G1–G8.** All eight are EASY, most are INLINE,
   and four of them (G3, G5, G6, G8) are situations an agent hits several times a session. (§2)

4. **Re-include Lee bounds and wire attrition as a composition hazard on every two-sample row.**
   Territory 02's regret was correct and the situation is universal, because the agent's attrition is
   timeouts. (§4c, G15)

5. **Reconcile the nine head-to-head contradictions in §4a.** Each is two territories disagreeing about
   what an agent has. Left unresolved they become inconsistent refusals in shipped code — most
   damagingly the Weitzman/secretary pair, where each territory cut the other's model and ranked its
   own.

6. **Sequence the calibration family behind a logging protocol.** The family's Wave 1 deliverable is
   the append-only prediction log with provenance and task-class fields; the four models attach to it.
   (§6)

7. **Add an input-tier column to every ranked table and re-rank within tier.** The families that look
   thin are thin only in their shippable tier, and the current single ordering hides it. (§6)

8. **Add digamma to the numerics core and reinstate KSG mutual information behind an n ≥ 100 gate.**
   The stated blocker is false and territory 09 needs digamma regardless. (§4d)

9. **Audit the situation phrasings for agent-workflow language.** Across 310 rows, almost none are
   phrased as "should I ask", "have I read enough", "is another subagent worth it", "am I looping".
   The mathematics exists (T10 #1, #4, #22, #23); the retrieval index does not. Given §0.6, this is
   the failure mode most likely to make the module unused. (§1b)

10. **Cut ~35 rows of depth from causal estimators, model-based EVT, bandit variants, and MCDA
    variants** to fund items 3 and 4. (§7)
