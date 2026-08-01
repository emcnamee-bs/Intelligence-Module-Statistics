# Territory 06 — Sequential Design, Sample Size, and Optimal Stopping

*Research report for the Intelligence Module statistics library. Target: pure Python 3 stdlib (`math`, `statistics`, `random`, `itertools`, `functools`), agent-scale n, CLI-invokable.*

---

## 1. Territory summary

This territory answers the two questions an agent should ask before and during any act of data collection: **"how many observations do I need?"** and **"can I stop now?"** The classical half (power analysis, minimum detectable effect, precision-based sizing, the rule of three) is arithmetic on the normal quantile function and is trivially implementable in stdlib Python — it is high-value precisely because an agent's unaided guess at "how many benchmark runs do I need" is routinely wrong by an order of magnitude in *either* direction. The modern half — **anytime-valid inference via e-values, test martingales, and confidence sequences** (Robbins → Ville → Howard/Ramdas/Waudby-Smith/Grünwald) — is a near-perfect fit for an agent's natural workflow, because it is the only framework in which "keep collecting until convinced, then stop immediately" is *mathematically legal* rather than p-hacking. The critical asymmetry an agent must internalize: a fixed-n test that is peeked at is invalid (continuous monitoring of an uncorrected z-test drives type-I error to 1.0 as n→∞ by the law of the iterated logarithm), whereas a confidence sequence may be inspected after literally every observation, by an adversary, with a data-dependent stopping rule, and still covers at 1−α. The price of that freedom is roughly a √(log log t) width inflation — in practice about 1.3–2× the fixed-n sample size *if you run to the horizon anyway*, but typically a large net saving because you usually don't.

---

## 2. Ranked model table

Tier legend for inputs: **INLINE** = a handful of numbers as CLI flags · **DATAFILE** = a small dataset in a file · **CONSTRUCT** = agent must build/simulate the dataset or a prior first.

