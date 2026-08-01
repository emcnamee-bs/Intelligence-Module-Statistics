# Review 02 — Independent claim verification

**Method.** Every checkable claim was re-derived from first principles and/or re-computed. Nothing
was verified by locating a source that agrees; §1.16 applies to the 13 territory reports and they
are not independent evidence of each other. Where a number was produced by simulation, the
simulation was written from scratch here, not read from a territory report. Scripts live in
`/tmp/vfy/work/` (`c1.py`, `c1f2.py`, `c2c3.py`, `c4.py`, `c4b.py`, `c4c.py`, `c5.py`,
`c5b_c6.py`, `c7.py`, `c7b.py`, `c8.py`, `c8b.py`, `other.py`).

---

## Verdict table

| # | Claim | Verdict |
|---|---|---|
| 1a | two-sided permutation p<0.05 unreachable at n₁=n₂=3, min p = 0.10 | **VERIFIED** (needs "two-sided" — one-sided reaches exactly 0.05) |
| 1b | paired sign/signed-rank p<0.05 unreachable at n≤5, min p = 0.0625 | **VERIFIED** |
| 1c | 95% distribution-free median CI first exists at n=6 | **VERIFIED** |
| 1d | split conformal 95% needs n ≥ 19 | **VERIFIED** (n = *calibration* set) |
| 1e | [min,max] covers (n−1)/(n+1); 71% at n=6; n=39 for 95% | **VERIFIED** (analytic + MC, 3 distributions) |
| 1f | two-sided 95/95 Wilks tolerance interval needs n=93 | **VERIFIED** (analytic + MC) |
| 1g | MAD = 0 on `[10,10,10,11,10,40]` | **VERIFIED** |
| 2 | AIC/BIC penalties cross at n=e²≈7.39; AIC harsher below | **VERIFIED** |
| 3 | `n ≥ ln α / ln p` unifies rule of three / Wilks / MTBF / quantile / reruns | **PARTIALLY VERIFIED — one entry is not in the cluster** |
| 4 | overconfidence gap detectable at N ≈ 11–25 | **REFUTED as stated** (normal-approx artifact; exact needs 19–33) |
| 5a | bootstrap coverage n=6 lognormal mean: 0.731 / 0.753 / 0.889 | **VERIFIED** (I get 0.750 / 0.770 / 0.885) |
| 5b | bootstrap of a median at odd n is degenerate | **VERIFIED as a theorem**; "meaningless" overstated |
| 6a | sample kurtosis bounded above by ≈ n−1 | **VERIFIED but misstated** — exact bound is n−2+1/(n−1) |
| 6b | at n=10 a Cauchy sample cannot look heavier-tailed than a normal one | **REFUTED** (AUC 0.867, power 0.60 at 5% FPR) |
| 7a | Siegmund CUSUM ARL within 1–4% of published tables | **PARTIALLY VERIFIED** — true for δ≤2, −14% at δ=4 |
| 7b | ARL₀ 370 → 91.75 under Western Electric rules | **VERIFIED** (my MC: 91.62) |
| 7c | naive rate addition gives 52, "wrong by ~76%" | **REFUTED** — correct naive answer is 83.3, error ≈ 9% |
| 8 | 2 × arithmetic mean of p-values is valid under arbitrary dependence | **VERIFIED and shown tight**; conditions under-stated |
| — | §1.37 PERT variance `(μ−a)(b−μ)/7`, R(δ) = 5/7 + (16/7)δ(1−δ) | **VERIFIED symbolically to exact zero residual** |
| — | §1.13 plug-in MI bias (K_X−1)(K_Y−1)/2n | **VERIFIED** (derivation + MC) |
| — | §1.18 uncertainty compounds as f^√k | **VERIFIED**, but only under independence |
| — | §1.24 Kelly log-growth affine in p | **VERIFIED**; the quoted simulation contradicts its own theorem |
| — | §1.31 random detector reaches SOTA F1 under point-adjust | **VERIFIED** by my own simulation (F1 = 0.90) |
| — | §1.18(2) "92% of variance is between-scenario" | **UNVERIFIABLE** (worked example not given) |

**Single most important error: §1.32 / §2.3, the Western Electric "naive addition" figure.** It is
the document's flagship composition hazard and its magnitude is wrong by roughly 8×.

---

## 1. §1.29 arithmetic floors — all verified by direct enumeration

**1a.** All C(6,3) = 20 label assignments enumerated. The two-sided p for the most extreme split is
2/20 = **0.10**; this is structural (the extreme statistic and its mirror). Confirmed.
*Correction to add:* the floor is **two-sided-specific**. The one-sided minimum is 1/20 = 0.05
exactly, which *is* α-attainable. §2.1 P3 states "p<0.05 unreachable at n=3" without the
qualifier; a library refusal message must say two-sided or it will be wrong for one-sided users.

