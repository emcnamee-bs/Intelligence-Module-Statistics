# Review 01 — Spec Coherence and Buildability

**Target:** `docs/superpowers/specs/2026-07-31-statistical-judgment-module-design.md`
**Against:** `RESEARCH.md`, `research/territories/*.md`
**Lens:** internal coherence and buildability. Could a competent engineer build exactly this without guessing?
**Verdict up front:** No. Wave 0 as written cannot be started to completion. Fourteen findings below, ranked.

Findings are ranked by severity: **BLOCKER** (Wave 0 cannot complete as written), **MAJOR** (engineer must
invent a contract the spec claims to define), **MINOR** (local inconsistency, cheap to fix).

---

## F1 — BLOCKER. The gate's own CLI signature is arithmetically incapable of the output the gate is built to produce

**Offending text (§5):**

```
python3 models/decision/value_of_information_reachability.py \
    --options "ship,hold" --loss-if-wrong 40 --current-belief 0.7 --cost-to-measure 2
```

> | EVPI = 0 | **Stop.** No measurement can change the decision. |

**And (§12, Wave 0 acceptance):**

> `value_of_information_reachability` — the gate itself (§5); **must produce EVPI = 0 on a constructed case**

**The problem.** Those four flags fully determine a 2-action / 2-state decision with a symmetric
zero-diagonal loss matrix: loss 0 when you pick the action matching the state, `L` when you don't.
Under that parameterisation:

```
prior-optimal action  = argmax(p, 1−p)
expected loss now     = min(p, 1−p)·L
expected loss under perfect information = 0
EVPI                  = min(p, 1−p)·L
```

For the worked example, EVPI = 0.3 × 40 = **12**. EVPI = 0 requires `p ∈ {0, 1}` or `L = 0` — i.e. the
agent already knows the answer, or nothing is at stake. In neither case would an agent be running a
statistics module. **The signature in §5 cannot emit the value that §5's routing table and §12's Wave 0
gate both require**, except in degenerate inputs that should themselves be refusals.

EVPI = 0 in the non-degenerate case requires *action dominance* — one action best in every state — which
needs a full loss table (`k` actions × states), not one scalar. And the "provable in about three lines"
result the spec cites is not EVPI at all: territory 10 row 22 is **EVSI** for an imperfect test, where
`EVSI = 0` follows from *threshold reachability* — neither a positive nor a negative result moves the
posterior across `p*`. That needs sensitivity and specificity, which the CLI does not accept.

**Concrete failure.** The engineer writes the script, writes the Wave 0 golden test, and it cannot be made
to pass with any legitimate input. Wave 0 stalls at item 5 with no way to resolve it from the spec.

**Fix.** Split the gate into two tools with distinct contracts:
- `evpi_upper_bound.py --loss-table <csv|inline> --prior <probs> --cost-to-measure C` — takes a real
  `k × states` payoff/loss table, returns `EVPI = E_θ[max_a v] − max_a E_θ[v]`, and returns exactly 0 when
  an action dominates. State that EVPI = 0 requires dominance, and require ≥2 actions × ≥2 states.
- `evsi_threshold_reachability.py --prior π --sensitivity Se --specificity Sp --payoffs ...` — computes
  `p*` and returns `EVSI = 0` **as a proof** when neither result crosses it. *This* is the three-line
  result and the one that belongs in Wave 0.

---

## F2 — BLOCKER. The gate's routing table inverts a one-directional test, and its modal input makes it always say "stop"

**Offending text (§5):**

> | EVPI > cost, data exists | Tier 1 or 2 — route to a model. |
> | EVPI > cost, data does not exist | **Tier 3.** Constructing the dataset is justified; the check says by how much. |

**Problem A — the inference only runs one way.** EVPI is the value of *perfect* information and is a hard
upper bound: `EVSI(n) ≤ EVPI` for all n. Territory 10 states this correctly:

> "EVPI is a hard *upper bound* on every downstream tool in this table: **if EVPI < the cost of the
> cheapest experiment, stop** and decide now."

Only the negative direction is valid. `EVPI > cost` does **not** imply any achievable measurement is worth
its cost — the best real sample may be worth a fraction of EVPI. And "the check says by how much" is
false: EVPI quantifies the value of an oracle, not of the dataset the agent is about to construct. A
module whose thesis is calibration ships, as its first act, a systematically **overconfident** justification
for going and measuring. That is the exact failure the module exists to prevent, in the gate.

**Problem B — the modal input yields a meaningless zero.** Territory 10 row 1 refusal:

> "Refuse if any option's value distribution was elicited as a point estimate (**then EVPI is mechanically
> 0 and meaningless**)."