| # | Model / method | SITUATION (agent phrasings) | Min viable inputs + tier | Beats what | Stdlib feasibility + numerics | REFUSE conditions |
|---|---|---|---|---|---|---|
| 1 | **Betting / hedged-capital confidence sequence for a bounded mean** (Waudby-Smith–Ramdas 2024) | "Can I stop sampling yet?" · "I'm scoring benchmark items 0–1 and want to stop as soon as I know the mean" · "Give me a CI I'm allowed to look at after every single observation" · "Keep running the eval until the answer is tight enough" | Stream/list of values in `[lo,hi]` (rescaled to [0,1]); `alpha`; optional `theta=0.5`, `c=0.5`. **DATAFILE** (or incremental append) | Fixed-n Wald/Wilson CI that is *invalid* under peeking; Hoeffding CS; naive "check after every run" | **MODERATE.** Grid over `m∈[0,1]` (e.g. 1000 pts) × running product of `1±λᵢ(m)(Xᵢ−m)`; `math.log/exp` only. O(grid·n), fine to n≈10⁵. No special functions. | Any value outside `[lo,hi]`; bounds not supplied/derivable; n=0; data reordered or sorted after collection (breaks the filtration); `alpha` or `c` changed after seeing data; non-i.i.d./drifting stream without a declared time-varying target |
| 2 | **Predictable plug-in empirical-Bernstein confidence sequence (PrPl-EB)** | Same as #1 but "just give me a closed form, no search" · "variance-adaptive anytime CI for a bounded metric" · "sequential CI for a pass rate" | List of values in `[lo,hi]`; `alpha` | Hoeffding-based CS (2–5× wider when variance is small); fixed-n CI under peeking | **EASY.** One pass, closed form. `math.log`, `math.sqrt`. See §2.1. | Same as #1; also refuse if `σ̂²₀` degenerate at t=1 (use the regularized estimator, don't divide by zero) |
| 3 | **Two-sample / one-sample power and sample size for means** (normal approx + t-correction; exact via noncentral t) | "How many runs to detect a 5% speedup?" · "Is 20 samples enough?" · "What n do I need for 80% power?" · "How many trials per arm?" | `delta`, `sd`, `alpha`, `power` (+`ratio`). **INLINE** — or estimate `sd` from a pilot **DATAFILE** | Guessing "30 is enough"; running an underpowered benchmark and reading noise as signal | **EASY** with normal approx (`Φ⁻¹` via Acklam/AS241 rational approx, ~25 lines). **MODERATE** for exact: t-quantile needs regularized incomplete beta (Lentz continued fraction); noncentral t needs a Poisson-weighted `I_x(a,b)` series. Iterate `n ← 2σ²(t_{1−α/2,ν}+t_{1−β,ν})²/Δ²`. | No effect size supplied *and* none derivable; `sd=0`; `power ≥ 1` or `≤ alpha`; `delta=0`; pilot `sd` from n<5 (report as an interval, or refuse and demand the MDE tool instead) |
| 4 | **Minimum detectable effect (MDE) at a fixed budget** | "I can only afford 200 runs — what's the smallest difference I could actually detect?" · "Is this experiment worth running at all?" · "What effect size am I powered for?" | `n` (or n per group), `sd`, `alpha`, `power` | The far more common failure than "too few samples": running a study that *cannot* answer the question. Inverts #3, which is the direction agents actually need | **EASY.** `MDE = (z_{1−α/2}+z_{1−β})·σ·√(2/n)`; t-version by one fixed-point iteration | `n < 4` per group; `sd` unknown and no pilot; asked for MDE on a metric with no meaningful scale |
| 5 | **Robbins normal-mixture confidence sequence** (Gaussian, known/plug-in σ) | "Anytime-valid CI for a mean with unbounded values (latency, memory, tokens)" · "Simplest legal peeking CI" · "Sequential CI for a continuous metric" | Running `n`, `mean`, `sd`; `alpha`; tuning `rho`. **INLINE or DATAFILE** | Fixed-n z-interval under peeking; Bonferroni over looks (wildly conservative) | **EASY.** One line: `x̄ ± σ·√( 2(tρ+1)/(t²ρ) · log(√(tρ+1)/α) )`. Only `log`, `sqrt`. | `rho` chosen after seeing data; σ estimated from the same peek without using the unknown-variance version (#6); heavy-tailed data with no bound and no sub-Gaussian justification |
| 6 | **Anytime-valid t-test / confidence sequence, unknown variance** (Wang–Ramdas 2024, universal inference) | "Sequential t-test" · "Anytime CI for a mean when I don't know the SD" · "Stop-when-convinced for latency measurements" | Stream of reals; `alpha`. **DATAFILE** | Robbins mixture with a plugged-in σ (which is not actually valid); repeated t-tests | **EASY–MODERATE.** Closed form; running plug-in `μ̃`, `σ̃`; products of Gaussian densities. No incomplete beta needed. See §2.2. | n < 2; zero sample variance; data not exchangeable |
| 7 | **Rule of three + zero-event sample sizing** | "The flaky test passed 300 times — how flaky can it still be?" · "Zero failures observed, what's the upper bound?" · "How many clean runs before I believe it's fixed?" · "No crashes in 1000 requests" | `n` and `k=0` → bound; or target `p0` → required `n`. **INLINE** | Concluding "0/300 means it's fixed" (it's consistent with a 1% failure rate). Highest value-per-line-of-code in the whole territory for an agent debugging flakes | **EASY.** Upper 1−α bound `= 1 − α^{1/n}` (≈ `3/n` at α=.05). Inverse: `n ≥ log(α)/log(1−p₀)` (≈ `3/p₀`). Generalize to k>0 with the exact Clopper–Pearson upper limit or Poisson `0.5·χ²_{2(k+1),1−α}`. | Trials not independent (retries of the same seed / same cached state); n=0; runs were stopped *because* they passed |
| 8 | **mSPRT always-valid p-value for a two-arm comparison** (Johari–Pekelis–Walsh) | "A/B compare two prompts/configs with continuous monitoring" · "Always-valid p-value for an ongoing comparison" · "Stop the A/B as soon as one wins" | Running `n`, `mean_A`, `mean_B`, `var` (or a **DATAFILE** of paired/streamed observations); `alpha`; mixture SD `tau` fixed in advance | Repeated two-sample t-tests (type-I ≈ 0.14 at 5 looks, →1 under continuous monitoring) | **EASY.** `Λₙ = √(σ²/(σ²+nτ²))·exp( n²τ²θ̂ₙ² / (2σ²(σ²+nτ²)) )`; `pₙ = min(p_{n−1}, 1/Λₙ)`. See §2.3. | `tau` tuned after looking at data (this is the #1 way people invalidate mSPRT); σ² estimated to 0; arms assigned non-randomly; refuse to report a *fixed-n* CI alongside it |
| 9 | **Two-proportion power / sample size** (normal approx, arcsine, and exact-conditional check) | "How many requests to detect error rate 2%→1%?" · "Sample size for a conversion / pass-rate comparison" · "Is my 3/50 vs 8/50 difference detectable?" | `p1`, `p2`, `alpha`, `power` (+ `ratio`). **INLINE** | Eyeballing two proportions; using the means formula on binary data | **EASY.** `n = (z_{1−α/2}√(2p̄q̄) + z_{1−β}√(p₁q₁+p₂q₂))²/(p₁−p₂)²`; arcsine variant `n = (z_a+z_b)²/(2(asin√p₁−asin√p₂)²)`. Exact Fisher power needs `math.comb` enumeration — feasible for n ≲ 200/arm. | `p ∉ (0,1)`; `p1 == p2`; expected cell count < 5 **and** no exact path taken; agent supplies observed proportions from the *same* data it wants to size (post-hoc power — refuse outright, redirect to #4) |
| 10 | **Naive-peeking α-inflation simulator** | "What actually happens if I just check after every 10 runs?" · "Why can't I peek?" · "How wrong is repeated testing?" | `n_max`, `n_looks` (or `look_every`), `alpha`, `n_sims`. **CONSTRUCT (simulation)** | Pure assertion. Turns "don't peek" into a number the agent can act on. Reference values (two-sided .05): 2 looks→.083, 3→.107, 4→.126, 5→.142, 10→.193, 20→.248, 50→.320, 100→.374 (Armitage–McPherson–Rowe 1969) | **EASY.** `random.gauss` + running mean; 20k sims × 1000 steps is ~seconds in pure Python. Deterministic with a fixed seed. | `n_sims < 1000` (Monte-Carlo error swamps the answer); refuse to report a *point* estimate without its MC standard error |
| 11 | **Wald's SPRT (simple vs simple) + ASN / OC curves** | "Is this flaky test's failure rate 1% or 10%? Fewest runs to tell." · "Sequential test between two specific hypotheses" · "Expected number of trials before I can decide" | `p0`/`p1` (or `mu0`/`mu1`,`sd`), `alpha`, `beta`. **INLINE**; then feed observations one at a time | Fixed-n testing when a simple-vs-simple framing is honest — SPRT is Wald–Wolfowitz optimal (minimizes E[N] under *both* hypotheses) and typically needs ~50% of fixed n | **EASY.** `A=(1−β)/α`, `B=β/(1−α)`; accumulate `log LR`. ASN: `E[N|H]= (…log B + …log A)/E[log LR|H]`. OC needs Wald's `h`-root: solve `E[(f₁/f₀)^h]=1` by bisection. | Alternative is composite (SPRT's α,β guarantees silently fail — redirect to #1/#6/#8); no upper truncation supplied for an unbounded run; LR undefined (zero density) |
| 12 | **Precision-based sample sizing (CI width / AIPE)** | "How many samples until my CI is ±2 ms?" · "I want an estimate, not a test — what n?" · "Size for precision not power" | Target half-width `h`, `sd` (or `p`), `alpha`; optional assurance `gamma`. **INLINE** | Power analysis when the agent doesn't actually have a hypothesis, only wants a tight number. Often the *correct* reframing of an agent's real goal | **EASY.** Mean: `n = (z_{1−α/2}σ/h)²`. Proportion: `n = z²p(1−p)/h²` (worst case p=.5). Assurance (Kelley–Rausch): inflate by `χ²_{ν,γ}/ν` — needs regularized incomplete gamma inverse (**MODERATE**) or a chi-square bisection. | `h ≤ 0`; `sd` guessed with no basis; agent asks for expected width but means guaranteed width (say so, offer the assurance version) |
| 13 | **Equivalence / non-inferiority sample size (TOST)** | "Prove the refactor did NOT slow things down by more than 3%" · "How many runs to show two configs are the same?" · "Sample size to rule out a regression" | `margin`, `sd`, `alpha`, `power` (+ assumed true diff `delta0`). **INLINE** | The pervasive agent error of reading p>0.05 as "no difference." A non-result can only be *proved* by an equivalence design | **EASY.** `n = 2σ²(z_{1−α}+z_{1−β/2})²/(margin−|δ₀|)²` (approx; exact needs bivariate noncentral t — use simulation instead). | `margin` not supplied (there is no such thing as a default equivalence margin — REFUSE); `|delta0| ≥ margin`; agent tries to set the margin after seeing the data |
| 14 | **Conditional power / stochastic curtailment (futility)** | "I'm halfway through — is there any chance this ends significant?" · "Should I kill this run early?" · "Is it hopeless?" | Information fraction `t`, current `z` (or B-value), `alpha`, assumed drift. **INLINE** | Burning the remaining 50% of a benchmark budget on an experiment that is already dead. Pure upside for an agent with a compute budget | **EASY.** `B(t)=Z_t√t`; `CP_θ = Φ((B(t) + θ(1−t) − z_{1−α})/√(1−t))`, with `θ = z_{1−α}+z_{1−β}` (design) or `θ = B(t)/t` (current trend). Report both. | `t ∉ (0,1)`; stopping for futility presented as evidence *for* the null (it isn't); using CP to stop for *efficacy* without an α-spending correction |
| 15 | **e-value combination and optional continuation** | "I ran three separate evals — how do I pool them?" · "Combine evidence from studies I decided to run based on earlier results" · "Convert this evidence to a p-value" | 2+ e-values, plus a dependence declaration (`independent` / `arbitrary`). **INLINE** | Fisher's method and meta-analysis, both of which are *invalid* when the decision to run study k depended on studies 1..k−1 — the normal agent workflow | **EASY.** Product (independent / same filtration, optional continuation), arithmetic mean (arbitrary dependence, Vovk–Wang), `p = min(1, 1/e)` by Markov/Ville. p→e calibrator `e = κp^{κ−1}`. | Mixing e-values for *different* nulls; taking a product under arbitrary dependence; converting p→e→p and claiming a gain; e < 0 |
| 16 | **Group-sequential design with α-spending (Lan–DeMets O'Brien–Fleming / Pocock)** | "I want to check 4 times during a 1000-run benchmark — what thresholds?" · "Pre-planned interim analyses" · "Adjusted critical values for K looks" | `K` looks (or information fractions), `alpha`, spending family. **INLINE** | Bonferroni across looks (too conservative), and naive peeking (too liberal). OBF spends almost nothing early → final threshold ≈ fixed-n | **MODERATE.** Spending: OBF-LD `α(t)=2(1−Φ(z_{1−α/2}/√t))`, Pocock-LD `α(t)=α·log(1+(e−1)t)`. Boundaries need K-dim MVN orthant probabilities — use the Armitage–McPherson–Rowe recursion: propagate the sub-density of the partial sum on a ~1000-point grid, Simpson-integrate, bisect for each `c_k`. ~150 lines, pure `math`. | Looks not pre-specified, or `K` changed after data (use α-spending with *information time*, not look count, and say so); unequal/unknown information fractions supplied as equal; K > ~20 (grid error accumulates — switch to a CS) |
| 17 | **Paired / within-subject design sizing + variance-reduction (CUPED-style) accounting** | "Should I run both versions on the same inputs?" · "How much does pairing save me?" · "Sample size for a before/after comparison" | `sd`, `rho` (correlation between paired measurements), `delta`, `alpha`, `power`. **INLINE**, `rho` from a pilot **DATAFILE** | Independent-groups sizing. `n_pairs = n_per_group_unpaired × (1−ρ)` — at ρ=0.9 that's a **10×** budget cut. Usually the single largest available win, and agents almost never think of it | **EASY.** `σ_d² = σ₁²+σ₂²−2ρσ₁σ₂`; then the one-sample formula. | `|rho| ≥ 1`; pairing claimed but the two runs share cached state / are not exchangeable; `rho` estimated from n<10 pairs (report sensitivity across a ρ range instead) |
| 18 | **Chow–Robbins sequential fixed-width / relative-precision stopping** | "Keep sampling until the CI is within 5% of the mean" · "Stop when the estimate stabilizes" · "Adaptive n for unknown variance" | Target half-width `h` (absolute) or relative `r`; `alpha`; `n0` minimum. **DATAFILE / streaming** | Guessing n from an unknown σ, then finding out σ was 3× bigger. Coverage is asymptotic, not anytime-valid — state this and offer #2/#6 as the rigorous alternative | **EASY.** Stop at `N = inf{n≥n₀ : n ≥ (z/h)²(s_n² + 1/n)}`. | `n0 < 10` (severe undercoverage); relative precision with a mean near 0; presenting the resulting interval as exactly 1−α (it is asymptotic — say "approximate") |
| 19 | **Secretary problem / 37% rule and full-information variant** | "I'm generating candidates one at a time and can't go back — when do I stop?" · "Best-choice stopping with no recall" · "How many options should I look at before committing?" | `N` (total candidates); optionally a known/estimated value distribution. **INLINE** | Stopping at the first "good enough" option, or exhaustively evaluating all N. Classic rule: skip `⌊N/e⌋`, take the next record; P(best) → 1/e ≈ 0.368 | **EASY.** Exact optimal `r` maximizes `((r−1)/N)·Σ_{i=r}^{N} 1/(i−1)`. Full-information (Gilbert–Mosteller) thresholds by backward recursion; P(win) → 0.5802. | `N` unknown (the rule collapses — refuse or switch to the odds algorithm #20); recall *is* possible (then just take the max); the objective is expected *value* not P(best) — different problem, use the full-information version |
| 20 | **Bruss' odds algorithm (last-success stopping)** | "Stop on the last success in a sequence" · "When is this the final good opportunity?" · "Optimal stopping with per-item success probabilities" | Vector of `p_i` per position. **INLINE (short) or DATAFILE** | Ad-hoc thresholds. Genuinely counterintuitive and exactly optimal | **EASY.** Odds `rᵢ = pᵢ/(1−pᵢ)`; sum from the end until `Σrᵢ ≥ 1` → threshold index s; win prob `= (Π_{i≥s}(1−pᵢ))·(Σ_{i≥s} rᵢ)`. | `pᵢ ∉ [0,1]`; positions not independent; objective is not "stop on the last success" (very specific — check it) |
| 21 | **Simon two-stage design (binary outcome, early futility)** | "Run 10; if ≤1 passes, give up; else run 19 more" · "Two-stage screening design" · "Cheap early kill for a pass/fail eval" | `p0` (uninteresting rate), `p1` (target), `alpha`, `beta`. **INLINE** | Single-stage binomial testing. Cuts expected n by ~30–50% when the thing is bad, which is the common case for an agent screening candidates | **EASY.** Exhaustive search over `(n1, r1, n, r)` with exact binomial tails via `math.comb`; minimize `E[N|p0] = n1 + (1−PET)(n−n1)` (optimal) or `n` (minimax). Few thousand candidates — sub-second. | `p1 ≤ p0`; n > ~300 (`math.comb` fine but the search grid explodes — cap it); agent wants to continue past stage 2 (that's a different design) |
| 22 | **Correlation sample size (Fisher z)** | "How many points to detect a correlation of 0.4?" · "Is my r=0.3 from 15 points meaningful?" · "Sample size for a relationship" | `r_target`, `alpha`, `power`. **INLINE** | Reading correlations off tiny n. `n = 3 + ((z_{1−α/2}+z_{1−β})/atanh(r))²` — for r=0.3 that's n≈85, which is far above what agents typically assume | **EASY.** `math.atanh`, `Φ⁻¹`. | `|r| ≥ 1`; `r = 0`; non-bivariate-normal data with outliers (recommend the rank version and widen); post-hoc power |
| 23 | **Rare-event / Poisson rate sizing and exposure planning** | "How long do I have to watch to see a 1-in-10000 error?" · "Sample size for a rare failure" · "How many log lines to find the bug?" | Rate `lambda0`/`lambda1` or target detectable rate; exposure units; `alpha`, `power`. **INLINE** | Sampling 1000 log lines to characterize a 0.01% event. Also: P(see ≥1 in n) = 1−e^{−λn} → need `n ≈ 3/λ` for 95% chance of at least one | **EASY.** Exact Poisson tails by direct summation; square-root (Anscombe) transform for the two-sample rate comparison: `n = (z_a+z_b)²/(2(√λ₁−√λ₀)²)` per unit exposure. | Events clustered / overdispersed (Poisson assumption dead — refuse and ask for a dispersion estimate); exposure not measured; zero events with no declared exposure |
| 24 | **Expected value of sample information (EVSI) / EVPI** | "Is it worth running 50 more tests given they cost X?" · "Should I gather more data or just decide?" · "What's the value of resolving this uncertainty?" | Prior over the unknown, action set, payoff/loss function, cost per observation, candidate `n`. **CONSTRUCT** | Collecting data by reflex, or deciding by reflex. EVPI is a cheap upper bound: if EVPI < cost of *any* sampling, stop immediately and decide | **MODERATE.** Nested Monte Carlo: sample θ ~ prior → simulate n obs → posterior-optimal action → payoff; `EVSI = E[max_a E_{θ|D}U] − max_a E_θ U`. Pure `random`; needs conjugate updating (Beta-Binomial / Normal-Normal) to stay cheap. | No explicit loss/payoff supplied (REFUSE — EVSI is meaningless without one); prior is a point mass; inner/outer MC loops too small (report MC SE); agent wants a decision but hasn't enumerated actions |
| 25 | **Best-arm identification with anytime-valid elimination** | "Which of 5 prompts is best, with the fewest samples?" · "Sequentially eliminate losing configs" · "Adaptive comparison of several options" | K arms, sampling callback or a growing **DATAFILE** per arm; `alpha`, optional tolerance `eps` | Running a fixed equal budget on all K arms, then arg-max (no error guarantee at all). Successive elimination with per-arm confidence sequences + a union bound gives a genuine δ-correct guarantee | **MODERATE.** Per-arm CS from #2/#5 at level `alpha/K`; eliminate arm j when its CS upper < best CS lower; loop. ~80 lines. | K=1; arms not independently sampled; `alpha/K` correction omitted; agent wants regret minimization not identification (different objective — that's a bandit, not this) |

### 2.1 PrPl-EB confidence sequence (exact formulas)

For observations `Yᵢ ∈ [0,1]` (rescale from `[lo,hi]`), with running regularized estimators

```
μ̂_t = (1/2 + Σ_{i≤t} Yᵢ) / (t+1)
σ̂²_t = (1/4 + Σ_{i≤t} (Yᵢ − μ̂ᵢ)²) / (t+1)
```

set the **predictable** betting fractions and interval

```
λ_t = min( sqrt( 2·log(2/α) / ( σ̂²_{t−1} · t · log(1+t) ) ), c )          c ∈ (0,1), default 0.5
νᵢ  = 4 (Yᵢ − μ̂_{i−1})²
ψ_E(λ) = ( −log(1−λ) − λ ) / 4

C_t = [ Σλᵢ Yᵢ / Σλᵢ ]  ±  [ ( log(2/α) + Σ νᵢ ψ_E(λᵢ) ) / Σλᵢ ]
```

Every quantity is predictable (uses only data up to `i−1`), which is what makes the wealth process a nonnegative martingale and hence Ville's inequality applicable. **Fixed-horizon variant** (if the agent commits to `R` samples up front, slightly tighter): `λᵢ = min(sqrt(2 log(2/α)/(R σ̂²_{i−1})), c)`.

### 2.2 Hedged-capital betting CS (grid inversion)

```
K_t⁺(m) = Π_{i≤t} (1 + λᵢ⁺(m)(Yᵢ − m))
K_t⁻(m) = Π_{i≤t} (1 − λᵢ⁻(m)(Yᵢ − m))
K_t^±(m) = max( θ·K_t⁺(m), (1−θ)·K_t⁻(m) )          θ = 1/2

λᵢ⁺(m) = min(|λ̃ᵢ|, c/m)      λᵢ⁻(m) = min(|λ̃ᵢ|, c/(1−m))
λ̃ᵢ = sqrt( 2 log(2/α) / (R σ̂²_{i−1}) )      (or the PrPl form above for the anytime version)

CS_t = { m ∈ [0,1] : max_{i≤t} K_i^±(m) < 1/α }
```

Defaults from the paper: `c ∈ {1/2, 3/4}`, `θ = 1/2`. Accumulate in logs. The set is an interval in practice; find its endpoints by bisection on `log K^±(m) − log(1/α)` rather than a dense grid once you have a bracketing point (the running mean). An alternative `λ` choice, **aGRAPA**, is the approximate-GRAPA plug-in `λ_t(m) = clip( (μ̂_{t−1} − m) / (σ̂²_{t−1} + (μ̂_{t−1} − m)²) )` — slightly more powerful, same cost.

### 2.3 mSPRT (Gaussian mixture) always-valid p-value

```
Λ_n = sqrt( σ²/(σ² + n τ²) ) · exp( n² τ² θ̂_n² / ( 2 σ² (σ² + n τ²) ) )
p_0 = 1,   p_n = min(p_{n−1}, 1/Λ_n)
```

with `θ̂_n` the running estimated difference and `σ²` the (pooled) per-observation variance. For binary arms, `σ²_n = p̂_A(1−p̂_A) + p̂_B(1−p̂_B)`. **`τ` must be fixed before data collection**; the standard guidance is `τ ≈ σ` or, better, set `τ` to the effect size the agent actually cares about. The inverted always-valid CI is `{θ₀ : Λ_n(θ₀) < 1/α}`, found by bisection.

### 2.4 Robbins normal-mixture CS

```
C_t = x̄_t ± σ · sqrt( ( 2 (t ρ + 1) / (t² ρ) ) · log( sqrt(t ρ + 1) / α ) )
```

`ρ > 0` is a tuning parameter that sets *when* the sequence is tightest; a good default is to choose ρ so the CS is optimized near the agent's planned horizon `t*`: roughly `ρ ≈ 1/t*`. This is the cheapest legal-peeking interval in the whole territory — literally one expression — and should be the library's default when the metric is unbounded and roughly sub-Gaussian.

### 2.5 The one number every agent should learn

Under **continuous** uncorrected monitoring of a z-test, type-I error → **1.0** as n → ∞ (law of the iterated logarithm). Under monitoring at K equally-spaced looks with nominal two-sided α=0.05, the actual error rate is 0.083 (K=2), 0.142 (K=5), 0.193 (K=10), 0.320 (K=50). A tool that lets an agent peek must therefore either (a) be a confidence sequence / e-process, (b) use pre-planned α-spending, or (c) print this table and refuse.

---

## 3. Recent advances (~last 10 years)

The dominant development is the maturation of **safe, anytime-valid inference (SAVI)** — a unification of Ville's inequality (1939), Wald's SPRT (1945), Robbins' mixture methods (1970), and game-theoretic probability (Shafer–Vovk) into a practical toolkit. This is the single most agent-relevant statistical advance of the decade.

**1. Confidence sequences became practical and tight.** Howard, Ramdas, McAuliffe & Sekhon (*Ann. Statist.* 2021; arXiv:1810.08240) gave time-uniform, nonparametric, nonasymptotic confidence sequences whose widths shrink to zero, unifying Cramér–Chernoff concentration, the LIL, and the SPRT; the companion *Probability Surveys* paper (arXiv:1808.03204) gives the supermartingale machinery. Practically: you get boundaries that are only ~√(log log t) worse than fixed-n while being valid at *every* t.

**2. Betting replaced concentration inequalities as the default construction.** Waudby-Smith & Ramdas, "Estimating means of bounded random variables by betting" (*JRSS-B* 86(1):1–27, 2024; arXiv:2010.09686) produce CIs and CSs for bounded means that dominate Hoeffding and classical empirical-Bernstein, adapting automatically to low variance and asymmetry. Shekhar & Ramdas (arXiv:2310.01547) show these betting sets are **near-optimal** — you cannot do much better. For an agent scoring evals in [0,1], this is the state of the art and it is ~60 lines of pure Python. Chugg & Ramdas (arXiv:2512.21300, Dec 2025) add the tightest known *closed-form* empirical-Bernstein CS, removing the grid search.

**3. E-values formalized "evidence you may keep accumulating."** Grünwald, de Heide & Koolen, "Safe testing" (*JRSS-B* 86(5):1091–1128, 2024) introduced **growth-rate-optimal (GRO)** e-variables and the key operational property, **optional continuation**: you may decide whether to run study *k+1* based on studies *1..k* and still multiply e-values, with type-I error preserved. Fisher's method and standard meta-analysis both break under exactly this workflow — which is the *normal* agent workflow. Ramdas, Grünwald, Vovk & Shafer, "Game-theoretic statistics and safe anytime-valid inference" (*Statistical Science* 2023; arXiv:2210.01948) is the readable survey; Ramdas & Wang, *Hypothesis Testing with E-values* (*Foundations and Trends in Statistics* 1(1–2):1–390, 2025; arXiv:2410.23614) is the 390-page reference text.

**4. Admissibility: there is no cleverer trick.** Ramdas, Ruf, Larsson & Koolen (arXiv:2009.03167) proved that *admissible* anytime-valid sequential inference **must** be built from nonnegative (super)martingales — explicitly for e-values/tests, implicitly by inversion for anytime p-values and confidence sequences. This is why the library should implement the martingale constructions and not search for shortcuts.

**5. Unknown variance and unbounded data got closed forms.** Wang & Ramdas, "Anytime-valid t-tests and confidence sequences for Gaussian means with unknown variance" (*Sequential Analysis*; arXiv:2310.03722) give a universal-inference e-process requiring only running plug-in estimators, logs, and exponentials — no incomplete beta, no noncentral t. Waudby-Smith, Arbour, Sinha, Kennedy & Ramdas, "Time-uniform central limit theory and asymptotic confidence sequences" (*Ann. Statist.* 52(6):2613–2640, 2024; arXiv:2103.06476) provide *asymptotic* CSs — time-uniform analogues of CLT intervals — which is the right tool when the metric is arbitrary and only weak assumptions hold.

**6. Industrial validation.** Johari, Pekelis & Walsh's mSPRT "always valid inference" (*Operations Research* 70(3), 2022; arXiv:1512.04922; KDD 2017 "Peeking at A/B tests") is deployed at Optimizely; Lindon, Ham, Tingley & Bojinov, "Anytime-Valid Confidence Sequences in an Enterprise A/B Testing Platform" (WWW '23) documents the Netflix deployment. Adaptive-clinical-trial adoption is underway (e.g. arXiv:2602.06379, "E-values for Adaptive Clinical Trials"). These are existence proofs that the machinery survives contact with messy real data.

**7. Sample-size planning for sequential designs caught up.** Schultzberg, "A closed-form sample size correction for always-valid inference with optional stopping" (arXiv:2606.18366, June 2026) gives a correction multiplier `k*(α, β, t₀)` in elementary functions plus the bivariate normal CDF, hitting empirical power within ~3 points of target in Gaussian simulations and saving 8–20% versus the conservative "last-point rule." This closes the last practical gap: an agent can now *plan a budget* for a sequential design, not just run one.

**8. Adjacent, worth tracking.** e-value-based FDR control (Wang & Ramdas, e-BH, arXiv:2009.02824) makes sequential + multiple-testing compose cleanly; Grünwald's work on data-driven α argues you may choose your rejection threshold *after* seeing the e-value; and confidence sequences for sampling *without* replacement (arXiv:2006.04347) matter for the very common agent task of sampling a finite log file or corpus.

---

## 4. Cut list

- **Response-adaptive randomization / Bayesian adaptive dose-finding (CRM, BOIN)** — requires MCMC or heavy tabulation; agent has no dose-toxicity problem.
- **Sample-size re-estimation with CHW weighting (Mehta–Pocock promising zone)** — subsumed by confidence sequences, which get adaptivity for free without the weighting bookkeeping.
- **Safe log-rank / anytime-valid survival tests** — real and elegant, but agents almost never have censored time-to-event data.
- **Cluster-randomized design effect / ICC sizing** — narrow; the useful kernel (inflate n by `1 + (m−1)ρ` when observations are correlated) is a one-line warning attached to #3, not its own tool.
- **Noncentral-F power for ANOVA / factorial designs** — implementable but agents compare 2 things, not 2×3 factorials; the pairwise tool covers the real cases.
- **Stein's two-stage fixed-width procedure** — historically important, dominated by Chow–Robbins (#18) and by CSs (#2/#6).
- **Fisher's method / Stouffer combination for pooling studies** — deliberately cut in favor of e-value products (#15), *because* they are invalid under the optional-continuation pattern agents actually use. Worth an explicit "don't do this" note.
- **Bayes factor sequential design with Schönbrodt–Wagenmakers thresholds** — largely isomorphic to e-values under a prior; keeping both invites the agent to pick whichever is more favorable.
- **Prophet inequalities, Pandora's box, house-selling with recall** — beautiful online-algorithms theory, but the input (a known value distribution plus a recall/cost structure) is almost never available to an agent.
- **Robbins' problem (minimize expected rank, full information)** — famously unsolved; cannot ship a rule.
- **General backward-induction optimal stopping over an arbitrary state space** — unbounded scope; the specific solved instances (#19–#21, #24) are what's shippable.
- **Sequential conformal prediction / online calibration** — real overlap with anytime-validity but belongs in a prediction/uncertainty territory.
- **Online FDR (LORD, SAFFRON, alpha-investing)** — belongs in the multiple-testing territory; cross-reference only.
- **UCB / Thompson sampling regret minimization** — different objective (maximize reward while learning, not decide-and-stop); different territory.
- **Exact multivariate-normal group-sequential boundaries for K > 20 looks** — grid-integration error accumulates; the honest answer at that point is "use a confidence sequence," so the tool should say that rather than return a number.
- **Post-hoc / observed power** — actively harmful, a deterministic function of the p-value. Should be an explicit REFUSE with a redirect to MDE (#4).

---

## 5. Cross-territory overlaps

| Overlapping territory | Shared surface | How to divide |
|---|---|---|
| **Estimation & confidence intervals** | Confidence sequences *are* intervals; PrPl-EB, Robbins, betting CS all produce CIs | CI territory owns fixed-n intervals (Wilson, Clopper–Pearson, bootstrap); this territory owns anything valid at a data-dependent stopping time. Both should share one `Φ`, `Φ⁻¹`, incomplete-beta/gamma numerics module. |
| **Hypothesis testing** | SPRT, mSPRT, e-values are tests; power analysis is defined against a test | Testing territory owns the fixed-n test statistics and their null distributions; this territory owns the *n-choosing* and *when-to-stop* wrappers around them. Effect-size definitions must be shared, not duplicated. |
| **Multiple testing / FDR** | α-spending is a within-experiment analogue of FWER control; e-BH and online FDR sit at the join | Multiple-testing owns across-hypothesis control; this territory owns across-*time* control. Flag the compound case (K arms × T looks) explicitly — it needs both. |
| **Bayesian inference** | GRO e-variables are Bayes factors with special priors; EVSI needs a prior + conjugate updating | Bayesian territory owns priors, conjugate updates, posterior summaries; this territory imports them for #24 and cites the Bayes-factor/e-value correspondence. |
| **Decision theory / loss functions** | EVSI, EVPI, cost-per-observation stopping, futility rules | Decision territory owns utilities and loss functions; here they are inputs. Refuse EVSI without an explicit loss. |
| **Effect sizes** | Every sample-size formula needs an effect size on a defined scale (Cohen's d, log odds ratio, relative lift) | Effect-size territory owns conversions and interpretation; this territory consumes them and must never invent a default. |
| **Resampling / bootstrap** | Pilot variance estimates that feed #3, #12, #17; simulation-based power when no closed form exists | Bootstrap territory owns the resampling engine; this territory calls it for `sd` estimation and for simulation-based power/α-inflation (#10, #13). |
| **Bandits / experimental design** | Best-arm identification (#25), allocation ratios, variance reduction | Bandit territory owns allocation and regret; this territory owns the stopping guarantee attached to it. |
| **Count / survival data** | Rule of three, Poisson exposure sizing (#7, #23) | Shared exact Poisson and binomial tail code. |

---

## 6. Sources

**Anytime-valid inference, e-values, confidence sequences**
- Howard, S. R., Ramdas, A., McAuliffe, J., Sekhon, J. (2021). *Time-uniform, nonparametric, nonasymptotic confidence sequences.* Annals of Statistics 49(2). https://arxiv.org/abs/1810.08240
- Howard, S. R., Ramdas, A., McAuliffe, J., Sekhon, J. (2020). *Time-uniform Chernoff bounds via nonnegative supermartingales.* Probability Surveys 17. https://arxiv.org/pdf/1808.03204
- Waudby-Smith, I., Ramdas, A. (2024). *Estimating means of bounded random variables by betting.* JRSS-B 86(1):1–27. https://academic.oup.com/jrsssb/article/86/1/1/7043257 · https://arxiv.org/abs/2010.09686
- Shekhar, S., Ramdas, A. (2023). *On the near-optimality of betting confidence sets for bounded means.* https://arxiv.org/pdf/2310.01547
- Chugg, B., Ramdas, A. (2025). *Closed-form empirical Bernstein confidence sequences for scalars and matrices.* https://arxiv.org/abs/2512.21300
- Grünwald, P., de Heide, R., Koolen, W. (2024). *Safe testing.* JRSS-B 86(5):1091–1128. https://academic.oup.com/jrsssb/article/86/5/1091/7623686 · https://doi.org/10.1093/jrsssb/qkae011
- Ramdas, A., Grünwald, P., Vovk, V., Shafer, G. (2023). *Game-theoretic statistics and safe anytime-valid inference.* Statistical Science. https://arxiv.org/pdf/2210.01948
- Ramdas, A., Wang, R. (2025). *Hypothesis testing with e-values.* Foundations and Trends in Statistics 1(1–2):1–390. https://arxiv.org/abs/2410.23614
- Ramdas, A., Ruf, J., Larsson, M., Koolen, W. *Admissible anytime-valid sequential inference must rely on nonnegative martingales.* https://arxiv.org/abs/2009.03167
- Wang, H., Ramdas, A. *Anytime-valid t-tests and confidence sequences for Gaussian means with unknown variance.* Sequential Analysis. https://arxiv.org/html/2310.03722v5
- Waudby-Smith, I., Arbour, D., Sinha, R., Kennedy, E. H., Ramdas, A. (2024). *Time-uniform central limit theory and asymptotic confidence sequences.* Annals of Statistics 52(6):2613–2640. https://arxiv.org/abs/2103.06476
- Waudby-Smith, I., Ramdas, A. (2020). *Confidence sequences for sampling without replacement.* NeurIPS. https://arxiv.org/pdf/2006.04347
- Wang, R., Ramdas, A. *False discovery rate control with e-values.* https://arxiv.org/abs/2009.02824
- Turner, R., Ly, A., Grünwald, P. *Generic E-variables for exact sequential k-sample tests that allow for optional stopping.* https://arxiv.org/abs/2106.02693
- Wasserman, L., Ramdas, A., Balakrishnan, S. (2020). *Universal inference.* PNAS 117(29):16880–16890.
- Ramdas, A. *Hypothesis testing using e-values, martingales & betting* (talk slides, good formula summary). https://stat.cmu.edu/~aramdas/talks/JHU24.pdf
- Ramdas, A. et al. *Fundamentals of large-scale sequential experimentation* (KDD 2019 tutorial). https://stat.cmu.edu/~aramdas/kdd19/

**Always-valid A/B testing / mSPRT / peeking**
- Johari, R., Koomen, P., Pekelis, L., Walsh, D. (2022). *Always valid inference: continuous monitoring of A/B tests.* Operations Research 70(3). https://arxiv.org/pdf/1512.04922 · https://pubsonline.informs.org/doi/pdf/10.1287/opre.2021.2135
- Johari, R., Pekelis, L., Walsh, D. (2017). *Peeking at A/B tests: why it matters, and what to do about it.* KDD. http://library.usc.edu.ph/ACM/KKD%202017/pdfs/p1517.pdf
- Deng, A., Lu, J., Chen, S. (2016). *Continuous monitoring of A/B tests without pain: optional stopping in Bayesian testing.* https://arxiv.org/pdf/1602.05549
- Lindon, M., Ham, D., Tingley, M., Bojinov, I. (2023). *Anytime-valid confidence sequences in an enterprise A/B testing platform.* WWW '23. https://dl.acm.org/doi/fullHtml/10.1145/3543873.3584635
- *Calculating always-valid p-values in R* — RStudio R Views (concrete mSPRT code). https://rviews.rstudio.com/2019/08/22/calculating-always-valid-p-values-in-r/
- Schultzberg, M. (2026). *A closed-form sample size correction for always-valid inference with optional stopping.* https://arxiv.org/abs/2606.18366

**Classical sequential analysis, group sequential, α-spending**
- Wald, A. (1945). *Sequential tests of statistical hypotheses.* Ann. Math. Statist. 16(2):117–186.
- Wald, A., Wolfowitz, J. (1948). *Optimum character of the sequential probability ratio test.* Ann. Math. Statist. 19(3):326–339.
- Robbins, H. (1970). *Statistical methods related to the law of the iterated logarithm.* Ann. Math. Statist. 41(5):1397–1409.
- Ville, J. (1939). *Étude critique de la notion de collectif.* (Ville's inequality.)
- Armitage, P., McPherson, C. K., Rowe, B. C. (1969). *Repeated significance tests on accumulating data.* JRSS-A 132(2):235–244. (The α-inflation table.)
- Pocock, S. J. (1977). *Group sequential methods in the design and analysis of clinical trials.* Biometrika 64(2):191–199.
- O'Brien, P. C., Fleming, T. R. (1979). *A multiple testing procedure for clinical trials.* Biometrics 35(3):549–556.
- Lan, K. K. G., DeMets, D. L. (1983). *Discrete sequential boundaries for clinical trials.* Biometrika 70(3):659–663. Spending-function formulas as implemented: https://keaven.github.io/gsDesign/reference/sfLDOF.html · https://search.r-project.org/CRAN/refmans/gsDesign/html/sfLDOF.html
- Lan–DeMets tutorial notes (worked spending functions): https://eclass.uoa.gr/modules/document/file.php/MATH301/PracticalSession3/LanDeMets.pdf
- Jennison, C., Turnbull, B. W. (2000). *Group Sequential Methods with Applications to Clinical Trials.* Chapman & Hall. (Reference for the recursive-integration algorithm.)

**Sample size, precision, rare events, equivalence**
- Hanley, J. A., Lippman-Hand, A. (1983). *If nothing goes wrong, is everything all right? Interpreting zero numerators.* JAMA 249(13):1743–1745. (Rule of three.)
- Chow, Y. S., Robbins, H. (1965). *On the asymptotic theory of fixed-width sequential confidence intervals for the mean.* Ann. Math. Statist. 36(2):457–462.
- Kelley, K., Rausch, J. R. (2006). *Sample size planning for the standardized mean difference: accuracy in parameter estimation via narrow confidence intervals.* Psychological Methods 11(4):363–385. (AIPE / assurance.)
- Simon, R. (1989). *Optimal two-stage designs for phase II clinical trials.* Controlled Clinical Trials 10(1):1–10.
- Schuirmann, D. J. (1987). *A comparison of the two one-sided tests procedure...* J. Pharmacokinet. Biopharm. 15(6):657–680. (TOST.)
- Lakens, D. (2017). *Equivalence tests: a practical primer for t-tests, correlations, and meta-analyses.* Social Psychological and Personality Science 8(4):355–362.
- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences*, 2nd ed. (Effect-size conventions and the base formulas.)
- Wichura, M. J. (1988). *Algorithm AS 241: the percentage points of the normal distribution.* Applied Statistics 37(3):477–484. (The `Φ⁻¹` implementation to use.)

**Optimal stopping**
- Ferguson, T. S. (1989). *Who solved the secretary problem?* Statistical Science 4(3):282–289.
- Gilbert, J. P., Mosteller, F. (1966). *Recognizing the maximum of a sequence.* JASA 61(313):35–73. (Full-information variant, 0.5802.)
- Bruss, F. T. (2000). *Sum the odds to one and stop.* Annals of Probability 28(3):1384–1391.
- Raiffa, H., Schlaifer, R. (1961). *Applied Statistical Decision Theory.* (EVSI / EVPI.)
- Berry, D. A., Fristedt, B. (1985). *Bandit Problems: Sequential Allocation of Experiments.*

*Note on verification: all arXiv IDs, DOIs, and URLs above were retrieved or confirmed during this research session except the classical pre-2000 references (Wald, Robbins, Ville, Armitage, Pocock, O'Brien–Fleming, Lan–DeMets, Chow–Robbins, Hanley, Simon, Schuirmann, Ferguson, Gilbert–Mosteller, Bruss, Cohen, Wichura, Raiffa–Schlaifer, Berry–Fristedt), which are cited from standard bibliographic knowledge and should be spot-checked before appearing in shipped documentation.*