**1b.** All 2ⁿ sign patterns enumerated for both the sign test and the signed-rank test. Minimum
two-sided p = 2/2ⁿ: n=5 → 0.0625, n=6 → 0.03125. Confirmed. (Sign and signed-rank share the same
floor because both bottom out at the single most extreme sign pattern.)

**1c.** Coverage of [x₍₁₎, x₍ₙ₎] for the median is 1 − 2·(1/2)ⁿ. n=5 → 0.9375, n=6 → **0.96875**.
First n reaching 0.95 is 6. Confirmed.

**1d.** Split conformal needs order statistic ⌈(n+1)(1−α)⌉ ≤ n. `0.95n + 0.95 ≤ n ⇔ n ≥ 19`.
Enumerated n=15…21; 19 is the first feasible. Confirmed.
*Add to the refusal text:* n here is the **calibration** set, so a split-conformal user needs
19 + a training set, not 19 total.

**1e.** (n−1)/(n+1) confirmed analytically and by 200 000-replicate Monte Carlo at n=6 and n=39
under normal, exponential and lognormal data (0.7116 / 0.7135 / 0.7129 vs 0.7143; 0.9501 / 0.9488 /
0.9503 vs 0.9500). Distribution-freeness confirmed, not assumed. n=39 → 38/40 = 0.95 exactly.

**1f.** Coverage of [x₍₁₎, x₍ₙ₎] ~ Beta(n−1, 2), so
`P(coverage ≥ p) = 1 − n·p^(n−1)(1−p) − p^n`. At p = γ = 0.95: n=92 → 0.947864, n=93 → **0.950024**.
400 000-replicate MC on uniforms: 0.94756 and 0.94965. Confirmed. (Two-sided 95/99 is n=**473**.)

---

## 2. §1.13 AIC/BIC crossover — VERIFIED

Per-parameter penalties are 2 (AIC) and ln n (BIC). Equal ⇔ ln n = 2 ⇔ **n = e² = 7.389**.
For n < e², ln n < 2, so **BIC's penalty is smaller and AIC penalizes complexity more**. For
integer n: AIC is harsher iff **n ≤ 7** (ln 7 = 1.946); BIC is harsher from n = 8 (ln 8 = 2.079).

Two things to add before this ships as a registry entry:

1. **AICc makes the inversion largely academic.** Below n/k ≈ 40 the correct small-sample criterion
   is AICc, whose penalty `2k + 2k(k+1)/(n−k−1)` is always ≥ 2k and dwarfs both at small n
   (n=5, k=2: AICc 10.0 vs AIC 4 vs BIC 3.2). If the library ships AICc — and at agent scale it
   must — then "AIC is harsher than BIC below n=7" is true of a criterion nobody should be using
   in that regime. State it as a curiosity about the raw penalties, not as guidance.
2. The crossover is about the **penalty**, not about which model wins; the log-likelihood difference
   is unchanged, so the practical inversion only bites when Δ(−2 logL) falls between kΔ(ln n) and 2kΔ.

---

## 3. §1.13 / §1.15 / §2.2 — the `n ≥ ln α / ln p` unification is REAL FOR FOUR OF FIVE, and one filed entry is not in the cluster

Each derived independently from scratch.

| Entry | Derivation | Same inequality? |
|---|---|---|
| **Rule of three** | 0 events in n Bernoulli(θ): `(1−θ)ⁿ ≤ α ⇒ n ≥ ln α / ln(1−θ)`; θ→0 gives θ̂_upper ≈ −ln α/n = 3/n | **YES** (base = 1−θ) |
| **One-sided Wilks tolerance** | coverage F(X₍ₙ₎) ~ Beta(n,1): `P(cov ≥ p) = 1 − pⁿ ≥ γ ⇒ pⁿ ≤ α ⇒ n ≥ ln α / ln p` | **YES** |
| **Upper CI on the p-quantile** | `P(q_p ≤ X₍ₙ₎) = 1 − pⁿ ≥ 1−α ⇒ n ≥ ln α / ln p` | **YES** (identical to the above) |
| **Reruns-to-confidence** | n consecutive passes: `(1−f)ⁿ ≤ 0.05 ⇒ n ≥ ln 0.05 / ln(1−f)` | **YES** (base = 1−f) |
| **Zero-failure MTBF** | `exp(−T/MTBF) ≤ α ⇒ MTBF ≥ −T/ln α = T/2.996` | **RELATED, NOT IDENTICAL** |
| **Two-sided Wilks tolerance** | `1 − n·p^(n−1)(1−p) − pⁿ ≥ γ` | **NO — transcendental in n, no closed form** |