An agent will almost always supply point estimates. The spec reads that same mechanical zero as
"**Stop.** No measurement can change the decision. The agent now has a *number* justifying stopping." The
spec converts a research-mandated refusal into a confident, wrong, proof-flavoured stop. Combined with F1,
the gate is either always non-zero (under the §5 CLI) or always zero-and-meaningless (under point
estimates) — never usefully informative.

**Fix.** (a) Use EVPI only as a *stop* screen: `EVPI < cost → stop`; never as a *go* signal. Route to a
model when EVPI ≥ cost only with the caveat printed, or better, require `EVSI(n) > cost(n)` for the
specific n proposed before authorising Tier 2/3. (b) Port territory 10's refusals verbatim into the gate:
refuse on point-estimate value inputs, refuse when `EVPI < 2·SE`, refuse on mixed units across options.

---

## F3 — BLOCKER. `baseline_to_beat` / `BASELINE_WINS` has no computable definition outside forecasting

**Offending text (§3 P9, §7, §9):**

> **P9** Every model **declares the baseline it must beat**, and prints the baseline instead when it doesn't
> `"baseline_to_beat": "assuming the rate is zero"`
> | `BASELINE_WINS` | 0 | Model fails to beat its declared baseline (P9) | **The baseline's answer**, not the model's |

**The problem.** P9 was generalised from a single family. Its origin (§1.39) is MASE — forecasting has a
held-out scoring rule, so "beats the naive forecast" is a computable comparison of two numbers on the same
loss. **The spec never defines the comparison operator for any other family**, and for most it does not
exist:

- `zero_events_observed_upper_bound`: the model returns an interval; the declared baseline "assuming the
  rate is zero" returns a point. There is no loss function in the spec comparing an interval to a point
  claim, no held-out data (the tier is INLINE, `--trials N` is the entire input), and no threshold. The
  model can never "fail to beat" this baseline, so `BASELINE_WINS` is dead code — yet L4 mandates a test
  for it.
- `three_point_estimate_to_range`: INLINE, no data at all. There is nothing to score against, and no
  baseline is even named in §12.
- The gate itself: what baseline must `value_of_information_reachability` beat? Unspecified.

**Compounding contradiction (§11 L4):**

> **L4** Refusal tests | ≥1 input per model per applicable mode (3, 4, `BASELINE_WINS`) **with no number emitted**

