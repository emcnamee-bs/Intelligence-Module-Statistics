# Territory 02 — Causal Inference

Research pass for the Intelligence Module. Scope: potential outcomes and DAG identification, confounder
adjustment, propensity scores, IV, DiD (including staggered-adoption corrections), RDD, synthetic control,
ITS, front-door/back-door, sensitivity analysis, negative controls, and no-data causal reasoning.

Constraint filter applied throughout: **pure Python 3 stdlib, n ∈ [3, few thousand], low dimensional,
agent has a handful of numbers / a small file / the ability to go build a dataset.**

---

## 1. Territory summary

Causal inference is the only branch of statistics that directly answers the three questions in the agent's
brief — *did this change cause the improvement, is this correlation confounded, would this have happened
anyway* — and it answers them by forcing the agent to name the counterfactual it is implicitly asserting.
Its highest-value contribution here is **not estimation**: the agent rarely has a panel dataset, but it
almost always has an effect size, a story, and an unstated assumption, and this field turns that unstated
assumption into a number the agent must defend ("an unmeasured confounder would need a risk ratio of 4.2
with both treatment and outcome — is that plausible here?"). A second, distinctive contribution is that a
large fraction of the field is **computable with zero data**: back-door/front-door identification,
good-vs-bad-control classification, omitted-variable bias *direction*, and worst-case bounds all run off a
declared causal graph and a couple of scalars, which is exactly the input tier an agent actually has. The
estimation half of the field is worth carrying mainly for the cases where the agent can *construct* the
data — a before/after metric series, a set of untreated comparison units, a running variable — and the
modern staggered-DiD literature matters here because the naive two-way fixed-effects regression an unaided
agent would write is now known to be *actively wrong*, sometimes sign-flipped, under heterogeneous effects.
The design rule that falls out: **rank sensitivity analysis and bounds above estimators**, because a
refusal-to-conclude with a defensible breakdown value beats a point estimate whose identifying assumption
was never checked.

### The sparse-data doctrine

The agent's modal predicament is: *one treated thing, a before number, an after number, and a story.*
What can be said rigorously?

| What the agent has | What is rigorously available |
|---|---|
| Two numbers (before, after) and nothing else | **Nothing causal.** Refuse. Offer: what would need to be true. |
| Before/after + an outcome range | Manski worst-case bounds (usually uninformative — that *is* the finding) |
| Before/after + a plausible monotonicity claim | MTR/MTS-narrowed bounds; often one-sided and informative |
| An effect estimate + its CI | **E-value** / bounding factor — the workhorse. Runs on 2–3 numbers. |
| A regression with controls + R² | Cinelli–Hazlett robustness value; Oster's δ |
| Before/after where units were *selected for being extreme* | Regression-to-the-mean decomposition (frequently explains the whole effect) |
| A pre-period time series ≥ ~8 points | Interrupted time series |
| Any untreated comparison unit | 2×2 DiD, and everything downstream of it |
| ≥ 5 untreated comparison units + long pre-period | Synthetic control + placebo permutation inference |
| A declared DAG and no data at all | Back-door / front-door identification, bad-control classification, bias direction |

---

## 2. Ranked model table

Tier tags: **INLINE** = a handful of numbers as CLI flags. **DATAFILE** = a small CSV the agent has or can
write. **MUST-CONSTRUCT-DATA** = the agent has to go gather comparison units / a running variable / a panel
before the tool is usable.

| # | Model / method | SITUATION (retrieval phrasings) | Minimum viable inputs + tier | Beats what | Stdlib feasibility | REFUSE-to-print conditions |
|---|---|---|---|---|---|---|
| 1 | **E-value / Ding–VanderWeele bounding factor** (sensitivity to unmeasured confounding) | "how strong would a hidden variable have to be to kill this result"; "is this association robust to confounding I didn't measure"; "could something else explain this correlation"; "how confident can I be this isn't confounded"; "what would have to be true for this effect to be fake" | `--rr 1.8 --lo 1.2 --hi 2.7` (risk/rate/odds/hazard ratio + CI), or `--smd 0.35 --se 0.10` for a standardized mean difference. **INLINE** | Agent's unaided move is a vibe-check ("seems plausible, could be confounded"). E-value converts that into a threshold on the *joint* confounder strength that the agent can then reason about with domain knowledge. Assumption-free: no assumption that the confounder is binary, single, or non-interacting. | **EASY.** `math.sqrt`, `exp`. E = RR + √(RR(RR−1)) for RR≥1; use 1/RR if RR<1. Continuous→RR via RR ≈ exp(0.91·d) (Chinn/VanderWeele approximation). E-value for the CI limit nearest the null is the more decision-relevant number. | Refuse if: RR reported on a scale the tool wasn't told (raw difference with no SD → no conversion); outcome is common and the *odds ratio* was passed as if it were a risk ratio (inflates E-value); the "effect" has no CI and no SE (cannot compute the limit E-value, which is the one that matters); selection bias/measurement error is the suspected problem, not confounding — E-values do not cover those. |
| 2 | **Back-door criterion + minimal adjustment sets + good/bad control classifier** | "what should I control for"; "should I include this variable in the comparison"; "is this analysis identified at all"; "am I adjusting for the wrong thing"; "does controlling for X help or hurt"; "I have a causal story, is it testable" | A DAG as edge list: `--edges "deploy->latency, load->deploy, load->latency"` plus `--exposure deploy --outcome latency`. **NO DATA AT ALL.** | The unaided agent controls for "everything available", which is a known bias-*generating* move: adjusting for a mediator destroys the total effect, adjusting for a collider or a descendant of the outcome manufactures association from nothing, and adjusting for a near-instrument amplifies whatever confounding bias remains. This is the single highest-leverage zero-cost tool in the territory. | **EASY–MODERATE.** Pure graph algorithms: ancestors/descendants, moralization + d-separation, then enumerate minimal adjustment sets. Textor et al.'s polynomial-delay listing algorithm is implementable; a brute-force subset search over ≤ ~15 candidate covariates is fine at agent scale. No numerics at all. | Refuse if: the graph is cyclic (not a DAG); no valid adjustment set exists (say so — that *is* the answer, then route to front-door/IV/bounds); the agent supplied a graph with no unobserved-confounder nodes at all (almost certainly an under-specified graph — force the agent to state which arrows they are *asserting are absent*, since identification is driven by absent arrows, not present ones). |
| 3 | **Difference-in-differences, canonical 2×2** | "did this change cause the improvement or would it have happened anyway"; "I have before and after for the thing I changed and something I didn't"; "how do I separate my change from the general trend"; "the metric improved but everything improved" | Four cell means + n's: `--treat-pre --treat-post --ctrl-pre --ctrl-post` with counts/SDs. **INLINE** at minimum; **DATAFILE** for unit-level SEs. | Beats the naive before/after delta, which attributes secular trend to the intervention. This is the workhorse for the agent's #1 question. The 2×2 case is where most agent situations actually land. | **EASY.** Four means, one interaction contrast. SE via pooled variances or unit-level OLS with an interaction. Needs a Student-t CDF (regularized incomplete beta — see RESEARCH.md §0.7). | Refuse if: only one pre-period *and* the agent has claimed no way to check parallel trends → print the identified set under a stated trend-violation magnitude instead of a point estimate (route to #10). Refuse the SE if there are < ~8 independent units per arm and the agent asked for a p-value (route to #15, randomization inference). Refuse outright if treatment and control were selected on the pre-period outcome (route to #5). |
| 4 | **Cinelli–Hazlett robustness value / partial-R² OVB** | "how much confounding would break my regression result"; "my coefficient survived adding controls, does that mean anything"; "is this regression coefficient causal"; "how sensitive is this estimate to what I couldn't measure" | Coefficient, its SE, residual df, and (optionally) a named benchmark covariate: `--beta 0.42 --se 0.11 --df 137 --benchmark-r2 0.08`. **INLINE** (all four come off standard regression output). | Strictly generalizes the "does the coefficient move when I add controls" heuristic that the agent would use unaided, which is uninformative on its own. RV is scale-free, handles multiple non-linear confounders, and supports *benchmarking* against an observed covariate ("as strong as the strongest thing I did measure"). | **EASY.** RV_q = ½(√(f_q⁴ + 4f_q²) − f_q²) with f_q = q·|t|/√df; partial R²_{Y~D|X} = t²/(t²+df). All closed form. Contour plots are the R package's selling point and are not needed — the scalar RV is the decision object. | Refuse if: the model is not linear-in-treatment (RV is derived for the linear/partially-linear case; for a logistic model route to E-value); df < ~10 (t-based quantities unstable); the agent passes a coefficient from a model that already conditions on a mediator or collider (route to #2 first — sensitivity to *unmeasured* confounding is meaningless if the *measured* adjustment set is wrong). |
| 5 | **Regression-to-the-mean decomposition** | "we fixed the worst offenders and they got better — was that us"; "the flaky tests we targeted are less flaky now"; "our slowest endpoints sped up after the optimization"; "did the intervention work or did it just bounce back"; "we intervened on an outlier and it normalized" | Baseline value, group mean, and a test–retest / period-to-period correlation (or repeated measurements to estimate it): `--pre 480 --mean 210 --r 0.6`. **INLINE**, or **DATAFILE** if r must be estimated from a pre-period. | This is the alternative explanation an unaided agent reliably fails to raise, and it is *the* dominant confounder in the agent's most common workflow: identify the worst N of something, fix them, observe improvement. Expected post = μ + r·(pre − μ), so (1−r)·(pre − μ) of the "improvement" is arithmetic, not causation. | **EASY.** One line of arithmetic plus an r estimate (Pearson correlation over two pre-periods). Optional: an SE for the RTM-adjusted residual effect. | Refuse if: units were **not** selected on the baseline outcome (RTM does not apply; saying so is the output); r cannot be estimated and the agent will not supply a range (then print the *bracket* over r ∈ [0,1], which spans "all real" to "all artifact" — often the honest answer); measurement is deterministic with no noise (r=1, no RTM). |
| 6 | **Manski worst-case bounds + MTR / MTS / MIV narrowing** | "what's the most and least this could possibly be"; "I can't identify the effect but can I bound it"; "how bad could the selection bias be"; "what can I say without assuming no confounding"; "give me a range I can defend" | Observed conditional means, group shares, and the outcome's logical range: `--y1-obs 0.62 --y0-obs 0.41 --p-treated 0.3 --ymin 0 --ymax 1`, plus optional `--assume mtr,mts`. **INLINE** | Beats both of the agent's unaided options: asserting the naive contrast is causal, or refusing to say anything. Worst-case bounds always have width (ymax−ymin) and usually straddle zero — **that is the finding**, and it's an honest one. The value is in the *narrowing*: adding monotone treatment response ("the change can't have hurt") or monotone treatment selection ("the units we treated were already worse") often yields a one-sided, decision-relevant bound. | **EASY.** Law of total probability, min/max. MIV bounds need an intersection over an ordered instrument's levels — still elementary. | Refuse if: `ymin/ymax` were set to the sample extrema rather than logical/known bounds (finite-sample bounds are then invalid — recent literature flags this explicitly); the agent asserts MTR/MTS without stating the substantive reason (make them type the justification, it goes in the output); outcome is unbounded with no defensible truncation. |
| 7 | **Interrupted time series / segmented regression** | "the metric changed after we shipped — is that the deploy"; "did this policy change the trend"; "I have a time series and one event"; "level shift or slope change after the intervention"; "no control group, just before and after over time" | A time-indexed outcome series + the intervention index: `--file metric.csv --intervention 2026-05-14`. Needs ≥ ~8 pre-points, ideally ≥ 12. **DATAFILE** | Beats a two-point before/after by separating *level shift* from *pre-existing slope*, which is the single most common way an agent gets fooled ("it was already trending down"). It is the only credible design when there is genuinely no control unit — the agent's very common case. | **MODERATE.** OLS on [1, t, D_t, (t−t₀)·D_t] — trivial. The hard part is honest inference: residuals are serially correlated, so needs Newey–West HAC SEs (easy: weighted autocovariance sum with Bartlett kernel) or Prais–Winsten. Also needs a Durbin–Watson / Ljung–Box autocorrelation check as a gate. | Refuse if: fewer than ~8 pre-intervention points (fit is not identified against noise — say so); the series is strongly seasonal and no seasonality term was fit (the "level shift" will be a seasonal artifact); a *second* co-timed event exists (the agent must be asked); autocorrelation is severe enough that the HAC correction changes significance (print both, refuse the headline). |
| 8 | **Probability of necessity / attributable fraction, with bounds** | "did *this* cause *that* in this specific instance"; "how likely is it that the outcome was because of the change"; "the failure happened after the deploy — was it the deploy"; "what fraction of the improvement is attributable to what we did"; "would the outcome have occurred anyway" | Binary exposure/outcome rates: `--p-y-given-x 0.30 --p-y-given-notx 0.12`, optionally experimental arms for tighter bounds. **INLINE** | This is the *literal* form of the agent's headline question ("did this change actually cause the improvement") and it is a genuinely different estimand from the ATE — an agent conflating "the average effect was positive" with "this instance was caused by it" makes a real error. Under monotonicity (the change cannot have hurt), PN = (RR−1)/RR, the excess-risk-ratio / attributable fraction. Without monotonicity, Tian–Pearl give informative bounds when both observational and experimental data exist. | **EASY.** Closed-form max/min over a handful of linear expressions. | Refuse if: monotonicity is asserted without justification and the tool would otherwise be printing a point value (print the bounds instead); only observational data is available *and* the exposure is confounded (PN bounds collapse to uninformative — say so); the outcome or exposure is not binary/binarizable without an arbitrary threshold. |
| 9 | **Propensity score weighting (IPW / overlap weights) with balance + positivity gate** | "the two groups aren't comparable"; "the projects that adopted this were already different"; "how do I compare treated and untreated fairly"; "adjust for selection into the treatment"; "control for baseline differences between groups" | Unit-level CSV: covariates, binary treatment, outcome. n ≥ ~50, covariates ≤ ~10. **DATAFILE / MUST-CONSTRUCT-DATA** | Beats naive group-mean comparison and beats "just throw the covariates in an OLS" by making the **overlap/positivity assumption visible and checkable** — the diagnostic output (standardized mean differences before/after weighting, propensity score overlap) is more valuable than the point estimate. Overlap weights (Li, Morgan & Zaslavsky) dominate raw IPW under poor overlap. | **MODERATE.** Logistic regression via IRLS (Newton–Raphson, p×p solve — fine at p≤~20); needs separation detection and a ridge fallback. Balance table is trivial. SE via bootstrap (`random`) rather than the sandwich, which is easier and more honest at these n. | Refuse if: any |SMD| > 0.10 after weighting (balance failed — the whole point); effective sample size after weighting drops below ~30% of n (extreme weights, positivity violated); any estimated propensity outside [0.05, 0.95] with non-trivial mass (no overlap — refuse and report the non-overlapping region); more covariates than n/10; the agent asks to adjust for a post-treatment variable (route to #2). |
| 10 | **Honest DiD / Rambachan–Roth breakdown value** | "how much could the trends have diverged before my conclusion flips"; "my pre-trends look okay but I'm not sure that's enough"; "what if parallel trends is only approximately true"; "sensitivity analysis for difference-in-differences"; "the control group isn't a perfect counterfactual" | Event-study coefficients (pre and post) + their SEs: `--pre "-0.02,0.01,-0.01" --post "0.18" --se ...`. **DATAFILE** (from a DiD/event-study fit). | Directly repairs the biggest live failure mode in DiD practice, documented by Roth (2022): pre-trend tests are **underpowered** — violations big enough to flip the conclusion are routinely undetected — and conditioning on passing the pretest can make bias *worse*. Instead of a binary "pre-trends passed", it returns a **breakdown value M̄**: "post-treatment trend violation would have to exceed M̄× the largest pre-period violation." | **EASY (restricted) / HARD (full).** The relative-magnitudes restriction with a single post-period reduces to an interval: effect ∈ [β_post − M̄·max\|pre\|, β_post + M̄·max\|pre\|], and the breakdown M̄ is a one-line solve. The **full** Rambachan–Roth fixed-length CI over the polyhedral identified set with moment-inequality inference is an LP + conditional inference problem — out of scope; the tool must say it is reporting the simplified version. | Refuse if: there are zero pre-periods (nothing to benchmark M̄ against — the method is undefined); the agent asks for the full FLCI (declare not implemented rather than silently substituting the crude interval); pre-period SEs are so large that max\|pre\| is dominated by noise (breakdown value becomes meaningless — report the noise floor). |
| 11 | **Callaway–Sant'Anna group-time ATT(g,t) + aggregation** (and Sun–Abraham interaction-weighted as a variant) | "different teams/regions adopted this at different times"; "staggered rollout, what's the effect"; "phased deployment across units"; "I ran a two-way fixed effects regression on a staggered rollout"; "units switched on at different dates" | Panel CSV: unit, period, first-treatment period (∞ for never-treated), outcome. Needs ≥ 2 adoption cohorts + ideally a never-treated group. **MUST-CONSTRUCT-DATA** | Beats the two-way fixed-effects regression an unaided agent would write, which under staggered adoption and heterogeneous effects uses **already-treated units as controls** ("forbidden comparisons"), assigns some 2×2s **negative weights**, and can return an estimate outside the convex hull of every unit's true effect — including the wrong sign. This is a case where the naive answer is not merely imprecise but wrong. | **MODERATE.** The unconditional (never-treated / not-yet-treated) version is a loop of 2×2 DiDs plus a weighted aggregation — genuinely easy. Doubly-robust version needs logistic propensity per (g,t) — moderate. The multiplier bootstrap for *uniform* confidence bands needs a Mammen/Rademacher draw loop — feasible with `random`, ~1000 draws at agent scale. | Refuse if: no never-treated **and** no not-yet-treated comparison exists for a given (g,t) (that cell is unidentified — drop it and say which); any cohort has < 3 units (aggregation weights become degenerate); treatment is non-absorbing (units switch off) — CS assumes staggered absorbing adoption, route to de Chaisemartin–D'Haultfœuille or refuse; treatment is continuous/dose-varying. |
| 12 | **Goodman–Bacon decomposition** (diagnostic, not estimator) | "is my fixed-effects difference-in-differences trustworthy"; "why does my TWFE result look weird"; "how much of my estimate comes from bad comparisons"; "diagnose a staggered rollout regression" | Same panel as #11. **MUST-CONSTRUCT-DATA** | Pure diagnosis: decomposes the TWFE coefficient into all constituent 2×2 DiDs with their weights, exposing what share of the estimate comes from **late-vs-already-treated** ("forbidden") comparisons. Gives the agent a *quantitative* reason to distrust its own regression rather than a literature citation. Cheap and highly interpretable. | **EASY.** Combinatorial enumeration over cohort pairs, closed-form weights from treatment-variance shares. No optimization. | Refuse if: unbalanced panel (the decomposition's weights assume balance — say so); only one adoption cohort (decomposition is trivial and the diagnostic is unnecessary); covariates in the TWFE model (the clean decomposition is for the unconditional case). |
| 13 | **Oster's δ / coefficient stability bound** | "my estimate barely moved when I added controls, is that reassuring"; "how much selection on unobservables would kill this"; "bound the omitted variable bias from what the controls did"; "is the coefficient stable enough to believe" | Four numbers from two regressions: `--beta-uncontrolled --r2-uncontrolled --beta-controlled --r2-controlled`, plus `--rmax` (Oster suggests 1.3·R̃). **INLINE** | Formalizes exactly the heuristic the agent would apply informally — "the coefficient didn't move much when I added controls" — and shows it is only valid *jointly with the R² movement*. Returns δ*, the ratio of unobservable-to-observable selection that would zero out the effect; δ* > 1 is the conventional survival threshold. | **EASY.** Closed form: β* ≈ β̃ − δ(β̇ − β̃)(R_max − R̃)/(R̃ − Ṙ); solve for δ at β*=0. | Refuse if: R̃ ≈ Ṙ (controls explained nothing — δ* explodes, meaningless); R_max not supplied and no defensible default (the answer is extremely sensitive to it — print the δ*(R_max) curve instead of a scalar); the added controls include a mediator (then coefficient movement is a *mediation* signal, not a confounding signal); β̇ and β̃ have opposite signs. |
| 14 | **Synthetic control + placebo permutation inference** | "one thing changed and I have a bunch of things that didn't"; "build me a counterfactual for this unit"; "what would this metric have done without the change"; "single treated unit, many candidate controls"; "no obvious matched control, can I make one" | Panel CSV: outcome by unit × period, one treated unit, ≥ 5 (ideally ≥ 15) donors, ≥ 8 (ideally ≥ 20) pre-periods. **MUST-CONSTRUCT-DATA** | Beats picking a single "similar" comparison unit by hand — which is what an unaided agent does, and which embeds an unexamined choice. Produces a weighted donor combination with explicit, sparse, interpretable weights and, crucially, a **permutation-based inference procedure valid at n=1 treated unit**, where no asymptotic SE exists. | **MODERATE.** The weights solve a simplex-constrained least squares: minimize ‖Y₁,pre − Y₀,pre w‖² s.t. w ≥ 0, Σw = 1. No QP library needed — projected gradient descent or Frank–Wolfe converges reliably at these sizes; exponentiated-gradient is another clean option. Placebo inference = re-run for every donor and rank the post/pre RMSPE ratio. `random` not even required (permutation is exhaustive over donors). | Refuse if: pre-treatment fit RMSPE is large relative to the estimated effect (the synthetic unit does not track the treated unit — the estimate is fit error, not effect); the treated unit is outside the convex hull of donors on pre-period outcomes (extrapolation — route to augmented SCM or refuse); fewer than ~8 pre-periods; a donor also received the treatment or a spillover; number of donors < ~5 (permutation p-value cannot go below 1/(J+1) — with 4 donors the minimum achievable p is 0.20, so say "no test is possible"). |
| 15 | **Randomization / permutation inference for DiD with few clusters** (Conley–Taber, MacKinnon–Webb) | "I only have a handful of teams/regions, is my p-value real"; "small number of groups, clustered standard errors look wrong"; "one treated cluster"; "exact test for a before/after with few units" | The same panel as the DiD, plus a cluster identifier. Works with as few as 1 treated + ~5 control clusters. **DATAFILE** | Cluster-robust SEs **severely over-reject** with few treated clusters, and the wild bootstrap can go either way. Bertrand–Duflo–Mullainathan showed that ignoring serial correlation gives ~45% false-positive rates on placebo laws. Permutation inference gives exact finite-sample validity under the sharp null. Directly relevant: the agent's "we rolled it out to 3 teams" case. | **EASY.** Enumerate or sample cluster-level treatment reassignments, recompute the statistic, rank. Uses only `itertools` and `random`. Exhaustive enumeration is feasible whenever C(n, k) is small — the exact regime this tool targets. | Refuse if: only 1 control cluster (the permutation distribution has 2 points); clusters differ so systematically that exchangeability is implausible (state the assumption, require acknowledgement); the achievable minimum p-value exceeds the requested α (print "no significant result is attainable with this many clusters" — a real and useful answer). |
| 16 | **Rosenbaum bounds (Γ) for matched pairs** | "how much hidden bias would overturn my matched comparison"; "sensitivity analysis after matching"; "my pairs look balanced on what I measured — what about what I didn't"; "how robust is this matched result" | Matched-pair outcome differences, or discordant-pair counts for binary outcomes. **DATAFILE** | The natural companion to any matching analysis, and the only sensitivity tool with an *exact* finite-sample interpretation. Returns Γ*, the odds-ratio of differential treatment assignment within a pair that would destroy significance. Complements the E-value (which is on the effect scale) by working on the *assignment* scale. | **EASY.** Under Γ, each pair's sign is Bernoulli with p⁺ = Γ/(1+Γ); signed-rank statistic has E = p⁺Σrᵢ and Var = p⁺(1−p⁺)Σrᵢ², then a normal approximation (exact via DP for n < ~25). Requires `NormalDist` only. | Refuse if: the matching was not 1:1 (formulas differ for variable ratio); pairs were matched on a post-treatment variable; n < 6 pairs (normal approximation invalid *and* exact test has no power); the unmatched analysis was not significant at Γ=1 (Γ* is undefined — say so). |
| 17 | **Negative control outcome / falsification test** | "how do I check whether my comparison is contaminated"; "is there residual confounding I can detect"; "sanity check this causal claim"; "test whether the effect shows up where it shouldn't"; "placebo outcome test" | The same design applied to an outcome the treatment provably cannot affect, or a pre-treatment period. **DATAFILE / MUST-CONSTRUCT-DATA** | A *detector*, not an estimator, and unusually cheap for an agent — it can very often construct one (a metric on an untouched subsystem, a pre-deploy window, a different endpoint). Finding a non-null "effect" on a negative control is decisive evidence of residual confounding, and it is the kind of check an unaided agent essentially never runs. | **EASY.** It's the primary analysis re-run on different columns. The tool's value is the *protocol* and the interpretation gate, not new math. | Refuse if: the agent cannot articulate *why* the negative control is causally unaffected by the treatment (the whole validity rests on this a-priori claim — make them type it); the negative control is not plausibly affected by the same confounder (then a null is uninformative, not reassuring); multiple negative controls tested and only the passing ones reported. |
| 18 | **IV: Wald / 2SLS + first-stage F + Anderson–Rubin CI** | "I have something that nudged adoption but shouldn't affect the outcome directly"; "partial compliance with the rollout"; "encouragement design"; "instrument for the treatment"; "natural experiment with imperfect take-up" | Unit-level CSV with instrument, treatment, outcome (+ covariates). **MUST-CONSTRUCT-DATA** — agents rarely have a valid instrument. | When a real instrument exists, it identifies a LATE under confounding that no adjustment method can handle. The key value-add over a naive 2SLS is the **weak-instrument discipline**: report the first-stage F / effective F, and report Anderson–Rubin confidence sets, which are valid *regardless* of instrument strength. With one instrument, AR is the recommended default. | **MODERATE.** 2SLS = two OLS passes. First-stage F is a standard test. AR CI is obtained by grid-inverting a 1-D F test over candidate β₀ — trivially easy in pure Python and far more robust than the delta-method SE. Effective F (Montiel Olea–Pflueger) is more involved; the simple F with a stated caveat is acceptable. | Refuse if: first-stage F < 10 **and** the agent asked for a point estimate + conventional SE (print only the AR set); the exclusion restriction was not stated in words (require it); the instrument is a covariate the agent also wants to control for elsewhere (contradiction); AR set is unbounded or empty (report as such — that is the honest result under weak identification); the monotonicity/no-defiers assumption is implausible. |
| 19 | **Balke–Pearl sharp IV bounds (binary)** | "I have an instrument but I don't believe the extra assumptions"; "bound the effect using the encouragement without assuming monotonicity"; "partial identification with an instrument"; "tightest possible range from a natural experiment" | An 8-cell joint distribution over binary (Z, X, Y): counts or proportions. **INLINE** (8 numbers) | Provably **tight** — narrower than Manski/Robins bounds — and requires no monotonicity, no homogeneity, no distributional assumption. The perfect complement to #18 for an agent that has an instrument but cannot defend the LATE assumptions. Extremely cheap given the input. | **EASY.** Closed-form: max over 4 lower expressions, min over 4 upper expressions, all linear in the 8 cell probabilities. | Refuse if: any variable is non-binary (the closed form does not apply; a general LP/symbolic-bound approach is out of scope); the instrument is not independent of the confounder (bounds are then invalid, not merely wide); cell counts are so small that the empirical joint has structural zeros driving the bounds. |
| 20 | **Front-door adjustment** | "I can't measure the confounder but I know the mechanism"; "the effect goes through a step I can observe"; "identification through a mediator"; "confounded treatment but a clean intermediate variable" | Joint distribution over (X, Z, Y) or a unit-level CSV with the mediator. **DATAFILE** | The only identification strategy that recovers a causal effect with an **unmeasured** treatment–outcome confounder and no instrument. Rare in practice but decisive when it applies, and an agent will not think of it unaided. P(y|do(x)) = Σ_z P(z|x) Σ_x' P(y|x',z)P(x'). | **EASY** for discrete variables (a sum over a small table). **MODERATE** for continuous (two regressions and a composition). | Refuse if: the mediator does not intercept *all* directed paths X→Y (any unmediated direct effect breaks it — this is the assumption that fails in practice, and the tool must interrogate it); there is a confounder of Z and Y; Z is measured with error (front-door is notably fragile to this); the agent has not supplied a DAG (require #2 first). |
| 21 | **Nearest-neighbour / caliper matching with bias correction** | "find me comparable units"; "pair up similar cases before and after"; "match on baseline characteristics"; "like-for-like comparison" | Unit-level CSV with covariates + binary treatment. **DATAFILE** | More transparent than weighting for small n, and produces the matched pairs that #16 (Rosenbaum bounds) consumes. Bias correction for inexact matches (Abadie–Imbens) removes the residual covariate imbalance. | **MODERATE.** Greedy nearest-neighbour on Mahalanobis distance needs a p×p covariance inverse (Cholesky, p small) — fine. Optimal matching needs a min-cost-flow solver — out of scope; greedy with caliper is the correct scope. | Refuse if: > 20% of treated units find no match within the caliper (the estimand silently changed — report which units were dropped and what they look like); covariates include post-treatment variables; matching without replacement on a small donor pool exhausts good matches (report the last-matched distances); no balance table requested/inspected. |
| 22 | **Regression discontinuity (local linear + McCrary density test)** | "there's a threshold and things on either side got different treatment"; "cutoff rule assigned the change"; "units just above and below a line"; "score-based eligibility for the rollout" | Unit-level CSV: running variable, outcome, cutoff. Needs meaningful density near the cutoff. **MUST-CONSTRUCT-DATA** | Near-experimental identification when a threshold rule exists (rate limits, size tiers, score cutoffs, canary percentage bands). Beats a naive above/below comparison by localizing and by explicitly testing for **manipulation** of the running variable — the assumption that actually fails in engineering settings, where thresholds are gameable. | **MODERATE.** Local linear with triangular kernel on each side = weighted OLS, easy. IK / CCT optimal bandwidth needs pilot higher-order fits (moderate); a defensible fallback is to report the estimate across a bandwidth grid and refuse if the sign flips. Robust bias-corrected CIs are moderate. McCrary density test is a local linear density fit — moderate; a binomial test on counts in a window either side is a cheap, honest substitute. | Refuse if: the density test rejects (manipulation of the running variable → RD invalid, full stop); effective n within the bandwidth < ~30 per side; the estimate changes sign across a reasonable bandwidth range; other treatments change at the same cutoff (compound discontinuity); the running variable is discrete with few mass points near the cutoff. |
| 23 | **AIPW / doubly robust ATE** | "combine adjustment and weighting"; "I'm not sure which model is right"; "most reliable adjusted comparison I can get"; "robust estimate of the average effect" | Unit-level CSV: covariates, binary treatment, outcome. n ≥ ~100. **DATAFILE** | Consistent if *either* the outcome model or the propensity model is correct, rather than requiring both. Materially better default than plain regression adjustment or plain IPW. Influence-function SEs are well-behaved. | **MODERATE.** One logistic (IRLS) + two OLS fits + the AIPW combination; SE from the influence function is a closed-form variance of a per-unit score. Cross-fitting is unnecessary for parametric nuisances at these n. | Refuse if: positivity fails (same gate as #9); n < ~100 (double robustness is asymptotic and gives no small-sample protection); the agent wants a "trust me it's robust" headline without seeing the propensity distribution. |
| 24 | **Synthetic difference-in-differences** | "combine synthetic control weights with a difference-in-differences"; "my synthetic control doesn't fit the pre-period well"; "panel with several treated units at once"; "robust panel estimate" | Panel CSV, treated set + donors, long pre-period. **MUST-CONSTRUCT-DATA** | Doubly robust across unit weights and time weights: consistent if either correctly absorbs the confounding. More robust than SC (which needs near-exact pre-fit) and than DiD (which needs parallel trends). Handles multiple treated units, unlike vanilla SC. | **MODERATE–HARD.** Two regularized simplex-constrained weight problems (unit and time) plus a weighted two-way regression. Same projected-gradient machinery as #14, run twice, with an added ridge penalty and an intercept-shifted objective. Inference via jackknife or placebo. Real but non-trivial implementation cost. | Refuse if: fewer than ~2 treated units and the agent wants the jackknife SE (undefined — route to placebo inference); pre-period shorter than the post-period; donors that are themselves treated. |

---

## 3. Recent advances (~2015–2026)

### 3.1 The staggered-DiD correction literature — the biggest change in the field

This is the one place where the "smart agent guessing unaided" is not merely imprecise but **reliably
wrong**, which makes it high-value for the module.

- **Goodman-Bacon (2021, *Journal of Econometrics*)** — decomposes the two-way fixed effects DiD estimator
  into a weighted average of all constituent 2×2 comparisons. Some of these use **already-treated units as
  controls**, and those receive weights that can be negative. Under treatment-effect heterogeneity over
  time, TWFE can be biased and even sign-flipped.
  <https://cdn.vanderbilt.edu/vu-my/wp-content/uploads/sites/2318/2019/07/29170757/ddtiming_7_29_2019.pdf>
- **de Chaisemartin & D'Haultfœuille (2020, *AER*; survey 2023; dynamic estimators 2024)** — showed that
  TWFE identifies a convex combination of ATEs only under effectively constant treatment effects; proposed
  estimators using "switchers vs. stayers" with strictly positive weights, and extended to non-binary,
  non-absorbing treatments that can rise and fall.
  Survey: <https://arxiv.org/pdf/2112.04565> · NBER: <https://www.nber.org/system/files/working_papers/w30564/w30564.pdf>
- **Callaway & Sant'Anna (2021, *Journal of Econometrics*)** — the group-time ATT(g,t) framework: estimate
  a clean 2×2 for each (adoption cohort, period) using never-treated or not-yet-treated comparisons, then
  aggregate with transparent weights (by calendar time, by event time, overall). Offers outcome-regression,
  IPW, and doubly-robust variants. **This is the reference implementation target for row #11.**
  <https://www.sciencedirect.com/science/article/abs/pii/S0304407620303948> ·
  <https://bcallaway11.github.io/did/>
- **Sun & Abraham (2021, *Journal of Econometrics*)** — interaction-weighted event-study estimator. Showed
  that in a standard event-study regression, the coefficient on a given lead/lag is contaminated by effects
  from *other* relative periods, so **apparent pre-trends can be manufactured purely by treatment-effect
  heterogeneity**. Important because it undercuts the pre-trend test the agent would naively rely on.
  <https://arxiv.org/abs/1804.05785>
- **Borusyak, Jaravel & Spiess (2024)** — "Revisiting Event-Study Designs: Robust and Efficient
  Estimation". Imputation approach: fit unit and period effects on untreated observations only, impute
  counterfactuals, average the residuals. Efficient under homoskedasticity and conceptually the simplest of
  the modern estimators to implement. <https://arxiv.org/abs/2108.12419>
- **Roth, Sant'Anna, Bilinski & Poe (2023, *Journal of Econometrics*)** — "What's Trending in
  Difference-in-Differences?", the canonical synthesis of all of the above. Best single entry point.
  <https://arxiv.org/pdf/2201.01194>

### 3.2 Modern sensitivity analysis — the highest-value cluster for a sparse-data agent

- **Ding & VanderWeele (2016, *Epidemiology*)** — "Sensitivity Analysis Without Assumptions". Derived a
  **sharp** bounding factor requiring no assumptions on the unmeasured confounder (not binary, not single,
  interactions allowed). Generalizes and strengthens the Cornfield conditions. <https://arxiv.org/abs/1507.03984>
- **VanderWeele & Ding (2017, *Annals of Internal Medicine*)** — the **E-value**, the single-number
  distillation of the above, plus conversions for risk/rate/odds/hazard ratios and standardized mean
  differences. This is the most deployable causal tool in the entire territory for an agent with three
  numbers. <https://www.acpjournals.org/doi/10.7326/M17-1485> · package paper:
  <https://journals.sagepub.com/doi/10.1177/1536867X20909696>
- **Cinelli & Hazlett (2020, *JRSS-B*)** — "Making Sense of Sensitivity: Extending Omitted Variable Bias".
  The **robustness value**, partial-R² parameterization, and benchmarking against observed covariates,
  computable from standard regression output alone. <https://carloscinelli.com/files/Cinelli%20and%20Hazlett%20(2020)%20-%20Making%20Sense%20of%20Sensitivity.pdf>
- **Rambachan & Roth (2023, *Review of Economic Studies*)** — "A More Credible Approach to Parallel
  Trends". Replaces the binary pre-trend test with a **breakdown value**: how large post-treatment trend
  violations would have to be, relative to observed pre-period violations, to overturn the conclusion.
  <https://scholar.harvard.edu/files/jroth/files/roth_jmp_honestparalleltrends_main.pdf> ·
  <https://github.com/asheshrambachan/HonestDiD>
- **Roth (2022, *AER: Insights*)** — "Pretest with Caution". Pre-trend tests are **underpowered**: linear
  violations detected only 50% of the time can produce bias as large as the estimated effect, and
  conditioning on passing a pretest can *worsen* bias and coverage. This is the empirical justification for
  never letting a tool print "pre-trends passed, therefore identified."
  <https://www.jonathandroth.com/assets/files/roth_pretrends_testing.pdf>
- **Oster (2019, *JBES*)** — "Unobservable Selection and Coefficient Stability". Formalizes the coefficient-
  movement heuristic by tying it to R² movement. <https://www.nber.org/system/files/working_papers/w19054/w19054.pdf>
- **Cinelli, Forney & Pearl (2024, *Sociological Methods & Research*)** — "A Crash Course in Good and Bad
  Controls". The definitive catalog of when conditioning helps (blocks confounding), hurts (blocks the
  causal path, opens a collider path, **amplifies** existing bias), or is neutral. The direct specification
  for row #2's classifier. <https://ftp.cs.ucla.edu/pub/stat_ser/r493-reprint.pdf>

### 3.3 Synthetic control and single-unit inference

- **Arkhangelsky, Athey, Hirshberg, Imbens & Wager (2021, *AER*)** — Synthetic Difference-in-Differences.
  Combines SC unit weights with DiD time weights; doubly robust across the two.
  <https://www.nber.org/system/files/working_papers/w25532/w25532.pdf>
- **Ben-Michael, Feller & Rothstein (2021, *JASA*)** — the Augmented Synthetic Control Method. Uses a ridge
  outcome model to de-bias SC when exact pre-treatment fit is infeasible (equivalently, permits some
  negative donor weights). Directly addresses row #14's main refusal condition. <https://arxiv.org/abs/1811.04170>
- **Chernozhukov, Wüthrich & Zhu (2021, *JASA* 116(536):1849–1864)** — "An Exact and Robust Conformal
  Inference Method for Counterfactual and Synthetic Controls". Permutation-of-residuals inference with
  **exact finite-sample validity** under exchangeable residuals. Notably stdlib-implementable, and the
  right inference procedure for a single treated unit. <https://arxiv.org/abs/1712.09089>
- **Lei & Candès-style refined placebo tests (2024)** — improvements on the standard in-space placebo test
  for the small-donor-pool regime. <https://arxiv.org/abs/2401.07152>
- **Abadie (2021, *JEL*)** — "Using Synthetic Controls: Feasibility, Data Requirements, and Methodological
  Aspects". The authoritative statement of when SC should *not* be used — the source for row #14's refusal
  gates. <https://conference.nber.org/confer/2021/SI2021/Abadie_2021.pdf>

### 3.4 Partial identification and bounds

- **Symbolic/automated bounds**: Balke & Pearl's 1997 linear-programming bounds have been generalized into
  automated symbolic-bound derivation for arbitrary discrete DAGs (`causaloptim`,
  <https://sachsmc.github.io/causaloptim/articles/CausalBoundsMethods.pdf>) and into polynomial-programming
  approaches for general discrete settings. Full automation is out of scope for stdlib, but the *canonical
  binary-IV closed forms* are trivially implementable.
- **Covariate-assisted IV bounds (Gabriel, Sachs et al., 2025, *JRSS-B* 87(5))** — tighter bounds by
  incorporating baseline covariates. <https://academic.oup.com/jrsssb/article/87/5/1508/8151396>
- **Manski & Pepper's MIV/MTS/MTR** remain the practical narrowing toolkit; the key modern caveat is that
  finite-sample bounds using *sample* extrema rather than known logical bounds are invalid
  (<https://arxiv.org/html/2509.01622v1>) — encoded as a refusal condition in row #6.
- **Probabilities of causation** (Tian & Pearl; Li & Pearl 2023) — bounds on PN/PS/PNS combining
  observational and experimental data. <https://proceedings.mlr.press/v206/li23d/li23d.pdf> ·
  <https://arxiv.org/pdf/1301.3898>

### 3.5 Inference with few clusters

- **MacKinnon & Webb (2020, *Journal of Econometrics*)** — randomization inference for DiD with few treated
  clusters; cluster-robust t-tests over-reject severely, and different wild bootstrap variants over- or
  under-reject dramatically.
  <https://www.sciencedirect.com/science/article/abs/pii/S0304407620301445>
- **Conley & Taber (2011)**, **Ferman & Pinto (2019)** placebo inference, and **inference with a single
  treated cluster** (<https://arxiv.org/pdf/2010.04076>) cover the extreme-sparse regime the agent
  frequently occupies.
- Foundational: **Bertrand, Duflo & Mullainathan (2004, *QJE*)** — ignoring serial correlation in DiD
  produced significant "effects" for up to 45% of placebo laws. <https://www.nber.org/papers/w8841>

### 3.6 Proximal causal inference

Tchetgen Tchetgen et al.'s **proximal causal inference** framework (2020–2024) generalizes negative
controls into a full identification strategy using a pair of confounding proxies and a "confounding bridge"
function. Powerful, but requires two valid proxies plus a bridge-function estimation step — see cut list.
Regression-based simplification: <https://arxiv.org/html/2402.00335>

---

## 4. Cut list

Considered and rejected, honestly.

| Rejected | Why |
|---|---|
| **CausalImpact / Bayesian structural time series** (Brodersen et al. 2015) | Needs Kalman filtering + spike-and-slab MCMC + seasonal state components. Implementable in stdlib only at heroic cost, and rows #7 (ITS) and #14 (SC) cover ~90% of the use cases with 5% of the code. |
| **Double machine learning / DML, causal forests, BART, TMLE** | All require flexible ML learners and cross-fitting. Their entire advantage is high-dimensional nuisance estimation, which is exactly the regime the agent is *not* in (low-dimensional, n ≤ few thousand). AIPW with parametric nuisances (#23) captures the honest fraction. |
| **Causal discovery (PC, FCI, GES, LiNGAM, NOTEARS)** | Tempting — "learn the DAG from the data" — but at agent-scale n these are dominated by false discoveries, the output is a Markov-equivalence class rather than a DAG, and faithfulness is untestable. Worse, it would let the agent skip the one step that has real value: *declaring* its causal assumptions. Actively harmful to the module's doctrine. |
| **Proximal causal inference / double negative controls** | Requires two distinct valid proxies for the unmeasured confounder plus bridge-function estimation. An agent will essentially never have this. The *single* negative control **detector** (#17) is retained; the estimator is not. |
| **Marginal structural models / g-formula / g-estimation for time-varying confounding** | Correct answer to a real problem (treatment-confounder feedback over time), but requires a longitudinal panel with repeatedly measured time-varying confounders. Not an input tier the agent occupies. |
| **Matrix completion / interactive fixed effects (Athey et al.; `gsynth`)** | Needs SVD and EM iterations over a matrix; nuclear-norm regularization needs a soft-thresholded SVD. Pure-Python SVD is doable but slow and numerically delicate, and SDID (#24) covers the same territory more cheaply. |
| **Full Rambachan–Roth fixed-length CIs / moment-inequality inference** | Requires LP over a polyhedral identified set plus conditional/hybrid inference. Only the simplified relative-magnitudes breakdown value (#10) is in scope, and the tool must label it as such. |
| **Mediation analysis (natural direct/indirect effects, Imai–Keele–Yamamoto sensitivity)** | Answers "how did it work", not "did it work". A defensible separate territory; here it would dilute the answer to the agent's actual question, and cross-world assumptions are hard to communicate. |
| **Regression kink design, difference-in-discontinuities, fuzzy RD** | Each needs a rarer setup than plain RD, which itself is already MUST-CONSTRUCT-DATA and near the bottom of the ranked list. Marginal value not worth the surface area. |
| **Lee bounds for attrition/selection** | Genuinely cheap (trimming bounds, closed form) and stdlib-easy. Cut only because it requires differential attrition between arms — a narrow situation for an agent — but it is the strongest candidate for later re-inclusion. |
| **Principal stratification** | Beyond the binary-IV/LATE case, requires modeling latent strata; identification is fragile and communication is worse. |
| **Interference / spillover estimators (network exposure mappings, cluster randomization)** | Needs an observed interference network. Retained instead as a **SUTVA violation check** inside the DiD/SC refusal gates ("did control units get affected?"), which is where the value actually is. |
| **Granger causality** | Not causal in the counterfactual sense; predictive-precedence only. Belongs to the time-series territory, and shipping it under a "causal inference" heading would invite exactly the misuse the module exists to prevent. |
| **Instrumental variables with many instruments (JIVE, LIML, many-IV corrections)** | An agent that has one instrument is already lucky; one that has forty is fictional. |
| **Structural equation modeling / path analysis with latent variables** | Requires covariance-structure fitting and identification checks that are effectively a separate library, and the linear-Gaussian assumptions are rarely defensible. |
| **Doubly robust DiD with covariates (Sant'Anna & Zhao)** | Good method; the marginal gain over unconditional CS (#11) at agent-scale n does not justify the extra propensity machinery in v1. Note as a v2 upgrade path for row #11. |

---

## 5. Cross-territory overlaps

Models likely to appear in other territories, possibly under another name:

| Here | Likely also in | Note for de-duplication |
|---|---|---|
| OLS / WLS engine, robust and clustered SEs, Newey–West HAC | **Regression** territory | Every estimator here (#3, #7, #11, #18, #22, #23) sits on the same OLS core. Build it once, in the regression territory, and have causal tools import it. |
| Logistic regression via IRLS | **Regression / GLM** territory | Shared by #9, #21, #23. |
| Permutation / randomization tests, bootstrap | **Resampling & inference** territory | #14 (placebo), #15 (randomization inference), #9 (bootstrap SE) all consume it. The *design-based* framing (permute treatment assignment, not observations) is the causal-specific twist and should be documented here. |
| Student-t, F, chi-square CDFs (regularized incomplete beta/gamma) | **Distributions** substrate | Already flagged in RESEARCH.md §0.7. Blocking dependency for #3, #7, #18. |
| Power / minimum detectable effect | **Experimental design** territory | Strong cross-reference: an agent's before/after often has *no power* to detect the claimed effect, which should be checked before any causal machinery runs. Roth (2022) is the causal-side citation for why. |
| Regression to the mean (#5) | **Measurement / reliability** territory | Same mathematics as attenuation and test–retest reliability; will be described there as a measurement phenomenon rather than a confounding one. Keep one implementation, two entry points. |
| Changepoint detection / CUSUM / structural breaks | **Time series** territory | Answers "*when* did it change", not "*did X cause* the change". ITS (#7) requires the changepoint to be **specified a priori** by the intervention date; using a *detected* changepoint as the intervention date invalidates the inference. This is a genuine misuse risk and should be an explicit cross-territory warning. |
| Overlap / positivity diagnostics (#9) | **ML validation / covariate shift** territory | Same idea as train-test distribution shift and propensity-based drift detection. |
| Multiple comparisons across placebo tests and negative controls | **Multiple testing** territory | Running a battery of falsification tests (#17) and reporting the best one is p-hacking; the correction belongs to that territory. |
| E-value / robustness value | **Decision analysis** territory | Both are "breakdown value" objects — the threshold at which a decision flips. Same shape as break-even analysis and value-of-information. |
| Meta-analysis, heterogeneity (I², τ²) | **Evidence synthesis** territory | Mathur & VanderWeele's meta-analytic E-values live at the boundary. |
| Anderson–Rubin CI (#18) | **Inference** territory | An instance of the general "invert a test to get a confidence set" pattern, which is worth generalizing (it also gives exact CIs for binomial proportions, etc.). |

---

## 6. Sources

**Staggered DiD**
- Goodman-Bacon, "Difference-in-Differences with Variation in Treatment Timing" — <https://cdn.vanderbilt.edu/vu-my/wp-content/uploads/sites/2318/2019/07/29170757/ddtiming_7_29_2019.pdf>
- Callaway & Sant'Anna, "Difference-in-Differences with Multiple Time Periods", *JoE* 2021 — <https://www.sciencedirect.com/science/article/abs/pii/S0304407620303948>; package docs <https://bcallaway11.github.io/did/>; vignette <https://cran.r-project.org/web/packages/did/vignettes/multi-period-did.html>
- Sun & Abraham, "Estimating Dynamic Treatment Effects in Event Studies with Heterogeneous Treatment Effects" — <https://arxiv.org/abs/1804.05785>; code <https://github.com/lsun20/EventStudyInteract>
- de Chaisemartin & D'Haultfœuille, "Two-Way Fixed Effects and DiD with Heterogeneous Treatment Effects: A Survey" — <https://arxiv.org/pdf/2112.04565>; NBER w30564 <https://www.nber.org/system/files/working_papers/w30564/w30564.pdf>; original <https://arxiv.org/pdf/1803.08807>; software <https://github.com/chaisemartinPackages/did_multiplegt>
- Borusyak, Jaravel & Spiess, "Revisiting Event Study Designs: Robust and Efficient Estimation" — <https://arxiv.org/abs/2108.12419>
- Roth, Sant'Anna, Bilinski & Poe, "What's Trending in Difference-in-Differences?" — <https://arxiv.org/pdf/2201.01194>
- Bertrand, Duflo & Mullainathan, "How Much Should We Trust Differences-in-Differences Estimates?" — <https://www.nber.org/papers/w8841>

**Sensitivity analysis**
- Ding & VanderWeele, "Sensitivity Analysis Without Assumptions", *Epidemiology* 2016 — <https://arxiv.org/abs/1507.03984>
- VanderWeele & Ding, "Sensitivity Analysis in Observational Research: Introducing the E-Value", *Ann Intern Med* 2017 — <https://www.acpjournals.org/doi/10.7326/M17-1485>
- Linden, Mathur & VanderWeele, "Conducting sensitivity analysis ... the evalue package" — <https://journals.sagepub.com/doi/10.1177/1536867X20909696>
- Cinelli & Hazlett, "Making Sense of Sensitivity: Extending Omitted Variable Bias", *JRSS-B* 2020 — <https://carloscinelli.com/files/Cinelli%20and%20Hazlett%20(2020)%20-%20Making%20Sense%20of%20Sensitivity.pdf>; `sensemakr` <https://cran.r-project.org/web/packages/sensemakr/sensemakr.pdf>
- Oster, "Unobservable Selection and Coefficient Stability" — <https://www.nber.org/system/files/working_papers/w19054/w19054.pdf>
- Rambachan & Roth, "A More Credible Approach to Parallel Trends" — <https://scholar.harvard.edu/files/jroth/files/roth_jmp_honestparalleltrends_main.pdf>; <https://github.com/asheshrambachan/HonestDiD>
- Roth, "Pretest with Caution", *AER: Insights* 2022 — <https://www.jonathandroth.com/assets/files/roth_pretrends_testing.pdf>
- Rosenbaum, "Sensitivity Analysis in Observational Studies" — <http://www-stat.wharton.upenn.edu/~rosenbap/BehStatSen.pdf>; `rbounds` <https://cran.r-project.org/web/packages/rbounds/rbounds.pdf>
- Generalized Cornfield conditions for the risk difference — <https://arxiv.org/pdf/1404.7175>
- Sharp bounds based on Ding–VanderWeele sensitivity parameters — <https://www.degruyter.com/document/doi/10.1515/jci-2023-0019/html>

**Graphs and identification**
- Cinelli, Forney & Pearl, "A Crash Course in Good and Bad Controls", *SMR* 2024 — <https://ftp.cs.ucla.edu/pub/stat_ser/r493-reprint.pdf>; journal <https://journals.sagepub.com/doi/full/10.1177/00491241221099552>
- Textor et al., "Drawing and Analyzing Causal DAGs with DAGitty" — <https://arxiv.org/pdf/1508.04633>; manual <https://www.dagitty.net/manual-3.x.pdf>
- Pearl, "Invited Commentary: Understanding Bias Amplification" — <https://ftp.cs.ucla.edu/pub/stat_ser/r386.pdf>
- Front-door primer with worked code — <https://arelbundock.com/posts/frontdoor/>
- Back-door / front-door / do-calculus lecture notes — <https://cse.sc.edu/~javidian/Notes_Presentations/BackFrontDoor.pdf>

**Bounds and partial identification**
- Balke & Pearl bounds, method exposition — <https://sachsmc.github.io/causaloptim/articles/CausalBoundsMethods.pdf>
- Covariate-assisted IV bounds, *JRSS-B* 2025 — <https://academic.oup.com/jrsssb/article/87/5/1508/8151396>
- Manski & Pepper, "Monotone Instrumental Variables" — <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=226634>
- Molinari, "Microeconometrics with Partial Identification" — <https://arxiv.org/pdf/2004.11751>
- Finite-sample non-parametric bounds (critique of sample-extrema bounds) — <https://arxiv.org/html/2509.01622v1>
- Pearl, "Probabilities of Causation: Three Counterfactual Interpretations and Their Identification" — <https://arxiv.org/pdf/1301.3898>
- Li & Pearl, "Probabilities of Causation: Role of Observational Data" — <https://proceedings.mlr.press/v206/li23d/li23d.pdf>
- Partial identification tutorial with Python — <https://carlos-mendez.org/post/python_partial_identification/>

**Panel / synthetic control**
- Arkhangelsky, Athey, Hirshberg, Imbens & Wager, "Synthetic Difference-in-Differences", *AER* 2021 — <https://www.nber.org/system/files/working_papers/w25532/w25532.pdf>
- Ben-Michael, Feller & Rothstein, "The Augmented Synthetic Control Method", *JASA* 2021 — <https://arxiv.org/abs/1811.04170>
- Chernozhukov, Wüthrich & Zhu, "An Exact and Robust Conformal Inference Method for Counterfactual and Synthetic Controls", *JASA* 116(536):1849–1864, 2021 — <https://arxiv.org/abs/1712.09089>
- Abadie, "Using Synthetic Controls: Feasibility, Data Requirements, and Methodological Aspects" — <https://conference.nber.org/confer/2021/SI2021/Abadie_2021.pdf>
- Lei & Candès-style refined placebo tests — <https://arxiv.org/abs/2401.07152>
- Placebo tests for synthetic controls — <https://mpra.ub.uni-muenchen.de/78079/1/MPRA_paper_78079.pdf>
- Athey & Imbens, "Identification and Inference in Nonlinear Difference-in-Differences Models" (changes-in-changes) — <https://scholar.harvard.edu/files/imbens/files/identification_and_inference_in_nonlinear_difference-in-differences_models.pdf>

**Few clusters / design-based inference**
- MacKinnon & Webb, "Randomization inference for DiD with few treated clusters", *JoE* 2020 — <https://www.sciencedirect.com/science/article/abs/pii/S0304407620301445>
- "Inference with a single treated cluster" — <https://arxiv.org/pdf/2010.04076>
- Ferman & Pinto, "Placebo inference on treatment effects when the number of clusters is small" — <https://www.sciencedirect.com/science/article/abs/pii/S0304407619300661>

**Propensity scores / weighting**
- Li, Morgan & Zaslavsky overlap weights, "Addressing Extreme Propensity Scores via the Overlap Weights" — <https://academic.oup.com/aje/article/188/1/250/5090958>
- Matsouaka et al., "Causal inference in the absence of positivity: The role of overlap weights" — <https://onlinelibrary.wiley.com/doi/10.1002/bimj.202300156>
- "A tutorial for propensity score weighting methods under violations of the positivity assumption" — <https://arxiv.org/pdf/2511.10077>
- `PSweight`: An R Package for Propensity Score Weighting Analysis — <https://journal.r-project.org/articles/RJ-2022-011/>

**RDD, IV, ITS**
- Imbens & Kalyanaraman, "Optimal Bandwidth Choice for the RD Estimator" — <https://www.nber.org/papers/w14726>
- Andrews, Stock & Sun, "Weak Instruments in IV Regression: Theory and Practice" — <https://scholar.harvard.edu/files/stock/files/andrews_stock_sun_wirev_011119.pdf>
- Montiel Olea & Pflueger effective F / robust F as weak-IV test — <https://www.sciencedirect.com/science/article/pii/S0304407625000053>
- "Interpretation of coefficients in segmented regression for interrupted time series analyses" — <https://pmc.ncbi.nlm.nih.gov/articles/PMC10925407/>
- "A common error in the segmented regression parameterization of ITS analyses", *IJE* — <https://academic.oup.com/ije/article/50/3/1011/5937253>
- Multiple-group controlled ITS: Newey–West vs Prais–Winsten simulation study — <https://arxiv.org/pdf/2603.24814>

**Negative controls / proximal**
- Regression-based proximal causal inference — <https://arxiv.org/html/2402.00335>; *AJE* <https://pmc.ncbi.nlm.nih.gov/articles/PMC12501610/>
- Negative control exposures: identifiability and use — <https://www.medrxiv.org/content/10.1101/2022.05.25.22275304.full.pdf>

**General**
- Ding, "A First Course in Causal Inference" — <https://arxiv.org/pdf/2305.18793>
- "Embracing Uncertainty: The Value of Partial Identification in Public Health and Clinical Research" — <https://pmc.ncbi.nlm.nih.gov/articles/PMC10799552/>