Numerical confirmations: rule-of-three exact bound `1 − α^(1/n)` vs 3/n → ratio 0.863 (n=10),
0.950 (n=30), 0.984 (n=100), 0.997 (n=1000). At n=100 the highest quantile with a 95% upper bound
is `0.05^(1/100) = 0.97049` — §1.13's "nothing above p97" is exactly right.

### The bug this creates

**The spec commits to one implementation backing five registry entries. That implementation cannot
produce n = 93.** §1.29 quotes the **two-sided** 95/95 Wilks figure (93); §1.15 and §2.2 file
"Wilks tolerance intervals" inside cluster C1 and quote the **one-sided** 95/99 figure (299). Those
are different mathematics:

| | one-sided (in C1) | two-sided (**not** in C1) |
|---|---|---|
| 95/95 | n = 59 | n = 93 |
| 95/99 | n = 299 | n = 473 |

Fix: either restrict C1's Wilks entry to the one-sided interval and give the two-sided interval its
own implementation (a monotone search over the Beta(n−1,2) survival function), or drop Wilks from
C1. Do not let one function serve both.

### Two further implementation traps in the "one identity"

1. **The base of the logarithm is a different quantity in different entries.** It is 1−θ (per-trial
   non-event probability) for the rule of three and reruns; it is p (content / quantile level) for
   tolerance intervals and quantile bounds. The literal formula `n >= log(alpha)/log(p)` in §2.2
   returns nonsense if `p` is fed a failure rate. Standardise the API on
   "per-observation probability of the outcome you want to *not* see", and name the parameter
   accordingly.
2. **The MTBF bound solves for a rate, not a sample size.** It is the Poisson/continuous-exposure
   limit of the same one-line algebra (α = survival^exposure), obtained as θ→0, n→∞ with nθ fixed.
   One module can serve it, but it is a *third* inversion of the equation (solve for n; solve for p
   given n; solve for a rate given exposure), not a fifth caller of the same inversion. That is fine
   engineering — it just is not literally "the same inequality," and the registry copy should not
   imply the same call signature.

**Verdict: the unification is real and worth the dedup, but as currently written it is 4/6 correct
with one entry that will produce wrong answers.**

---

## 4. §1.8 — N ≈ 11–25 is REFUTED as stated; the qualitative finding survives

