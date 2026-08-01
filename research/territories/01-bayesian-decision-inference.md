# Territory 01 — Bayesian Inference and Decision Theory Under Sparse Data

Research pass for the Intelligence Module. Scope: conjugate updating, reference and weakly
informative priors, small-sample posterior inference, hierarchical partial pooling with few
groups, Bayes factors and posterior odds, loss functions and Bayes-optimal actions, decision
trees with expected utility, prior robustness, and approximate inference feasible in pure
Python 3 stdlib (grid, Laplace, importance sampling, Metropolis, slice sampling).

**Contents**
1. [Territory summary](#1-territory-summary)
2. [Ranked model table](#2-ranked-model-table)
3. [Recent advances](#3-recent-advances-last-10-years)
4. [Cut list](#4-cut-list)
5. [Cross-territory overlaps](#5-cross-territory-overlaps)
6. [Sources](#6-sources)

Appendix A: [Empirical stdlib feasibility measurements](#appendix-a--measured-stdlib-feasibility)
Appendix B: [Numerics inventory](#appendix-b--numerics-inventory-what-the-territory-needs-from-the-math-layer)

---

## 1. Territory summary

This territory is the only one in the library that answers an agent's actual question. Every
other statistical tradition answers "would this data be surprising if nothing were going on";
an agent asking *is this difference real*, *should I run one more test*, *which option do I
pick* needs a probability over the world and a decision rule, and only Bayes supplies both in
one object. Its second property matters more for agents than for scientists: **it degrades
gracefully to n = 0**. A conjugate posterior at n = 3 is not a broken t-test — it is a wide,
honest, correctly-shaped distribution, whereas the frequentist machinery either refuses,
emits a nonsense interval, or (worse) emits a plausible-looking one. Third, it converts the
agent's own prose beliefs into a legitimate input: an LLM writing "I'd guess around 20%,
surprised above 40%" is doing prior elicitation, and there is now peer-reviewed evidence that
LLM-elicited priors beat both uninformative defaults and in-context learning at low n
([AutoElicit](https://arxiv.org/abs/2411.17284)). Fourth, the territory carries its own
falsifier — prior sensitivity analysis — which is precisely the "refuse to print a number"
mechanism the project's doctrine demands, because the honest answer to most sparse-data
questions is *your prior is doing the work*. Fifth and least obviously, almost all of it is
**closed form or one-dimensional quadrature**, so the stdlib constraint costs far less here
than it would in a regression- or ML-flavoured territory: the pure-Python tax is paid mostly
in the two special functions (regularized incomplete beta and gamma) that the project has
already scoped.

The territory's characteristic failure — the thing the tool must police — is that a Bayesian
answer *always* returns a number. There is no `p > 0.05` to hide behind. A posterior computed
from 2 observations and a prior invented on the spot looks identical in output format to one
computed from 2,000. The gate is therefore not "did the computation converge" but "how much
of this answer came from the data", and every row below carries that obligation.

---

## 2. Ranked model table

Ranking weights: (frequency an agent hits the predicament) × (margin over unaided guessing) ×
(stdlib feasibility) × (robustness of the answer at genuinely small n).

Input tiers: **INLINE** = a handful of numbers/beliefs as CLI flags. **DATAFILE** = a small
file the agent already has. **MUST-CONSTRUCT-DATA** = the agent has to go generate observations
(run the benchmark 30×, sample the logs) before the model is usable.

---

### Tier A — the workhorses (fire constantly, huge margin over guessing, trivially feasible)

| # | Model / method | SITUATION (retrieval phrasings) | Minimum viable inputs | Beats what | Stdlib feasibility | Refuse-to-print failure modes |
|---|---|---|---|---|---|---|
| 1 | **Beta-Binomial conjugate posterior** (incl. zero-event / rule-of-three case) | "3 of 5 tests passed — what's the real pass rate?" · "it worked 7 out of 8 times, how confident should I be?" · "zero failures in 40 runs, does that mean it never fails?" · "what's my success probability and how wide is the uncertainty?" · "how flaky is this test really" | `--successes k --trials n [--prior jeffreys\|uniform\|a,b]`. **INLINE** | The point estimate `k/n`. At n=5, `3/5 = 60%` has a 95% credible interval of roughly **[23%, 88%]** — the agent's unaided instinct is to treat 60% as a fact. Zero-event case: `0/40 → 0%` is the naive answer and is catastrophically wrong; Jeffreys gives a 95% upper bound ≈ 0.088, within a whisker of the rule of three (3/40 = 0.075) | **EASY.** Posterior is analytic. Interval needs regularized incomplete beta `I_x(a,b)` plus bisection for its inverse. Verified exact to 1e-16 against published values (Appendix A) | Trials not exchangeable (all 40 runs hit the same cached path; failures share one root cause) · outcome defined post hoc after seeing the data · n counted from a filtered/selected subset · "trials" that are actually one trial repeated |
| 2 | **Two-group Bayesian proportion comparison** — P(A>B), **expected loss**, uplift posterior | "is variant B actually better or is this noise?" · "model A got 7/10, model B got 5/10 — is that a real difference?" · "which of these two configs should I ship?" · "did my fix actually reduce the error rate?" · "A/B test with tiny samples" | `--a-succ --a-trials --b-succ --b-trials [--epsilon 0.002]` where ε is the **threshold of caring** in the metric's own units. **INLINE** | Chi-square/Fisher, which on 7/10 vs 5/10 returns p ≈ 0.65 and tells the agent nothing actionable; and the agent's eyeball, which reads 70% vs 50% as "B is worse". Returns **P(A>B) = 0.79** *and*, more importantly, **expected loss** `E[max(λ_B − λ_A, 0)] = 0.014` — the expected uplift forfeited by choosing A if you're wrong. Expected loss dominates P(best) as a stopping rule because it is **magnitude-aware**: P(best) scores a 0.01% miss and a 5% miss identically (Stucchio/VWO) | **EASY.** Exact closed form: Evan Miller / Cook's finite series for P(X>Y) with X~Beta(a,b), Y~Beta(c,d) — `min(a,c)` terms, evaluated in logs via `lgamma` to avoid overflow; microseconds, machine precision (verified vs 200k-draw Monte Carlo, Appendix A). Expected loss and the 3-arm case have matching closed forms; ≥4 arms fall back to `random.betavariate` MC | Non-randomised assignment (B ran later, on warmer cache, on different inputs) — an observational comparison masquerading as an experiment · **peeking: Bayesian A/B is *not* immune to optional stopping** in the sense agents assume — the posterior quantity is coherent, but the *rate at which the ε-threshold rule declares a winner* is affected, so any error-rate claim must be simulated, not asserted · outcomes not binary (truncated continuous) · no ε supplied → report the full uplift posterior and refuse the ship/no-ship verdict |
| 3 | **Normal conjugate with unknown variance (NIG) → Student-t posterior + Student-t posterior predictive** | "5 benchmark runs averaging 120 ms — is that slower than the 100 ms baseline?" · "how much do I trust this mean from a handful of measurements?" · "what latency should I expect on the next request?" · "small sample, don't know the spread" | `--data 118,124,119,131,108` or `--n --mean --sd`, optional `--ref 100`. **INLINE or DATAFILE** | Two things at once. (a) Reporting `mean ± sd/√n` with a normal quantile, which at n=5 is ~25% too narrow. (b) The much bigger error: quoting the **credible interval on the mean** when the agent asked what the **next run** will do. At n=5, mean interval ≈ ±13 ms, predictive interval ≈ ±34 ms. Agents conflate these constantly | **MODERATE.** Posterior for μ is `t_{2a_n}`; predictive is `t` with an inflated scale. Needs the t CDF/quantile, i.e. regularized incomplete beta + inverse. Reference prior `p(μ,σ) ∝ 1/σ` reproduces the classic t interval numerically while licensing a probability statement | n < 3 under the reference prior (posterior for σ improper at n ≤ 2 — must demand an explicit prior or refuse) · visible outliers or heavy tails (switch to a t-likelihood, which needs MCMC — row 14) · time trend / autocorrelation in the runs (warm-up effects make the runs non-exchangeable — refuse, this is the single most common violation in benchmark data) |
| 4 | **Bayes action under an explicit loss function** (decision table, expected utility, asymmetric-loss point estimates, decision-flip threshold) | "which option should I pick?" · "the downside of being wrong isn't symmetric" · "should I roll back or wait?" · "how confident would I have to be to justify doing X?" · "cost of a false positive is way worse than a false negative here" · **"what timeout / retry budget / buffer size should I set?"** | `--actions ship,rollback --states broken,fine --payoffs ...` plus state probabilities (from a prior row's posterior, or elicited); **or** a posterior plus `--loss squared\|abs\|linex --a\|pinball --tau\|newsvendor --cu --co`. **INLINE** | Two habits. (a) **Modal-state planning** — optimising for the single most likely world, which is wrong whenever the tail state is expensive. (b) Reporting the **posterior mean regardless of the loss**, which is only correct under squared error. The loss→estimator table is the underused half of this row: `squared→mean`, `absolute→median`, `0-1→mode`, `pinball(τ)→τ-quantile`, `LINEX(a)→ −(1/a)·log E[e^{−aθ}]`, `newsvendor(c_u,c_o)→ F⁻¹(c_u/(c_u+c_o))`. **The agent-native case: "what timeout should I set" is a newsvendor problem** — cost of too-short ≠ cost of too-long, so the answer is the critical-fractile quantile of the latency posterior, never the mean and never p95-by-folklore. Also emits the killer diagnostic: **"the decision flips at P(broken) = 0.19; you're at 0.31"** | **EASY.** Arithmetic. Sample-based LINEX is `-(1/a)*log(mean(exp(-a*x)))` via log-sum-exp; pinball/newsvendor is `sorted(draws)[int(tau*N)]`. Extras (EVPI, regret of the runner-up, decision-flip threshold via bisection) are elementary | Payoffs on incommensurable scales silently added (dollars + hours + reputation) · utility assumed linear over a range where it plainly isn't (ruin, deadlines, rate limits) · states not exhaustive or not mutually exclusive · the probabilities were invented and no sensitivity band was supplied — then report the flip threshold **only**, and suppress the recommendation · **no loss declared → refuse to emit a point estimate at all** (this is the highest-leverage single constraint in the territory) |
| 5 | **Gamma-Poisson conjugate for rates and counts** (+ negative-binomial posterior predictive) | "3 errors last week, 7 this week — is the error rate up?" · "how often does this actually happen per hour?" · "count data, small numbers, different exposure windows" · "crash rate went from 2 to 5, should I care?" · "how many alerts should I expect tomorrow?" | `--count 7 --exposure 168 [--count2 --exposure2] [--prior-rate --prior-strength]`. **INLINE** | Comparing raw counts without normalising exposure, and treating 3→7 as a 133% increase. The Gamma posterior over the rate plus the exact P(λ₂>λ₁) shows the two windows overlap heavily. Predictive is negative-binomial, not Poisson — noticeably wider, which is the number the agent actually wants for "how many tomorrow" | **EASY.** Analytic posterior `Gamma(a+Σy, b+Σt)`; predictive NB in closed form; rate comparison via a finite sum or 1-D quadrature. Only needs `lgamma` | Overdispersion (variance ≫ mean — clustered incidents from one outage): must run the dispersion check and escalate to NB/hierarchical rather than print a Poisson answer · non-constant rate over the window (a spike, not a rate) · exposure unknown or estimated · events not independent (retry storms) |
| 6 | **Prior sensitivity analysis / robustness gate** (power-scaling + prior ladder + robustness **breakdown point**) | "how much of this conclusion is my prior?" · "would a skeptic get the same answer?" · "am I just seeing what I assumed?" · "is this result driven by the data or by my assumptions?" · "how robust is this to how I set it up" | Runs *on top of* any row above. Needs the model's log-prior and log-likelihood, or existing posterior draws. **No extra user input** | Reporting a posterior with no indication that at n=4 it is 85% prior. This is the doctrine feature. Its best output is not an interval but a **breakdown point**: *"this conclusion survives up to s = 4 adversarial pseudo-observations"* or *"a 12% chance your prior is wrong is enough to flip the decision"* — a single falsifiable number where hand-waving sensitivity analysis gives none. Also the honest answer to the Lindley paradox for row 10 | **MODERATE.** Three implementations. (a) **Power-scaling** (Kallioinen et al.): weights are literally `p(θ)^(α−1)`; distance is the normalised square-root **cumulative** Jensen–Shannon divergence between weighted ECDFs (CDFs, not densities — so it is sorting, not density estimation); sensitivity = d(CJS)/d(log₂α) at α=1. Threshold **0.05**. The 2×2 diagnosis — prior-sensitive & likelihood-sensitive = *prior–data conflict*; prior-sensitive only = *weak likelihood*; likelihood-only = *healthy* — is the actual deliverable. Power-scaling is analytic for exponential-family priors (`normal(μ,σ)^α ∝ normal(μ, α^{−1/2}σ)`, `beta(s₁,s₂)^α ∝ beta(αs₁−α+1, αs₂−α+1)`, etc.). (b) **Prior ladder**: refit under reference / weakly-informative / skeptical-null, report whether the *decision* flips. (c) **Breakdown point**: IDM `s`-sweep, or ε-contamination where maximising over point-mass contaminants reduces to a **1-D search** over θ. **Key stdlib insight: at ≤3 parameters, recompute the α-scaled posterior exactly on the same grid — no importance sampling, no k̂, no PSIS layer at all.** | Pareto k̂ above `min(1 − 1/log₁₀(S), 0.7)` under IS-based power-scaling → refuse and refit (or switch to the grid route) · a prior ladder that is secretly one prior in three costumes (all centred at the same place) · the model is so weakly identified that *every* prior in the ladder flips it — report "unidentified", not a range · **both** prior and likelihood sensitivity near zero — that is a fitting/computation problem, not a robust result |
| 7 | **Posterior predictive distribution** (Beta-Binomial / Negative-Binomial / Student-t predictive) | "what will happen next time?" · "how many failures should I expect in the next 100 runs?" · "give me a range for the next observation, not for the average" · "what's the worst plausible case for tomorrow?" · "predict the next value with uncertainty" | Whatever the fitted model needed, plus `--horizon m`. **INLINE or DATAFILE** | The **plug-in predictive**: taking the posterior mean parameter and generating from that distribution. At n < 10 this is dramatically too narrow — it throws away parameter uncertainty entirely. For 0/40 failures, plug-in says "expect 0 in the next 100"; the beta-binomial predictive says P(≥1 failure in 100) ≈ 0.19 | **EASY.** All three predictives are closed form. Beta-binomial pmf and NB pmf need only `lgamma`; t predictive needs incomplete beta | The parametric family is wrong for the tail (asking for a 99.9th percentile from a Student-t fitted to 6 points is a fiction — cap the reportable quantile at roughly `1 − 1/(2n)` and refuse beyond) · the process changes between now and the prediction window · horizon far outside the observed exposure |

---

### Tier B — high value, fires often, needs real machinery

| # | Model / method | SITUATION (retrieval phrasings) | Minimum viable inputs | Beats what | Stdlib feasibility | Refuse-to-print failure modes |
|---|---|---|---|---|---|---|
| 8 | **Value of information: EVPI / EVPPI / EVSI** — "is one more run worth it?" | "should I gather more data before deciding?" · "how many more runs do I need?" · "is it worth the time to test this further?" · "when do I stop investigating?" · "how much would perfect information be worth here?" · "which unknown should I go resolve first?" | The row-4 decision table + the current posterior + `--cost-per-observation`. **INLINE** | The agent's two default behaviours: decide immediately, or run 100 more tests reflexively. EVSI answers in the decision's own units: *"one more run buys 0.003 expected utility; it costs 0.05 — stop and decide now"*. **EVPI is a hard upper bound on the value of any experiment, tool call, or search** (Howard's "value of clairvoyance") — if perfect knowledge of X is worth less than one more tool call, the tool call has negative value no matter how uncertain X feels. EVPPI additionally beats the tornado-diagram reflex: **a high-variance parameter that never flips the argmax has EVPPI exactly 0**, and no sensitivity chart will tell you that | **EASY** in the cases that matter, once the closed forms are hard-coded. Two-action, value linear in θ~Normal(μ,σ²), threshold k: `EVPI = σ·L(\|z\|)`, `z=(μ−k)/σ`, with the **unit normal loss integral** `L(z)=φ(z)−z(1−Φ(z))` — one line of `NormalDist`. Normal–normal EVSI: the pre-posterior mean has variance `σ_pre² = σ⁴/(σ²+s²/n)`, so `EVSI(n)=σ_pre·L(\|μ−k\|/σ_pre)` — **sweeping n gives the entire EVSI-vs-n curve for free**, which is the single most useful output. Beta-binomial EVSI is an **exact O(n) finite sum** over the m+1 predictive outcomes. General case: nested MC, or Strong–Oakley regression on an existing draw set | EVPI computed but no decision actually pending (then the number is theatre) · the cost of sampling isn't in the same units as the payoffs · the "one more observation" would not be exchangeable with the existing ones — the classic: **re-running the same flaky test learns almost nothing, but the model assumes it buys a full observation's worth of information** · nested-MC EVSI with too few inner draws (biased upward, and the bias is invisible) |
| 9 | **Hierarchical partial pooling with few groups** (J ≈ 3–30) | "I have 6 services each with a handful of observations — which is worst?" · "one of these groups looks terrible but it has tiny n" · "should I treat these as the same or different?" · "rank these variants when they have different sample sizes" · "is this outlier group real or just noise?" | Per-group `(y_j, se_j)` or `(k_j, n_j)`, J ≥ 3, plus an explicit prior on the between-group SD τ. **DATAFILE** | Both naive alternatives, and it is the highest-margin row in the territory. **No pooling** (each group's own rate) is guaranteed to put the smallest-n group at the extremes of the ranking — the "worst service" is almost always the one with 4 observations. **Complete pooling** erases real differences. Partial pooling shrinks each group toward the grand mean by exactly its own noise-to-signal ratio, and the shrinkage *is* the answer | **MODERATE — and much easier than it looks.** For the normal case with known `se_j`, θ and μ marginalise analytically, leaving a **one-dimensional grid over τ** (the BDA3 eight-schools recipe): `p(τ\|y) ∝ p(τ)·√V_μ·Π_j N(y_j \| μ̂, se_j²+τ²)`. **No MCMC, hence no funnel, no divergences, no R̂.** Binomial groups need a 2-D grid over (mean, concentration) of a beta-binomial. Verified: the 7-parameter Metropolis alternative runs 60k iterations in 0.14 s (Appendix A). **Prior on τ — use the PC prior, which for a group-level SD is exactly `σ ~ Exponential(λ)` with `λ = −ln(α)/U` from one user statement `P(σ > U) = α`** (Simpson et al.): one interpretable knob, finite density at zero so shrink-to-no-heterogeneity is reachable, and `random.expovariate` for sampling | **J < 4 → refuse or force an explicit, defended τ prior.** With three groups τ is essentially unidentified and the entire answer is the prior — the single most important guard in the territory ([Röver et al. 2021](https://arxiv.org/abs/2007.08352)) · **the uniform-on-σ prior gives an improper posterior at J ≤ 2** (Gelman 2006) · **reject `InverseGamma(ε,ε)` outright** — arbitrarily sensitive to ε, and structurally incapable of shrinking to the base model since any Γ(a,b) on precision has zero density at σ=0; it is still the endemic WinBUGS-era default and the tool should name it as an error · half-Cauchy at small J inherits the Cauchy tail, so posterior upper quantiles of τ are set by the scale parameter, not the data · groups not exchangeable (a known, modellable difference is a covariate, not a random effect) · `se_j` supplied as a guess |
| 10 | **Bayes factor for a point null with a stated robustness region** (JZS t-test; exact beta-binomial BF) | "is there evidence that there's *no* difference?" · "how strong is the evidence either way?" · "the test came back non-significant — does that mean it's the same?" · "quantify support for the null" · "how much evidence do I actually have?" | `--t --n` (or two groups), or `--k --n --p0`; plus `--scale 0.707`. **INLINE** | The thing a p-value structurally cannot do: **support the null**. "p = 0.42, not significant" is the agent's default read and it conflates absence of evidence with evidence of absence. BF₀₁ = 4.2 says the data are 4× more likely under "no effect". Emitting the **robustness region** — the range of prior scales over which the verdict holds — is what makes it safe | **MODERATE.** Rouder et al.'s JZS BF is a **one-dimensional integral over g** with an inverse-gamma weight — Gauss-Legendre or adaptive Simpson in stdlib, milliseconds. The binomial BF against a point p₀ is fully closed form (ratio of beta functions). Robustness region = bisection over the scale parameter | **The point null must be genuinely plausible.** "Is the effect exactly zero" is rarely the real question — if the agent means "is it small enough to ignore", route to ROPE (row 17), not here · vague/flat prior on the effect → Jeffreys–Lindley paradox drives BF toward the null mechanically; refuse to accept an unbounded scale · reporting BF as posterior odds without stating the model priors · Savage-Dickey shortcut used where nuisance priors don't match ([Heck 2019](https://bpspsychub.onlinelibrary.wiley.com/doi/10.1111/bmsp.12150)) |
| 11 | **Prior elicitation from stated quantiles** (fit Beta / Normal / LogNormal / Gamma to two quantiles; roulette bins; prior-sample-size feedback) | "I believe it's around 20% but could be as high as 40%" · "turn my hunch into a prior" · "how do I encode what I already know?" · "I have a rough sense of the range" · "what prior should I use here?" | `--quantile 0.5:0.2 --quantile 0.95:0.4 --family beta`, or `--roulette "0-10:3,10-20:8,..."`. **INLINE** | The two failure modes of an agent picking a prior freehand: (a) writing `Beta(2,8)` because it "looks about right", with no check that it implies the stated beliefs; (b) reaching for `Uniform` as "uninformative" — a strong and usually wrong claim (uniform on a conversion rate says 95% is as plausible as 5%). Nobody, human or model, can introspect α and β; everyone can state a median and an upper bound. The tool also reports the **implied prior sample size** (`a+b`) and a SHELF-style feedback check (*"your prior implies P(X>0.5)=0.08 — is that right?"*), which is what catches incoherent elicitation | **EASY→MODERATE.** Normal/LogNormal closed form: `σ=(x₂−x₁)/(z₂−z₁)`, `μ=x₁−σz₁`. Beta by the `beta.select` recipe: reparameterise to (mean m, precision K), grid `K=exp(linspace(−3,8,100))`, for each K **bisect on m** until `I_{x₁}(Km, K(1−m)) = p₁` (monotone in m, always converges), then interpolate over log K to match the second quantile, return `(K₀m₀, K₀(1−m₀))`. Only stdlib gap is `I_x(a,b)`. ≥3 quantiles → least squares over candidate families | Stated quantiles internally inconsistent (q05 > median) · **no member of the family fits within tolerance → refuse rather than fit the nearest thing**; a bad best-fit is a signal the stated beliefs are incoherent and must go back to the caller · the elicited belief was formed **after** seeing the data (double-counting — the most likely abuse when an LLM is its own expert) · implied prior sample size exceeding the real one by >5× without explicit acknowledgement |
| 12 | **Sequential evidence accumulation with a stopping rule** (Sequential Bayes Factors; e-values / anytime-valid alternative) | "how many runs is enough?" · "can I stop testing now?" · "I keep checking as data comes in — is that cheating?" · "when do I have enough evidence to call it?" · "design a benchmark run that will actually settle this" | Thresholds (`--stop-at-bf 6`), a per-observation cost or budget, and the ability to keep sampling. **MUST-CONSTRUCT-DATA** | Fixed-n power analysis (frequentist, requires an effect size the agent doesn't have) and, far more commonly, **unprincipled peeking** — the agent runs the benchmark until the answer looks good. Bayes factors are immune to optional stopping *for the Bayesian quantity* (likelihood principle); e-processes give a genuine anytime-valid Type-I guarantee if the agent wants one. Either way the agent gets a stopping rule instead of a vibe | **MODERATE.** The BF itself is row 10. The value-add is (a) the stopping loop and (b) simulating operating characteristics — expected stopping n, and error rates under a stated effect — which is a straightforward pure-Python Monte Carlo (10⁴ synthetic trajectories, seconds). E-values for simple nulls (Bernoulli, Gaussian-known-σ) are closed form | Claiming a frequentist error rate for an SBF stopping rule without having simulated it · unbounded sampling budget with a threshold that may never be reached (report the futility bound) · the data-generating process drifts across the sampling period · the agent stops early on a *different* statistic than the one the rule governs |
| 13 | **Grid approximation engine (1–3 parameters)** | "fit this small custom model" · "I have a likelihood but no conjugate form" · "one or two unknowns, need the full posterior" · "posterior for a weird parameterisation" | A log-likelihood + log-prior expressed in the tool's mini-DSL or a plug-in Python function; bounds. **DATAFILE** | Laplace/normal approximation, which is wrong exactly where it matters — skewed and bounded posteriors at small n (variance parameters, rates near zero). Grid gives the **exact** posterior to grid resolution, including bimodality and boundary mass, with no convergence question at all. For 1–2 parameters it is strictly better than MCMC | **EASY (with one caveat).** Log-space evaluation + logsumexp normalisation; marginals by summation; quantiles by cumulative sum. **Measured: 200×200 = 40,000 evaluations against n=300 raw data takes 0.6 s** (Appendix A) — but with sufficient statistics it is milliseconds. The design rule: reduce to sufficient statistics or cap `G^d × n` | Grid bounds truncating posterior mass — **must** verify edge mass < 1e-6 and auto-expand, else refuse · d ≥ 4 (`G^d` blows up; route to row 14) · sharply peaked likelihood falling between grid points at n large (adaptive refinement or route to Laplace) · unnormalisable / improper posterior |
| 14 | **Adaptive random-walk Metropolis (+ slice sampling) with rank-normalised R̂ and ESS gating** | "fit a model with 4–10 parameters" · "no closed form, need to sample the posterior" · "hierarchical model with a t-likelihood" · "robust regression on a few dozen points" | A log-posterior function, initial values, chains. **DATAFILE** | The alternative is *not fitting the model* — collapsing to a conjugate approximation that assumes away the outliers or the hierarchy. Also beats naive fixed-step Metropolis, which either never moves or never accepts | **MODERATE.** Random-walk Metropolis with Robbins–Monro adaptation of the step scale toward 0.234 (multivariate) / 0.44 (univariate) acceptance during warm-up, **frozen thereafter** (adaptation must stop for ergodicity). Slice sampling is the better default for the agent case: one tunable, self-adapting interval, robust to a bad initial scale ([Neal 2003](https://doi.org/10.1214/aos/1056562461)). **Measured: 7 parameters, 60,000 iterations, 0.14 s** — pure Python MCMC at agent scale is a non-issue (Appendix A) | **This row is the project's canonical refuse case.** The `bayesian-workflow` evaluation found agents report results despite divergence warnings. Therefore: rank-normalised split-R̂ > 1.01, bulk-ESS or tail-ESS < 100 per chain, or MCSE > 0.1 × posterior SD → **suppress the headline number entirely**, print only the diagnostic ([Vehtari et al. 2021](https://arxiv.org/abs/1903.08008)) · strongly correlated parameters without reparameterisation · funnel geometry in a non-centred-parameterisable hierarchical model · single chain (R̂ uncomputable) |
| 15 | **Empirical-Bayes shrinkage / ranking with unequal sample sizes** | "rank these 12 items when they have wildly different n" · "the top of my leaderboard is all tiny samples" · "which of these is genuinely best?" · "adjust these rates for how much data each one has" · "regression to the mean" | `(k_j, n_j)` or `(y_j, se_j)` for K ≥ 4 items. **DATAFILE** | Ranking by raw rate — where the winner is essentially always the smallest-n item, and the effect is severe (this is Efron–Morris's baseball result and the "most extreme county" fallacy). Cheaper than row 9 and often sufficient when the agent only needs an ordering | **MODERATE.** Beta-binomial marginal MLE by 2-D Nelder–Mead or coordinate bisection on `lgamma` terms; method-of-moments start. Normal case: James–Stein factor `1 − (K−3)σ²/Σ(y_j−ȳ)²`, one line | K < 4 (James–Stein dominance requires K ≥ 4; below that just report row 1 per item) · items not exchangeable — shrinking a genuinely different-kind item toward the group mean is a real error, not conservatism · the group was **selected** for extremeness before shrinking (double dipping) · the tool should always prefer row 9 when a full posterior is wanted; EB understates uncertainty by treating the estimated hyperprior as known |
| 16 | **Gamma-Exponential / Weibull reliability with censoring** | "when will this fail?" · "it's survived 200 hours with no failures — what's the MTBF?" · "how likely is it to last another week?" · "time-to-failure with almost no failures" · "reliability estimate from a short test" | `--failures d --total-time-on-test T` (censored units contribute their time), optional Weibull `--shape`. **INLINE or DATAFILE** | `MTBF = T/d`, which is **undefined at d = 0** and wildly unstable at d = 1 or 2 — precisely the regime an agent is in. The Gamma posterior handles d = 0 natively, and the posterior predictive survival function `P(T>t) = (b_n/(b_n+t))^{a_n}` (a Lomax) is a clean, heavier-tailed answer to "will it last another week" | **EASY** for exponential (conjugate Gamma, Lomax predictive, closed form). **MODERATE→HARD** for Weibull (2 parameters, no conjugacy — route to row 13's grid, which handles it comfortably) | **Non-constant hazard.** Exponential assumes a memoryless, flat hazard; burn-in and wear-out both violate it and both are common. If the agent's data show any trend in inter-failure times, refuse the exponential and demand Weibull · Weibull with < 5 failures requires a real prior on the shape parameter or the answer is 100% prior · censoring not independent of failure (units pulled from the test because they looked sick) |

---

### Tier C — narrower or heavier, but each owns a question nothing else answers

| # | Model / method | SITUATION (retrieval phrasings) | Minimum viable inputs | Beats what | Stdlib feasibility | Refuse-to-print failure modes |
|---|---|---|---|---|---|---|
| 17 | **ROPE + HDI practical-equivalence decision rule** | "is this difference big enough to matter?" · "it's statistically real but is it meaningful?" · "how do I decide the two are effectively the same?" · "declare equivalence" · "practical significance vs statistical significance" | An existing posterior (from any row) + `--rope-lo --rope-hi` (the smallest difference the agent would act on). **INLINE** | Both "significant, therefore act" and "not significant, therefore identical". Emits a three-way verdict — accept / reject / **undecided** — and the undecided verdict is the valuable one, because it is the honest state at small n and no other rule can express it | **EASY.** Posterior mass inside the interval; HDI by scanning the sorted draws or the quadrature grid for the shortest interval of the target mass | **No ROPE supplied** → refuse outright rather than invent a default; the interval encodes the agent's actual decision threshold and guessing it is the whole error ([Kruschke's rule is only as good as the ROPE](https://doi.org/10.1037/a0029146)) · HDI reported on a parameter the agent then transforms (HDI is not transformation-invariant; use the equal-tailed interval if the scale will change) · ROPE chosen after seeing the posterior |
| 18 | **Dirichlet-Multinomial conjugate** | "which of these five failure categories dominates?" · "did the distribution across buckets shift?" · "I have counts across categories and not many of them" · "proportions that must sum to one" · "is this category over-represented?" | `--counts 4,1,7,0,2 [--prior jeffreys\|perks\|uniform]`. **INLINE** | Reading raw proportions off 14 observations spread across 5 categories, where every one of them has an enormous credible interval and the zero-count category is *not* impossible. Also gives the joint — P(category 3 is the largest) — which per-category intervals cannot | **EASY.** Posterior `Dirichlet(α+n)`; draws via K `random.gammavariate` calls normalised (stdlib, exact); marginals are Beta so intervals are analytic. Walley's IDM gives interval-valued bounds for free | Categories defined after inspecting the data (the classic: "other" bucket split once something interesting appeared) · counts from overlapping/non-exclusive categories · K comparable to or larger than n → the prior dominates every cell; report the pooled statement only · ordinal categories treated as nominal (throws away the ordering) |
| 19 | **Logarithmic opinion pooling with extremization** | "three sources disagree — how do I combine them?" · "merge conflicting estimates" · "two models give different probabilities, what do I believe?" · "aggregate several forecasts" · "consensus probability from disagreeing experts" | `--probs 0.2,0.55,0.35 [--weights] [--extremize 1.7]`. **INLINE** | The arithmetic mean of probabilities, which is **provably under-confident** when sources hold partly independent information — averaging 0.2 and 0.8 to 0.5 discards the fact that both are confident. Log pooling (normalised weighted geometric mean of odds) is externally Bayesian and sharper; extremizing the pooled log-odds by a ≈ 1.5–2.5 is the Good Judgment Project's empirically validated correction | **EASY.** Log-odds arithmetic. The only hard part is choosing the extremization coefficient and the weights | **Correlated sources** — the single fatal violation. Three sources that all read the same upstream report are one source, and extremization makes the error *worse*, not better. If the agent cannot argue for partial independence, refuse to extremize and fall back to linear pooling · any source stating exactly 0 or 1 (log pool collapses) · weights derived from the same data being pooled |
| 20 | **Bayesian bootstrap (Rubin) for arbitrary statistics** | "credible interval on the median" · "uncertainty on a weird statistic with no formula" · "I don't want to assume a distribution" · "nonparametric uncertainty from a small sample" · "interval on the 90th percentile" | `--data <file> --statistic median\|p90\|trimmed-mean\|<expr>`. **DATAFILE** | A normal approximation on a statistic that has no tractable sampling distribution, and the agent's habit of reporting the sample median as a point fact. Also beats the classical bootstrap at small n: Dirichlet weights are continuous, so the resampling distribution is smooth rather than lumpy | **EASY.** Draw `n` Exponential(1) variates, normalise → Dirichlet(1,…,1) weights; compute the weighted statistic; repeat 2,000×. Entirely `random.expovariate`. Microseconds per replicate | **Support limitation:** the Bayesian bootstrap puts zero mass outside the observed values, so tail quantiles are hard-capped by the sample max — refuse any requested quantile beyond about `1 − 1/(2n)` · n < 8 (the weight distribution is dominated by a few points) · heavy tails where the sample max is nowhere near the population tail · non-iid / clustered data (needs a block version) |
| 21 | **PSIS-LOO / WAIC predictive model comparison** | "which of these explanations should I believe?" · "is the more complex model actually better?" · "compare two candidate models fairly" · "am I overfitting with this extra term?" · "which model predicts better out of sample" | Pointwise log-likelihood matrix from posterior draws (S × n) for each model. **DATAFILE** | In-sample fit (always favours complexity), parameter counting, and Bayes factors (which answer "which model is *true*" — the wrong question when both are wrong). Crucially reports `elpd_diff` **with its standard error**, which is what stops the agent declaring a winner on a 0.4-nat difference | **MODERATE.** Requires the model to emit pointwise log-lik; PSIS itself is a sort, a generalised-Pareto fit to the top 20% of importance ratios (2-parameter, closed-form profile estimator — no optimiser needed), and reweighting. All stdlib | Any k̂ above `min(1 − 1/log10(S), 0.7)` → refuse, the LOO estimate is unreliable ([Vehtari et al.](https://arxiv.org/abs/1507.02646)) · n < ~20 makes the `elpd_diff` SE uninformative · `\|elpd_diff\| < 4` **or** `< 2·SE` → print "cannot distinguish; prefer the simpler model" and suppress the ranking (this is failure mode 4 from the `bayesian-workflow` eval) · models fitted to different data or different transformations of y |
| 22 | **Laplace approximation + marginal likelihood** | "fast approximate posterior for a small model" · "estimate the model evidence" · "I need this to be quick and the posterior looks bell-shaped" · "approximate Bayes without sampling" | A log-posterior + a starting point. **DATAFILE** | BIC — which is Laplace with a crude Hessian and an n→∞ assumption that fails at exactly the sample sizes this territory serves. Also 100–1000× faster than MCMC when it applies | **MODERATE.** Mode by Nelder–Mead (stdlib, ~60 lines); Hessian by central finite differences; `log Z ≈ logpost(θ̂) + (d/2)log2π − ½log\|H\|`. Determinant of a ≤6×6 matrix by Gaussian elimination with partial pivoting — trivial and numerically fine at this size | Skewed or bounded posteriors (variance parameters near zero, rates near 0 or 1) — **the dominant sparse-data case**, so this row must self-check against a grid or a few hundred MCMC draws and refuse when the discrepancy is large · multimodality · mode on a boundary (Hessian not negative-definite) · n small enough that the posterior is visibly non-Gaussian |
| 23 | **Thompson sampling / posterior-sampling action rule** | "which option should I try next, given I'll learn from the result?" · "explore or exploit?" · "I have several candidates and limited attempts" · "keep testing the promising ones without abandoning the others" · "adaptive allocation across variants" | Per-arm posteriors (rows 1/5) + the number of remaining pulls. **INLINE, updated online** | ε-greedy (wastes a fixed fraction on known-bad arms) and greedy pick-the-best-so-far (locks onto an early lucky arm and never recovers — the dominant failure when each arm has 3 observations). One posterior draw per arm, argmax; near-optimal regret ([Agrawal & Goyal](https://arxiv.org/abs/1111.1797)) | **EASY.** One `random.betavariate` / `gammavariate` per arm per round | **Not a one-shot decision rule.** If there is no future learning, TS is strictly worse than row 4's Bayes action — route accordingly; this is the most likely misuse · non-stationary rewards (needs discounting) · delayed feedback · arms with very different costs (needs a budget-aware variant) |
| 24 | **Posterior predictive check / Bayesian surprise for anomaly** | "is this observation an anomaly?" · "does my model still fit?" · "this value looks weird — is it?" · "how surprising is this given what I knew?" · "did something change?" | A fitted model's posterior draws + the new observation(s). **DATAFILE** | A z-score against the sample mean and sd, which at small n is dominated by the candidate outlier itself. The posterior predictive tail probability accounts for parameter uncertainty, so a point that is 3 sd out at n=6 is often unremarkable | **EASY** given predictive draws (rows 7, 13, 14) | **Do not call it a p-value.** Posterior predictive p-values are conservative and non-uniform under the null (Bayarri & Berger); use the *partial* posterior predictive, or simply report the predictive quantile and refuse the significance framing · the candidate point was included in the fit (double use of data — must use the leave-one-out predictive, which rows 21's PSIS gives cheaply) · n < 5, where nothing is detectable |
| 25 | **Bayesian stacking / model averaging of predictive distributions** | "several explanations are plausible — do I have to pick one?" · "combine competing models" · "hedge across model uncertainty" · "which mixture of these hypotheses" | LOO pointwise log-lik for 2–5 models (row 21's output). **DATAFILE** | Selecting the single best model and then reasoning as if it were true — which understates predictive uncertainty in exactly the sparse regime where model choice is least certain. Stacking beats BMA when no candidate is the true model, which is the normal case ([Yao et al. 2018](https://arxiv.org/abs/1704.02030)) | **MODERATE.** Optimise mixture weights on the simplex to maximise the LOO log score. For ≤4 models a coarse simplex grid plus local refinement is adequate and needs no optimiser; ≥5 models needs projected gradient ascent (~40 lines) | Inherits every row-21 refusal (bad k̂, tiny n) · fewer than 2 genuinely distinct models · models fitted on different data · the agent wanting an interpretable "which one is right" answer — stacking deliberately does not provide one |
| 26 | **Simulation-based calibration (SBC)** — self-test, not an agent-facing model | "is this tool itself correct?" · "validate the sampler" · "are my credible intervals actually covering?" | The model's prior sampler + likelihood sampler + inference routine. **MUST-CONSTRUCT-DATA (synthetic)** | Unit tests on point estimates, which cannot detect a systematically over-narrow posterior. SBC checks that rank statistics of the true parameter within the posterior draws are uniform — a necessary condition for correct inference ([Talts et al.](https://arxiv.org/abs/1804.06788); [Modrák et al.](https://arxiv.org/abs/2211.02383)) | **EASY.** Sample θ from prior, sample data, refit, compute the rank of θ among draws; repeat ~500×; test rank uniformity. Slow only in aggregate — a CI job, not a request-time call | Not applicable at request time. Should live in the library's test suite, and every model in this territory should ship an SBC result as its correctness evidence |

---

## 3. Recent advances (last ~10 years)

Advances included only where they **materially change what a pure-stdlib tool can do or must
refuse to do**.

**1. Rank-normalised split-R̂ and bulk/tail-ESS (Vehtari, Gelman, Simpson, Carpenter, Bürkner,
2021).** The classical Gelman–Rubin R̂ fails silently on heavy-tailed posteriors and when
variance differs across chains — both routine in sparse-data hierarchical models. The
replacement adds rank-normalisation, folding (to catch scale differences), and separate bulk
and tail ESS. **Consequence for this library: the refusal threshold is R̂ > 1.01, not 1.1, and
tail-ESS must be checked separately** because credible-interval endpoints are tail quantities.
All of it is sorting and arithmetic — fully stdlib.
<https://arxiv.org/abs/1903.08008>

**2. Pareto-smoothed importance sampling and its 2024 threshold revision (Vehtari, Simpson,
Gelman, Yao, Gabry).** PSIS turns importance sampling from a technique that fails invisibly
into one with a **self-diagnosing reliability statistic**, k̂. The revised paper replaces the
fixed 0.7 cut with the sample-size-aware `min(1 − 1/log10(S), 0.7)`. This is the single most
useful import into this territory: it makes cheap posterior reweighting — for LOO (row 21),
for power-scaling prior sensitivity (row 6), for "what if I drop this point" — safe to
automate, because the tool knows when to refuse. The generalised-Pareto fit uses a
closed-form profile estimator; no optimiser needed.
<https://arxiv.org/abs/1507.02646> · LOO application: <https://arxiv.org/abs/1507.04544>

**3. Power-scaling prior sensitivity analysis (Kallioinen, Paananen, Bürkner, Vehtari, 2023).**
Prior sensitivity used to mean refitting the model under a handful of priors — expensive and
arbitrary. Power-scaling raises the prior to a power α and importance-reweights the *existing*
draws, giving a continuous sensitivity gradient (cumulative Jensen–Shannon distance against
log₂α) that separates **prior-data conflict** from **prior dominance**. It costs one pass over
the draws and is guarded by k̂. This is the operational form of the project's "suppress the
number when it isn't earned" doctrine.
<https://arxiv.org/abs/2107.14054>

**4. Penalised-complexity priors (Simpson, Rue, Riebler, Martins, Sørbye, 2017).** A principled
recipe for default priors on "flexibility" parameters — group-level SDs, degrees of freedom,
overdispersion — derived by putting an exponential penalty on the KL distance from a simpler
base model. It gives *defensible* defaults where the library would otherwise be inventing
voodoo constants, and it is exactly what row 9 needs for its τ prior when J is small. The
resulting priors are typically exponential on a scale parameter — trivial to evaluate.
<https://arxiv.org/abs/1403.4630>

**5. Safe testing, e-values, and anytime-valid inference (Grünwald, de Heide, Koolen, 2019→;
Ramdas et al.).** E-values give an evidence measure that is valid **under arbitrary optional
stopping and optional continuation** — Ville's inequality bounds the probability that an
e-process ever exceeds 1/α. For an agent that continuously accumulates evidence and decides
when to stop, this is closer to the native use case than either p-values or Bayes factors. For
simple nulls the e-value *is* a likelihood ratio, so the closed forms this library already
needs cover the common cases.
<https://arxiv.org/abs/1906.07801>

**6. Simulation-based calibration checking (Talts et al. 2018; Modrák et al. 2023).** SBC turned
"is my Bayesian implementation correct" from an unanswerable question into a mechanical test.
Modrák et al. sharpened it with better-powered test statistics and clarified what SBC can and
cannot detect. **Consequence: every model in this territory can ship a machine-checkable
correctness certificate**, which is a considerably stronger claim than golden-value tests.
<https://arxiv.org/abs/1804.06788> · <https://arxiv.org/abs/2211.02383>

**7. Stacking of predictive distributions (Yao, Vehtari, Simpson, Gelman, 2018).** Established
that under M-open (no candidate model is true — always, for an agent) stacking LOO predictive
distributions dominates Bayesian model averaging by marginal likelihood, and that BMA weights
degenerate to a single model as n grows even when that model is wrong.
<https://arxiv.org/abs/1704.02030>

**8. Bayesian Workflow (Gelman, Vehtari, Simpson, Margossian, Carpenter, Yao, Kennedy, Gabry,
Bürkner, Modrák, 2020).** The field's own statement that fitting a model is one step in a loop
that includes prior predictive checking, fake-data validation, diagnostics, posterior predictive
checking, and model comparison. Directly relevant because it is the intellectual ancestor of the
`bayesian-workflow` skill this project benchmarked against, and it names the steps a CLI tool
must either perform or explicitly decline.
<https://arxiv.org/abs/2011.01808>

**9. Weakly informative heterogeneity priors for very few groups (Röver, Bender, Dias,
Schmid, Schmidli, Sturtz, Weber, Friede, 2021; Lilienthal et al. 2024).** A decade of applied
work converged on the finding that with **k < 5 groups the between-group SD is effectively
unidentified**, uniform and inverse-gamma priors both behave badly, and half-normal or
empirically-derived log-normal priors on τ are the defensible choices. This is the empirical
basis for row 9's hard refusal at J < 4.
<https://arxiv.org/abs/2007.08352> · <https://onlinelibrary.wiley.com/doi/full/10.1002/jrsm.1685>

**10. LLM-elicited priors (AutoElicit, Capstick et al. 2024/25; "Had enough of experts?", 2024;
LLM-Prior, 2025).** The newest and most consequential for this project specifically. These
papers treat an LLM as the domain expert in a formal prior-elicitation loop and find the
resulting priors reduce sample complexity and **outperform both uninformative priors and
in-context learning**. It converts row 11 from a convenience into a validated method: the agent
supplying its own beliefs as a prior is a documented technique with measured benefit, not a
hack.
<https://arxiv.org/abs/2411.17284> · <https://openreview.net/forum?id=3iDxHRQfVy> ·
<https://arxiv.org/abs/2508.03766>

**11. General Bayesian updating / loss-likelihood bootstrap (Bissiri, Holmes, Walker 2016;
Lyddon, Holmes, Walker 2019).** A coherent way to update beliefs about a parameter defined by a
**loss function** rather than a likelihood — which is exactly the agent's situation when it
cares about a decision-relevant quantity (a median, a quantile, a cost) and has no generative
model. Pairs naturally with row 20.
<https://arxiv.org/abs/1306.6430> · <https://arxiv.org/abs/1709.07616>

---

## 4. Cut list

Rejected, with the reason. Ordered roughly by how tempting each was.

| Considered | Why cut |
|---|---|
| **Hamiltonian Monte Carlo / NUTS** | Needs gradients. Autodiff in pure stdlib is a project unto itself, and finite-difference gradients make HMC slower *and* less reliable than the slice sampler at ≤10 dimensions. Row 14 is strictly better under the constraint. |
| **Variational inference (ADVI / mean-field)** | Same gradient problem, plus VI systematically underestimates posterior variance — the one quantity that matters most at n=5. Actively harmful here. |
| **Gaussian processes / Bayesian optimisation** | O(n³) dense linear algebra with Cholesky, plus kernel hyperparameter optimisation. Feasible to n≈200 in pure Python but the code volume is disproportionate, and the agent use case (expensive black-box tuning) is rare and better served elsewhere. |
| **Bayesian nonparametrics (Dirichlet process mixtures, CRP)** | Needs a sampler over partitions, thousands of iterations, and a lot of care. The "how many clusters" question is real but belongs to a clustering territory, and DP priors are notoriously prior-sensitive at small n — the worst possible combination here. |
| **Bridge sampling / thermodynamic integration for marginal likelihoods** | The correct way to get a Bayes factor for a non-nested, non-conjugate model. But it needs a well-tuned proposal, many temperature rungs, and its own convergence diagnostics — a whole subsystem to serve a question (row 10) that closed forms and 1-D quadrature already answer for the common cases. |
| **Reversible-jump MCMC** | Trans-dimensional sampling with model-specific jump proposals. Enormous implementation surface; row 25's stacking answers "which model" adequately. |
| **Full Bayesian regression with shrinkage priors (horseshoe, regularised horseshoe)** | Excellent methods, but they need p ≫ n problems to earn their keep, and p ≫ n is not the agent's situation. Also gradient-hungry to sample well. |
| **Bayesian networks / probabilistic graphical model inference** | Structure learning needs far more data than an agent will have, and the CLI ergonomics of specifying a DAG through flags are terrible. Causal DAGs belong in the causal-inference territory. |
| **Bayesian changepoint detection (BOCPD, Adams & MacKay)** | Genuinely useful and genuinely stdlib-feasible (O(n²) run-length recursion), but "when did the regime change" is a time-series question, and it will be a stronger fit under a changepoint/time-series territory than here. **Flagged for pickup, not dismissed.** |
| **Bayesian assurance / probability-of-success sample sizing (O'Hagan & Stevens)** | Overlaps rows 8 and 12 almost entirely. Kept as a framing note inside row 12 rather than a separate model. |
| **Dempster–Shafer belief functions** | Combining conflicting evidence is a real need (row 19), but Dempster's rule produces notoriously counter-intuitive results under high conflict (the Zadeh counterexample), and the frame-of-discernment machinery is a heavy conceptual tax. Log pooling is better behaved and easier to explain. |
| **Full imprecise-probability / credal-set inference (Walley)** | The interval-valued output is intellectually the right answer to "your prior is doing the work", but the general theory needs LP solvers and the output ("the probability is between 0.2 and 0.7") is hard for an agent to act on. **Kept only the closed-form IDM binomial/Dirichlet bounds inside rows 6 and 18.** |
| **Approximate Bayesian Computation (ABC)** | Requires a simulator the agent almost never has, and needs 10⁵–10⁶ simulations for a usable posterior at any nontrivial tolerance. Poor fit for both constraints. |
| **Objective/reference priors beyond Jeffreys (Berger–Bernardo)** | Deriving a reference prior requires an asymptotic expansion per model. Precompute Jeffreys priors for the handful of conjugate families the library ships and stop there. |
| **Empirical Bayes for the *hyperprior* in row 9** | Tempting shortcut (plug in τ̂ instead of integrating), but at J < 10 it collapses to τ̂ = 0 far too often, producing complete pooling and falsely confident intervals. Integrate over τ; the 1-D grid is cheap. |
| **Bayesian quantile regression / asymmetric-Laplace likelihood** | Interesting for "how bad can it get", but the ALD is a working likelihood rather than a real model and the posterior needs calibration adjustment. Row 20 answers the same question honestly. |
| **Conformal prediction** | Best-in-class distribution-free prediction intervals, but it is not Bayesian and does not use a prior — belongs to a prediction/calibration territory. Notably it *is* the better tool than row 7 when n is moderate and no prior is available. |
| **Bayes factors for non-nested composite hypotheses via intrinsic/fractional Bayes factors** | Solves the improper-prior problem elegantly but is fiddly, contested, and would need per-model derivation. Row 6's robustness region is a more honest response to the same worry. |
| **Decision trees with sequential/multi-stage decisions (full dynamic programming)** | A two-stage decision with a "gather information first" node is row 8. Beyond two stages, the specification burden on the agent (a tree through CLI flags) exceeds the value; and a genuinely multi-stage problem is an MDP, i.e. another territory. |
| **Prior predictive checking as a standalone model** | It is a *step*, not a model — folded into rows 6 and 11 as an automatic output (the tool should always report what the prior implies about observables before showing the posterior). |
| **Multi-armed bandit algorithms other than Thompson (UCB, EXP3, Gittins)** | UCB and EXP3 are not Bayesian; Gittins indices are Bayesian-optimal but computationally forbidding and only apply to discounted independent-arm problems. Row 23 covers the need. |

---

## 5. Cross-territory overlaps

| Model here | Likely to reappear as | Suggested ownership |
|---|---|---|
| Row 2 (two-proportion comparison) | "Two-sample proportion test", "Fisher's exact test", "A/B test" in a **hypothesis-testing / experiment-design** territory | Keep the Bayesian version here; the router should send *decision-framed* phrasings ("which should I ship") here and *error-rate-framed* phrasings ("what's my false positive rate") there. Both should cross-reference. |
| Row 3 (Student-t posterior) | "One-sample t-test", "Welch's t-test" | Numerically near-identical intervals under the reference prior. Ship **one** t-distribution implementation in the shared math layer; the territories differ only in interpretation and output framing. |
| Row 9 (hierarchical partial pooling) | "Random-effects meta-analysis", "mixed-effects model", "multilevel model" in a **regression** or **meta-analysis** territory | Same model, three vocabularies. This should be a single implementation with three retrieval entry points, otherwise it will be built three times. |
| Row 12 (sequential stopping) | "Sequential analysis", "group sequential design", "alpha spending", "always-valid p-values" in an **experiment-design** territory | Split by guarantee type: Bayesian evidence thresholds here, frequentist error-spending there, e-values shared. |
| Row 15 (empirical-Bayes shrinkage) | "Regression to the mean", "James–Stein", "FDR / local fdr" in a **multiple-comparisons** territory | Local-fdr is empirical Bayes wearing a testing hat. Shared beta-binomial marginal-MLE routine. |
| Row 16 (reliability with censoring) | "Survival analysis", "Kaplan–Meier", "hazard modelling" in a **time-to-event** territory | The censoring bookkeeping is identical; only the estimator differs. Share the data model. |
| Row 19 (opinion pooling) | "Forecast aggregation", "ensembling", "evidence synthesis", "meta-analysis" | Meta-analysis (row 9) and opinion pooling (row 19) answer the same user question — "combine these disagreeing numbers" — with different assumptions about whether the sources are studies or opinions. The router **must** disambiguate on whether sample sizes exist. |
| Row 20 (Bayesian bootstrap) | "Bootstrap confidence interval", "resampling" in a **nonparametric / resampling** territory | Same code, one line different (Dirichlet weights vs multinomial resampling). Build once. |
| Row 21 (PSIS-LOO) | "Cross-validation", "AIC/BIC", "model selection" in a **model-selection** territory | The PSIS implementation is shared infrastructure; it also powers row 6's power-scaling and row 24's LOO predictive. High-leverage shared component. |
| Row 23 (Thompson sampling) | "Multi-armed bandit", "explore/exploit", "adaptive allocation" in a **sequential-decision / RL** territory | Belongs there long-term; keep a thin version here because it needs only a conjugate posterior. |
| Row 24 (posterior predictive check) | "Outlier detection", "anomaly detection", "goodness of fit" in an **anomaly** territory | The Bayesian version needs a fitted model; the anomaly territory's methods (MAD, isolation, EVT) do not. Route on whether a model exists. |
| Rows 13/14/22 (grid, MCMC, Laplace) | Not models — **shared inference infrastructure**. | Should live in a common engine layer, not duplicated per territory. Every territory that needs a non-conjugate posterior calls these. |
| Row 4 (loss functions, Bayes action) | "Expected utility", "decision matrix", "cost-sensitive classification" in a **decision-analysis** territory | If a decision territory exists, row 4 and row 8 arguably move there wholesale, with this territory supplying the posteriors. Worth an explicit boundary decision. |

---

## 6. Sources

**Foundational / conjugate machinery**
- Murphy, K. (2007). *Conjugate Bayesian analysis of the Gaussian distribution.* <https://www.cs.ubc.ca/~murphyk/Papers/bayesGauss.pdf>
- Gelman, Carlin, Stern, Dunson, Vehtari, Rubin. *Bayesian Data Analysis, 3rd ed.* (free PDF) <http://www.stat.columbia.edu/~gelman/book/>
- Stan Development Team. *Prior Choice Recommendations* (wiki). <https://github.com/stan-dev/stan/wiki/prior-choice-recommendations>
- Gelman, A. (2006). Prior distributions for variance parameters in hierarchical models. *Bayesian Analysis* 1(3):515–534. <https://doi.org/10.1214/06-BA117A>
- Brown, Cai, DasGupta (2001). Interval estimation for a binomial proportion. *Statistical Science* 16(2):101–133. (Jeffreys interval coverage.) <https://doi.org/10.1214/ss/1009213286>
- Rule of three (zero-event upper bound). <https://www.pmean.com/01/zeroevents.html>

**Bayes factors, evidence, stopping**
- Kass, R. & Raftery, A. (1995). Bayes factors. *JASA* 90(430):773–795. <https://doi.org/10.1080/01621459.1995.10476572>
- Rouder, Speckman, Sun, Morey, Iverson (2009). Bayesian t tests for accepting and rejecting the null hypothesis. *Psychonomic Bulletin & Review* 16(2):225–237. <https://doi.org/10.3758/PBR.16.2.225>
- Schönbrodt, F. & Wagenmakers, E-J. (2018). Bayes factor design analysis: planning for compelling evidence. *Psychonomic Bulletin & Review* 25:128–142. <https://doi.org/10.3758/s13423-017-1230-y>
- Heck, D. (2019). A caveat on the Savage–Dickey density ratio. *BJMSP* 72(2):316–333. <https://bpspsychub.onlinelibrary.wiley.com/doi/10.1111/bmsp.12150>
- Grünwald, de Heide, Koolen. *Safe Testing.* <https://arxiv.org/abs/1906.07801>
- van Erven / Ramdas et al. on the Jeffreys–Lindley paradox and resolution. <https://arxiv.org/pdf/1610.09433>
- Sensitivity analysis of Bayes factors to prior scale. <https://link.springer.com/article/10.3758/s13428-019-01262-w>

**Computation, diagnostics, robustness**
- Vehtari, Gelman, Simpson, Carpenter, Bürkner (2021). Rank-normalization, folding, and localization: an improved R̂. *Bayesian Analysis* 16(2):667–718. <https://arxiv.org/abs/1903.08008>
- Vehtari, Simpson, Gelman, Yao, Gabry. *Pareto smoothed importance sampling.* (rev. 2024) <https://arxiv.org/abs/1507.02646>
- Vehtari, Gelman, Gabry (2017). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. *Stat. & Computing* 27:1413–1432. <https://arxiv.org/abs/1507.04544>
- Kallioinen, Paananen, Bürkner, Vehtari (2023). Detecting and diagnosing prior and likelihood sensitivity with power-scaling. *Stat. & Computing* 34:57. <https://arxiv.org/abs/2107.14054>
- Simpson, Rue, Riebler, Martins, Sørbye (2017). Penalising model component complexity. *Statistical Science* 32(1):1–28. <https://arxiv.org/abs/1403.4630>
- Talts, Betancourt, Simpson, Vehtari, Gelman (2018). Validating Bayesian inference algorithms with simulation-based calibration. <https://arxiv.org/abs/1804.06788>
- Modrák, Moon, Kim, Bürkner, Huurre, Faltejsková, Gelman, Vehtari (2023). Simulation-based calibration checking for Bayesian computation. *Bayesian Analysis*. <https://arxiv.org/abs/2211.02383>
- Neal, R. (2003). Slice sampling. *Annals of Statistics* 31(3):705–767. <https://doi.org/10.1214/aos/1056562461>
- Roberts, G. & Rosenthal, J. Optimising and adapting the Metropolis algorithm (handbook chapter; 0.234 / 0.44 acceptance targets, Robbins–Monro adaptation). <https://probability.ca/jeff/ftpdir/handbookart.pdf>
- Gelman, Vehtari, Simpson, et al. (2020). *Bayesian Workflow.* <https://arxiv.org/abs/2011.01808>
- Yao, Vehtari, Simpson, Gelman (2018). Using stacking to average Bayesian predictive distributions. *Bayesian Analysis* 13(3):917–1007. <https://arxiv.org/abs/1704.02030>

**Decision theory, A/B, pooling, elicitation**
- Cook, J.D. *Exact calculation of Beta inequalities.* (closed-form P(X>Y) for Beta variates) <https://www.johndcook.com/exact_beta_inequalities.pdf>
- Cook, J.D. *Random inequalities V: Beta distributions.* <https://www.johndcook.com/blog/2008/08/21/random-inequalities-v-beta-distributions/>
- Miller, E. *Formulas for Bayesian A/B testing.* <https://www.evanmiller.org/bayesian-ab-testing.html>
- Kruschke, J. (2013). Bayesian estimation supersedes the t test. *JEP: General* 142(2):573–603. <https://doi.org/10.1037/a0029146>
- Kruschke, J. (2018). Rejecting or accepting parameter values in Bayesian estimation (ROPE + HDI). *AMPPS* 1(2):270–280. <https://doi.org/10.1177/2515245918771304>
- Heath, Manolopoulou, Baio. *A review of methods for the analysis of the expected value of information.* <https://arxiv.org/abs/1610.03619>
- Satopää, Baron, Foster, Mellers, Tetlock, Ungar (2014). Combining multiple probability predictions using a simple logit model (extremization). *Int. J. Forecasting* 30(2):344–356. <https://doi.org/10.1016/j.ijforecast.2013.09.009>
- Walley, P. (1996). Inferences from multinomial data: learning about a bag of marbles (Imprecise Dirichlet Model). *JRSS-B* 58(1):3–57. <https://doi.org/10.1111/j.2517-6161.1996.tb02065.x>
- Rubin, D. (1981). The Bayesian bootstrap. *Annals of Statistics* 9(1):130–134. <https://doi.org/10.1214/aos/1176345338>
- Lyddon, Holmes, Walker (2019). General Bayesian updating and the loss-likelihood bootstrap. *Biometrika* 106(2):465–478. <https://arxiv.org/abs/1709.07616>
- Bissiri, Holmes, Walker (2016). A general framework for updating belief distributions. *JRSS-B* 78(5):1103–1130. <https://arxiv.org/abs/1306.6430>
- Efron, B. & Morris, C. (1975). Data analysis using Stein's estimator and its generalizations. *JASA* 70(350):311–319. Also Efron & Hastie, *CASI* ch.7: <https://efron.ckirby.su.domains/other/CASI_Chap7_Nov2014.pdf>
- Agrawal, S. & Goyal, N. Analysis of Thompson sampling for the multi-armed bandit problem. <https://arxiv.org/abs/1111.1797>
- Russo, Van Roy, Kazerouni, Osband, Wen. *A tutorial on Thompson sampling.* <https://arxiv.org/abs/1707.02038>

**Few-groups hierarchical / meta-analysis**
- Röver, Bender, Dias, Schmid, Schmidli, Sturtz, Weber, Friede (2021). On weakly informative prior distributions for the heterogeneity parameter in Bayesian random-effects meta-analysis. *Research Synthesis Methods* 12(4):448–474. <https://arxiv.org/abs/2007.08352>
- Lilienthal et al. (2024). Bayesian random-effects meta-analysis with empirical heterogeneity priors for very few studies. *Research Synthesis Methods*. <https://onlinelibrary.wiley.com/doi/full/10.1002/jrsm.1685>

**LLM-as-expert prior elicitation**
- Capstick, Krishnan, Barnaghi. *AutoElicit: using large language models for expert prior elicitation in predictive modelling.* <https://arxiv.org/abs/2411.17284> · code: <https://github.com/alexcapstick/llm-elicited-priors>
- *Had enough of experts? Elicitation and evaluation of Bayesian priors from large language models.* <https://openreview.net/forum?id=3iDxHRQfVy>
- *LLM-Prior: a framework for knowledge-driven prior elicitation and aggregation.* <https://arxiv.org/pdf/2508.03766>

**Anomaly / predictive checks**
- Bayarri, M.J. & Berger, J. (2000). P-values for composite null models. *JASA* 95(452):1127–1142. (Why posterior predictive p-values are conservative; partial posterior predictive p-values.) <https://doi.org/10.1080/01621459.2000.10474309>

**Numerics (already in the project's Part 0, repeated for completeness)**
- ASA063 — incomplete beta. <https://people.math.sc.edu/Burkardt/py_src/asa063/asa063.html>
- ASA032 — incomplete gamma. <https://people.math.sc.edu/Burkardt/c_src/asa032/asa032.html>

---

## Appendix A — Measured stdlib feasibility

Everything below was **run**, not estimated. Python 3, no third-party packages, on the
development machine. These measurements are the evidence behind the feasibility column.

| Operation | Result |
|---|---|
| Regularized incomplete beta `I_x(a,b)` via Lentz continued fraction (~25 lines) | `I_0.5(2,3) = 0.6875000000000002` (exact 0.6875); `I_0.3(5,2) = 0.010935000000000010` (ref 0.010935). **Machine precision.** |
| Cook's exact `P(Beta(a,b) > Beta(c,d))`, a=71,b=29,c=80,d=20 | `0.93245476548` in **< 0.1 ms**; 200,000-draw Monte Carlo agrees to 4 decimal places. Exact closed form is both faster and more accurate than simulation. |
| Random-walk Metropolis, 2 parameters, n = 500 data points, 4,000 iterations | **0.10 s**, acceptance 0.34, posterior mean recovered to 0.998 (truth 1.0). |
| Random-walk Metropolis, **7 parameters**, J = 5 non-centred hierarchical model, 60,000 iterations | **0.14 s**, acceptance 0.53. Pure-Python MCMC is a non-issue at agent scale. |
| 2-D grid approximation, 200 × 200 = 40,000 cells, recomputing an n = 300 likelihood at every cell | **0.6 s.** With sufficient statistics precomputed this drops to milliseconds. |

**Design consequences.** (1) MCMC is *cheap* — the binding constraint on rows 13/14 is
correctness and diagnostics, not speed, so the library should spend its budget on R̂/ESS gating
rather than on optimisation. (2) Grid approximation must reduce to sufficient statistics or cap
`G^d × n`; the naive form is the only measured operation that approaches a second. (3) Wherever
a closed form exists (row 2), it beats Monte Carlo on both axes and should be preferred without
exception.

## Appendix B — Numerics inventory: what the territory needs from the math layer

Consolidated so the shared math layer can be scoped once. Ordered by how many rows depend on it.

| Primitive | Needed by rows | Notes |
|---|---|---|
| `math.lgamma` | 1, 2, 5, 7, 15, 16, 18, 21 | stdlib. Free. |
| Regularized incomplete beta `I_x(a,b)` + inverse | 1, 2, 3, 10, 11, 17, 18 | The single highest-leverage function in the territory. Continued fraction; verified above. Inverse by bisection on `I_x`. |
| Regularized incomplete gamma `P(a,x)` + inverse | 5, 7, 16 | Series below `x < a+1`, continued fraction above. ASA032. |
| `statistics.NormalDist` (`cdf`, `inv_cdf`) | 3, 9, 15, 19, 22 | stdlib. Free. |
| `random.gammavariate` / `betavariate` / `expovariate` | 18, 20, 23, and all sampling-based rows | stdlib, correctly implemented. Free. |
| logsumexp (numerically stable) | 13, 21, 25 | Five lines. |
| Bisection / Brent root-find | 4, 6, 10, 11, 17 | Twenty lines. Used for decision-flip thresholds, robustness regions, quantile inversion, quantile-matched prior fitting. |
| Nelder–Mead (derivative-free, ≤6 dims) | 15, 22 | ~60 lines. No gradients required — this is the reason Laplace is feasible at all. |
| Dense linear algebra: determinant + solve, ≤ 6×6 | 22 | Gaussian elimination with partial pivoting. Numerically fine at this size. |
| Generalized-Pareto tail fit (2-param) | 6, 21 | Closed-form profile-likelihood estimator; **no optimiser needed**. Unlocks PSIS and thus k̂ diagnostics. |
| Rank-normalisation, split-R̂, bulk/tail-ESS, MCSE | 14, and every MCMC-backed row | Sorting + autocovariance sums. The autocovariance is O(N²) naively — use the Geyer initial-positive-sequence truncation to keep it linear-ish in practice. |
| Gauss–Legendre or adaptive Simpson quadrature (1-D) | 5, 8, 10 | Fixed 64-node Gauss–Legendre is sufficient for the JZS integral and the rate comparisons. |
