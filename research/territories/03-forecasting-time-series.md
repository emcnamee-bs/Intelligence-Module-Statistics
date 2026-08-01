# Territory 03 — Forecasting and Time Series

Research pass for the Intelligence Module. Scope: what an AI agent can legitimately compute about
*what happens next* using only Python 3 standard library, on series of length 5 to a few thousand —
with the very-short-series case (5–20 points) treated as the default, not the exception.

---

## 1. Territory summary

Forecasting is the territory where the agent's unaided instinct is *most* likely to be both confident
and wrong, which makes it the highest-yield place to put a verification tool. The field's single most
replicated empirical result — across the M1, M3, M4 and NN3 competitions and thirty years of
follow-up — is that **simple methods are nearly as accurate as complex ones, and combinations of
simple methods beat any of them individually**; the M4 winner beat a plain average-of-exponential-
smoothing benchmark by single-digit percentages, not by an order of magnitude. That is
liberating for a stdlib library: the methods that actually win (Theta, damped-trend exponential
smoothing, simple averaging of a small pool) are forty lines of Python each, and the elaborate
methods that are infeasible here would not have bought much anyway. The second replicated result is
darker and matters more for agent calibration: **prediction intervals from fitted models are
systematically too narrow**, because the standard formulas condition on the fitted model being the
true data-generating process and ignore parameter, model-selection and structural-change
uncertainty — Hyndman and Billah say so explicitly in the Theta paper itself. So the deliverable
here is not "a forecast"; it is a point estimate the agent could have roughly guessed, wrapped in an
*empirically calibrated* interval it could not have guessed, plus a rolling-origin scorecard that
says whether the model beats doing nothing at all.

---

## 2. Ranked model table