**Assumptions used (stated, per the brief).**
A1. Predictions are grouped by exact stated confidence value (§1.9's own recommendation), so all N
carry the same stated confidence c. A2. Outcomes are independent Bernoulli(q). A3. Test is the
**exact** binomial test of H₀: q = c against q < c. A4. Gap Δ = c − q.

Territory 07 (line ~205) used the **normal approximation**
`n ≥ [(z₀.₉₇₅√(p̄q̄) + z₀.₈₀√(π(1−π)))/Δ]²`. I reproduced its table to the decimal, so the table is
internally consistent — but the approximation is worst exactly in the small-N regime the headline
advertises (p near 0.9, tiny n, heavy discreteness).

| Gap Δ | §1.8 / T07 (normal approx) | **exact, two-sided α=.05** | exact, one-sided α=.05 | understatement |
|---|---|---|---|---|
| 0.30 | 11 | **19** | 16 | 71% |
| 0.25 | 16 | **25** | 18 | 60% |
| 0.20 | 24 | **33** | 25 | 39% |
| 0.15 | 40 | **53** | 44 | 31% |
| 0.10 | 85 | **100** | 83 | 17% |
| 0.05 | 315 | **348** | 277 | 10% |

Exact power was computed by full binomial enumeration with a monotone-stable crossing rule (power
≥ 0.80 at n, n+1 and n+2) to defeat the sawtooth — the raw first crossing is unusable here (power
at n=8 is 0.685 for Δ=0.30 but falls to 0.517 at n=9).

I also ran the more generous **pooled calibration-in-the-large** framing (stated confidences spread
over §1.9's observed lattice {0.70,0.75,0.80,0.85,0.90,0.99}, exact Poisson-binomial null by DP):
Δ=0.30 → N=18, Δ=0.20 → N=35, Δ=0.10 → N=105. Pooling does not rescue the 11–25 figure.

**Three further problems with the headline.**

1. **ECE is not the signed calibration-in-the-large gap.** ECE is a *mean absolute* deviation
   across confidence levels; Δ is a signed gap at one level. They coincide only if all
   miscalibration is one-directional. The published range 0.17–0.57 maps to N = **41 down to 6**
   (exact, two-sided), which is not the interval 11–25 at either end.
2. **§1.8 contradicts §1.9.** §1.9 mandates grouping by exact stated value. Under that rule N is a
   *per-bucket* count, so "an agent that has logged ~20 resolved predictions" needs ~20 in the
   modal bucket — roughly 6–8× that many total predictions given a 6–8 value lattice.
3. Testing all 6–8 buckets separately needs a multiplicity correction, which raises N again.

**Corrected statement to ship:** *"For a gap of the size published for LLM verbalized confidence
(≈0.20–0.30), an exact binomial test reaches 80% power at N ≈ 19–33 resolved predictions at a
single stated confidence level. A 10-point gap needs N ≈ 100; a 5-point gap N ≈ 350."* The
load-bearing conclusion — **tens, not the ~200 imported from clinical prediction modelling** —
survives intact, and it is still the right call to promote the calibration family.

---

## 5. §1.27 bootstrap — VERIFIED

Independent re-simulation, lognormal(μ=0, σ=1), 4000 replicates × B=2000 resamples, BCa with
jackknife acceleration and bias correction implemented from the definition:

| n | percentile | BCa | boot-t | (claimed) |
|---|---|---|---|---|
| 6 | **0.750** | **0.770** | **0.885** | 0.731 / 0.753 / 0.889 |
| 10 | 0.802 | 0.822 | 0.906 | 0.800 / 0.828 / 0.905 |
| 20 | 0.851 | 0.869 | 0.912 | — |
| 50 | 0.897 | 0.908 | 0.927 | — |

Agreement is within Monte Carlo noise at both n=6 and n=10. The n=10 row matches to three decimals.
The width claim also holds: boot-t mean width 9.91 vs percentile 2.25 at n=6, a **4.4×** ratio
("roughly 4× wider"). §1.27's headline conclusion — percentile and BCa are the two an agent reaches
for first and the two that fail hardest — is correct.

**One thing to fix before these numbers ship.** The coverage is extremely sensitive to σ, which
§1.27 does not state:

| σ at n=6 | percentile | BCa | boot-t | boot-t / percentile width |
|---|---|---|---|---|
| 0.5 | 0.828 | 0.828 | 0.923 | 2.2× |
| 1.0 | 0.750 | 0.770 | 0.885 | 4.4× |
| 1.5 | 0.616 | 0.656 | 0.815 | 13.8× |
| 2.0 | 0.489 | 0.535 | 0.759 | 86× |

Any datafile carrying "0.731" must carry "lognormal(0,1)" beside it, or an agent will read it as a
property of the bootstrap at n=6 rather than of one DGP.

### 5b. Median bootstrap degeneracy — VERIFIED as a theorem, "meaningless" is overstated

For odd n the resample median is the ((n+1)/2)-th order statistic of the resample, hence always one
of the n original data values. So it takes **at most n distinct values, and exactly n in practice**.
Measured over 20 000 resamples: n=5 → 5, n=7 → 7, n=9 → 9, n=11 → 11. This is a proof, not a
simulation result, and it is the strongest-supported line in §1.27.

Two refinements:

- **It is not exclusive to odd n.** At even n the median is a mean of two order statistics, giving
  at most n(n+1)/2 values — measured 21 at n=6 (the theoretical max), 34 at n=8, 45 at n=10. Still
  a coarse lattice. Framing the pathology as odd-n-specific will let an even-n caller through.
- **"Any quantile computed from it is meaningless" is too strong.** Measured coverage of the
  nominal-95% bootstrap-percentile CI for the true median on normal data: n=5 → 0.943, n=7 → 0.880,
  n=9 → 0.935, n=15 → 0.918, n=25 → 0.942. That is **erratic and non-monotone**, which is a better
  and more defensible indictment than "meaningless" — and it makes the case for the exact
  order-statistic interval (0.983 / 0.962 / 0.966 / 0.954 at the same n) on the right grounds.

---

## 6. §1.29 kurtosis — bound MISSTATED, conclusion REFUTED

### The exact bound

Maximise b₂ = m₄/m₂² subject to Σz = 0, Σz² = n. The optimum puts one point at +√(n−1) and the
remaining n−1 at −√(n−1)/(n−1), giving

```
b2_max = [(n−1)² + 1/(n−1)] / n  =  (n² − 3n + 3)/(n − 1)  =  n − 2 + 1/(n−1)
```

Verified by explicit construction at n = 2, 3, 5, 10, 20, 50, 100, and by 400 000 random Cauchy
samples at n=6 and n=10 which touch the bound exactly (4.200000 and 8.111111) and never exceed it.

"**Approximately n−1**" is 11% high at n=10 (9 vs 8.111), 23% high at n=5, 33% high at n=3. It is
asymptotically **n−2**, not n−1. Note the territory 04 row states both "bounded above by ≈ n−1"
*and* "at n=10 the maximum possible b₂ ≈ 8.1" in the same sentence — the second figure is the exact
bound and contradicts the first. Ship `(n²−3n+3)/(n−1)`; it is exact, closed-form and one line.
Also declare the estimator: this bound is for the Fisher–Pearson b₂ = m₄/m₂². Excess kurtosis is
bounded by n − 5 + 1/(n−1) (= 5.111 at n=10), and bias-corrected G₂ has a different bound again.

### "A Cauchy sample at n=10 cannot look heavier-tailed than a normal one" — REFUTED

Measured, 20 000 samples each at n=10:

| statistic | normal | Cauchy | AUC | power at 5% FPR |
|---|---|---|---|---|
| b₂ | median 2.281, p95 3.911, max 7.185 | median 4.603, p95 8.039, max 8.111 | **0.867** | **0.601** |
| max\|x\|/Σ\|x\| | median 0.2309 | median 0.4208 | **0.903** | **0.685** |

Kurtosis at n=10 discriminates Cauchy from normal with AUC 0.867 and 60% power at a 5% false
positive rate. It is weak, ceiling-compressed, and a poor choice — but it is not "arithmetically
incapable of detecting the thing it is used to detect," and the recommended replacement beats it by
8 points of power, not by the clean separation implied.

The error is a **like-for-unlike comparison**: the report quotes *medians* for its preferred
statistic (0.234 vs 0.409 — which I reproduce as 0.2309 vs 0.4208) but *maxima* for the statistic it
rejects (8.11 vs 6.57). Both kurtosis distributions are hard-capped at 8.111, so their maxima
necessarily overlap and carry no information about discriminability; and the quoted normal maximum
of 6.57 is an artifact of a 2000-draw simulation (I get 7.185 at 20 000, and it converges toward the
same 8.111 ceiling).

**Corrected statement:** *"Sample kurtosis is bounded above by (n²−3n+3)/(n−1) = n−2+1/(n−1), so at
n=10 no sample of any distribution can exceed b₂ = 8.11. The ceiling compresses the difference
between a normal and a Cauchy sample: kurtosis still separates them (AUC 0.87, power 0.60 at 5%
FPR), but max|x|/Σ|x| does slightly better (AUC 0.90, power 0.69) for one line of arithmetic and no
ceiling artifact. Neither supports a distributional conclusion at n=10."*

This also removes the row from the §1.2 `naive_answer_is_wrong` category — the naive answer here is
weak and ceiling-biased, not wrong.

---

## 7. §1.32 — Siegmund partially verified; the Western Electric addition claim is REFUTED

### 7a. Siegmund's CUSUM ARL approximation

`ARL(Δ) = [exp(−2Δb) + 2Δb − 1]/(2Δ²)`, b = h + 1.166, Δ = δ − k; two-sided by rate addition of the
two one-sided arms. Compared against Montgomery's published table (k=0.5, h=5) **and** against my
own Monte Carlo (60k–200k chains), so the table itself is independently checked:

| shift δ | published | Siegmund | Siegmund err | **my MC** | MC vs published |
|---|---|---|---|---|---|
| 0.00 | 465 | 469.1 | **+0.88%** | 466.8 | +0.40% |
| 0.25 | 139 | 139.8 | +0.56% | 139.8 | +0.59% |
| 0.50 | 38.0 | 38.01 | +0.02% | 37.90 | −0.25% |
| 1.00 | 10.4 | 10.34 | −0.61% | 10.38 | −0.17% |
| 1.50 | 5.75 | 5.67 | −1.46% | 5.75 | −0.01% |
| 2.00 | 4.01 | 3.89 | −3.03% | 4.01 | +0.00% |
| 2.50 | 3.11 | 2.96 | **−4.89%** | 3.12 | +0.22% |
| 3.00 | 2.57 | 2.39 | **−7.14%** | 2.58 | +0.21% |
| 4.00 | 2.01 | 1.72 | **−14.38%** | 2.01 | +0.13% |

My MC reproduces Montgomery to within 0.6% everywhere, so the discrepancies at large δ are
Siegmund's, not the table's — expected, since the approximation is a Brownian-limit result that
degrades as the per-observation drift grows.

**Verdict: PARTIALLY VERIFIED.** "Within 1–4%" holds for δ ≤ 2, which is the region CUSUM is
designed for, and holds at **+0.88% for the in-control ARL₀** — the only value needed for the
stated use (deriving h from a declared false-alarm rate). The blanket claim across "published
tables" is false past δ ≈ 2.5. Ship it with a declared validity envelope (|δ − k| ≲ 1.5), and use
the MC engine for out-of-control ARLs.

### 7b. ARL₀ 370 → 91.75 — VERIFIED

Zero-state MC, 300 000 chains, standard normal, rules: (1) one point beyond 3σ; (2) 2 of 3
consecutive beyond 2σ same side; (3) 4 of 5 consecutive beyond 1σ same side; (4) 8 consecutive on
one side.

- Rule 1 alone: **369.0** (analytic 370.4)
- Rules 1+2+3+4: **91.62** vs the published 91.75 — agreement to 0.14%.

The 4× increase in false alarms is real and the refusal is well founded.

### 7c. "Naive addition gives 52, wrong by ~76%" — REFUTED

Measured ARL₀ for each rule **genuinely alone**:

| rule | territory 13's table | **my MC (rule alone)** | my MC (rule 1 + rule k) | Champ & Woodall's published row |
|---|---|---|---|---|
| 1 | 370 | **369.0** | 369.0 | 370.4 |
| 2 | 327 | **510.4** | 224.9 | 225.44 |
| 3 | 181 | **291.4** | 166.0 | 166.05 |
| 4 | 128 | **255.7** | 152.8 | 152.73 |

Adding the **true** per-rule alarm rates gives `1/Σ(1/ARL_i)` = **83.25** against a true combined
91.62 — an error of **−9.1%**, not −76%.

**Where 52 came from.** Two stacked errors, neither of which is "rates don't add":

1. Territory 13's individual ARLs are computed from **marginal per-point alarm probabilities**
   (its own table is labelled "independent-point calculation"). That is wrong for run rules because
   overlapping windows make the alarm events positively dependent in time. Rule 4 is the clearest
   case: the marginal probability 2·(1/2)⁸ = 1/128 gives ARL 128, but the mean waiting time for a
   run of 8 like symbols is 2⁸ − 1 = **255**, which my MC reproduces (255.7). So each individual
   ARL is understated by 40–80% before any combining happens.
2. Summing the reciprocals of that table gives `1/(1/370 + 1/327 + 1/181 + 1/128)` = **52.4** —
   exactly the quoted figure. Using Champ & Woodall's published rows instead gives 50.7. But
   **each C&W row is the "rule 1 + rule k" scheme, not rule k alone** — I reproduce them to three
   figures (224.9, 166.0, 152.8). So that variant of the calculation triple-counts rule 1.

**The composition hazard is real but small.** Overlapping-window dependence costs ~10%, not 76%.
This matters disproportionately because §1.32 calls it "the cleanest argument in the sweep for a
Monte Carlo engine," §2.3 lists it as one of five composition hazards, and §2.1 P5 elevates
composition error to a governing principle partly on its strength. **The conclusion (ship an ARL
Monte Carlo engine; don't add rule rates) is still right — the ~10% dependence error plus the
40–80% error from marginal per-point probabilities together justify it. But the specific "52" and
"wrong by ~76%" figures must be removed, and the stronger argument substituted: the naive route is
wrong mainly because per-rule ARLs themselves cannot be computed from marginal probabilities.**

---

## 8. §1.16 Vovk–Wang — mathematically VERIFIED and shown tight; conditions under-stated

I verified this by **solving for the worst-case dependence structure**, not by consulting the
source. For K p-values discretised onto m equal cells with exactly uniform marginals, the quantity
`max over all couplings of P(mean(p) ≤ t)` is a multi-marginal optimal-transport linear program.
Solved with HiGHS for K = 2, 3, 4, 5 at grids up to m = 800:

| α | worst-case P(mean ≤ α/2) | ratio to α |
|---|---|---|
| 0.05 | 0.050000 | **1.0000** |
| 0.10 | 0.100000 | **1.0000** |
| 0.20 | 0.20000 | 1.0000 |
| 0.50 | 0.50000 | **1.0000** |

The bound is **never violated** (so 2·mean is valid) and is **attained with equality** at α = 0.05,
0.10 and 0.50 (so the constant 2 cannot be reduced, including at practically relevant α). The
statement in §1.16 is correct.

**Conditions §1.16 should state and does not:**

1. Each pᵢ must be a valid (super-uniform) p-value **under the same null**. The merged value is a
   p-value for the **intersection null** ∩Hᵢ, i.e. "at least one source has a real effect" — not a
   pooled effect estimate, and not a test of a common effect size.
2. **K must be fixed in advance.** Choosing which p-values to average after seeing them breaks
   validity. Given §1.6's finding that adaptive collection is the agent's natural behaviour, this
   needs to be an explicit precondition, not an assumption.
3. **The price is a hard factor of 2.** In exactly the pseudo-replication limit §1.16 describes —
   k perfectly correlated agents all reporting p — the merged value is 2p. Any single-source p
   above 0.025 becomes non-significant after merging, and k correlated agents give a *strictly
   worse* answer than one agent. That is correct behaviour and arguably the point, but §1.16 sells
   it as "mitigation available and cheap," which reads as though it recovers something. It does
   not: it is a **validity guard that prevents false certainty, not a way to extract evidence from
   correlated sources.** Say so, or an agent will read a merged 0.08 as a failed analysis rather
   than as the honest answer.
4. Correspondingly it is very lossy under independence (5 independent p-values of 0.04: 2·mean =
   0.080, Fisher = 3.7e−4). Keeping independence-assuming methods as opt-in, as §1.16 proposes, is
   right — but the opt-in must be gated on provenance, not on the agent's assertion.

**Probable citation error (flagged, not verified — I checked the mathematics, not the bibliography).**
The 2 × arithmetic-mean result is Vovk & Wang, *Combining p-values via averaging*, **Biometrika**
107(4):791–808 (2020). The Annals of Statistics 2022 paper (50(1):351–375) is Vovk, **Wang & Wang**,
*Admissible ways of merging p-values under arbitrary dependence*. §1.16's "Vovk & Wang (AoS 2022)"
appears to merge the two. Per §2.5(4) this needs resolving before the model ships.

---

## Other claims checked

### §1.37 PERT variance — VERIFIED symbolically, exactly

Re-derived in sympy from α = 1 + 4(m−a)/(b−a), β = 1 + 4(b−m)/(b−a):
α + β = 6 exactly; μ = (a + 4m + b)/6 exactly;
`Var − (μ−a)(b−μ)/7` simplifies to **exactly 0**; and
`R(δ) − [5/7 + (16/7)δ(1−δ)]` simplifies to **exactly 0**. Every row of §1.37's table reproduces:
δ=0 → R=0.714286, SD ratio 0.845154, classical overstates by +18.32%; δ=0.14645 → R=1.000005;
δ=0.25 → −6.46%; δ=0.5 → R=9/7=1.285714, classical understates by −11.81%. This is the
best-supported claim in the document and should be treated as settled.

### §1.13 plug-in MI upward bias — VERIFIED

Derived from Miller–Madow: bias(Ĥ) = −(K−1)/2n, so for MI = H(X)+H(Y)−H(X,Y) the bias is
`[−(K_X−1) − (K_Y−1) + (K_XK_Y−1)]/2n = (K_X−1)(K_Y−1)/2n`. MC on independent variables:
K=3×3, n=50 → measured 0.0428 vs predicted 0.0400; 4×5, n=100 → 0.0644 vs 0.0600; 2×2, n=30 →
0.0176 vs 0.0167. Correct to first order, slightly conservative (the true bias is a little larger
at small n) — which is the safe direction for a refusal rule.

### §1.13 PSIS-LOO k̂ = min(1 − 1/log₁₀S, 0.7) — arithmetically consistent

The n-dependent branch binds only below S ≈ 2154 (1 − 1/log₁₀S < 0.7 ⇔ log₁₀S < 10/3). At S=1000
the threshold is 0.667. Worth stating in the registry entry, since above ~2000 draws the rule is
indistinguishable from the flat 0.7 it replaced.

### §1.18(1) uncertainty compounds as f^√k — VERIFIED, with a missing precondition

Derived: if each log-factor has 90% half-width ln f, the sum of k has half-width √k·ln f, so the
product's interval is median × f^±√k. MC (400 000 draws): k=4, f=3 → 8.98 (predicted 9.00); k=9 →
27.07 (27.00); k=16 → 82.0 (81.0).

**But the √k saving requires independence in log space**, which §1.18 does not state and which
Fermi factors routinely violate (a shared scale assumption correlates everything). Equicorrelated
log-errors, k=4, f=3:

| ρ | actual ± factor |
|---|---|
| 0.0 | 9.02 (= f^√k) |
| 0.3 | 20.6 |
| 0.6 | 39.4 |
| 1.0 | 80.8 (= f^k) |

At ρ = 0.3 the spread is already more than double the f^√k answer. §1.18 says agents get this wrong
"in both directions"; shipping f^√k without an independence check would make the module a source of
the under-widening error it is meant to prevent. The model must ask whether the factors share a
driver, and interpolate — `f^√(k + k(k−1)ρ)` is the exact equicorrelated answer.

### §1.24 Kelly — theorem VERIFIED, but §1.24 contradicts itself

`G(f) = Σ pᵢ log(1 + rᵢf)` is **linear in the vector p**, so `E_p[G(f)] = G_{E[p]}(f)` and the
argmax over f is **exactly** invariant to any uncertainty in p. Confirmed numerically on a
three-outcome bet: f* at p̄ and f* maximising the average of G over 3000 Dirichlet draws are
identical.

§1.24 then cites a simulation in which "σ = 20% on p moves f* only from 0.40 to 0.36." That
**contradicts the theorem stated two lines earlier** — under the stated theorem the movement is
exactly zero. The only way to produce movement is to average the *per-draw* f* values (a Jensen
artifact: I measure 0.3794 vs 0.3776, a small shift in the right direction), which is the wrong
quantity: it is the mean of the optimal fractions, not the fraction that is optimal. Either drop
the simulation or relabel it as an illustration of the wrong estimator. As written, an implementer
will conclude the invariance is approximate when it is exact — and the exactness is the whole point
of the row.

### §1.31 random detector under point-adjust — VERIFIED by my own simulation

10 000-point series, 29 injected anomaly segments (20% anomalous). A purely random detector, scored
under the point-adjust protocol (any hit inside a segment marks the whole segment detected):

| random flag rate | raw F1 | point-adjust F1 |
|---|---|---|
| 0.005 | 0.010 | 0.519 |
| 0.020 | 0.037 | 0.831 |
| 0.050 | 0.081 | **0.896** |
| 0.100 | 0.137 | 0.834 |

Confirmed: random scoring reaches F1 ≈ 0.90 under point-adjust while its honest F1 is 0.08. §1.31's
licence to stay classical is well founded.

### §1.18(2) "92% of total variance is between-scenario" — UNVERIFIABLE

The worked three-scenario example is not reproduced in Part 1 or Part 2, so the figure cannot be
checked. It is highly sensitive to the assumed within-scenario spreads and scenario weights. Per
§2.5(3) it must not enter a shipped datafile until the example is written down.

---

## Recommended edits

**Must fix (produce wrong answers or wrong magnitudes):**

1. **§1.32 / §2.3 / §2.1 P5** — delete "naive addition gives 52, wrong by ~76%". Replace with: true
   naive rate addition gives 83.3 vs 91.6, a 9% error; the larger error is in computing per-rule
   ARLs from marginal per-point probabilities (rule 4: 128 quoted vs 255 true). Correct territory
   13's §3.4 individual-ARL table.
2. **§1.15 / §2.2 C1** — restrict the Wilks entry to the **one-sided** tolerance interval and give
   the two-sided interval its own implementation. One function cannot produce both 59/299 and
   93/473. Rename C1's parameter to make the base of the logarithm unambiguous.
3. **§1.8** — replace 11–25 with the exact-binomial 19–33; state that N is per-confidence-bucket;
   stop equating ECE with the signed gap.
4. **§1.29 kurtosis row** — replace "≈ n−1" with `(n²−3n+3)/(n−1)`; delete "cannot look heavier-
   tailed"; report AUC/power on a like-for-like basis (0.87/0.60 vs 0.90/0.69); remove from the
   `naive_answer_is_wrong` category.

**Should fix (overstated or missing a precondition):**

5. §1.32 — bound Siegmund's claim to |δ − k| ≲ 1.5 (error reaches −14% at δ=4).
6. §1.16 — add the four preconditions above, especially the factor-of-2 price and "K fixed in
   advance"; check the Biometrika 2020 vs AoS 2022 attribution.
7. §1.18(1) — add the independence precondition and the equicorrelated formula.
8. §1.24 — remove or relabel the 0.40 → 0.36 simulation; it contradicts the exact result.
9. §1.27 — attach "lognormal(0,1)" to the coverage figures; extend the median-degeneracy warning to
   even n; replace "meaningless" with the measured 0.88–0.94 erratic coverage.
10. §1.29 / §2.1 P3 — qualify the permutation floor as **two-sided** (one-sided reaches 0.05
    exactly at 3v3); note that the split-conformal n=19 is the calibration set.
11. §1.13 — note that AICc dominates the AIC/BIC crossover at the n where the crossover occurs.

**Nothing found wrong with:** §1.29 floors 1a–1f and the MAD example, §1.13's AIC/BIC crossover and
MI bias and quantile-bound arithmetic, §1.27's bootstrap coverage figures, §1.32's 370→91.75,
§1.16's Vovk–Wang mathematics, §1.31, and §1.37 — which verifies exactly and is the model the rest
of the document should be held to.