`BASELINE_WINS` is defined in §9 as the mode that **does** emit a number (the baseline's). The L4 sentence
requires the opposite of the §9 contract for the same mode. An engineer writing the test harness has two
mutually exclusive assertions and no tiebreak. The same sentence also mixes naming conventions — two exit
codes and one mode name — implying `BASELINE_WINS` has no exit code of its own, which is F4.

**Fix.** Either:
1. Narrow P9 to families with a held-out scoring rule (forecasting, calibration, model-choice,
   monitoring), make `baseline_to_beat` nullable, and have the registry carry
   `baseline_metric` (e.g. `"MASE"`, `"log-score"`), `baseline_comparison` (`"<"`/`">"`), and
   `baseline_requires_holdout: bool`; or
2. Keep P9 library-wide but redefine `BASELINE_WINS` as *width dominance* — the model's interval is no
   narrower than the baseline's at the same coverage — and specify that comparison in `lib/report.py`.

Whichever is chosen, `baseline_to_beat` must become a machine-checkable structure, not the free-text
English string shown in §7. Fix the L4 clause to `"no model-derived number emitted"`.

---

## F4 — BLOCKER. The output contract — Wave 0's entire deliverable — is one sentence, and it conflicts with itself

**Offending text:**

> §6: `report.py  # output contract, --json, the **five** output modes`
> §9: `### **Six** output modes`
> §9: `--json emits the same content with "status" set to the mode.`

Four distinct defects:

**(a) Five vs six.** §6 and §9 disagree on the number of modes. Trivial in isolation, but `report.py` is a
Wave 0 file and this is its only specification.

**(b) No mode precedence.** Four of the six modes can co-occur. The spec's own pilot proves it: §12 says
`benchmark_regression_from_repeated_runs` "exercises `BASELINE_WINS` **and** the p<0.05-unreachable floor
at n=3". At n=3 that model is simultaneously `REFUSED` (arithmetic floor, §9), plausibly `BASELINE_WINS`
(three runs will rarely beat "assume no regression"), and plausibly `ROBUSTNESS`. Exit status is a single
integer. **The spec never states which mode wins.** Two engineers will resolve this differently and the
L4 tests will be non-deterministic across implementations.

**(c) All four informative modes share exit 0.** `OK`, `CAVEAT`, `ROBUSTNESS`, `BASELINE_WINS` are all
exit 0. An agent doing the obvious thing — `if rc == 0: use the number` — receives the *baseline's* answer
believing it is the model's, with no signal. This voids P9 for exit-code-checking callers and directly
contradicts the §9 rationale for splitting exit 3 from exit 2 ("two situations demanding opposite
responses"): `OK` and `BASELINE_WINS` also demand opposite responses and are given the same code. It also
strains success criterion 4 ("No script ever emits a confident number when ... it fails to beat its own
declared baseline") — it emits a confident number that the exit code certifies as fine.

**(d) No JSON schema exists.** "the same content" is not a schema. Undefined: the key names; whether
`NO ANSWER EXISTS` and `REFUSED` emit a `value` key at all (null? absent? — the two require different
consumer code); where the mandatory `CAVEAT` line, the `ROBUSTNESS` breakdown value, the baseline's answer,
the remedy text, and the composition hazards live; whether there is an output `schema_version`
(`registry.json` has one, output does not); what appears on stdout vs stderr. The one artifact Wave 0
exists to "prove" is the one artifact with no definition.

**Fix.** Add a §9 subsection specifying:
- a strict total precedence order, e.g.
  `NO ANSWER EXISTS > REFUSED > BASELINE_WINS > ROBUSTNESS > CAVEAT > OK`, with all *other* applicable
  modes listed in a `also_applies: []` array so information is not lost;
- distinct exit codes: `0 OK`, `1 internal error` (currently unassigned — an uncaught Python exception
  exits 1 and falls outside the contract, violating "solve, don't punt"), `2 usage`, `3 REFUSED`,
  `4 NO ANSWER EXISTS`, `5 BASELINE_WINS`, `6 ROBUSTNESS`, `7 CAVEAT`. If exit-code proliferation is
  unwanted, at minimum give `BASELINE_WINS` its own non-zero code;
- a literal JSON example for **each** of the six modes, in the spec, with every key named and typed.
  These six blobs are the acceptance criterion for `report.py`.

---

## F5 — BLOCKER. Wave 0's file list does not match what Wave 0's pilots need, in both directions

**Offending text (§12 items 3 and 5, against §6):**

> 3. `lib/special.py`, `lib/dist.py`, `lib/exact.py`, `lib/grid.py`, `lib/optim.py`, `lib/report.py`
> 5. ... `benchmark_regression_from_repeated_runs` — **DATAFILE**/MUST-CONSTRUCT ...
> §6: `dataio.py  # CSV/JSON loading, messy-input handling  **[Wave 1]**`

**Missing.** The only DATAFILE-tier pilot in Wave 0 needs CSV loading, and the CSV loader is explicitly
scheduled for Wave 1. The engineer must either ship an untracked ad-hoc parser inside the model (breaking
"one tested implementation" and guaranteeing divergence from the real `dataio.py` in Wave 1) or pull
`dataio.py` forward. The spec does not say which.

**Unneeded.** Trace the four pilots against the six Wave 0 libs:

| Pilot | special | dist | exact | grid | optim | report | dataio |
|---|---|---|---|---|---|---|---|
| `value_of_information_reachability` | – | maybe `NormalDist` (stdlib) | – | – | – | ✔ | – |
| `zero_events_observed_upper_bound` | – | – | ✔ (`coverage_inequality`) | – | – | ✔ | – |
| `benchmark_regression_from_repeated_runs` | – | maybe | ✔ (permutation) | – | – | ✔ | **✔ (Wave 1!)** |
| `three_point_estimate_to_range` | ✔ if exact quantiles | ✔ if exact quantiles | – | – | – | ✔ | – |

**`lib/grid.py` and `lib/optim.py` are used by zero Wave 0 pilots.** Wave 0 is defined as "prove the
contract" with a review gate at the end; building two untested-by-any-caller numerics modules with full L1
golden suites is orthogonal to that purpose, and it is the largest single chunk of Wave 0's effort. It also
violates the spec's own P2 discipline applied to itself (§11.2): golden tests on a module no model calls
establish no power against the failures that matter.

**Fix.** Wave 0 libs = `report.py`, `exact.py`, `dataio.py`, plus `special.py`/`dist.py` **only if**
`three_point_estimate_to_range` ships exact PERT quantiles (if it ships moments + `random.betavariate`
Monte Carlo, both drop out too). Move `grid.py` and `optim.py` to Wave 1, gated on the first model that
calls them.

---

## F6 — BLOCKER. Wave 0 builds a registry for 310 models, four of which exist; `route.py` and L5 are undefined against it

**Offending text (§12):**

> 2. **Dedup pass** over the 310 ranked models → implementation list + registry entries (§8).
> 4. `registry.json`, `route.py`, `generate_docs.py`, CI drift check.
> 6. Full **L1–L5** ladder green on those four.

**Circularity and dangling state.** Item 2 produces registry entries for ~310 models. Item 4 generates
`INDEX.md` and `docs/families/*.md` **from** that registry. Item 5 implements four. Therefore at the Wave 0
review gate:

- `INDEX.md` advertises ~306 models whose `path` files do not exist;
- `route.py` will happily return top-3 matches pointing at missing scripts — the agent runs
  `python3 models/causal/e_value.py`, gets `No such file`, exit 2 from the shell, which the contract in §9
  assigns to "you typed the flag wrong". Nothing in the spec prevents this;
- the CI "fail on diff" check freezes ~310 hand-written `usage` strings, `baseline_to_beat` strings, and
  `refuses_when` strings for models nobody has written. Every one will be wrong in detail, and every
  correction is a CI-gated churn event. Speculative documentation is being made load-bearing.
- **Composition hazards will dangle.** `composition_hazards` "names model ids that must not be chained into
  this one". At Wave 0 those ids reference unwritten models. No validation rule is specified for whether a
  referenced id must exist, so CI cannot check referential integrity — the field's only enforcement
  mechanism is unavailable exactly when the registry is being authored.

**L5 is unsatisfiable.** "Full L1–L5 ladder green on those four" — but L5 is *routing evals*: "Recall@3 on
a labelled query set **and** false-positive control on should-match-nothing queries". Recall@3 is a
property of `route.py` over the whole registry, not of four scripts. Over a 310-entry registry the labelled
query set must cover 310 models; over a 4-entry registry it is meaningless. The spec does not say which
registry L5 runs against, and there is no notion of a query "correctly" matching an unimplemented model.

**Fix.** Add `"status": "shipped" | "planned"` to the model schema. Wave 0 registry contains the schema,
the implementation-cluster list from the dedup pass, and **four `shipped` entries only** — the dedup pass
output goes to a separate `research/dedup-clusters.md`, not into `registry.json`. `route.py` filters to
`shipped` by default and, if it must surface planned entries, prints them under an explicit
`NOT YET IMPLEMENTED` heading with no `usage` line. `generate_docs.py` renders only `shipped`. CI validates
that every `composition_hazards` id resolves to an existing registry entry. L5's query set is scoped to
`shipped` entries plus the should-match-nothing set.

---

## F7 — MAJOR. `route.py` is a Wave 0 deliverable with an L5 gate and no specified algorithm

**Offending text (§6):**

> `route.py   # Discovery: query -> ranked matches + usage`

That is the entire specification. The word "ranked" is the only hint at a mechanism; no retrieval method is
named anywhere in the spec or in `RESEARCH.md`. (BM25, TF-IDF, edit distance, and embeddings appear
nowhere in either document.) Undefined, all of it required to write the file:

1. **Scoring function.** Exact-token overlap? Stemming (which stemmer, hand-rolled)? Stopwords? Are
   `situations` phrases scored as documents or as whole-phrase matches? Are `keywords` weighted above
   `situations`? Is `title` indexed? IDF over what corpus — the registry is 310 short documents, where IDF
   is unstable and dominated by family-common words like "rate", "test", "data".
2. **A match threshold.** L5 demands "false-positive control on should-match-nothing queries", which
   requires a score below which `route.py` returns nothing. No threshold, no method for setting one, and no
   definition of what "returns nothing" looks like (empty list? a message? which exit code?). **L5 cannot be
   written.**
3. **Cross-family behaviour.** What does `route.py` do when the top matches span three families — say
   "is this slowdown real" hitting `signal-vs-noise`, `monitoring`, and `forecasting`? Return the global
   top-3 (possibly three near-duplicates of one identity cluster), or one per family, or group by family?
   The C1 cluster alone spans four families with near-identical `situations` phrasing, so **the identity
   clusters guarantee this case is common, and the spec is silent.**
4. **Identity-cluster collapse.** If five entries share `implementation: exact-binomial-coverage-inequality`
   and all five match, does the agent see five results or one? Showing five wastes the top-3 slots on one
   piece of mathematics; showing one discards the family-specific phrasing that the dedup design exists to
   preserve.
5. **`naive_answer_is_wrong` contradicts false-positive control.** §7 says the router "surfaces the warning
   **even on a weak match**". "Weak" is undefined, and surfacing weak matches is definitionally a false
   positive — the thing L5 is supposed to control. The two requirements pull in opposite directions with no
   arbitration.

**Fix.** Specify the algorithm concretely in §6 or a new subsection: e.g. lowercase + punctuation strip +
a fixed inline stopword list; per-entry document = `title + situations + keywords`, keywords weighted 2×;
BM25 with stated `k1`/`b` **or** simple cosine over log-TF (pick one, and justify); a stated absolute score
floor plus a relative floor (`score < 0.4 × top_score` drops); deduplicate results by `implementation` id,
showing the best-matching entry per implementation; return at most one entry per family in the top 3 unless
fewer than 3 families match; and a defined empty result (`{"matches": [], "status": "NO_MATCH"}`, exit 0).
Then define `naive_answer_is_wrong` surfacing as a **second, separately-scored** list with its own lower
threshold, so it does not pollute the recall/FP metric.

---

## F8 — MAJOR. Composition hazards are stranded — the design does not deliver the property that justifies it being a skill

**Offending text:**

> §2.3 of `RESEARCH.md`: "These motivate the `composition_hazards` registry field and are the strongest
> argument that this is a **skill** and not a folder of scripts. No individual model can detect any of them."
> §13: "`composition_hazards` registry field; **router prints them**"

**The problem.** The hazard is a property of a *sequence of two invocations over time*. The chosen
enforcement point is a *single stateless routing call*. These do not line up:

- **Wrong moment.** The changepoint→ITS hazard fires when the agent feeds a *detected* date into ITS. At
  the moment the agent routes to changepoint detection, no hazard exists. At the moment it routes to ITS —
  if it routes at all — the router has no memory of the earlier run and cannot know the date's provenance.
  It can only print "ITS has hazards" unconditionally, which is a static warning, i.e. exactly the
  "warning adjacent to a number" pattern §9 rejects on evidence: *"Agents have been observed ignoring
  diagnostics... A warning adjacent to a number does not work."* The spec applies that lesson to model
  output and then ignores it for the router.
- **Bypassable.** The router is not on the critical path. §9 guarantees `--help` "always yields exact
  usage without reading the file", §6 ships `INDEX.md` and grep-able `docs/families/*.md`, and §5 says the
  skill's first act is the EVPI script, not `route.py`. A second-tool invocation reached via `--help` or
  grep sees no hazard at all.
- **Alarm fatigue.** Printing every hazard on every match trains the agent to skip the hazard block, at
  which point the field is decorative.
- **`independence_required: true` and `data_provenance_required` have the same defect** — booleans in a
  JSON file cannot compel a script to ask anything. Territory 10 already prescribes the right shape:
  *"This is the dominant real-world failure and must be checked by an **explicit question**."*
- **Never exercised in Wave 0.** None of the five hazards in §2.3 touches any of the four pilots, so the
  Wave 0 review gate validates none of the mechanism that supposedly justifies the skill wrapper.

**Fix.** Move enforcement into the model boundary, where refusal is available:
- Each hazard generates a **required CLI flag** on the *downstream* model, with no default:
  `interrupted_time_series.py --intervention-date-source {a-priori|detected}` → `detected` ⇒ `REFUSED`
  (exit 3) with the remedy; `pool_studies.py --collection {fixed|adaptive}` → `adaptive` ⇒ `REFUSED`,
  route to e-value products; `combine_forecasts.py --sources {independent|shared-generator|unknown}` →
  anything but `independent` ⇒ Vovk–Wang default with the effective-k adjustment.
- Change the registry field from `composition_hazards: ["model-id"]` to
  `{"upstream": "<model-id>", "guard_flag": "<flag>", "unsafe_value": "<v>", "why": "<text>"}` so CI can
  assert the flag actually exists in the downstream script's argparse.
- Keep the router print as a *secondary* affordance, not the enforcement.
- Add one composition-hazard pair to Wave 0 so the mechanism is proven at the review gate — otherwise the
  skill-vs-scripts thesis is untested until Wave 1.

---

## F9 — MAJOR. `implementation` indirection vs "one script per model" is unresolved, and the header creates a third source of truth

**Offending text:**

> §7: `"path": "lib/exact.py:coverage_inequality"`, `"note": "Backs 5 registry entries across 4 families."`
> §8: "One tested implementation, **many registry entries** routing into it."
> §9: "**Standalone** `python3 models/<family>/<name>.py` with `argparse`"
> `README.md`: "`models/<family>/` | **One script per model**"

**Unanswered question.** Do the five C1 entries produce five `.py` files or one? The schema gives each
model entry its own `path`, so five. But then the dedup pass saves almost nothing — the shared part is a
~40-line inequality, the per-entry work (flags, tier, baseline, refusals, output framing, golden cases) is
all still five-fold. If instead it is one file with five registry aliases, then `path` is non-unique,
`route.py` returns five rows pointing at one script, and a single `argparse` must express five different
`usage` strings, five `baseline_to_beat` values, and five sets of refusals — which it cannot. The spec
asserts the benefit ("substantially reduces the true cost of Wave 1") without resolving the mechanism.

**Three sources of truth.** §7 declares `registry.json` the "**SINGLE SOURCE OF TRUTH**". §9 then mandates
a 7-field header on every script duplicating five registry fields (`WHAT`↔`title`, `WHEN`↔`situations`,
`INPUTS`/`EXAMPLE`↔`usage`, `OUTPUT`↔`output`, `BASELINE`↔`baseline_to_beat`, `ASSUMPTIONS`↔`refuses_when`),
and argparse holds a third copy of the usage. CI checks *doc* drift only (`INDEX.md`, `docs/families/`); it
does not check header↔registry or argparse↔registry drift. Two of the three copies will rot silently.

**Also.** The §9 header budget is "≤12 lines, ~120 tokens" for 7 fields where `INPUTS` is "Each flag, its
meaning, its units". The closed-form EVSI model takes five numbers; the decision-tree model takes a schema.
Twelve lines is not reachable for a mid-sized model. Either the budget or the `INPUTS` requirement has to
give.

**Fix.** State the rule explicitly: *one script per registry entry; shared mathematics lives in `lib/` and
is imported*. Then have `generate_docs.py` **generate the header block** into each script from the registry
(delimited by sentinel comments) and have CI fail on drift, the same way it does for `INDEX.md`. Add an
argparse↔`usage` consistency check by running `--help` in CI and diffing flag names. Relax the header to
"≤12 lines *or* ≤160 tokens, `INPUTS` may reference `--help` when flags exceed 4".

---

## F10 — MAJOR. The four pilots do not exercise "every output mode", and one is mapped to the wrong mode

**Offending text (§12):**

> 5. **Four pilot models**, chosen to exercise **every tier and every output mode**:
>    - `zero_events_observed_upper_bound` — INLINE, C1 cluster, exercises `NO ANSWER EXISTS` **at n=0**

**Mode coverage, counted.** Named across the four pilots: `NO ANSWER EXISTS`, `BASELINE_WINS`, and
implicitly `OK`. Not exercised by any named pilot: **`CAVEAT`, `ROBUSTNESS`, `REFUSED`**. `ROBUSTNESS` is
the worst omission — it is the P4 mode, the one that must emit a computed **breakdown value**, and none of
the four pilots has a matter-of-degree assumption capable of producing one (VOI: arithmetic; rule of three:
distribution-free; PERT: no data; benchmark regression: exchangeability is structural, not graded). So the
Wave 0 gate — whose stated purpose is *"Contract problems get found on four scripts, not thirty"* — leaves
half the contract untested until Wave 1, including the mode with the most novel output shape.

**Wrong mode.** The registry example for this exact model says `"refuses_when": "trials < 1"`. `n = 0` is
`trials < 1`, which is `REFUSED` (exit 3) by the registry and `NO ANSWER EXISTS` (exit 4) by §12. Two
sections of one spec assign one input two different exit codes. Substantively, §9 defines
`NO ANSWER EXISTS` as *"The question is malformed regardless of data"*; "I have no observations yet" is
neither malformed nor data-independent — it is the ordinary empty-input case, arguably even exit 2. None of
the research's `NO ANSWER EXISTS` exemplars (decreasing-hazard abandonment, reliability-growth
extrapolation) resembles it.

**Fix.** Reassign: `n = 0` → `REFUSED`. Add a fifth pilot that genuinely produces a breakdown value — the
E-value is the obvious candidate (§1.1: "computable from three inputs", INLINE, no data) and it exercises
`ROBUSTNESS` and `naive_answer_is_wrong` together. Take `NO ANSWER EXISTS` from a real exemplar
(`when_to_abandon_a_long_running_process` under decreasing hazard). Add an explicit
`"emits_modes": ["OK","ROBUSTNESS","REFUSED"]` array to the registry so L4 can be generated rather than
guessed, and add a CI check that the union of `emits_modes` across Wave 0 covers all six.

---

## F11 — MAJOR. §5's fallback reinstates the heuristic gate that §5 exists to abolish, and the gate itself violates P7

**Offending text:**

> §5: "**This replaces the heuristic gating doctrine of the previous revision.** ... Those are heuristics
> an overconfident agent can talk itself past in either direction."
> §5: "**Fallback.** When the decision cannot be put in a loss table (no quantified stakes), fall back to
> the qualitative gate: if the decision is cheap to reverse or the answer is already determined, stop."
> §1 success criterion 2: "The module never fires on decisions where no number could change the action —
> and **can now *prove* that case** rather than judge it (§5)."
> §5: "**The skill's first act is always the same**"

Three collisions:

1. **"Always" vs the fallback.** The first act is not always the same; it is the VOI script when stakes are
   quantified and a vibe otherwise. Since most agent judgment calls arrive without a loss table, the
   fallback is the *common* path, not the exception — so the heuristic gate the spec calls talk-past-able is
   still the primary gate in practice, now with a footnote.
2. **P8 and success criterion 2 overclaim.** "Can now prove that case" holds only under the quantified
   branch. As written, the criterion is unfalsifiable in the majority case.
3. **P7 violation at the gate.** P7: *"The module consumes stated numbers; it never generates them."*
   The gate demands `--loss-if-wrong 40`, `--current-belief 0.7`, `--cost-to-measure 2`. Where does an agent
   asked "is this benchmark regression real?" get 40? It invents them — and the module's very first act
   becomes the thing P7 forbids, on inputs the answer is maximally sensitive to (EVPI is linear in `L`).
   Territory 10 anticipated this: *"Refuse if V or c is unknown."* The spec does not carry that refusal
   forward.

**Fix.** Rewrite §5 as a two-branch gate with the branch condition stated first and honestly: *"If the
decision has quantified stakes, the gate is arithmetic (§5a). If it does not, the gate is heuristic (§5b),
and the module's confidence in the stop/go call is correspondingly lower."* Require the gate script to
accept `--stakes-source {stated|estimated}` and to emit `CAVEAT` (never `OK`) when `estimated`, printing a
sensitivity range over `L` rather than a point EVPI. Soften success criterion 2 to "can prove that case
whenever stakes are quantified".

---

## F12 — MAJOR. `NO ANSWER EXISTS` conflates "no answer exists" with "this library cannot compute it"

**Offending text (§9):**

> `NO ANSWER EXISTS` ... **the question is malformed regardless of data** ... Examples from the sweep —
> ... **multi-parameter EVPPI is out of stdlib reach and the tool should say so rather than approximate.**

The first two examples are genuine (decreasing hazard: the optimal policy is degenerate; reliability-growth
extrapolation: formally unsupported). The third is a **capability boundary of this implementation** —
`RESEARCH.md` §1.25 calls it exactly that: *"An honest capability boundary... Multi-parameter EVPPI needs
GAMs or Gaussian processes."* Methods exist; we lack the dependencies.

**Concrete failure.** An agent told "NO ANSWER EXISTS: multi-parameter EVPPI" reasonably concludes no
method exists and stops looking — the module has manufactured a false certainty about the state of the
field. That is the module's own thesis failure (overconfidence from a verification tool), inverted.

**Fix.** Add a seventh mode `OUT_OF_SCOPE` (exit 5 or 8, per F4's renumbering) whose contract is: name the
method that *would* answer this, name why it is unavailable here (stdlib constraint), and give the closest
in-scope alternative (single-parameter EVPPI, run per parameter). Move the EVPPI case there. Keep
`NO ANSWER EXISTS` strictly for the mathematically-degenerate cases.

---

## F13 — MINOR. `tier` is a scalar field for a property that is input-dependent, and one pilot already has two values

**Offending text:** §7 `"tier": "INLINE"` (string) vs §12 `benchmark_regression_from_repeated_runs —
**DATAFILE/MUST-CONSTRUCT**`.

Territory 10 repeatedly makes tier conditional on input size: *"INLINE for ≤4 options with mean/sd;
DATAFILE otherwise"*, *"INLINE for ≤6 options, DATAFILE beyond"*. Beyond that, `MUST-CONSTRUCT-DATA` is not
a property of a model at all — it describes the *agent's current state* (no data yet), and every DATAFILE
model is MUST-CONSTRUCT when the agent has nothing. Encoding it as a model attribute means the same model
has different tiers for different callers, which a scalar cannot express and `route.py` cannot use.

**Fix.** `"tiers": ["INLINE", "DATAFILE"]` (array), plus an optional `"tier_rule"` string
(`"INLINE if options<=4"`). Drop `MUST-CONSTRUCT-DATA` from the registry entirely — it belongs to §5's gate
output (Tier 3 is a *routing verdict*, not a model attribute), which is where §5 already puts it.

---

## F14 — MINOR. The one worked registry entry in the spec is internally inconsistent, and `refuses_when` is under-typed

**Offending text (§7):**

> `"usage": "--trials N [--confidence 0.95]"`
> `"output": "upper bound on the true rate, **and the n needed for a target bound**"`
> `"refuses_when": "trials < 1"`

- The declared output requires a target bound; the declared usage has no flag to supply one. The spec's
  single worked example cannot produce its own declared output. (Add `[--target-bound P]`, or drop the
  clause.)
- `refuses_when` is a single English string. Every territory lists 3–5 distinct refusal conditions per
  model, each mapping to a different mode (`REFUSED` vs `NO ANSWER EXISTS` vs `BASELINE_WINS`) and each
  needing its own remedy text. One string can express none of that, and L4 ("≥1 input per model per
  applicable mode") has no machine-readable source to generate from. This is the same defect as F3's
  free-text `baseline_to_beat`.
- Nothing defines the legal values of `data_provenance_required` (shown as `null`, enum unspecified) or the
  element shape of `composition_hazards` (shown as `[]`; §1.6 requires "model ids ... **and why**", which a
  bare id list cannot carry).

**Fix.** `"refusals": [{"when": "trials < 1", "mode": "REFUSED", "remedy": "..."}]`.
`"data_provenance_required": null | "elicitation-protocol" | "collection-rule" | "assignment-mechanism"` as
a documented enum. Composition hazards as objects (see F8). Add a JSON Schema file for `registry.json` and
a CI validation step — currently CI validates generated-doc drift but never validates the source of truth
itself.

---

## Scope realism — Wave 0 is three units of work, not one

Wave 0 as written contains five activities with disjoint skill sets, disjoint failure modes, and one shared
review gate:

| Activity | Nature | Rough shape |
|---|---|---|
| 1. Record L6 baselines | Eval design + agent runs | Design ≥3 representative judgment tasks, run an agent without the module, capture verbatim failures |
| 2. Dedup pass over 310 models | Research triage + curation | ~310 × ~10 curated fields, most for models that will never be written in Wave 0 or 1 |
| 3. Six `lib/` modules with L1 goldens | Numerics + published-reference sourcing | Two of the six are called by nothing in Wave 0 (F5) |
| 4. `route.py`, `generate_docs.py`, CI | Retrieval engineering | Algorithm entirely unspecified (F7) |
| 5. Four models + L1–L5 ladder | The actual contract proof | The only part that matches the stated purpose |

Only (5) — and the `report.py` slice of (3) — serves the stated purpose, *"prove the contract... Contract
problems get found on four scripts, not thirty."* (2) is the largest and least reversible item, and it is
pure speculation about unwritten models that CI will then freeze. (4) is a research problem masquerading as
a build task.

Additionally, **L6 is recorded in Wave 0 and re-run only in Wave 1** ("L6 re-run against baseline"). So the
Wave 0 review gate never asks whether the module improved anything — it checks that the contract is
self-consistent, which given F1–F4 it is not. The one measurement that would justify continuing is deferred
past the gate that is supposed to decide whether to continue.

**Recommended split:**
- **Wave 0a — contract proof.** `report.py` (with the six JSON blobs from F4 as its acceptance criteria),
  `exact.py`, `dataio.py`, five pilots (four current + one `ROBUSTNESS` model per F10), a 5-entry registry,
  `route.py` against those five, L1–L4 green. Review gate here.
- **Wave 0b — baselines.** L6 scenario design and baseline recording, run against 0a's five models so the
  Wave 0 gate has an actual before/after signal.
- **Wave 0c — index build.** Dedup pass, full registry population, `generate_docs.py`, L5 at scale. Starts
  *after* the contract is proven, so 310 entries are authored against a schema that has survived contact
  with five real models rather than against a hypothesis.

---

## Cross-cutting note

The pattern under F1, F2, F3, F5, F6, F7, and F8 is the same: **a principle from `RESEARCH.md` was promoted
to a library-wide contract without checking that the mechanism generalises.** P9 generalised MASE (F3); P8
generalised territory 10's EVSI threshold-reachability result into an EVPI gate whose arithmetic does not
support it (F1, F2); P5's composition hazards were promoted to a registry field with no enforcement point
(F8). `RESEARCH.md` §2.5 warns about precisely this — convergent findings are hypotheses, not
confirmations — and §1.27 is the worked example of a four-territory convergence that was still wrong in the
detail nobody checked. The generalisation step deserves the same scepticism the research applies to itself:
for each of P1–P10, name the family where it does *not* apply, and encode that exception in the schema.