Ranking = (how often an agent faces the situation) × (margin over the agent's unaided guess) ×
(stdlib feasibility). Input tiers: **INLINE** = a handful of numbers as CLI flags; **DATAFILE** = a
small series in a file; **MUST-CONSTRUCT-DATA** = the agent has to go build the series first.

| # | Model / method | SITUATION (agent phrasing, for keyword retrieval) | Minimum viable inputs | Beats what | Stdlib feasibility | Failure modes → REFUSE |
|---|---|---|---|---|---|---|
| 1 | **Rolling-origin backtest + MASE scorecard** (Tashman 2000; Hyndman & Koehler 2006) | "is my forecast any good"; "should I trust this projection"; "which of these two estimates is better"; "am I actually beating a guess" | `--series` (n ≥ 8), `--h`, `--methods`. DATAFILE | The agent's habit of trusting a fitted line because it looks right. MASE < 1 means you beat the in-sample one-step naive; MASE ≥ 1 means **print the naive forecast instead**. This is the gate every other row passes through | **EASY**. Loop, refit, mean absolute error, scale by in-sample naive MAE | < 5 usable origins (needs roughly n ≥ h + 8); comparing methods refit on different windows; any leakage of future data into deseasonalisation or scaling |
| 2 | **Theta method / SES-with-drift** (Assimakopoulos & Nikolopoulos 2000; Hyndman & Billah 2003) | "what's next month's number"; "extrapolate this trend but don't be silly about it"; "forecast this short series"; "project this forward a few periods" | `--series` (n ≥ 5), `--h`. DATAFILE | Naive and linear regression both. Won M3 outright over 3,003 series. Halves the OLS slope, so it degrades gracefully toward naive as noise rises — exactly the right behaviour at n = 8. **Does not beat naive** on random-walk-like data (prices, FX, anything with no persistent drift) | **EASY**. OLS line + SES; α by 1-D golden-section search on SSE. Closed-form PI available | n < 5; a level shift in the last ~20% of the series (Hyndman & Billah's own worst case, series N0529, was a level shift); strictly multiplicative growth without a log transform |
| 3 | **Damped-trend exponential smoothing, ETS(A,Aₙ,N)** (Gardner & McKenzie 1985, 2011) | "this is growing, how much longer"; "extend this trend but it can't grow forever"; "is the growth slowing"; "conservative projection" | `--series` (n ≥ 7), `--h`. DATAFILE | Undamped Holt, which over-extrapolates and blows up at long h. Fildes et al. (2008) call it "a benchmark forecasting method for all others to beat." Gardner & McKenzie's explanation: on M3, the fitted parameters produced a *true* damped trend only ~43% of the time — the rest collapsed to random walk, SES, or deterministic trend, i.e. the method auto-selects its own special cases | **MODERATE**. 3 parameters (α, β\*, φ) → Nelder–Mead on SSE, ~200 evals, milliseconds. Constrain φ ∈ [0.80, 0.98] | n < 7 (3 params + 2 initial states); trend estimated from < 5 points; series that is a cumulative running total (monotone by construction — damping is meaningless) |
| 4 | **Forecast combination — simple mean / median of a small pool** (Bates & Granger 1969; Makridakis et al. 2020; Smith & Wallis 2009) | "which model should I use"; "the models disagree"; "give me one number from several estimates"; "combine these forecasts" | 2–5 forecast vectors, or `--series` + `--pool naive,ses,theta,damped`. DATAFILE | Picking the single best-on-backtest model, which is the agent's instinct and is *worse* — the winner was partly lucky. In M4, **12 of the 17 most accurate methods were combinations**, and 5 of the top 6 submissions were combination implementations. The combination puzzle: estimated optimal weights carry finite-sample error that exceeds the theoretical gain | **EASY**. Arithmetic mean or median across methods. Prefer **median** with ≥ 3 members — one member blowing up cannot drag it | Fewer than 2 genuinely distinct members (averaging SES with SES is not a combination); members with wildly different bias signs and no diagnosis of why; estimating weights from < ~30 rolling-origin errors per member — refuse to weight, fall back to the mean |
| 5 | **Empirical / conformal prediction intervals from rolling-origin errors** (Williams & Goodman 1971; Chatfield 1993; Gibbs & Candès 2021) | "what's a defensible range"; "how confident should I be in this forecast"; "worst case / best case for next month"; "give me an 80% interval" | Rolling-origin h-step errors (≥ 10 per horizon), or `--series` + method. DATAFILE | Model-based Gaussian intervals, which are **known to be too narrow**. Hyndman & Billah state it in-line about their own formula: "this formula does not include the variation due to estimation error and will therefore give intervals which are too narrow." Empirical intervals absorb parameter error, model misspecification and non-Gaussian tails because they are measured, not derived | **EASY**. Empirical quantiles of signed h-step errors (asymmetric, which is correct). Adaptive Conformal Inference is a one-line online update: αₜ₊₁ = αₜ + γ(target − 1{yₜ ∈ Cₜ}) | < 10 errors at that horizon (fall back to a Gaussian interval **inflated by a documented factor**, and label it as such); errors that are themselves trending or heteroscedastic; reusing h=1 errors to build an h=6 interval |
| 6 | **Simple exponential smoothing, ETS(A,N,N)** (Brown 1959; Hyndman et al. 2002) | "what's the current level"; "smooth out this noise"; "this bounces around, what's the real value"; "flat forecast" | `--series` (n ≥ 5), `--h`. DATAFILE | The last observation (naive) when there is measurement noise but no trend; and the full-sample mean when the level drifts. Optimal for the local level model / ARIMA(0,1,1) | **EASY**. One parameter, golden-section search on SSE over α ∈ (0,1) | Visible trend (F_T > ~0.4) — SES will lag persistently; strong seasonality; n < 5 |
| 7 | **Naive, seasonal-naive, drift and mean baselines** (Hyndman & Athanasopoulos, *FPP3* §5.2) | "just tell me the simplest reasonable guess"; "what's the baseline"; "is a model even worth it here" | `--series` (n ≥ 2, or ≥ m+1 for seasonal). DATAFILE / INLINE | Everything, surprisingly often. Naive is optimal for a random walk and is the correct answer for most financial and price series. Seasonal-naive is very hard to beat on strongly seasonal data. The tourism competition found naive very strong at yearly frequency. **This row's job is to be the thing other rows must beat** | **EASY**. σ̂ₕ formulas: mean σ̂√(1+1/T); naive σ̂√h; seasonal naive σ̂√(k+1) with k = ⌊(h−1)/m⌋; drift σ̂√(h(1+h/(T−1))) | Seasonal naive with < 2 full cycles observed; drift computed from only the first and last points when those are outliers (it literally is y_T + h(y_T−y₁)/(T−1) — two points decide everything) |
| 8 | **Reference-class / outside-view base-rate forecasting** (Kahneman & Tversky 1979; Flyvbjerg 2006) | "how long will this take"; "how much will this cost"; "am I being optimistic"; "what usually happens with things like this" | `--inside-estimate`, `--class-mean`, `--rho`; or a reference distribution of past outcomes. INLINE or MUST-CONSTRUCT-DATA | The inside view, by a very large margin. K&T's regression-corrected estimate: `corrected = class_mean + ρ·(inside − class_mean)`, ρ ≈ 2·(pairwise ordering accuracy) − 1. Batselier & Vanhoucke (2016) tested reference-class forecasting head-to-head against Monte Carlo and earned-value forecasting on real project data: "RCF indeed performs best, for both cost and time forecasting." Flyvbjerg's Hong Kong leave-one-out test: the P50 uplift sufficed in 9/18 cases, the P80 in 14/18 — i.e. the quantiles are *calibrated*, not merely conservative | **EASY** arithmetically. The hard part is the reference class, which is retrieval, not maths | No defensible reference class (< ~5 comparable prior outcomes) — refuse, and say so rather than inventing a multiplier; a reference class the agent selected *after* seeing the inside estimate; **heavy-tailed classes where the mean does not exist** (see failure note below) |
| 9 | **Monte Carlo throughput sampling → completion date** (Vacanti; Magennis) | "when will this be done"; "how many sprints left"; "will we finish by Friday"; "probability we ship this month" | `--throughput` (≥ 6–11 historical periods of items-completed), `--remaining` items. INLINE or DATAFILE | Velocity/story-point division (`remaining ÷ average velocity`), which returns a single date with no distribution and is systematically optimistic because it uses the mean of a right-skewed throughput distribution. Resampling returns the whole completion-date distribution, so the agent can quote a P85 instead of a P50 it will then miss | **EASY**. Sample historical throughput with replacement, accumulate until remaining ≤ 0, repeat 10k times, take quantiles. Pure `random.choice` | Fewer than ~6 historical periods; throughput with an obvious regime change (team size change, holiday) inside the sample window; scope that is still growing — refuse unless a scope-creep rate is supplied |
| 10 | **Kaplan–Meier / parametric survival for time-to-completion** (Kaplan & Meier 1958) | "how long do these usually take"; "some are still open, what's the typical duration"; "median time to resolve"; "how long until this ticket closes" | `--durations` with a `--censored` flag per item (n ≥ 8, ≥ 4 events). DATAFILE | **The mean duration of the completed items only — which is the agent's default and is biased downward**, because the still-open long-running items are precisely the ones excluded. Kaplan–Meier uses the censored observations as the partial information they are: Ŝ(t) = Π(1 − dᵢ/nᵢ). This bias-correction, not the curve, is the reason the row exists | **EASY**. KM is a sorted loop over event times. Greenwood's formula gives the variance. Weibull/log-logistic MLE by Nelder–Mead is MODERATE and rarely needed at n < 30 | **Refuse to report a median when Ŝ(t) never falls below 0.5** — the median is not reached and is not estimable; report the largest quantile that *is* reached instead. Also refuse when censoring is informative (items cancelled *because* they were slow — this breaks the independent-censoring assumption and biases the estimate the wrong way), and when n < 8 or events < 4 |
| 11 | **PERT / three-point beta estimate** (Malcolm et al. 1959; Grubbs 1962; Herrerías-Velasco et al. 2011) | "optimistic, likely, pessimistic — what's the expected duration"; "three-point estimate"; "how long will this task take"; "range for this effort" | `--optimistic --most-likely --pessimistic` (3 numbers). **INLINE** — the friendliest row in the territory | The most-likely value alone, which ignores the right skew that dominates task durations. μ = (o + 4m + p)/6 | **EASY**, but see below — the *classical variance is wrong* | Elicited bounds that are not real bounds. Buehler's thesis study is the datum that should govern this tool: predicted 33.9 days, *stated worst case* 48.6 days, **actual 55.5 days** — the pessimistic end of the three-point estimate was below the realised mean. A tool that prints (p−o)/6 as σ without warning is complicit |
| 12 | **Theil–Sen slope + Mann–Kendall trend test** (Sen 1968; Mann 1945) | "is this actually trending or is it noise"; "is the slowdown real"; "has this gotten worse"; "is the increase significant" | `--series` (n ≥ 6). DATAFILE | Eyeballing a chart, and OLS slope, which a single outlier can flip. Theil–Sen (median of all pairwise slopes) has ~29% breakdown; Mann–Kendall needs no distributional assumption and has an exact null distribution for n ≤ 10, which is precisely the agent's regime | **EASY**. Theil–Sen = median of n(n−1)/2 pairwise slopes; MK S = Σ sign(yⱼ − yᵢ), Var(S) = n(n−1)(2n+5)/18 | **Autocorrelation inflates the type-I error badly** — with positively autocorrelated data MK will declare trends that are not there. Refuse (or apply Hamed–Rao variance correction) when lag-1 autocorrelation is materially positive. Also refuse on seasonal data without using the seasonal MK variant |
| 13 | **Threshold-crossing time from a fitted trend (inverse prediction)** | "when will this hit X"; "when do we run out of disk"; "when does this cross the limit"; "how long until we breach the SLO" | `--series`, `--threshold`. DATAFILE | Dividing the gap by the last observed delta, which produces a date with no interval at all. Point estimate t\* = (c − a)/b from ŷ = a + bt | **MODERATE**. Point estimate is trivial; the *interval* is a ratio of two estimates and requires Fieller's theorem, which is closed-form but fiddly | **This row has the single sharpest refusal rule in the territory: if the slope's confidence interval contains zero, the crossing-time interval is unbounded or disjoint, and the tool must refuse to print a date.** Also refuse when the threshold is far outside the observed range (extrapolation beyond ~1× the data span), or when the series is bounded (a percentage approaching 100%) and a linear model would cross the bound |
| 14 | **Automatic ETS selection over a restricted pool by AICc** (Hyndman et al. 2002) | "pick the right model for this series"; "does this have a trend or seasonality"; "fit the best simple forecaster" | `--series` (n ≥ 10 non-seasonal, ≥ 2m + 5 seasonal), `--h`. DATAFILE | Manual model choice. AICc = AIC + 2k(k+1)/(n−k−1) is "a proxy for the one-step forecast out-of-sample MSE" and automatically penalises the parameter count that short series cannot support | **MODERATE**. Restrict to {ANN, AAN, AAdN, AAA, AAdA} — 5 models × Nelder–Mead. Skip multiplicative-error and multiplicative-trend forms | n ≤ k + 1 (AICc denominator goes negative — hard refuse); seasonal models with < 2 full cycles; comparing AICc across different transformations of y (log vs level) — invalid |
| 15 | **STL / classical decomposition + trend and seasonal strength** (Cleveland et al. 1990; Wang et al. 2006) | "is this seasonal"; "strip out the weekly pattern"; "is the underlying trend up"; "is this month actually bad or is it just January" | `--series` (n ≥ 2m + 1), `--period`. DATAFILE | Comparing raw month-over-month numbers, which is the most common agent error on seasonal data. F_T = max(0, 1 − Var(R)/Var(T+R)); F_S = max(0, 1 − Var(R)/Var(S+R)) — both in [0,1] and both excellent *routing* features | **MODERATE**. Classical additive/multiplicative decomposition (centred MA + seasonal means) is EASY; genuine STL with LOESS is HARD but rarely necessary at this scale | Fewer than 2 full cycles — refuse to report a seasonal index at all; unknown or non-integer period; multiplicative decomposition on a series containing zeros or negatives |
| 16 | **Croston / SBA / TSB for intermittent series** (Croston 1972; Syntetos & Boylan 2005; Teunter et al. 2011) | "mostly zeros with occasional spikes"; "sporadic demand"; "rare events per period"; "how many will we get next month" | `--series` (n ≥ 12 with ≥ 3 non-zero periods). DATAFILE | SES applied directly, which Croston showed is positively biased right after a demand period ("issue point bias"). **SBA** applies the (1 − α/2) correction for Croston's own inversion bias and "constitutes the benchmark against which other proposed methodologies in the area are assessed" | **EASY**. Two SES recursions (size, interval) + the correction factor. Route with the SBC scheme: ADI cutoff 1.32, CV² cutoff 0.49 — **these two constants are UNVERIFIED against primary text (§6.0); check before shipping as defaults** | < 3 non-zero observations; obsolescence (a long zero tail) — Croston and SBA *never revise downward* during zero periods, which is exactly the case TSB was built for, so route to TSB rather than printing a stale Croston number |
| 17 | **Local level / local linear trend structural model via Kalman filter** (Harvey 1989; Durbin & Koopman 2012) | "what's the underlying signal under this noise"; "I have gaps in the data"; "measurements are irregular"; "estimate the true current level and its uncertainty" | `--series` with gaps allowed, `--h`. DATAFILE | ETS, in exactly two situations: **missing observations** and **irregular time spacing**, which the Kalman recursion handles natively and exponential smoothing does not. Also returns a variance on the level, not just a point | **MODERATE**. Scalar Kalman filter is ~30 lines; variances by Nelder–Mead on the diffuse log-likelihood. At steady state the gain equals the SES α, and the reduced form is ARIMA(0,1,1) — so on a complete, regular series it buys nothing over row 6 | Diffuse initialisation done wrong (a common silent bug — validate against SES on a complete series); n < 10 for a two-variance model; using it on regular complete data where SES is equivalent and cheaper — the tool should say so rather than dress up SES as a Kalman filter |
| 18 | **Logistic (Verhulst) and Gompertz growth curves** | "when does this saturate"; "what's the ceiling"; "adoption curve"; "S-curve, how high does it go" | `--series` (n ≥ 8), ideally spanning the inflection. DATAFILE | Linear extrapolation, which is unbounded and absurd for anything with a natural ceiling. Logistic y(t) = K/(1 + e^(−r(t−t₀))), inflection at K/2; Gompertz y(t) = K·e^(−b·e^(−ct)), inflection at K/e ≈ 0.368K | **MODERATE**. 3 parameters by Nelder–Mead on SSE; needs sensible starts (K₀ ≈ 1.2·max(y)) | **The carrying capacity K is very poorly identified until the series passes its inflection point.** Before the inflection, logistic and exponential growth are nearly indistinguishable and K is essentially unconstrained by the data — early-pandemic logistic case-count fits were the mass-scale demonstration. If the last observation is below the fitted inflection, the tool must refuse to print K (report the growth rate only) |
| 19 | **Little's Law** (Little 1961) | "how long is this taking end to end"; "what's our cycle time"; "how much work in progress can we handle"; "what throughput do we need" | `--wip`, `--throughput` (or any two of L, λ, W). **INLINE** | Guessing cycle time from a couple of remembered tickets. L = λW is exact, distribution-free, and needs no assumptions about arrival or service distributions | **EASY** (one division) — the entire difficulty is validity checking, which is where the tool earns its keep | Refuse unless the observation window is a genuine steady state: arrivals ≈ departures over the window, all items that entered eventually exited, the window begins and ends with comparable WIP, and units are consistent. The **flow-debt** failure — WIP accumulating because departures lag arrivals — makes the computed W an understatement of what new work will actually experience, and is the single most common misapplication in Kanban practice |
| 20 | **Restricted-grid ARIMA** (Box & Jenkins; Hyndman & Khandakar 2008) | "fit an ARIMA"; "is there autocorrelation structure I can exploit"; "model this properly" | `--series` (n ≥ 20 preferred), `--h`. DATAFILE | Occasionally beats ETS on series with genuine short-lag autoregressive structure. **Usually does not beat Theta or damped trend at n < 30**, and honesty about that is the point of this row's existence | **HARD** for full ML estimation with a seasonal component; **MODERATE** if restricted to d ∈ {0,1}, p + q ≤ 2, conditional-sum-of-squares estimation | n < 20 for anything beyond one parameter — the fpp3 experiment is decisive here: fitting ARIMA to 152 annual M3 series with fewer than 20 observations, AICc chose **zero parameters for 21 series, one parameter for 86, two for 31, three for 13, and four for exactly one**. Hyndman: there is "no justification for the magic number of 30." Refuse seasonal ARIMA below 3 full cycles |
| 21 | **Kingman's VUT approximation and M/M/1 / M/M/c waiting time** (Kingman 1961) | "will adding load blow up latency"; "how much headroom do we need"; "why is the queue so long at 85% utilisation"; "should we add a worker" | `--utilisation`, `--service-time`, and CVs of arrival and service (defaults 1). **INLINE** | Linear intuition about utilisation. Wq ≈ (ρ/(1−ρ))·((c_a² + c_s²)/2)·τ makes the hyperbolic blow-up explicit — the agent's mental model that 90% utilisation is "a bit worse than 80%" is wrong by a factor of ~2.25 in the ρ/(1−ρ) term alone | **EASY**. M/M/c requires the Erlang-C sum, which is a short loop | ρ ≥ 1 — hard refuse, the queue is unbounded and no finite number is correct. Also refuse when the observation window is short enough that ρ is estimated to within ±0.05 of 1, since Wq is then arbitrarily sensitive. Kingman's is a **heavy-traffic** approximation: it degrades at low ρ, and it silently assumes a single unbounded FIFO queue (no batching, no priorities, no balking) |
| 22 | **Bass diffusion model** (Bass 1969) | "how fast will this get adopted"; "when does uptake peak"; "new product / new feature adoption curve" | `--series` of cumulative adoptions (n ≥ 10). DATAFILE | Logistic fitting, when there is a genuine distinction between external influence (p, advertising/discovery) and internal influence (q, word of mouth). Peak at t\* = ln(q/p)/(p+q) | **MODERATE**. 3 parameters (m, p, q) by Nelder–Mead, or the classic OLS-on-quadratic estimator as a starting point | Same K-identifiability problem as row 18, worse: m, p and q trade off strongly pre-peak. Refuse to print m before the observed peak. Also refuse when the series is not cumulative adoptions of a fixed-population product |
| 23 | **Temporal aggregation (ADIDA / MAPA-lite)** (Nikolopoulos et al. 2011; Kourentzes et al. 2014) | "this data is too noisy at daily level"; "should I look at weekly instead"; "the numbers jump around too much" | `--series`, `--aggregation-level`. DATAFILE | Modelling a noisy high-frequency series directly. Aggregating buckets up attenuates noise and can strengthen the trend signal, then the forecast is disaggregated back. Especially effective for intermittent series, where it converts zeros into counts | **EASY**. Non-overlapping (or overlapping) block sums plus a disaggregation profile | Aggregation that destroys the seasonality of interest (never aggregate across the seasonal period you care about); fewer than ~5 aggregated buckets; disaggregating with a profile estimated from fewer than 2 cycles |

### 2.1 Implementation notes on the top rows

**Theta (row 2)** — the practically useful formulation is Nikolopoulos et al.'s, not the original
algebra. Fit OLS `ŷ = α̂ + β̂t`. Then `Z_t(θ) = θ·y_t + (1−θ)(α̂ + β̂t)`. Classic Theta is
θ₁ = 0, θ₂ = 2, combined 50/50 — which is exactly recomposition, since
`0.5·Z_t(0) + 0.5·Z_t(2) = y_t`. Hyndman & Billah's equivalent closed form:

```
X̂_n(h) = SES_n(h) + (b̂₀/2)·( h − 1 + 1/α − (1−α)^n / α )
```

with underlying state space `X_t = ℓ_{t−1} + b + ε_t`, `ℓ_t = ℓ_{t−1} + b + αε_t` — i.e.
ARIMA(0,1,1) with drift — giving the closed-form interval
`X̂_n(h) ± 1.96σ√((h−1)α² + 1)`. Their M3 annual results (sMAPE averaged over h = 1…6): original
A&N Theta **16.90**, their reimplementation **16.62**, MLE-optimised SES-with-drift **16.55**. The
margin between "the M3 winner" and "SES with a fitted drift" is 0.35 sMAPE points. That number is
the best single calibration of how much sophistication is worth in this territory.

The **Optimised Theta** generalisation (Fiorucci et al. 2016) keeps θ₁ = 0 and optimises θ₂ = θ ≥ 1,
with the recomposition weight forced to `ω = (θ₂ − 1)/(θ₂ − θ₁)` — the unique weight for which the
decomposition reconstructs the original series (their Theorem 1, requiring θ₁ ≤ 1 ≤ θ₂). Forecast:
`Ŷ_{t+k|t} = (1 − 1/θ)[α̂ + β̂(t+k)] + (1/θ)·Ẑ_{t+k|t}(θ)`. One extra scalar to optimise; worth it
above n ≈ 20, not below.

**Damped trend (row 3)** —
```
ℓ_t = α·y_t + (1−α)(ℓ_{t−1} + φ·b_{t−1})
b_t = β*(ℓ_t − ℓ_{t−1}) + (1−β*)·φ·b_{t−1}
ŷ_{t+h} = ℓ_t + (φ + φ² + … + φ^h)·b_t
```
The bounded sum `Σφ^i → φ/(1−φ)` is the whole point: forecasts approach an asymptote instead of
diverging. Do **not** let φ → 1 in the optimiser; clamp to [0.80, 0.98].

**PERT (row 11) — the classical variance is inconsistent with the classical mean.**
The beta-PERT whose mode is m and whose mean is (o + 4m + p)/6 has α + β = 6, and its true variance
is `(μ − o)(p − μ)/7`, **not** `((p − o)/6)²`. The ratio of true to classical variance is
`R(δ) = 5/7 + (16/7)·δ(1−δ)` with `δ = (m − o)/(p − o)`.

*Verified numerically during this pass:* α + β = 6 exactly, the classical mean and the beta mean
agree to machine precision, and the `(μ−o)(p−μ)/7` identity holds to machine precision at every δ.

| δ (mode position) | R = Var_true/Var_classical | SD_true / SD_classical |
|---|---|---|
| 0 or 1 (extreme) | 0.714 | 0.845 — **classical overstates SD by 18.3%** |
| 0.05 | 0.823 | 0.907 |
| **0.14645** | 1.000 | **1.000** — exact |
| 0.25 | 1.143 | 1.069 |
| **0.50 (symmetric)** | 1.286 | **1.134** |
| **0.85355** | 1.000 | **1.000** — exact |

The classical σ is exact only at δ = 0.14645 and δ = 0.85355. For a **symmetric** estimate
(δ = 0.5) the classical SD is **11.8% below the true SD** — equivalently, the true SD is **13.4%
higher** than the classical one. At extreme modes the classical formula **overstates** SD by up to
**18.3%**.

**Treat this as a bug class, not a footnote: textbook PERT is optimistically narrow in exactly the
common symmetric case**, which is the case an agent will hit most often when it has no strong view
about skew. A tool that prints `(p − o)/6` as σ is under-reporting uncertainty by ~12% precisely
when the user is least equipped to notice. Use `√((μ−o)(p−μ)/7)`.

Grubbs (1962) showed
exactly three beta shapes satisfy both the classical mean and σ = range/6 under mode-matching:
(4,4), (3+√2, 3−√2) and (3−√2, 3+√2). Herrerías-Velasco et al. (2011) is the modern correction.
Farnum & Stanton (1987): the mean formula degrades unless `o + 0.13(p−o) < m < p − 0.13(p−o)`.
Modified PERT uses `μ = (o + λm + p)/(λ+2)` and `Var = (μ−o)(p−μ)/(λ+3)`, with λ ≈ 2.5–3.0
recommended (λ = 4 is already a thin-tailed prior).

The 1959 originating paper knew: "this simplification gives biased estimates such that the estimated
expected time of events are always too small." Clark (1962): "it is not suggested that the beta or
any other distribution is appropriate." Roos & den Hertog (2020) computed distributionally robust
bounds over *all* distributions matching support and mean and found "the effect of PERT's assumption
regarding an underlying beta distribution is limited" — converging with Hajdu & Bokor (2016) on the
conclusion that **the distribution-family argument is a red herring; network topology and variance
magnitude are what move the answer.** Spend implementation effort on widening elicited ranges, not
on choosing between beta and triangular.

**Reference class (row 8) — the heavy-tail refusal.** Flyvbjerg et al. (2022), on 5,392 IT projects,
fit a power law `p(x) = 0.65·(x/2.0)^−2.3` with α = 2.3 (sd 0.058) and 26.5% of observations in the
tail, beating lognormal (Vuong LLR 3.55, p < 0.001). Critically, over the tail range
7.1 ≤ x₀ ≤ 18.8 the estimated α < 2, so in their own words "the average cost overrun for IT projects
does not exist (i.e., cannot be calculated)." **A tool asked for an expected overrun on an IT
project must refuse to print a mean and print quantiles instead.** The transport uplift table with
real confidence levels (Flyvbjerg 2006): roads P50 +15% / P80 +32% (n=172); rail P50 +40% / P80 +57%
(n=46); fixed links P50 +23% / P80 +55% (n=34).

The Edinburgh Tram is the cleanest cautionary tale for this library specifically: Arup computed a P80
of £400m (×1.57) in 2004; the 2007 business case applied **zero** optimism-bias uplift, substituting
a "P90 Monte Carlo contingency." Outturn £776m and three years late = **+55.8%**, almost exactly the
57% rail P80 it declined to apply. **Running a Monte Carlo does not substitute for an outside-view
uplift — quantitative risk analysis is inside-view and imports the same bias.** If the library ships
both row 9 and row 8, it must say this.

**Growth curves (row 18) — why K must be refused pre-inflection.** The refusal rule is a statement
about where the *curvature information* lives, and it follows from the model geometry rather than
from any empirical constant. Logistic `y = K/(1 + e^(−r(t−t₀)))` has its inflection at y = K/2;
Gompertz `y = K·e^(−b·e^(−ct))` at y = K/e ≈ 0.368K. Below the inflection the second derivative is
still positive and increasing, so the data are consistent with a very wide family of (K, r) pairs
trading off against each other — a larger K with a slower r fits essentially as well. Only after the
inflection does the *deceleration* appear, and deceleration is the only feature of the data that
constrains K at all. Two consequences for the tool:

- If the last observation lies below the fitted inflection, **refuse to print K or a saturation
  date**; report the current growth rate and doubling time only.
- Even past the inflection, report K as an interval from a residual bootstrap, never as a point.
  Report the fitted inflection position alongside it so the caller can see how much deceleration
  the estimate is actually resting on.

The mass-scale demonstration is the COVID-19 curve-fitting episode. Jewell, Lewnard & Jewell (2020),
*Caution Warranted: Using the Institute for Health Metrics and Evaluation Model for Predicting the
Course of the COVID-19 Pandemic*, Ann Intern Med 173(3):226–227, is the canonical critique of
projecting a fitted saturating curve from pre-inflection data. Ioannidis, Cripps & Tanner (2022) is
worth citing **for its failure taxonomy and its prescription to model predictive distributions
rather than point estimates** — it does *not* supply numeric forecast-error magnitudes, so it must
not be cited as if it did.

I did not obtain a verified published constant for "what fraction of K must be observed before K is
estimable." The ≥ inflection rule above is derived, not cited; **treat it as a documented heuristic
and do not promote it into a lookup table.**

### 2.2 Cross-cutting refusal rules

These bind every row and belong in shared validation, not per-model code:

- **n < 4** — refuse all modelling; echo the observations and their range.
- **n < 2m + 1** — refuse any seasonal component. Below 3 full cycles, refuse seasonal ARIMA.
- **n ≤ k + 1** — refuse AICc (its denominator is negative or zero).
- **Level shift detected in the last ~20% of the series** — refuse trend extrapolation, or refit from
  the break and say which. Structural breaks are the dominant killer of extrapolation, and they are
  detectable cheaply (CUSUM, or a two-segment SSE comparison).
- **Cumulative series modelled as a flow** — a running total is monotone by construction; trend tests
  and damped trend are meaningless on it. Detect monotonicity + the phrase "total" and refuse.
- **Irregular time spacing** where the model assumes regular spacing.
- **< 5 rolling-origin folds** — print the MASE but refuse to declare a winner between methods.
- **Bounded quantities** (proportions, percentages, counts) whose Gaussian interval crosses the bound
  — refuse or transform, never print a 112% upper bound.

---

## 3. Recent advances (~last 10 years)

**Optimised and Dynamic Theta (2016).** Fiorucci, Pellegrini, Louzada & Petropoulos generalised the
theta-line selection and derived the unique recomposition weight ω = (θ₂−1)/(θ₂−θ₁). The Dynamic
Optimised Theta variant is a genuine state-space model with proper likelihood and intervals, and
remains among the strongest fully-automatic univariate methods. Stdlib-feasible.
<https://arxiv.org/pdf/1503.03529> · <https://doi.org/10.1016/j.ijforecast.2016.02.005>

**M4 (2018–2020) settled the simple-vs-complex question for single-series forecasting.** 100,000
series. The six pure-ML entrants performed poorly — only one beat Naive2, and none beat the Comb
benchmark. The winner (Smyl's ES-RNN) and runner-up (Montero-Manso et al.'s FFORMA) were both
*hybrids* that used cross-learning across series, and **12 of the 17 most accurate methods were
combinations**. Petropoulos' summary: "if utilised properly, machine learning can increase the
forecasting performance" — but the mechanism was cross-learning over 100,000 series, which an agent
holding one 12-point series does not have.
<https://doi.org/10.1016/j.ijforecast.2019.04.014>

**M5 (2020–2022) is the counterexample, and it does not transfer.** For the first time, all
top-performing methods were pure ML (LightGBM), beating every statistical benchmark and their
combinations, in both the accuracy and uncertainty tracks. But M5 was 42,840 hierarchical retail
series with exogenous variables (price, promotions, calendar) and cross-learning across a large
related pool. **None of those conditions hold for the agent's typical task.** Citing M5 as a reason
to distrust Theta on a 12-point series would be a misreading.
<https://doi.org/10.1016/j.ijforecast.2021.11.013> ·
<https://doi.org/10.1016/j.ijforecast.2021.10.009>

**Statistical vs ML head-to-head with a controlled protocol (2018).** Makridakis, Spiliotis &
Assimakopoulos, PLOS ONE, on 1,045 monthly M3 series: 10 ML methods vs 8 statistical. Statistical
won decisively; Theta, comb-ES and ARIMA led; the best ML method (MLP, 8.39% sMAPE) was "only 0.19%
more accurate than Naive 2"; **the seasonal naive benchmark outperformed half the ML methods**; and
the statistical methods were also far cheaper computationally.
<https://doi.org/10.1371/journal.pone.0194889>

**"Are Transformers Effective for Time Series Forecasting?" (Zeng et al., AAAI 2023).** An
"embarrassingly simple one-layer linear model" (DLinear/LTSF-Linear) outperformed the entire family
of transformer LTSF models "in all cases," often by a large margin, across nine datasets. The stated
cause is that permutation-invariant self-attention loses temporal ordering. This is the deep-learning
era's independent rediscovery of the M-competition finding.
<https://arxiv.org/abs/2205.13504>

**Conformal prediction for time series (2021–2025)** — the most important advance *for this library*,
because the interval problem is where agents are weakest and where classical formulas are known to
fail. EnbPI (Xu & Xie, ICML 2021 / IEEE TPAMI) wraps any bootstrap ensemble and gives approximately
valid marginal coverage without requiring exchangeability. Adaptive Conformal Inference (Gibbs &
Candès 2021) is an online update of the miscoverage level that is trivially implementable in stdlib:
`α_{t+1} = α_t + γ·(target − 1{y_t ∈ C_t})`. SPCI (Xu & Xie 2023) adds time-adaptive re-estimation
of residual quantiles. A 2025 survey consolidates finite-sample guarantees under weak dependence.
<https://arxiv.org/abs/2010.09107> · <https://arxiv.org/abs/2106.00170> ·
<https://arxiv.org/abs/2212.03281> · <https://arxiv.org/abs/2511.13608>

**Validity of k-fold CV for autoregressive models (Bergmeir, Hyndman & Koo, 2018).** Standard
practice forbids random k-fold CV on time series. They show it *is* valid for purely autoregressive
models when the residuals are uncorrelated, and that it uses the data far more efficiently than
rolling-origin evaluation. At n = 15 that difference is decisive, so this is directly actionable for
the short-series case — with the residual-autocorrelation check (Ljung–Box) as the precondition.
<https://doi.org/10.1016/j.csda.2017.11.003>

**Optimal forecast reconciliation, MinT (Wickramasuriya, Athanasopoulos & Hyndman, 2019).** When the
agent holds both a total and its components (per-team, per-region, per-service), reconciling the
hierarchy improves *every* level, not just coherence. Full MinT needs a covariance estimate and a
matrix inverse; OLS reconciliation and bottom-up are stdlib-feasible and capture much of the gain.
<https://doi.org/10.1080/01621459.2018.1448825>

**Intermittent demand: TSB and the obsolescence problem (Teunter, Syntetos & Babai, 2011).** Croston
and SBA update only in demand periods, so they never revise downward as an item dies. TSB updates the
demand *probability* every period. This is now the routing rule for a zero-tail series.
<https://doi.org/10.1016/j.ejor.2011.05.018>

**Time-series foundation models (2023–2025)** — Chronos, TimesFM, TimeGPT, Moirai, Lag-Llama. Chronos
tokenises series into a fixed vocabulary and applies a T5 language model; it significantly beats
alternatives in-domain and is "comparable and occasionally superior" zero-shot across 42 datasets.
This is the current frontier and is **structurally out of reach for a stdlib module** — noted here so
the cut is explicit rather than accidental. <https://arxiv.org/abs/2403.07815>

**Solving the forecast combination puzzle (Lee & Lee; Frazier et al., 2023).** Recent work argues the
puzzle is partly an artefact of low-powered predictive-accuracy tests with non-standard asymptotics,
and that efficient estimation can let weighted combinations win. This does **not** change the
recommendation for this library — at agent scale there are nowhere near enough errors to estimate
weights efficiently — but it means "always equal-weight" should be stated as a small-sample decision,
not a law. <https://arxiv.org/abs/2308.05263>

---

## 4. Cut list

| Rejected | Why |
|---|---|
| Deep learning forecasters (N-BEATS, N-HiTS, DeepAR, TFT, PatchTST, LSTM) | Infeasible in stdlib, and all require a large pool of related series to cross-learn from — the exact resource an agent with one series lacks. |
| Foundation models (Chronos, TimeGPT, TimesFM, Moirai, Lag-Llama) | Require network access and pretrained weights; violates the module's portability constraint outright. |
| Facebook Prophet | Needs Stan; and repeatedly underperforms plain ETS/Theta on M-competition data despite its popularity. |
| ES-RNN (the M4 winner) | Hybrid needing cross-series training at scale; unreproducible for one short series. |
| FFORMA's gradient-boosted meta-learner | The *feature extraction* is stdlib-feasible and worth stealing; the GBM weighting needs a labelled meta-dataset of thousands of series that the agent will never have. |
| Seasonal ARIMA (SARIMA) with seasonal differencing | Needs ≥ 3 full seasonal cycles plus room for parameters; almost never available at agent scale. |
| TBATS / BATS / complex multiple seasonality | Multiple seasonal cycles are rare in agent-scale data, and the fitting cost is not repayable. |
| GARCH / ARCH volatility models | Answers a different question (variance dynamics), needs hundreds of observations, and belongs in a risk territory if anywhere. |
| VAR / VECM / multivariate econometrics | Parameter count grows as k²p; hopeless below a few hundred observations. |
| DSGE, Markov-switching, threshold (SETAR) models | Domain-specific macro/finance machinery with no domain-agnostic agent use case and severe data appetites. |
| Singular spectrum analysis | Needs eigendecomposition and long series; the trajectory-matrix work is not repaid at n < 100. |
| Bayesian structural time series (bsts / MCMC) | Sampler infeasible in stdlib within an acceptable latency budget; the Kalman MLE version (row 16) captures the useful part. |
| Grey system models GM(1,1) | Marketed for short series, but is essentially a constrained exponential fit with weak comparative evidence; Theta dominates it and is better understood. |
| Neural network autoregression (nnetar) | No advantage over ETS at these sizes; adds a fitting failure mode for nothing. |
| Undamped Holt's linear trend | Strictly dominated by damped trend, which contains it as the φ = 1 special case and avoids its long-horizon blow-up. |
| Plain Croston (uncorrected) | Known inversion bias; SBA is the same code plus one multiplication and is the field's benchmark. |
| Full MinT reconciliation with shrinkage covariance | Matrix inversion of a possibly ill-conditioned covariance is exactly the numerics to avoid in stdlib; OLS reconciliation / bottom-up gets most of the value. |
| Judgmental adjustment and scenario methods | Real and well-evidenced, but procedural rather than computational — belongs in a skill's prose, not in a callable model. |
| Wavelet / EMD hybrid decompositions | Popular in applied energy papers, weak out-of-sample evidence, and heavy numerics. |
| Spectral periodogram period detection | Kept as a small *utility*, not a headline model — the agent almost always already knows whether the period is 7, 12 or 52. |
| Story-point velocity extrapolation | Explicitly cut in favour of throughput Monte Carlo (row 9): it discards the distribution and uses the mean of a right-skewed variable. |

---

## 5. Cross-territory overlaps

- **Regression** — the trend fit under Theta, Theil–Sen, growth curves and threshold crossing is all
  regression. Threshold crossing in particular is *inverse prediction / calibration*, and its
  interval needs Fieller's theorem, which properly lives in the regression territory. Do not
  duplicate the OLS implementation.
- **Hypothesis testing** — Mann–Kendall, Ljung–Box on residuals (the precondition for row 14 and for
  Bergmeir's k-fold result), seasonality tests, and **Diebold–Mariano** for asking whether one
  forecaster is *significantly* better than another rather than merely lower on MASE.
- **Change point / anomaly detection** — the single largest source of catastrophic forecast error is
  a structural break, and the forecasting tool should be a *consumer* of a changepoint detector, not
  reimplement one. This dependency should be wired, not documented.
- **Distributions and numerics** — Student-t quantiles for small-n intervals; χ² for Ljung–Box; the
  beta distribution for PERT (rows 11 and 8 need the incomplete beta already flagged in RESEARCH.md
  §0.7); the Erlang-C sum for M/M/c.
- **Bayesian methods** — reference-class forecasting (row 8) is an empirical-Bayes prior in
  disguise; K&T's `class_mean + ρ·(inside − class_mean)` is literally shrinkage toward a prior mean.
  Damped trend is shrinkage of the slope. The two territories should agree on one shrinkage vocabulary.
- **Resampling and simulation** — bootstrap prediction intervals (row 5), throughput Monte Carlo
  (row 9), and Willemain-style intermittent-demand bootstrap all share one resampling engine.
- **Decision analysis** — a forecast is only useful against a loss function. Pinball loss for
  quantiles, and the asymmetry of over- vs under-forecasting, belong there but must be reachable
  from here.
- **Queueing / capacity** — rows 19 and 21 sit on the boundary. If a separate operations territory
  exists, they should live there and be *referenced* from forecasting, since the agent's phrasing
  ("when will this be done") arrives at forecasting first.

---

## 6. Sources

### 6.0 Verification status — read before using any constant

WebSearch budget was exhausted partway through this pass; the remainder was done by direct fetch and
by downloading and parsing primary PDFs. Sources below are tagged accordingly. **No constant tagged
UNVERIFIED may be promoted into a shipped lookup table, threshold, or default without being checked
against the primary source first.**

**[FULL TEXT VERIFIED]** — parsed the primary document in this pass:
Hyndman & Billah (2003) *Unmasking the Theta method* (all formulas, the ARIMA(0,1,1)-with-drift
equivalence, the 95% PI form, and the M3 annual sMAPE table 16.90 / 16.62 / 16.55 are read directly
off the paper); Fiorucci et al. *The Optimised Theta Method* (Theorem 1 and the ω weight);
Petropoulos et al. *Forecasting: theory and practice* (Croston→SBA→TSB narrative, the "SBA
constitutes the benchmark" claim, the competitions section, Bergmeir's cross-validation section);
Makridakis, Spiliotis & Assimakopoulos (2018) PLOS ONE (the 8.39% MLP / 0.19%-over-Naive2 figures);
*FPP3* chapters on the ETS taxonomy, benchmark σ̂ₕ formulas, PI multipliers, STL strength features,
simple methods, time-series CV, and very short series (including the 21/86/31/13/1 parameter-count
breakdown over 152 short annual M3 series); Hyndman's *Fitting models to short time series* (the
32/95/15/2 breakdown over 144 series).

**[DERIVED AND NUMERICALLY VERIFIED IN THIS PASS]** — the beta-PERT correction: α+β = 6, the
`(μ−o)(p−μ)/7` identity, `R(δ) = 5/7 + (16/7)δ(1−δ)`, the unity points at δ = 0.14645 / 0.85355, and
the −11.8% / +13.4% / +18.3% SD figures were all recomputed and checked to machine precision.

**[ABSTRACT ONLY]** — Zeng et al. DLinear; Ansari et al. Chronos; *Solving the Forecast Combination
Puzzle*; *A Gentle Introduction to Conformal Time Series Forecasting*.

**[UNVERIFIED — publisher paywall or 403 in this pass]**, cited from secondary summaries and from
the Petropoulos et al. review rather than from the primary text. Specifically flagged constants:
- The **M4 headline figures** (12-of-17 combinations; 5-of-top-6; six pure-ML entrants with only one
  beating Naive2 and none beating Comb). Corroborated by two independent secondary sources including
  the Petropoulos review, but the IJF paper itself returned 403. **No OWA/sMAPE point values are
  quoted anywhere in this report, deliberately** — I could not verify any, and the "single-digit
  percent over Comb" phrasing in §1 is intentionally qualitative.
- The **M5 findings** (LightGBM sweep of both tracks).
- The **SBC classification cutoffs ADI = 1.32 and CV² = 0.49** in row 16. This is the one numeric
  threshold in the table that I could not trace to primary text in this pass. **Do not ship it as a
  routing default until checked against Syntetos, Boylan & Croston (2005).**
- Gardner & McKenzie's **"~43% of M3 series"** damped-trend figure; the Fildes et al. (2008)
  "benchmark for all others to beat" quotation (widely reproduced, but quoted here second-hand).
- Chatfield (1993) and Makridakis et al. (1987) on interval coverage — the Bath PDF redirected and
  the IJF copy is paywalled, so **no empirical coverage percentages are quoted in this report**. The
  "intervals are too narrow" claim rests instead on Hyndman & Billah's own in-text statement, which
  *is* full-text verified.
- Bergmeir, Hyndman & Koo (2018); Wickramasuriya et al. (2019) MinT; Teunter et al. (2011) TSB;
  Kaplan & Meier (1958); the EnbPI / ACI / SPCI arXiv identifiers.
- Flyvbjerg and PERT-history figures relayed from the estimation research stream; of these, the
  **47.9%-on-budget** figure and MacCrimmon & Ryavec's "33% mean / 17% σ" were flagged as
  secondary-sourced at origin and should be treated as the weakest numbers in this document.

**Known gap:** no verified published constant for the fraction of carrying capacity that must be
observed before K is estimable (see §2.1). The rule given there is derived, not cited.

### 6.1 Citations

**Competitions and the simple-beats-complex evidence**
- Makridakis, Spiliotis & Assimakopoulos (2020), *The M4 Competition: 100,000 time series and 61 forecasting methods*, IJF 36(1) — <https://doi.org/10.1016/j.ijforecast.2019.04.014>
- Makridakis, Spiliotis & Assimakopoulos (2018), *Statistical and Machine Learning forecasting methods: Concerns and ways forward*, PLOS ONE — <https://doi.org/10.1371/journal.pone.0194889>
- Makridakis, Spiliotis & Assimakopoulos (2022), *M5 accuracy competition: Results, findings, and conclusions*, IJF — <https://doi.org/10.1016/j.ijforecast.2021.11.013>
- Makridakis et al. (2021), *The M5 uncertainty competition: Results, findings and conclusions*, IJF — <https://doi.org/10.1016/j.ijforecast.2021.10.009>
- Makridakis & Hibon (2000), *The M3-Competition: results, conclusions and implications*, IJF 16(4)
- Petropoulos et al. (2022), *Forecasting: theory and practice*, IJF 38(3) — <https://arxiv.org/abs/2012.03854> (the field's current encyclopedia; §2.3.3 Theta, §2.6 combination, §2.8 intermittent, §2.12.7 competitions)
- M4 code and benchmarks — <https://github.com/Mcompetitions/M4-methods>

**Theta**
- Assimakopoulos & Nikolopoulos (2000), *The theta model: a decomposition approach to forecasting*, IJF 16(4), 521–530
- Hyndman & Billah (2003), *Unmasking the Theta method*, IJF 19(2) — <https://robjhyndman.com/papers/Theta.pdf>
- Fiorucci, Pellegrini, Louzada & Petropoulos (2016), *Models for optimising the theta method and their relationship to state space models*, IJF — <https://arxiv.org/pdf/1503.03529>

**Exponential smoothing and state space**
- Gardner & McKenzie (1985), *Forecasting trends in time series*, Management Science 31(10)
- Gardner & McKenzie (2011), *Why the damped trend works*, JORS 62 — <https://doi.org/10.1057/jors.2010.37>
- Gardner (2010), *Damped trend exponential smoothing: A modelling viewpoint* — <https://www.bauer.uh.edu/gardner/Damped-trend-Modelling.pdf>
- Fildes, Nikolopoulos, Crone & Syntetos (2008), *Forecasting and operational research: a review*, JORS 59 (the "benchmark for all others to beat" verdict)
- Hyndman, Koehler, Snyder & Grose (2002), *A state space framework for automatic forecasting using exponential smoothing methods*, IJF 18(3)
- Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (3rd ed) — ETS taxonomy <https://otexts.com/fpp3/taxonomy.html>; benchmarks <https://otexts.com/fpp3/simple-methods.html>; intervals <https://otexts.com/fpp3/prediction-intervals.html>

**Short series**
- Hyndman, *Fitting models to short time series* — <https://robjhyndman.com/hyndsight/short-time-series/>
- *FPP3* §13.7, Very long and very short time series — <https://otexts.com/fpp3/long-short-ts.html>

**Evaluation and intervals**
- Hyndman & Koehler (2006), *Another look at measures of forecast accuracy*, IJF 22(4) (MASE)
- Tashman (2000), *Out-of-sample tests of forecasting accuracy: an analysis and review*, IJF 16(4) (rolling origin)
- Hyndman, *Cross-validation for time series* — <https://robjhyndman.com/hyndsight/tscv/>; *Rolling scaled forecast accuracy* — <https://robjhyndman.com/hyndsight/rolling_mase.html>
- Bergmeir, Hyndman & Koo (2018), *A note on the validity of cross-validation for evaluating autoregressive time series prediction*, CSDA 120 — <https://doi.org/10.1016/j.csda.2017.11.003>
- Chatfield (1993), *Calculating interval forecasts*, JBES 11(2)
- Makridakis, Hibon, Lusk & Belhadjali (1987), *Confidence intervals: An empirical investigation of the series in the M-competition*, IJF 3(3–4) — <https://doi.org/10.1016/0169-2070(87)90045-8>
- Williams & Goodman (1971), *A simple method for the construction of empirical confidence limits for economic forecasts*, JASA 66

**Conformal prediction for time series**
- Xu & Xie (2021), *Conformal prediction interval for dynamic time-series*, ICML — <https://arxiv.org/abs/2010.09107>; code <https://github.com/hamrel-cxu/EnbPI>
- Gibbs & Candès (2021), *Adaptive conformal inference under distribution shift* — <https://arxiv.org/abs/2106.00170>
- Xu & Xie (2023), *Sequential predictive conformal inference for time series*, ICML — <https://arxiv.org/abs/2212.03281>
- *A Gentle Introduction to Conformal Time Series Forecasting* (2025) — <https://arxiv.org/abs/2511.13608>

**Combination**
- Bates & Granger (1969), *The combination of forecasts*, OR Quarterly 20(4)
- Smith & Wallis (2009), *A simple explanation of the forecast combination puzzle*, Oxford Bulletin of Economics and Statistics 71(3)
- Claeskens, Magnus, Vasnev & Wang (2016), *The forecast combination puzzle: A simple theoretical explanation*, IJF 32(3) — <https://doi.org/10.1016/j.ijforecast.2016.02.005>
- *Solving the Forecast Combination Puzzle* (2023) — <https://arxiv.org/abs/2308.05263>
- Montero-Manso, Athanasopoulos, Hyndman & Talagala (2020), *FFORMA: Feature-based forecast model averaging*, IJF 36(1)

**Intermittent demand**
- Croston (1972), *Forecasting and stock control for intermittent demands*, OR Quarterly 23(3)
- Syntetos & Boylan (2005), *The accuracy of intermittent demand estimates*, IJF 21(2) (SBA)
- Syntetos, Boylan & Croston (2005), *On the categorization of demand patterns*, JORS 56 (the ADI = 1.32 / CV² = 0.49 scheme) — **cutoffs UNVERIFIED against primary text in this pass; see §6.0**
- Kostenko & Hyndman (2006), *A note on the categorization of demand patterns*, JORS 57
- Teunter, Syntetos & Babai (2011), *Intermittent demand: Linking forecasting to inventory obsolescence*, EJOR 214(3) — <https://doi.org/10.1016/j.ejor.2011.05.018>
- Willemain, Smart & Schwarz (2004), *A new approach to forecasting intermittent demand for service parts inventories*, IJF 20(3)
- Boylan & Syntetos (2021), *Intermittent Demand Forecasting*, Wiley

**Decomposition, hierarchies, aggregation**
- Cleveland, Cleveland, McRae & Terpenning (1990), *STL: A seasonal-trend decomposition procedure based on loess*, J. Official Statistics 6(1)
- Wang, Smith & Hyndman (2006), *Characteristic-based clustering for time series data*, DMKD 13(3) (trend/seasonal strength) — see <https://otexts.com/fpp3/stlfeatures.html>
- Wickramasuriya, Athanasopoulos & Hyndman (2019), *Optimal forecast reconciliation for hierarchical and grouped time series through trace minimization*, JASA 114(526) — <https://doi.org/10.1080/01621459.2018.1448825>
- Nikolopoulos, Syntetos, Boylan, Petropoulos & Assimakopoulos (2011), *An aggregate–disaggregate intermittent demand approach (ADIDA)*, JORS 62
- Kourentzes, Petropoulos & Trapero (2014), *Improving forecasting by estimating time series structural components across multiple frequencies* (MAPA), IJF 30(2)

**Trend detection**
- Mann (1945), *Nonparametric tests against trend*, Econometrica 13(3)
- Sen (1968), *Estimates of the regression coefficient based on Kendall's tau*, JASA 63(324)
- Hamed & Rao (1998), *A modified Mann-Kendall trend test for autocorrelated data*, J. Hydrology 204

**Estimation, reference classes, project duration**
- Malcolm, Roseboom, Clark & Fazar (1959), *Application of a technique for research and development program evaluation*, Operations Research 7(5)
- Grubbs (1962), *Attempts to validate certain PERT statistics or "picking on PERT"*, OR 10(6) — <https://doi.org/10.1287/opre.10.6.912>
- Herrerías-Velasco, Herrerías-Pleguezuelo & van Dorp (2011), *Revisiting the PERT mean and variance*, EJOR 210(2) — <https://www2.seas.gwu.edu/~dorpjr/Publications/JournalPapers/EJOR2011.pdf>
- Farnum & Stanton (1987), *Some results concerning the estimation of beta distribution parameters in PERT*, JORS 38 — <https://doi.org/10.1057/jors.1987.45>
- Roos & den Hertog (2020), *A distributionally robust analysis of the program evaluation and review technique*, EJOR — <https://doi.org/10.1016/j.ejor.2020.09.027>
- Kahneman & Tversky (1979), *Intuitive prediction: biases and corrective procedures*, DTIC AD-A047747 — <https://apps.dtic.mil/dtic/tr/fulltext/u2/a047747.pdf>
- Flyvbjerg (2006), *From Nobel Prize to project management: getting risks right*, PMJ 37(3) — <https://arxiv.org/abs/1302.3642>
- Flyvbjerg, Hon & Fok (2016), *Reference-class forecasting for Hong Kong's major roadworks projects* — <https://arxiv.org/abs/1710.09419>
- Flyvbjerg, Budzier, Lee, Keil, Lunn & Bester (2022), *The empirical reality of IT project cost overruns*, JMIS 39(3) — <https://arxiv.org/abs/2210.01573>
- Batselier & Vanhoucke (2016), *Practical application and empirical evaluation of reference class forecasting for project management*, PMJ 47(5) — <https://doi.org/10.1177/875697281604700504>
- Buehler, Griffin & Ross (1994), *Exploring the "planning fallacy"*, JPSP 67(3)

**Survival / time-to-event**
- Kaplan & Meier (1958), *Nonparametric estimation from incomplete observations*, JASA 53(282) — UNVERIFIED in this pass
- Greenwood (1926), *The natural duration of cancer* (the variance formula for Ŝ(t))

**Growth curves and saturation**
- Jewell, Lewnard & Jewell (2020), *Caution Warranted: Using the Institute for Health Metrics and Evaluation Model for Predicting the Course of the COVID-19 Pandemic*, **Annals of Internal Medicine 173(3):226–227** — <https://doi.org/10.7326/M20-1565> (note: this is the Ann Intern Med paper, **not** the JAMA one; the two are distinct and are frequently conflated)
- Ioannidis, Cripps & Tanner (2022), *Forecasting for COVID-19 has failed*, IJF 38(2) — <https://doi.org/10.1016/j.ijforecast.2020.08.004>. **Cite only for its failure taxonomy and its prescription to model predictive distributions rather than point estimates. It reports no numeric forecast-error magnitudes; do not attribute any to it.**
- Bass (1969), *A new product growth for model consumer durables*, Management Science 15(5)

**Flow, queueing**
- Little (1961), *A proof for the queuing formula L = λW*, Operations Research 9(3)
- Kingman (1961), *The single server queue in heavy traffic*, Math. Proc. Cambridge Phil. Soc. 57(4)
- Vacanti, *Actionable Agile Metrics for Predictability* (Little's Law's conditions for flow systems)

**Deep learning boundary**
- Zeng, Chen, Zhang & Xu (2023), *Are Transformers Effective for Time Series Forecasting?*, AAAI — <https://arxiv.org/abs/2205.13504>
- Ansari et al. (2024), *Chronos: Learning the Language of Time Series* — <https://arxiv.org/abs/2403.07815>
