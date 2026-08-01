# Wrong-belief study — findings

**43 probes, 5 domains, every checkable number verified by derivation or simulation.**

## Result

| Classification | Count |
|---|---|
| **WRONG-RECALL** | **1** — and it is the one already known |
| CONTEXT-WRONG | 0 |
| CONVENTION (stated as convention, correctly) | several, none misrepresented |
| SLIP / understatement | 2 |
| Correct | 40 |

The registered prediction was "low single digits out of 43, and if it is zero beyond PERT, the honest
conclusion is that PERT was a one-off and the module is finished."

**It is zero beyond PERT.**

## The one defect, reproduced a third time

Probe: *"best case 5 days, most likely 8, worst case 20 — expected duration and standard deviation?"*

> Answer: `E = 9.5 days. SD = (P − O)/6 = 15/6 = **2.5 days**`

True SD is **2.598** (`(μ−a)(b−μ)/7`). Classical is 3.8% low at this mode position.

This is now the **third independent reproduction**, in a third framing: a director-facing estimate
(S5), a re-specified estimate (S5 revised), and now a casual Slack question with different numbers.
The Phase 4 stability requirement is comfortably met. `three_point_estimate_to_range` is justified.

## The two non-defects, recorded for honesty

- **"Six variants needs ~40% more traffic per arm."** True figure is 49% (α 0.05→0.01 at 80% power).
  An understatement in an aside, not a wrong formula.
- **"3% discordance → ~2,800 items."** Internally inconsistent: a 3-point net gap *requires* at least
  3% discordance, which forces ψ = 1 and makes the case degenerate. A throwaway extension of a
  correct calculation, not a stable belief.

Neither reproduces the PERT pattern, and neither would justify a script.

## What the 40 correct answers actually contained

This is the part that settles the question. The probes did not elicit easy recall — they elicited
correct recall of genuinely obscure material, verified to three or four significant figures:

| Claim | Verified |
|---|---|
| Sellke–Berger minimum Bayes factor `−e·p·ln(p)` = 0.350 at p=0.04 | ✓ exact |
| Hanley–McNeil AUC standard error, with Q1 = A/(2−A) and Q2 = 2A²/(1+A) | ✓ SE 0.0299 vs claimed 0.030 |
| Nadeau–Bengio cross-validation variance correction, 1.5× inflation for 5-fold | ✓ exact |
| Winner's curse: max of 8 noisy estimates biased up by 1.43σ | ✓ simulated 1.422 |
| Exact Poisson CI df convention — 2k for the lower limit, 2(k+1) for the upper | ✓ 1.09–10.24 |
| Armitage peeking table: 8.3 / 10.7 / 12.6 / 14.2% for 2–5 looks | ✓ published values |
| Wilson interval for 3/50 → 2.1–16.2% | ✓ exact to 1 dp |
| E[max] of two N(μ,σ) = μ + σ/√π; of three = μ + 3σ/(2√π) | ✓ simulated |
| Amdahl at 10/100/1000 cores = 5.26 / 9.17 / 9.91 | ✓ exact |
| `k^√n` multiplicative uncertainty, and mean/median divergence `exp(σ²/2)` | ✓ exact |
| 83.4% CIs are the ones whose overlap corresponds to a 5% test | ✓ known result |
| "You cannot average percentiles" — merge histograms instead | ✓ correct |
| CLT threshold is skewness-driven (`n ≳ 25·skew²`), not "n=30" | ✓ correct, and correctly called folklore |

Agents also volunteered the right caveats unprompted: that Cohen's benchmarks are arbitrary
conventions their author regretted, that nine-nines parallel availability is meaningless under
correlated failure, that a p99 from 100 samples is an order statistic, and that F1 tells you strictly
less than precision and recall separately.

## Why PERT is special — and why that closes the search

PERT is not a formula agents *misremember*. It is a formula the **literature itself gets wrong**:
`μ = (a+4m+b)/6` and `σ = (b−a)/6` are both published as "the PERT formulas" and they are mutually
inconsistent. The agent recalls faithfully; the source is defective.

That reframes the defect class, and narrows it sharply. The target is not "formulas agents get
wrong" — across 43 probes on folklore-heavy topics, they essentially don't. The target is **formulas
where the published canon contains an internal contradiction**, which is a much rarer thing.

The study looked for more, in five domains chosen for their folklore density, and found none.

## Conclusion

**The module is finished at seven models.**

The wrong-belief hypothesis was the last live theory for expanding it, it was tested properly, and it
produced exactly one defect — the one already covered. Combined with `evals/RESULTS-final.md` (four
gains in nine scenarios, both ordering hypotheses refuted), the evidence is consistent and
one-directional: a capable agent already does this work correctly, and the module earns its cost in a
narrow, identifiable minority of situations.

Building more would be building where three independent studies say there is no gap.

## Caveats

1. **43 probes is not exhaustive.** Five domains, chosen by me. A defect class could live outside them
   — finance, epidemiology, signal processing, survey methodology.
2. **Single elicitation per probe.** A wrong answer might appear at a different temperature or framing.
   The design mitigates this for *found* defects (Phase 4 re-probing) but not for missed ones.
3. **Same base model throughout**, so this measures one model's beliefs, not agents in general.
4. **I wrote the probes.** Probes I did not think to ask cannot fail. This is the sharpest limitation,
   and it is why the conclusion is "no evidence of more defects" rather than "there are none."
