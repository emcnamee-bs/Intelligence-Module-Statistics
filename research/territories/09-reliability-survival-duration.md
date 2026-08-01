# Territory 09 — Reliability, Survival, and Duration Modeling

*Research pass: 2026-07-31. Scope: pure-stdlib Python 3, n ∈ [3, few thousand], agent-invoked from CLI.*

---

## 1. Territory summary

This territory answers the four questions an agent asks more than almost any other: *when will this
finish*, *will it survive*, *what does its age tell me*, and *when should I give up on it* — and it is
the one territory where the agent's data is **structurally incomplete by default**, because the thing
being measured is usually still running. Censoring is not an edge case here; it is the normal case, and
the single largest accuracy win in the whole territory is simply refusing to throw away the in-flight
observations the way a naive average does. The second largest win is the **hazard-shape verdict**: whether
the thing ages (Weibull k>1, remaining life shrinks with age), is memoryless (k=1, age tells you nothing),
or is Lindy (k<1 or Pareto, remaining life *grows* with age) — a three-way distinction an unaided agent
essentially never makes, and which flips the sign of its advice about a long-running process. The third
is **honest behaviour at zero failures**, where an agent's unaided instinct is either "100% reliable" or
silence, when a two-line exact bound is available. Countervailing this, the territory also contains the
best-documented failures in applied statistics — reliability growth extrapolation and software reliability
growth models — which we should ship with refusal guards rather than pretend into usefulness.

---

## 2. Ranked model table

Tiers: **INLINE** = a handful of numbers as CLI flags · **DATAFILE** = a small table on disk ·
**MUST-CONSTRUCT-DATA** = the agent has to go instrument or collect something first.

Standard input shape for this territory, referenced below as **(t, δ)**: one row per unit, `duration`
and `event` where `event=1` means it actually failed/finished and `event=0` means right-censored
("still running at time t", "was fine when I last looked").

---

### 1. Exponential MTBF / failure rate with censoring + exact χ² interval

| | |
|---|---|
| **SITUATION** | "we've run this thing for 340 hours total and seen 3 failures — what's the real failure rate?" · "how often does this break, and how sure am I?" · "mean time between failures with a confidence interval" · "6 crashes across 12 machines over 2 weeks" |
| **Inputs / tier** | Total exposure time `T` (summed across all units, censored ones included at their full observed time) and failure count `r`. **INLINE** — two numbers. |
| **Beats** | The agent's `r/T` point estimate stated with no interval, and — much worse — an average computed only over units that failed, which discards the censored exposure and inflates the rate. At r=3 the exact 90% interval spans roughly a factor of 4; agents routinely act as if the point estimate is the truth. |
| **Feasibility** | **EASY–MODERATE**. λ̂ = r/T; MTBF = T/r. Exact two-sided 100(1−α)%: `2T/χ²_{1−α/2}(2r+2) ≤ MTBF ≤ 2T/χ²_{α/2}(2r)` for time-truncated tests (use `2r` df in the upper for failure-truncated). Needs the **inverse regularized incomplete gamma** (χ² quantiles) — the same primitive Part 0 already plans via ASA032/ASA239 plus a Newton or bisection inversion. Nothing else. |
| **REFUSE when** | (a) A Laplace trend test on the failure times rejects stationarity — a single MTBF number is *meaningless* for a system whose intensity is trending; route to Crow-AMSAA instead. (b) Exposure time for any unit is unknown or estimated (the denominator is the whole game). (c) r=0 — print the one-sided lower bound only, never an MTBF point estimate and never "∞". (d) Failures are not independent (one root cause producing a burst counts as one failure, not five) — refuse unless the caller asserts independence. |

---

### 2. Zero-failure reliability bound (rule of three + exponential zero-failure bound)

| | |
|---|---|
| **SITUATION** | "200 runs, zero failures — how reliable is it actually?" · "it hasn't broken once in 6 weeks, what can I claim?" · "no errors so far, what's my upper bound on the error rate?" · "how confident can I be that this is fine?" |
| **Inputs / tier** | Either (a) `n` independent trials, 0 failures, or (b) total exposure `T` with 0 failures. **INLINE**. |
| **Beats** | Both of the agent's unaided answers. It will either say "100% reliable" (unfalsifiable, wrong) or hedge with no number. The correction is one line: with 0 failures in n trials, the 95% upper bound on failure probability is ≈ **3/n** (exactly `1−α^{1/n}`, and 3/n is the classic approximation). 200 clean runs buys you "failure rate below 1.5%", *not* "reliable". Equivalently for time: 95% lower bound on MTBF = `T/(−ln 0.05)` = `T/2.996` ≈ T/3. Six weeks clean ⇒ MTBF ≥ 2 weeks at 95%. That gap between intuition and arithmetic is the largest in the territory. |
| **Feasibility** | **EASY**. Closed form, no special functions: `p_upper = 1 − α^{1/n}`; `MTBF_lower = 2T/χ²_{α}(2)` = `T/(−ln α)` because χ²(2) has a closed-form tail. |
| **REFUSE when** | (a) The n runs are not exchangeable with the future runs being forecast — same seed, same input, same session, same machine. This is the dominant real violation for agents: 200 reruns of one cached test are n=1. Require the caller to affirm independence and vary-what-varies. (b) Any request for a *point* reliability estimate at zero failures — there isn't one worth printing. (c) The observation window did not include the conditions of interest (no zero-failure bound survives a regime change). |

---

### 3. Kaplan–Meier estimator + Greenwood / log-log CI + survival-at-horizon + median

| | |
|---|---|
| **SITUATION** | "some of these finished and some are still running — what's the distribution?" · "what fraction survive past a week?" · "typical time to failure when half my data is incomplete" · "chance it makes it to Friday" · "median lifetime with censored observations" |
| **Inputs / tier** | **(t, δ)** table, n ≥ ~5 with ≥3 events. **DATAFILE**. |
| **Beats** | The mean-of-completed-observations, which is biased *downward*, often severely — because the long-lived units are exactly the ones still censored. With 50% censoring on a Weibull the naive mean can understate the median by 40%+. Also beats the agent's implicit "drop the incomplete rows" data cleaning, which is the same error one step earlier. |
| **Feasibility** | **EASY**. Ŝ(t) = ∏_{t_i≤t}(1 − d_i/n_i). Greenwood variance; prefer the **complementary log-log** interval `Ŝ(t)^exp(±z·σ̂(t)/(Ŝ(t)ln Ŝ(t)))`, which has materially better small-sample coverage than the linear interval and is the SAS default — the linear interval is "very liberal" at small n while log-log and arcsine-√ are near-nominal down to n≈25 with 50% censoring. Median CI by Brookmeyer–Crowley (invert the pointwise band). Only needs `NormalDist.inv_cdf`. |
| **REFUSE when** | (a) **Informative censoring** — units were stopped *because* they looked like they'd fail (timeouts, manual kills, "I cancelled the ones that were clearly stuck"). KM assumes censoring is independent of the failure mechanism and agent data violates this constantly. Ask explicitly; refuse if the answer is yes and route to competing risks (#17). (b) Median requested but Ŝ never reaches 0.5 — print "median not reached, ≥ t_max" and route to RMST (#14). (c) Risk set at the requested horizon < 5 — suppress the CI, or the whole number if < 3. (d) Left truncation present (units entered observation late) without adjustment. |

---

### 4. Conditional survival & mean residual life — age-based remaining-duration ("Lindy vs mortality")

| | |
|---|---|
| **SITUATION** | "it's been running 40 days without failing — what does that tell me about tomorrow?" · "does surviving this long make it more or less likely to keep going?" · "given it's already lasted X, how much longer?" · "expected remaining time for something that's already old" · "should I trust a long-running process more or less than a fresh one?" |
| **Inputs / tier** | Current age `a`, plus **either** fitted lifetime parameters (INLINE) **or** a **(t, δ)** table to fit first (DATAFILE). Outputs: S(t\|T>a) = S(a+t)/S(a), mean residual life **m(a) = ∫₀^∞ S(a+u)du / S(a)**, and residual quantiles. |
| **Beats** | This is the single most **underused** tool in the territory and the one where agent intuition is most reliably wrong — and wrong in *both* directions depending on the case. Unaided, an agent applies folk-Lindy universally ("it's been stable for months, so it's stable") when the fitted shape often says the opposite. The verdicts differ qualitatively: **exponential** m(a) = 1/λ, constant — *age tells you literally nothing*; **Weibull k>1** m(a) decreasing — *the longer it's run, the sooner it dies*; **Weibull k<1 / lognormal far tail / Pareto** m(a) increasing — *genuine Lindy, expected remaining life grows with age*; **Pareto(α)** m(a) = a/(α−1), exactly proportional to age, the canonical Lindy law. Telling the agent which regime it is in is worth more than any single number. |
| **Feasibility** | **MODERATE**. Requires a fitted family (#5/#9/#18) plus numeric integration of S over the residual tail. Use adaptive Simpson with a tail-tail analytic remainder (closed form for exponential and Pareto; for Weibull, m(a) is an incomplete-gamma expression: `m(a) = (λ/S(a))·Γ(1+1/k, (a/λ)^k)` in upper-incomplete-gamma form). Nonparametric alternative: KM-based m̂(a) = area under Ŝ beyond a, divided by Ŝ(a) — trivial once #3 exists, and worth shipping as the assumption-free fallback. |
| **REFUSE when** | (a) The fitted family fails a goodness-of-fit check (LR against a nesting alternative, or Anderson–Darling on the uncensored subset) — the MRL verdict is *entirely* a function of the family, so an unvalidated family produces a confident wrong sign. (b) `a` exceeds ~1.5× the largest observed duration — this is pure extrapolation into the tail where families disagree most. (c) Fewer than 5 observed events. (d) Pareto with α̂ ≤ 1 — the mean does not exist; print residual *median* only. (e) A hard upper bound on lifetime exists (a timeout, a scheduled restart) — no unbounded model may be used. |

---

### 5. Weibull MLE with right censoring — the hazard-shape verdict

| | |
|---|---|
| **SITUATION** | "does this get more likely to fail the longer it runs?" · "fit a lifetime distribution to these durations, some incomplete" · "is this wearing out or burning in?" · "what's the shape of the failure curve" · "infant mortality or wear-out?" |
| **Inputs / tier** | **(t, δ)**, ≥3 uncensored events. **DATAFILE**. |
| **Beats** | Everything downstream depends on the shape parameter k, and there is no way to guess it. k<1 = decreasing hazard (infant mortality, Lindy-ish, *restarting is bad*); k≈1 = exponential/memoryless (*restarting is neutral, and age is uninformative*); k>1 = increasing hazard (wear-out, *proactive restart is good*). That last sentence is actionable operational advice an agent cannot produce unaided, and it converts directly into a restart policy. |
| **Feasibility** | **MODERATE, but pleasantly so.** The scale drops out analytically, leaving a **one-dimensional monotone score equation in k**: `Σ t_i^k ln t_i / Σ t_i^k − 1/k − (Σ_{δ=1} ln t_i)/r = 0`, sums over *all* units, the last sum over events only. Solve by bracketing + Brent/bisection — extremely robust, no matrix algebra. Then `λ̂ = (Σ t_i^k / r)^{1/k}`. CIs from the observed-information matrix (2×2 analytic inverse) or better, a profile-likelihood interval on k via a second 1-D root find on `2(ℓ̂ − ℓ(k)) = χ²_{1,1−α}`. |
| **REFUSE when** | (a) r < 3 uncensored events — k is effectively unidentified; refuse and fall back to exponential (#1) with the caveat printed. (b) All observations censored — no fit exists. (c) The profile CI for k contains 1 *and* is wide — refuse the "it's aging / it's Lindy" verdict and report "indistinguishable from memoryless at this n". This is the honest answer at n=10 and agents will otherwise over-read the point estimate. (d) MLE is known to be **biased for small n and the bias worsens with censoring fraction**; below n≈20 apply a shape bias correction or report median-rank-regression alongside and refuse if the two disagree by >25% (Genschel & Meeker find MRR competitive-to-better for low quantiles and heavy censoring, ML better for the shape at larger n — the disagreement itself is the diagnostic). |

---

### 6. Nelson–Aalen cumulative hazard + nonparametric hazard-shape diagnostic

| | |
|---|---|
| **SITUATION** | "is the failure rate constant or changing?" · "which lifetime model should I even use here?" · "before I fit anything, what does the hazard look like?" · "is this a bathtub curve?" |
| **Inputs / tier** | **(t, δ)**. **DATAFILE**. |
| **Beats** | The blind choice of exponential-because-it's-easy. Ĥ(t) = Σ d_i/n_i; plot/regress Ĥ against t. **Linear ⇒ exponential; convex ⇒ increasing hazard; concave ⇒ decreasing hazard.** Equivalently regress `ln Ĥ` on `ln t` — the slope is a fast, robust pre-estimate of the Weibull k and a sanity check on #5. Serves as the **router** for this whole territory. |
| **Feasibility** | **EASY**. Pure bookkeeping plus a least-squares line. Aalen variance Σ d_i/n_i² for bands. |
| **REFUSE when** | (a) Fewer than ~8 events — the shape verdict is noise. (b) The log-log slope CI contains 1 — report "flat within noise", do not name a shape. (c) Ties are heavy relative to n (coarse timestamp resolution, e.g. everything rounded to whole seconds when durations are seconds) — refuse, the estimator degenerates. |

---

### 7. Remaining time from partial progress (renewal-rate ETA with an honest interval)

| | |
|---|---|
| **SITUATION** | "it's done 340 of 1000 items in 12 minutes, when will it finish?" · "ETA for this job" · "how much longer" · "am I halfway?" · "progress bar says 34%, is that trustworthy?" |
| **Inputs / tier** | Best: per-item completion timestamps (**DATAFILE**, enables the interval). Minimum: items done, items remaining, elapsed (**INLINE**, point estimate + a crude interval only). |
| **Beats** | The linear extrapolation `elapsed × remaining/done`, which the agent does automatically and which is (i) point-only, with no interval, and (ii) systematically optimistic whenever per-item time is heterogeneous or trending. Two corrections matter: variance of remaining time is `m·Var(per-item)` so the **relative** interval narrows as √m — quantify it rather than assert precision; and a **trend test on per-item durations** catches the extremely common "it slows down as it goes" (growing working set, degrading cache, later items are harder). |
| **Feasibility** | **MODERATE**. Mean and variance of per-item time from the observed prefix; ETA ~ Normal(m·μ̂, m·σ̂²) by CLT for m large, or gamma-based for small m; add a Mann-Kendall / OLS-slope trend test on item duration vs index, and if the trend is significant, fit the trend and integrate it forward instead of using a flat rate. |
| **REFUSE when** | (a) Progress is non-monotone or the total is unknown/changing (very common: crawlers, recursive builds) — refuse an ETA outright. (b) Fraction complete < ~10% — the interval is wider than useful; print the interval and *suppress the point estimate* so the agent cannot quote it. (c) A significant trend is detected and the caller asked for the flat-rate answer — refuse the flat answer, give the trended one. (d) "Items" are not comparable units of work (e.g. files of wildly varying size) — require a size-weighted denominator or refuse. |

---

### 8. Optimal give-up / abandon threshold (stopping time from a fitted duration distribution)

| | |
|---|---|
| **SITUATION** | "how long should I wait before killing this?" · "when do I give up and retry?" · "is it hung or just slow?" · "what timeout should I set?" · "should I restart it or keep waiting?" |
| **Inputs / tier** | A fitted duration distribution (from #5/#9/#18) + current elapsed `a` + the cost ratio `c = cost of restarting / cost per unit time of waiting`. **INLINE** given a prior fit; **DATAFILE** otherwise. |
| **Beats** | Pure gut feel, and an entire class of agent misbehaviour (waiting 20 minutes on a process that empirically never takes more than 90 seconds; or killing at 30s something whose 90th percentile is 4 minutes). The decision rule is **entirely determined by the hazard shape**, which is why this belongs downstream of #5: with **increasing hazard (k>1)** there is a finite interior optimum — wait, then abandon at a computable threshold; with **decreasing hazard (k<1, Lindy)** the optimum is degenerate — *never* abandon once you've started, because every minute survived improves the outlook; with **constant hazard** the decision is time-invariant — either abandon immediately or never, decided purely by whether `1/λ` exceeds the restart cost. Naming which of the three regimes you're in is most of the value. |
| **Feasibility** | **MODERATE**. Minimize expected total cost `E[cost \| abandon at τ]` over τ by 1-D golden-section search over the fitted survival function; the objective involves the same truncated integrals as MRL (#4). A practical, robust alternative worth shipping alongside: the **empirical quantile rule** — set the timeout at the KM q-th percentile with a stated false-kill rate q, which needs no cost model at all. |
| **REFUSE when** | (a) No cost ratio supplied and no percentile target supplied — refuse; there is no assumption-free optimal timeout. (b) The hazard is decreasing — refuse to print a finite threshold, print "no interior optimum: under a decreasing hazard the model says do not abandon" (and say so loudly, because it contradicts intuition). (c) The fit is based on fewer than 8 events. (d) Restarts are not independent draws from the same distribution (the retry will hit the same deterministic bug) — the whole model collapses; require the caller to affirm. |

---

### 9. Lognormal lifetime MLE with right censoring

| | |
|---|---|
| **SITUATION** | "how long do these tasks usually take?" · "fit a distribution to these durations" · "repair times / recovery times / response latencies" · "most finish fast but a few take forever" |
| **Inputs / tier** | **(t, δ)**, all t > 0, ≥5 events. **DATAFILE**. |
| **Beats** | The Gaussian-on-raw-durations that an agent reaches for, which produces negative lower confidence limits and badly understates the right tail. Lognormal is the correct default for durations generated by *multiplicative* processes — repair/recovery times, human-in-the-loop delays, request latencies, anything that is a product of many small factors — and it has the distinctive hazard shape that **rises then falls**, which no Weibull can do. That non-monotone hazard is exactly the "if it hasn't finished by now, it's probably stuck for a while" pattern. |
| **Feasibility** | **MODERATE**. Censored log-likelihood in (μ, σ) on log-scale: uncensored terms are normal log-densities, censored terms are `ln(1 − Φ((ln t − μ)/σ))`. Optimize with Nelder–Mead in 2-D (well-behaved, unimodal) or an EM / Newton scheme. Needs only `NormalDist` (cdf, pdf, inv_cdf) which stdlib supplies. |
| **REFUSE when** | (a) Any duration ≤ 0. (b) < 5 events. (c) Censoring fraction > ~80% — μ and σ trade off almost perfectly and the optimizer will return something confident and meaningless. (d) A comparison against Weibull by AIC is within ~2 units — refuse to name a family, report both tail predictions, and let the divergence between them *be* the answer (the divergence in the far tail is the honest uncertainty). |

---

### 10. Memorylessness / trend guard: Laplace centroid test + TTT transform

| | |
|---|---|
| **SITUATION** | "can I assume a constant failure rate here?" · "is it getting worse over time?" · "are failures speeding up or slowing down?" · "is MTBF even a meaningful number for this?" |
| **Inputs / tier** | Ordered failure times within a known observation window `[0, T]`. **DATAFILE** (or INLINE for a short list). |
| **Beats** | The **memorylessness trap** — the single most consequential unforced error in this territory. Assuming exponential is seductive because it makes everything closed-form, and it is *wrong in a specific direction*: it says age is uninformative, which suppresses both the wear-out warning and the Lindy reassurance. This test is the gate that should run before #1 ever prints. Laplace statistic: `U = (Σt_i/n − T/2) / (T√(1/12n))` ~ N(0,1); U > 0 means intensity increasing (deteriorating), U < 0 means decreasing (improving/growing). |
| **Feasibility** | **EASY**. Closed form + `NormalDist.cdf`. The TTT-transform (scaled total-time-on-test plot: convex ⇒ IFR, concave ⇒ DFR, diagonal ⇒ exponential) is a second EASY diagnostic worth emitting in the same report. |
| **REFUSE when** | (a) The window endpoint `T` is unknown or guessed — the statistic is extremely sensitive to it and a wrong T manufactures a trend. (b) n < 4 failures. (c) Failure times are from *different* units pooled together — the Laplace test is for a single repairable system's failure process; pooling independent units is a different (and invalid) question. |

---

### 11. Crow-AMSAA / Duane power-law NHPP (reliability growth, "is it getting better?")

| | |
|---|---|
| **SITUATION** | "is the flake rate improving after my fixes?" · "are we finding bugs slower than we used to?" · "reliability growth" · "failures per week are dropping — is that real?" · "current MTBF given we've been fixing things" |
| **Inputs / tier** | Failure times from one continuously-observed system + total time T. **DATAFILE**. |
| **Beats** | Eyeballing a downward-sloping failure count, which cannot distinguish real growth from Poisson noise. Gives a testable β with a CI: intensity λ(t) = λβt^{β−1}, **β<1 = improving, β=1 = no change, β>1 = degrading**, plus an *instantaneous* MTBF (1/λ(T)) that is the right number to quote for "where are we now", as distinct from the cumulative MTBF that the agent would naively compute and that lags reality badly. |
| **Feasibility** | **EASY**. Closed-form MLE for time-truncated data: `β̂ = n / Σ_{i=1}^{n} ln(T/t_i)`, `λ̂ = n/T^β̂`. Crow's exact confidence bounds on β use χ² quantiles (already needed for #1); Fisher-matrix bounds are a 2×2 inverse. |
| **REFUSE when** | (a) **Any extrapolation request.** The National Academies panel (2015) reviewing DoD practice states plainly that they "do not support the use of these models for such predictions, absent a comprehensive validation". Print the current state; refuse to project forward. This is a hard refusal, not a warning. (b) Data spans a change in test intensity, environment, or workload — the model assumes homogeneous effort and will read a workload change as reliability growth. (c) β's CI contains 1 — refuse the "it's improving" verdict; say "no detectable trend". (d) Failures come from multiple systems that were not all tested identically. |

---

### 12. Log-rank test (censored two-group comparison), with exact permutation fallback

| | |
|---|---|
| **SITUATION** | "did my change make things last longer?" · "compare uptime before and after the fix, some still running" · "is group A failing sooner than group B?" · "A/B test on time-to-failure" |
| **Inputs / tier** | **(t, δ, group)**. **DATAFILE**. |
| **Beats** | A t-test or Mann-Whitney on raw durations, which is simply invalid with censoring and which the agent will otherwise reach for. The log-rank is the maximally powerful test under proportional hazards and uses the censored observations correctly. |
| **Feasibility** | **EASY**. Sum observed-minus-expected events at each event time; `χ² = (O−E)²/V`, 1 df — and the χ²₁ tail has the closed form `P = erfc(√(x/2))`, so **no special functions are needed at all** beyond `math.erfc`. Permutation version: shuffle group labels, recompute, 10k reps — trivially fast in pure Python at n ≤ 500. |
| **REFUSE when** | (a) The KM curves **cross** — the log-rank has near-zero power against crossing hazards and will report "no difference" when the difference is large and time-dependent. Detect the crossing and refuse; route to RMST difference (#14). (b) Either group has < 5 events — use the permutation p-value, refuse the asymptotic one. (c) Group assignment was not randomized or at least exchangeable — refuse a causal reading (this belongs as a printed refusal of *interpretation*, not of the number). |

---

### 13. Renewal process / inspection-paradox corrector (length-biased waiting time)

| | |
|---|---|
| **SITUATION** | "how long until the next one of these?" · "I just showed up — how long will I wait?" · "average gap between events vs. how long I actually have to wait" · "the current gap has already been 20 minutes, is that unusual?" · "why does the bus always take longer than the schedule says" |
| **Inputs / tier** | A list of inter-event gaps (**DATAFILE**), or mean + variance of gaps (**INLINE**). |
| **Beats** | The universal wrong answer, which is "mean gap ÷ 2". The correct expected residual wait from a random arrival is `E[X²]/(2E[X]) = (μ/2)(1 + CV²)`, which for a heavy-tailed gap distribution can be many times μ/2 — and for the exponential case is exactly μ, twice the naive answer. It also corrects the mirror error: the gap you happen to land in is **length-biased** and stochastically larger than a typical gap, so "the interval I'm currently observing is 20 minutes" is *not* evidence that the typical interval is 20 minutes. Agents get both of these wrong essentially 100% of the time, and both arise constantly in log analysis and monitoring reasoning. |
| **Feasibility** | **EASY**. Two moments and a division. The size-biased correction to recover the underlying gap distribution from length-biased samples is a reweighting by 1/x. |
| **REFUSE when** | (a) Only one gap observed, or n < 4 — the second moment is unestimable. (b) Sample CV is extreme (> ~3) with small n — E[X²] is dominated by one point; refuse the mean-based answer and give a median-based residual instead. (c) The process is not stationary (a trend test rejects) — renewal theory does not apply. (d) Note the 2024 result that the inspection paradox **can fail to occur** for certain non-renewal / dependent-interval processes: if gaps are negatively autocorrelated, refuse the standard formula. |

---

### 14. Restricted mean survival time (RMST) and RMST difference

| | |
|---|---|
| **SITUATION** | "average lifetime, but most of them haven't failed yet" · "median not reached, give me something usable" · "expected uptime over the next 30 days" · "how much longer does version B last on average than version A" |
| **Inputs / tier** | **(t, δ)** + a horizon τ; two-group form for the difference. **DATAFILE**. |
| **Beats** | The unreachable median (very common in agent data: most units still running ⇒ Ŝ never crosses 0.5) and the uncomputable mean (the largest observation is censored ⇒ the mean is not identified). RMST = ∫₀^τ Ŝ(u)du is always computable, is in units of time (interpretable: "expected running time over the next 30 days"), and **requires no proportional-hazards assumption** — making it the right two-group comparison when hazards cross and the log-rank fails. |
| **Feasibility** | **EASY** given #3 — it is the area under the KM step function, a trapezoid/rectangle sum. Variance by the standard Greenwood-based formula; the two-group difference is a simple contrast. |
| **REFUSE when** | (a) τ exceeds the largest observed time in *either* group — the area beyond the last observation is not identified; refuse, or clamp τ and say so. (b) The risk set at τ is below ~20% of the original n — the tail of Ŝ dominates the integral and is barely estimated. (c) τ was chosen *after* seeing the data to maximize the difference — refuse unless τ is pre-specified or set by an external decision horizon. |

---

### 15. Mean cumulative function (MCF) for recurrent failures in repairable systems

| | |
|---|---|
| **SITUATION** | "this same service keeps crashing — how often, and is it accelerating?" · "recurring incidents per system over time" · "failures per machine, machines observed for different lengths of time" · "how many more outages should I expect this quarter?" |
| **Inputs / tier** | Per-unit event times + per-unit observation window end. **DATAFILE**. |
| **Beats** | The category error of fitting a *lifetime* distribution to the inter-failure times of a **repairable** system. Repaired systems are not renewed; their inter-arrival times are neither i.i.d. nor exponential, and Weibull-on-gaps is a standard and serious mistake. Nelson's MCF is nonparametric, handles staggered observation windows correctly (each unit contributes only while under observation), and its slope *is* the recurrence rate. Also beats the naive "total failures / total machine-hours" which silently assumes stationarity. |
| **Feasibility** | **EASY**. At each event time, average the increment over units still under observation; cumulate. Nelson's variance formula for pointwise CIs. |
| **REFUSE when** | (a) Any unit's observation window is unknown — the risk-set denominator is wrong and the MCF bends spuriously. (b) Units are heterogeneous in a known way (different hardware, different load) and the caller wants one pooled curve — refuse the pooled curve, stratify. (c) The tail region where fewer than 3 units remain under observation — truncate the curve there rather than plotting a spike. |

---

### 16. Binomial reliability + reliability demonstration test planner

| | |
|---|---|
| **SITUATION** | "37 of 40 runs passed — what's the real pass rate?" · "how many runs do I need to be 95% sure this is 99% reliable?" · "how much testing is enough?" · "success/fail data, not durations" |
| **Inputs / tier** | `n`, `k` successes (**INLINE**); or target reliability R and confidence C to get required n (**INLINE**). |
| **Beats** | The bare `k/n`. Clopper–Pearson or Jeffreys interval; and crucially the **inverse** question, which agents never compute: to demonstrate reliability R at confidence C with zero failures allowed requires `n = ln(1−C)/ln(R)` runs — demonstrating 99% at 95% confidence needs **299 clean runs**. Printing that number is usually the whole intervention, because it reveals that the proposed test cannot possibly support the claim being made. |
| **Feasibility** | **EASY–MODERATE**. Jeffreys interval is a Beta quantile ⇒ inverse regularized incomplete beta (already a Part 0 primitive). Clopper–Pearson likewise. The planner is a logarithm. |
| **REFUSE when** | (a) Runs are correlated / not exchangeable (see #2). (b) The interval is requested when `n < 5`. (c) The demonstration plan returns an n the caller cannot run — do not silently soften; state the shortfall in reliability-that-can-actually-be-demonstrated at the affordable n. **Overlaps the proportions territory — implement once, index from both.** |

---

### 17. Competing risks: Aalen–Johansen cumulative incidence

| | |
|---|---|
| **SITUATION** | "jobs either succeed, fail, or get killed by the timeout — what fraction actually fail?" · "multiple ways this can end" · "probability of failing *from this specific cause* by day 30" · "some were cancelled for unrelated reasons" |
| **Inputs / tier** | **(t, cause)** where cause ∈ {0=censored, 1..m=exit types}. **DATAFILE**. |
| **Beats** | `1 − KM`, which **overestimates** cause-specific incidence whenever a competing exit is present — sometimes dramatically — because it treats a unit that exited via a competing cause as if it were still at risk of the cause of interest. Agent data is full of competing exits (success vs. crash vs. OOM-kill vs. manual cancel) that are routinely lumped into "censored". Aalen–Johansen: `CIF_j(t) = Σ_{t_i≤t} Ŝ(t_{i−1})·d_{ij}/n_i` — correctly weighted by overall survival. |
| **Feasibility** | **EASY** for the point estimate (bookkeeping on top of #3). Variance is messier; **use a nonparametric bootstrap** (500–2000 resamples), which at n ≤ 2000 is comfortably fast in pure Python and avoids implementing the delta-method variance. |
| **REFUSE when** | (a) The exit cause is unknown for any event — misclassifying a competing event as censored is exactly the bias this tool exists to remove, and doing it partially is worse than not using the tool. (b) The "competing cause" is actually administrative censoring (the study just ended) — that *is* censoring; classifying it as a competing event understates incidence. Force the caller to distinguish and refuse if they can't. (c) Fewer than 3 events of the cause of interest. |

---

### 18. Pareto / power-law (Lindy) lifetime fit with censoring + LR test vs exponential

| | |
|---|---|
| **SITUATION** | "does surviving longer make it *more* likely to keep surviving?" · "is this Lindy?" · "heavy-tailed durations, a few run forever" · "the longer it's been up the more I trust it — is that justified?" |
| **Inputs / tier** | **(t, δ)** with a threshold x_min. **DATAFILE**. |
| **Beats** | The folk invocation of the Lindy effect, which agents apply as a vibe. This makes it falsifiable. Pareto MLE (Hill-type, with a censoring correction): `α̂ = r / Σ ln(t_i/x_min)` summed over *all* units above threshold, r = event count. Then the Lindy law is exact: **m(a) = a/(α−1)** — remaining life is a fixed *multiple* of current age. Then test it: a likelihood-ratio against exponential, or the Clauset–Shalizi–Newman KS-based procedure for whether the power law is even a defensible description. |
| **Feasibility** | **EASY**. Closed-form MLE; LR test against exponential on the same data is one χ² tail. |
| **REFUSE when** | (a) The LR test does not reject exponential — refuse the Lindy claim, it's unsupported. (b) **A hard upper bound on lifetime exists** — timeouts, scheduled restarts, deploy cadence, session limits. This is the killer in agent contexts: almost every process an agent watches has a ceiling, and a power law asserts there is none. Refuse if any max-duration cap is configured. (c) α̂ ≤ 1 — the mean is infinite; print residual quantiles only, never a mean. (d) x_min chosen post-hoc to make the fit work. (e) fewer than 10 observations above threshold (Hill estimator is badly biased below that). |

---

### 19. Cox proportional hazards, small scale, with Firth penalization and profile-likelihood CIs

| | |
|---|---|
| **SITUATION** | "does machine type / config / input size affect time-to-failure?" · "which factor makes these die sooner?" · "hazard ratio between two conditions, adjusted" · "regression on censored durations" |
| **Inputs / tier** | **(t, δ, x₁..x_p)**, p ≤ 3. **DATAFILE**. |
| **Beats** | Comparing group means of completed durations. Gives an adjusted hazard ratio without specifying a baseline distribution. |
| **Feasibility** | **MODERATE–HARD**. Newton–Raphson on the Efron-tie partial likelihood with analytic gradient and Hessian; p ≤ 3 means the linear solve is a 3×3 explicit inverse. Firth penalization (add `½ln det I(β)` to the log-likelihood) is the harder part — implement by optimizing the penalized objective with Nelder–Mead and a numerically-computed log-determinant, which is fine at p ≤ 3. Profile-likelihood CIs by 1-D root finds. Schoenfeld-residual correlation test for the PH assumption. |
| **REFUSE when** | (a) **Events per covariate < 10** without Firth; < 5 even with it. The 2024 Jóźwiak et al. simulation found relative bias up to 72% and standard errors overstated by ~48% in small studies with low-prevalence markers, and recommends the Firth-modified score function *with profile-likelihood intervals rather than Wald* for studies below roughly 400–600 subjects. Wald intervals should not be offered at all at agent scale. (b) **Monotone likelihood / separation** — β diverges; refuse the unpenalized fit outright, only Firth may print. (c) Schoenfeld test rejects PH — refuse the single hazard ratio, route to RMST difference (#14). (d) Any covariate is perfectly collinear or near-constant. This model is ranked below the nonparametrics deliberately: at agent scale it is usually the wrong reach. |

---

### 20. Turnbull NPMLE for interval-censored / polled-monitoring data

| | |
|---|---|
| **SITUATION** | "I only check every 5 minutes, so I know it died sometime between checks" · "health check was green at 10:00 and red at 10:15" · "I don't know exactly when it failed, just a window" · "cron-based monitoring, coarse timestamps" |
| **Inputs / tier** | Per-unit `(L, R)` intervals bracketing the failure. **DATAFILE**. |
| **Beats** | The two hacks an agent uses instead: imputing the interval midpoint (understates variance, biases the curve) or imputing the right endpoint (biases everything late). **This is a genuinely common and completely unhandled agent data shape** — any polling-based monitor produces interval-censored data, and treating a poll-detected failure as an exact failure time at the poll instant is systematically wrong by up to one poll period. |
| **Feasibility** | **MODERATE**. Turnbull's self-consistency EM over the Turnbull intervals: find the maximal cliques of overlapping intervals, then iterate `p ← p·(assignment weights)` to convergence. Pure Python, converges in tens of iterations at agent scale. Right-censored data is the degenerate case (R = ∞), so this **subsumes #3** and can share one implementation. |
| **REFUSE when** | (a) Inspection times depend on the unit's state ("I checked more often on the ones that looked sick") — informative inspection breaks the estimator. (b) Poll interval is comparable to or larger than the median lifetime — refuse, there is almost no information about the shape. (c) EM has not converged within the iteration cap. |

---

### 21. Piecewise-constant / changepoint hazard (bathtub fit)

| | |
|---|---|
| **SITUATION** | "it fails a lot early then settles down" · "did the failure rate change at some point?" · "bathtub curve" · "burn-in period then steady state" · "when did things start getting worse?" |
| **Inputs / tier** | **(t, δ)** with ≥ 15 events. **DATAFILE**. |
| **Beats** | A single global rate that averages an infant-mortality phase and a steady-state phase into a number describing neither. Fitting exponential rates on either side of a changepoint τ and profiling the likelihood over τ gives both the changepoint and a test of whether the split is warranted. Directly relevant to the very common "new deploy is flaky for the first hour then fine" pattern. |
| **Feasibility** | **MODERATE**. The MLE for each segment is closed form (events/exposure within the segment), so profiling over τ is a scan over candidate event times — O(n) evaluations of a closed form. LR test for one segment vs two, with the caveat that the null distribution is nonstandard (τ is not identified under the null) — use a permutation/bootstrap null rather than a naive χ². |
| **REFUSE when** | (a) Either segment has < 3 events. (b) The estimated τ is within the first or last 10% of the time axis — that's boundary noise, not a changepoint. (c) A naive χ² p-value is requested — refuse it, only the bootstrap null is valid here. **Overlaps the changepoint-detection territory; share the machinery.** |

---

### 22. Software reliability growth: Goel–Okumoto and Musa–Okumoto (residual defect estimate)

| | |
|---|---|
| **SITUATION** | "how many bugs are left in this?" · "are we done testing?" · "defect discovery is slowing down — how close to clean are we?" · "predict remaining defects from the discovery curve" |
| **Inputs / tier** | Cumulative defect counts over test time. **DATAFILE**. |
| **Beats** | Arguably nothing, and we should say so. **Included with a hostile posture**, because agents will otherwise be asked this question and invent an answer. Goel–Okumoto (finite-failure NHPP): `m(t) = N(1−e^{−bt})`, estimates a total defect count N. Musa–Okumoto (infinite-failure, logarithmic): `m(t) = (1/θ)ln(1+λ₀θt)`, no finite N — and MO tends to fit real industrial data better precisely because assuming a finite bug count is optimistic. The comparative literature is genuinely mixed: MO / inflection-S / GO do best on industrial data, Gompertz / Yamada on open-source data, and *no model is universally applicable*; none applies at all during early testing when the failure rate is still increasing. |
| **Feasibility** | **MODERATE**. GO reduces to a 1-D root find in b after eliminating N; MO likewise. Both are notoriously non-convergent. |
| **REFUSE when** | (a) The cumulative-defect curve is **not concave** — GO's MLE has no finite solution and b̂ diverges; this happens whenever discovery is still accelerating, which is most of early testing. Detect and refuse. (b) Testing effort changed mid-stream (more testers, new test suite, different environment) — the model reads effort changes as reliability. (c) The upper confidence limit on N̂ is unbounded, which is the *usual* case — refuse to print "N remaining bugs" and print only the lower bound plus an explicit statement that the total is not identified. (d) Any request to use this as a ship/no-ship gate — refuse the framing. |

---

### 23. Gamma / Erlang model for multi-stage durations

| | |
|---|---|
| **SITUATION** | "this pipeline has 5 stages, how long end to end?" · "sum of several independent steps" · "total time for a multi-step process" · "why is my total time less variable than the individual steps" |
| **Inputs / tier** | Either per-stage durations (**MUST-CONSTRUCT-DATA** — the agent has to instrument the stages) or total durations + known stage count k (**DATAFILE**). |
| **Beats** | Adding the per-stage means and then guessing at the total's spread. The Erlang/gamma result is that variances add while the CV *shrinks* as 1/√k, so multi-stage totals are proportionally tighter than their parts — an agent's intuition tends to compound the uncertainty instead. Also yields a hazard that increases toward an asymptote, the honest "it should have finished by now" shape. |
| **Feasibility** | **MODERATE**. Gamma MLE needs digamma (implementable in ~15 lines by recurrence + asymptotic series) and a 1-D solve; with k known from structure, only the scale is free and it's closed form. Right-censoring needs the regularized incomplete gamma, already a required primitive. |
| **REFUSE when** | (a) Stages are not independent (a slow stage predicts a slow next stage) — check with a rank correlation on the instrumented data and refuse if it's significant. (b) k is not known structurally and n < 15 — the shape is poorly identified. (c) Any stage duration has a heavy tail — the sum is dominated by one stage and the gamma is wrong. |

---

## 3. Recent advances (≈ last 10 years)

**Conformal prediction for censored data (2023–2025) — the most important development for this project.**
Classical survival inference gives you a *population* curve; an agent usually wants an *individual*
guarantee ("I can promise with 90% confidence this runs at least X more minutes"). Conformalized survival
analysis delivers exactly that: a distribution-free **lower predictive bound (LPB)** on an individual's
survival time with finite-sample coverage. The line runs Candès–Lei–Ramdas (JRSS-B 2023, LPB under type-I
censoring via covariate-shift weighting), Gui–Barber–Ma (Biometrika 2024, adaptive cutoffs), and then
three 2024–2025 papers that relax the type-I assumption to general right censoring:
[Qin, Piao, Ning & Shen, *Conformal predictive intervals in survival analysis: a re-sampling approach*,
Biometrics 2025](https://arxiv.org/abs/2408.06539) (bootstrap-based, one- and two-sided, "excellent average
coverage for the lower bound … regardless of whether the working model is correctly specified");
[Holmes & Marandon, *Two-sided conformalized survival analysis*, 2024/2025](https://arxiv.org/abs/2410.24136)
(two-sided bounds for individuals similar to the uncensored population, lower bound otherwise, finite-sample
coverage under i.i.d. only); and [Sesia & Svetnik, *Conformal Survival Bands for Risk Screening under
Right-Censoring*, 2025](https://arxiv.org/abs/2505.04568) (model-agnostic survival bands via IPCW + FDR
control). **Relevance and feasibility:** split conformal with a KM-based or IPCW weighting is *pure-Python
tractable* — it is a sort, a quantile, and a reweighting on top of any point predictor we already have.
This is the single strongest candidate for a "new" tool in this territory that has no classical equivalent,
and it degrades gracefully: when the model is wrong, coverage holds and the interval just gets wide.

**Restricted mean survival time promoted from footnote to primary endpoint (2014–present).** Driven by
the recognition that proportional hazards is routinely violated, RMST has moved from a secondary summary
to a recommended primary measure — "in trials where early and late treatment effects can potentially
differ, RMST should be prioritized over a single hazard ratio", and it is preferred when the median is
not reached. For an agent this is a straight upgrade over the median in the (very common) case where most
units are still running.

**Firth-corrected Cox as the small-sample default (2020–2024).** [Jóźwiak, Nguyen, Sollfrank, Linn &
Hauptmann, *Cox proportional hazards regression in small studies of predictive biomarkers*, Scientific
Reports 14:14232, 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11190253/) quantified the damage: relative
bias up to 72% and standard errors inflated ~48% in adverse small-sample scenarios, with the Firth-modified
score function converging on >95% of datasets versus substantially lower for standard Cox. Their
recommendation — Firth **plus profile-likelihood intervals, not Wald** — should be our default and our
Wald intervals should simply not exist. Related: the "10 events per variable" rule has been shown to be
both too conservative in some settings and insufficient in others, with EPV ≥ 20 needed to eliminate bias
when low-prevalence predictors are present, and penalization recommended otherwise.

**The formal retreat from reliability-growth extrapolation (2015).** [National Research Council,
*Reliability Growth: Enhancing Defense System Reliability*, National Academies Press, 2015](https://www.nationalacademies.org/read/18987/chapter/6)
reviewed Duane, AMSAA-Crow and PM-2 and concluded the panel "do not support the use of these models for
such predictions, absent a comprehensive validation", citing the mismatch between the continuous-growth
assumption and the step-function reality of discrete fixes, and the observation that "time on test is
often not a good predictor linking time with system reliability". This is the best available citation for
making extrapolation a **refusal** rather than a caveat.

**Machine-learning survival models and their honest limits (2016–present).** Random survival forests,
DeepSurv (2018), DeepHit (2018), and transformer-based survival models are the visible advance, and they
are the wrong tool here: they need frameworks we cannot use, and the benchmark literature consistently
finds limited or no gain over a well-specified Cox/parametric model at the sample sizes an agent has
(n in the tens to low hundreds). Recording this as a *negative* result is valuable — it means the
pure-stdlib constraint costs us essentially nothing in this territory.

**Pseudo-observations and IPCW for direct regression on censored outcomes (Andersen–Perme onward).**
Jackknife pseudo-values for S(τ) or RMST convert a censored outcome into a complete one that can be fed
to ordinary least squares or GEE. This is a genuinely stdlib-friendly route to covariate effects that
sidesteps the partial likelihood entirely, and it produces coefficients on an interpretable scale
(days of RMST, or probability points of survival) rather than a hazard ratio. Worth a second pass as
a possible replacement for #19.

**Reappraisal of the inspection paradox (2024).** [*On Non-Occurrence of the Inspection
Paradox*, Stats 7(2):24, 2024](https://www.mdpi.com/2571-905X/7/2/24) characterizes conditions under
which the length-biasing effect vanishes or reverses — relevant because it means the standard
`E[X²]/(2E[X])` correction is not unconditional and needs a stationarity/independence guard.

**Small-sample Weibull: bias correction as standard practice.** The Genschel–Meeker line of work
(Quality Engineering, 2010, and follow-ups) settled the long-running ML-vs-median-rank-regression dispute
into a nuanced answer: MRR is competitive or better for low quantiles and heavily censored small samples,
ML is better for the shape at larger n, and bias correction of the ML shape estimate should be routine
below n≈20. The practical upshot for us is to **compute both and treat their disagreement as a
diagnostic**, which no single-method tool does.

---

## 4. Cut list

- **DeepSurv / DeepHit / N-MTLR / survival transformers** — require torch; and at n < 200 they lose to a
  two-parameter Weibull. Fails both constraints simultaneously.
- **Random survival forests, gradient-boosted survival** — implementable in pure Python but slow, and the
  benchmark evidence gives no accuracy gain at agent sample sizes.
- **Frailty / shared-frailty Cox** — needs numerical integration per cluster; agents rarely have a
  clustering structure they can articulate.
- **Multi-state / illness-death models** — data requirements are an order of magnitude beyond what an
  agent has; the transition-matrix machinery belongs in a Markov territory anyway.
- **Joint longitudinal–survival models** — far too heavy, no plausible agent use case.
- **Fine–Gray subdistribution hazard regression** — competing risks *regression* needs IPCW weights on top
  of Cox machinery; at agent scale the nonparametric CIF (#17) is the whole useful answer.
- **Copula-based dependent competing risks** — non-identifiable without an assumed copula; a tool that
  requires the user to assume the answer.
- **Cure / mixture-cure models** ("some jobs never finish") — genuinely tempting and a real agent
  situation, but identifying the cure fraction requires a clear KM plateau with substantial follow-up,
  which n < 100 rarely provides. Cut with regret; revisit if the KM tool shows plateaus in practice.
- **3-parameter Weibull (with threshold)** — the likelihood is unbounded as the threshold approaches the
  minimum observation; a classic trap. Refuse rather than implement.
- **Log-logistic, Gompertz, generalized gamma, Birnbaum–Saunders** — Weibull + lognormal + Pareto already
  span monotone-increasing, monotone-decreasing, hump-shaped, and Lindy hazards. More families at n < 200
  just enables overfitting-by-family-selection.
- **Accelerated life testing models (Arrhenius, Coffin–Manson, inverse power law)** — require physical
  stress covariates an agent does not have.
- **MIL-HDBK-217 / Telcordia SR-332 / FIDES parts-count prediction** — hardware-specific handbook methods,
  widely discredited even in their own field.
- **Buckley–James / rank-based AFT with unspecified error** — fragile iteration, marginal gain over
  parametric Weibull AFT.
- **Kernel hazard rate estimation** — bandwidth selection is the whole problem and is unsolvable at n < 100.
- **Bayesian nonparametric survival (Dirichlet process, beta-Stacy priors)** — MCMC; out of scope. Note:
  *parametric* Bayesian MTBF (Gamma–Poisson conjugate) is in scope and belongs in the Bayesian territory.
- **Andersen–Gill / PWP / WLW recurrent-event Cox** — Cox is already marginal at this scale; the MCF (#15)
  covers the recurrent-event need nonparametrically.
- **Jelinski–Moranda** — degenerate MLE (b̂ frequently infinite), strictly superseded by Goel–Okumoto.
- **Littlewood–Verrall, Schick–Wolverton, Yamada delayed-S** — variants of #22 with no better track record;
  including more SRGMs increases the chance of the agent finding one that "fits".
- **Duane in its original non-stochastic form** — no inference possible; Crow-AMSAA (#11) strictly dominates.
- **Fault trees / reliability block diagrams / system reliability algebra** — this is arithmetic on
  independent probabilities, which an agent does correctly unaided.
- **Markov availability models, repairman/queueing models** — belongs in a Markov-chains/queueing territory.
- **Simultaneous confidence bands for KM (Hall–Wellner, equal-precision)** — cheap, but pointwise log-log
  bands (#3) answer the agent's question ("chance it survives to Friday") and the simultaneous version
  answers a question no agent asks.
- **Left-truncation-adjusted estimators as a separate model** — folded into #3 as a required input flag
  and a refusal condition rather than a distinct tool.

---

## 5. Cross-territory overlaps

| Overlap | Detail | Resolution |
|---|---|---|
| **Counts & rates (Poisson)** | The exponential MTBF interval (#1) *is* the Garwood exact Poisson rate interval; r failures in T exposure is a Poisson count. | Implement the χ²-based exact rate interval **once**, index the same code from both territories under both phrasings ("failure rate" and "event rate"). |
| **Proportions / binomial** | Zero-failure rule of three (#2) is the one-sided Clopper–Pearson at x=0; #16 is Clopper–Pearson/Jeffreys wholesale. | Own the *reliability-demonstration framing* (n for R at C) here; own the general interval there. |
| **Changepoint detection** | #21 (bathtub changepoint), #11 (growth trend), and "did my fix work" are the same machinery with different likelihoods. | Share the profile-over-τ scan and the bootstrap null. |
| **Extreme values / heavy tails** | #18's Hill estimator and the Clauset–Shalizi–Newman power-law test are shared with tail estimation. | Shared tail-index primitive. |
| **Bayesian methods** | Gamma–Poisson conjugacy is the natural home for "similar systems fail at rate X" priors, and turns #2's zero-failure case into a posterior rather than a bound. | This territory ships the frequentist bound; the Bayesian territory ships the prior-informed version and links back. |
| **Time series / trend testing** | The Laplace test (#10) and Mann–Kendall (#7) are trend tests. | Share; index under both "is it getting worse" and "is there a trend". |
| **Regression** | Cox (#19), AFT, and pseudo-observation regression are regression with a censored response. | Keep the censoring handling here; borrow the linear-algebra and profile-likelihood utilities. |
| **Decision theory / optimal stopping** | #8's give-up threshold is an optimal-stopping problem wearing a hazard function. | Decision territory supplies the cost model; this territory supplies the survival function. |
| **Experiment design / power** | #16's demonstration-test planner is a sample-size calculation. | Same primitive, different phrasing; index from both. |
| **Model selection** | AIC/LR comparison across Weibull / lognormal / Pareto (#5, #9, #18). | Use the shared model-comparison utility; the *refusal on near-ties* is territory-specific and stays here. |
| **Queueing / renewal** | #13's inspection paradox and residual waiting time are renewal theory. | Owned here (it's a duration question); flagged from queueing. |

---

## 6. Sources

**Verified this pass:**

- Qin J, Piao J, Ning J, Shen Y. *Conformal predictive intervals in survival analysis: a re-sampling approach.* Biometrics 81(2), 2025. https://arxiv.org/abs/2408.06539 · https://academic.oup.com/biometrics/article-abstract/81/2/ujaf063/8149055
- Holmes C, Marandon A. *Two-sided conformalized survival analysis.* arXiv 2410.24136 (2024, rev. 2025). https://arxiv.org/abs/2410.24136
- Sesia M, Svetnik V. *Conformal Survival Bands for Risk Screening under Right-Censoring.* arXiv 2505.04568 (2025). https://arxiv.org/abs/2505.04568
- Yi et al. *Survival Conformal Prediction Under Random Censoring.* Stat, 2025. https://onlinelibrary.wiley.com/doi/abs/10.1002/sta4.70052
- Jóźwiak K, Nguyen VH, Sollfrank L, Linn SC, Hauptmann M. *Cox proportional hazards regression in small studies of predictive biomarkers.* Scientific Reports 14:14232, 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC11190253/
- National Research Council. *Reliability Growth: Enhancing Defense System Reliability.* National Academies Press, 2015 — Ch. on reliability growth models. https://www.nationalacademies.org/read/18987/chapter/6
- *On Non-Occurrence of the Inspection Paradox.* Stats 7(2):24, 2024. https://www.mdpi.com/2571-905X/7/2/24
- Vittinghoff E, McCulloch CE. *Relaxing the Rule of Ten Events per Variable in Logistic and Cox Regression.* Am J Epidemiol 165(6):710, 2007. https://academic.oup.com/aje/article/165/6/710/63906
- van Smeden M et al. *Adequate sample size for developing prediction models is not simply related to events per variable.* J Clin Epidemiol, 2016. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5045274/
- Heinze G, Schemper M. *A Solution to the Problem of Monotone Likelihood in Cox Regression.* Biometrics, 2001. https://www.researchgate.net/publication/227607817_A_Solution_to_the_Problem_of_Monotone_Likelihood_in_Cox_Regression
- Genschel U, Meeker WQ. *A Comparison of Maximum Likelihood and Median-Rank Regression for Weibull Estimation.* Quality Engineering, 2010. https://www.semanticscholar.org/paper/da2202a342b0ec6638ccbe78b992ed4371b549a8 · https://dr.lib.iastate.edu/handle/20.500.12876/90352/
- *Bias Corrected Weibull Parameter Estimation and Impact on Confidence Bounds.* https://www.researchgate.net/publication/345882371_Bias_Corrected_Weibull_Parameter_Estimation_and_Impact_on_Confidence_Bounds
- Barber S, Jennison C. *Pointwise confidence intervals for a survival distribution with small samples or heavy censoring.* Biometrika / PubMed 23632624. https://pubmed.ncbi.nlm.nih.gov/23632624/
- *A Brief Overview of Restricted Mean Survival Time Estimators and Associated Variances.* Stats 3(2):10, 2020. https://www.mdpi.com/2571-905X/3/2/10
- *Are restricted mean survival time methods especially useful for noninferiority trials?* PMC8329935. https://pmc.ncbi.nlm.nih.gov/articles/PMC8329935/
- *Challenges in Interpreting Survival Metrics in Clinical Trials: The Utility of Restricted Mean Survival Analyses.* ScienceDirect, 2025. https://www.sciencedirect.com/science/article/pii/S0360301625001439
- Quanterion / RMQSI. *Confidence Bounds on the Mean Time Between Failure (MTBF) for a Time-Truncated Test.* https://www.rmqsi.org/confidence-bounds-on-the-mean-time-between-failure-mtbf-for-a-time-truncated-test/
- ReliaSoft. *Chi-Squared Distribution and Reliability Demonstration Test Design.* HotWire 116. https://help.reliasoft.com/articles/content/hotwire/issue116/relbasics116.htm
- ReliaWiki. *Crow-AMSAA (NHPP)* and *Duane Model.* http://reliawiki.com/index.php/Crow-AMSAA_(NHPP) · http://reliawiki.com/index.php/Duane_Model
- ReliaSoft. *Crow-AMSAA Confidence Bounds.* https://help.reliasoft.com/reference/reliability_growth_and_repairable_system_analysis/rg_rsa/crow-amsaa_confidence_bounds.html
- Reliability Analytics Toolkit. *Confidence Limits — Exponential Distribution.* https://reliabilityanalyticstoolkit.appspot.com/confidence_limits_exponential_distribution
- AFIT STAT COE. *Reliability Test Planning for Mean Time Between Failures.* https://www.afit.edu/stat/statcoe_files/Reliability_Test_Planning_for_Mean_Time_Between_Failures2.pdf
- Whitt W. *The Inspection Paradox; The Residual Lifetime, the Age...* Columbia IEOR 6711 lecture notes. http://www.columbia.edu/~ww2040/6711F12/lect1011.pdf
- *Lindy effect* (with the Pareto/MRL derivation and the 1<ε<∞ condition). https://en.wikipedia.org/wiki/Lindy_effect
- *Risk, Randomness, and the Power of the Lindy Effect.* SIAM News. https://www.siam.org/publications/siam-news/articles/risk-randomness-and-the-power-of-the-lindy-effect/
- *The mean residual life at random age and its connection to variability measures.* Probability in the Engineering and Informational Sciences, Cambridge. https://www.cambridge.org/core/journals/probability-in-the-engineering-and-informational-sciences/article/EF266B298D5277CC853A8D888C2184DB
- Grottke M. *Software Reliability Model Study* (IST-1999-55017, Deliverable A.2). https://www.grottke.de/documents/SRModelStudy.pdf
- *A Comparative Analysis of Software Reliability Growth Models using Defects Data of Closed and Open Source Software.* IEEE. https://ieeexplore.ieee.org/document/6479816/
- Quanterion. *Models Commonly Used to Measure Reliability Growth.* https://www.quanterion.com/models-commonly-used-to-measure-reliability-growth/
- Traore I. *Reliability Growth Models* (SENG 426 notes). https://www.ece.uvic.ca/~itraore/seng426-07/notes/qual07-8.pdf
- Brookmeyer–Crowley median CI, implementation reference. https://metricgate.com/docs/median-survival-ci/
- Enhancing Survival Analysis: review of CI methods for censored data. https://medium.com/@akash.bstats/enhancing-survival-analysis-a-comprehensive-review-of-confidence-interval-methods-for-censored-e6d9fa9db0d0

**Canonical references (not fetched, standard):**

- Meeker WQ, Escobar LA, Pascual FG. *Statistical Methods for Reliability Data*, 2nd ed., Wiley 2022 — the reference text for everything in §2 rows 1–11, 15, 20, 23.
- Klein JP, Moeschberger ML. *Survival Analysis: Techniques for Censored and Truncated Data*, 2nd ed., Springer — KM, Nelson–Aalen, log-rank, competing risks, Turnbull.
- Kalbfleisch JD, Prentice RL. *The Statistical Analysis of Failure Time Data*, 2nd ed., Wiley.
- Nelson W. *Recurrent Events Data Analysis for Product Repairs, Disease Recurrences, and Other Applications*, ASA-SIAM 2003 — the MCF (#15).
- Rigdon SE, Basu AP. *Statistical Methods for the Reliability of Repairable Systems*, Wiley 2000 — Laplace test, power-law process.
- Turnbull BW. *The Empirical Distribution Function with Arbitrarily Grouped, Censored and Truncated Data.* JRSS-B 38(3), 1976.
- Aalen OO, Johansen S. *An empirical transition matrix for non-homogeneous Markov chains based on censored observations.* Scand J Statist 5, 1978.
- Clauset A, Shalizi CR, Newman MEJ. *Power-law distributions in empirical data.* SIAM Review 51(4), 2009 — the discipline for #18.
- Candès E, Lei L, Ramdas A. *Conformalized survival analysis.* JRSS-B 85(1), 2023.
- Gui Y, Barber RF, Ma C. *Conformalized survival analysis with adaptive cut-offs.* Biometrika 111(2), 2024.
- Uno H et al. *Moving beyond the hazard ratio in quantifying the between-group difference in survival analysis.* J Clin Oncol 32(22), 2014 — the RMST advocacy paper.
- Andersen PK, Perme MP. *Pseudo-observations in survival analysis.* Stat Methods Med Res 19(1), 2010.
