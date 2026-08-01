# Review 03 — Agent usability: will this change behavior, or is it shelfware?

**Reviewing:** `docs/superpowers/specs/2026-07-31-statistical-judgment-module-design.md` (rev. cf1ecf9)
**Against:** `RESEARCH.md` §0.3, §0.4, §1.21, §1.33, §2.1, and Anthropic's
[Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
**Lens:** an agent that is capable but busy, under token pressure, and biased toward finishing.

**Verdict in one line:** the library design is excellent and the skill design has been deleted. The
mandated first act — a value-of-information gate requiring a loss table — cannot be honestly
populated in most ordinary situations, is not structurally enforced, and when it *is* populated it
will be populated with numbers the agent invented, which violates the module's own P7 and
manufactures exactly the false authority the project exists to prevent.

---

## Finding 0 (structural, discovered while reviewing) — the revision deleted the agent-facing spec

Before the ranked findings, a fact that changes how everything else should be read.

The previous revision (`da58e65`) had a `## 5. The skill` section containing the YAML frontmatter,
the SKILL.md body structure, and the gating doctrine; and a `## 7. route.py — discovery` section
specifying the router's output format, the no-match floor, and the `--family` / `--id` flags. The
revision (`cf1ecf9`) replaced §5 with `## 5. The gate` and dropped §7 entirely.

Net effect on the current spec:

| Artifact | Previously specified | Now |
|---|---|---|
| Skill `name` | `statistical-judgment` | absent |
| `description` frontmatter | full text, 12 trigger phrases | absent |
| SKILL.md body structure | 6 numbered sections, ~200 lines | absent (only "<500 lines. The gate + navigation") |
| `route.py` output contract | title / meaning / tier / usage, ≤3 matches | absent (one line in a directory tree) |
| No-confident-match behavior | specified, floor calibrated against L5 | absent |
| Guidance-form principle | "conditional on observable predicates, not a prohibition" | **deleted** |

The current spec specifies `lib/special.py` down to the two functions it contains, and specifies the
skill — the only part of this system an agent actually interacts with — not at all. Wave 0 item 4
says "`registry.json`, `route.py`, `generate_docs.py`, CI drift check" with no contract for any of
them. This is not a nitpick: **a build to the current spec produces a library nobody triggers.**

The deleted guidance-form note is the most costly loss, because the new gate is the exact shape it
warned against. "The skill's first act is always the same" is a compliance ritual. The thing it
replaced was a conditional keyed on observable predicates.

**Fix:** restore §5 (frontmatter + body structure) and §7 (router contract) verbatim from `da58e65`
as the baseline, then apply the amendments below. Restore the guidance-form paragraph as a
project-wide principle (it deserves to be P11).

---

## Finding 1 — The gate is a wall, not a door

**Ranked #1. This is the spec's headline claim and it does not survive contact with ordinary work.**

The mandated first act is:

```
python3 models/decision/value_of_information_reachability.py \
    --options "ship,hold" --loss-if-wrong 40 --current-belief 0.7 --cost-to-measure 2
```

Four inputs required: a discrete option set, a scalar loss, a subjective probability, and a cost in
loss-commensurate units. Walking six ordinary situations:

### 1. A flaky test — "this test failed 3 of 40 CI runs"

Options: quarantine / investigate / ignore — fine, discrete. `--loss-if-wrong`: the cost of a missed
real bug is unbounded and unknown to the agent; the cost of quarantining a genuinely-broken test is
also unknown. `--cost-to-measure`: 100 reruns ≈ 20 minutes of CI. **Units do not commensurate** —
loss is in "escaped defects", cost is in "CI minutes". `--current-belief`: the agent would have to
invent P(test is genuinely broken), which is the question it came here to answer.
**Verdict: cannot populate. 1 of 4 inputs available.**

### 2. A benchmark that looks slower — "p50 went 120ms → 130ms"

Options: ship / investigate. `--loss-if-wrong` requires an SLO or a stated user impact the agent
usually does not have. `--cost-to-measure`: 30 reruns ≈ 5 minutes — genuinely available. Note that
`RESEARCH.md` §1.33 says the right input here is a **declared minimum-interesting effect**, not a
loss table: "Requiring the agent to state what size of regression would matter *before* computing is
itself the guard against p-value theatre." The research already identified the elicitable quantity,
and the gate asks for a different, harder one.
**Verdict: partly populable, and the gate asks for the wrong input.**

### 3. Conflicting docs — "doc A says 30s timeout, doc B says 60s"

Not a statistical question at all; it is a provenance/recency question. There is no loss table
because there is no sampling to be done. Running the gate here is pure ceremony that costs a bash
round-trip to conclude what was obvious.
**Verdict: cannot populate, and the gate does not even protect against this false positive — by the
time you run the gate you have already paid for SKILL.md.**

### 4. An estimate for a user — "how long will this migration take?"

`--options` presumes a finite action set; an estimate is continuous and frequently attached to *no
decision at all* (the user just asked). A single scalar `--loss-if-wrong` cannot express asymmetric
loss — and §1.36 notes the closely-related timeout question is a **newsvendor problem**, i.e.
explicitly asymmetric. The gate's data model cannot represent it.
**Verdict: cannot populate.** Worth flagging that `three_point_estimate_to_range` is one of the four
Wave 0 pilot models, so **a pilot model is unreachable through the mandated gate.** That will surface
in Wave 0 as a contract contradiction; better to fix it now.

### 5. An anomalous metric — "error rate spiked 4× for ten minutes"

Options: page / wait. Loss requires the cost of a page vs. the cost of a missed incident — org
knowledge the agent rarely has. §1.32's framing for this family is **false-alarm rates (ARL₀)**, not
loss tables. And this case is time-critical: inserting a mandatory round trip ahead of the
anomaly model is actively harmful.
**Verdict: cannot populate, and the gate is the wrong shape for the family.**

### 6. Choosing between two libraries

The one case where `--options` fits naturally. But `--loss-if-wrong` = the cost of migrating later,
genuinely unknowable ex ante; `--current-belief` = a subjective probability the agent must invent;
`--cost-to-measure` = building two spikes, days of work. All three fabricated. EVPI will almost
certainly say "measure", so the gate does no work even after the fabrication.
**Verdict: agent fabricates all three inputs; gate returns a non-answer.**

### Tally and the deeper problem

Zero of six cleanly populable. One partly (and it wants a minimum-interesting effect, not a loss
table). Five require the agent to invent numbers.

That last point is the serious one. **P7 says the module consumes stated numbers and never generates
them, because LLM-elicited priors measure at effective sample size zero (§1.17). The gate demands
exactly the class of number P7 forbids, and it demands it first, before any other guard is active.**
The gate is the single largest P7 violation surface in the design, and it is mandatory.

EVPI is monotone in `--loss-if-wrong` and `--cost-to-measure`. If those are invented, the verdict is
determined entirely by invented inputs — but it returns wearing the authority of a computed result.
The spec then celebrates precisely this: *"The agent now has a **number** justifying stopping."* A
number justifying stopping, derived from fabricated inputs, is worse than the heuristic it replaced,
because the heuristic at least looked like a judgment and invited scrutiny. §0.2's own thesis —
evidence tools induce overconfidence because the agent mistakes availability for correctness — turns
around and lands on the gate.

### The fallback swallows the gate

> **Fallback.** When the decision cannot be put in a loss table (no quantified stakes), fall back to
> the qualitative gate: if the decision is cheap to reverse or the answer is already determined, stop.

One sentence, free, and by the analysis above it applies in roughly five of six cases. An agent under
token pressure takes it every time. So in the common case the "computable gate" *is* the old
heuristic gate — except the old one was a four-tier table with a stated guidance form, and the new
one is a single sentence. **Net effect of the revision: the gate got weaker in the common case and
falsely authoritative in the rare case.** The risk register's "Skill over-triggers — **Downgraded.**
Now computable" is not supported.

### Fixes

1. **Demote the loss-table EVPI from "always the first act" to one of three gate forms**, selected by
   what the agent actually holds. The gate script dispatches:
   - **Form A — minimum interesting effect (default).** "What is the smallest difference that would
     change what you do?" One question, answerable in 5 of the 6 scenarios above, already the
     recommended input for the benchmark family (§1.33), and a real guard against p-value theatre.
   - **Form B — loss table (EVPI/EVSI).** Only when stakes are genuinely quantified and stated.
   - **Form C — unquantified.** Emits `UNQUANTIFIED` plus the two observable predicates (is the answer
     already determined? is the decision cheap to reverse?) as an explicit checklist the agent
     answers in its response, not silently.
   All three forms are cheap; all three emit the same downstream token (see Finding 3).
2. **Enforce P7 at the gate.** Require provenance on every loss input: `--loss-source "user stated:
   2 engineer-days"`. If provenance parses as agent-estimated, the script emits `NO ANSWER EXISTS`
   and directs the agent to Form A or C. This makes P7 mechanically enforceable at the one place it
   is currently violated by design.
3. **Support asymmetric loss** (`--loss-if-false-positive` / `--loss-if-false-negative`) or explicitly
   refuse continuous-estimate questions with a pointer to the newsvendor model, per §1.36.
4. **Do not print a stopping number when the inputs were not user-supplied.** Print the verdict
   without the arithmetic. A verdict cannot be laundered; a number can.

---

## Finding 2 — Nothing enforces the gate, so it will be skipped silently

**Ranked #2.**

**The problem.** "The skill's first act is always the same" is prose. No script checks it. No exit
code depends on it. `route.py` works without it; every model works without it.

**The concrete failure.** Agent triggers, reads SKILL.md, runs `route.py "is this 8% slowdown real"`,
gets three matches with usage lines, runs the model, reports the number. Total elapsed: three tool
calls, correct-looking output, zero errors, no gate. This is not a lapse — it is the *efficient*
path, and it works. On day one the gate is optional in practice.

Four compounding reasons the agent skips it:

1. The four flags are unavailable (Finding 1).
2. The fallback sentence is free and adjacent.
3. **The agent arrived at the skill because it already decided statistics was warranted.** The gate
   asks it to relitigate a decision it made one turn ago. That is motivationally backwards; agents
   do not spontaneously re-open settled questions under time pressure.
4. Per the literature note in the prompt and the deleted guidance-form paragraph: compliance-shaped
   instructions ("always do X first") get negotiated away under competing incentives. Structural
   constraints do not.

**Fixes, strongest first.**

- **Fold the gate into `route.py`.** The router is the one step the agent *must* run, because it is
  the only way to learn a model's flags without reading a file. Make `route.py "<predicament>"` run
  the reachability logic and either return matches or return
  `STOP: no measurement changes this decision`. One invocation instead of two, and compliance becomes
  the path of least resistance rather than an extra tax on it. **This is the single highest-leverage
  change in this review.**
- **Make the gate's output a required model input** (plan-validate-execute, which §0.4 already flags
  as recommended). The gate emits an opaque `--decision-context` token encoding its verdict; every
  model refuses with exit 3 without one. Critically, the gate must have a **zero-input mode that
  still emits a token** (verdict `UNQUANTIFIED`) — otherwise agents route around the requirement, and
  a guard that is expensive to satisfy honestly gets satisfied dishonestly.
- **Add an eval for it.** L6 must include a scenario scored specifically on "was the gate run before
  the model", not just on the final answer. Behavior you do not measure, you do not get.

---

## Finding 3 — The token-budget claim is not honest

**Ranked #3.**

**The claim.** "Near-zero discovery cost via `route.py`"; the gate "answers the cost objection
honestly: the module's opening move is a cheap check on whether it should run at all" (§5, §1.21).

**Traced end-to-end** — benchmark regression, the most favorable realistic case:

| Step | Tokens (favorable) | Tokens (realistic) |
|---|---|---|
| Description in system prompt (charged every session, used or not) | 180 | 180 |
| Read SKILL.md (spec cap 500 lines; prev. rev. targeted ~200) | 3,000 | 4,000 |
| Construct the loss table — reasoning, often a user round trip | 300 | 1,200 |
| Run gate + read output | 150 | 200 |
| `route.py` query + ≤3 matches | 400 | 400 |
| Open one `docs/families/*.md` when matches are ambiguous (p≈0.4) | 0 | 800 |
| Run model + read output (ROBUSTNESS breakdown, caveats) | 200 | 250 |
| Interpret and write the answer | 400 | 500 |
| One retry — REFUSED / BASELINE_WINS / novel mode needing interpretation | 0 | 500 |
| **Total** | **≈4,600** | **≈8,000** |

Tier 3 (MUST-CONSTRUCT-DATA) is unbounded on top of this: 30 benchmark reruns means 30 tool
invocations with their output.

**Compare the precedent.** `bayesian-workflow` measured **+87% tokens** (§0.3). Against a ~10k-token
baseline judgment task that is ≈ +8,700 tokens. **Our realistic path is ≈8,000. Same order of
magnitude as the precedent — not "near-zero."**

**The structural flaw, which matters more than the arithmetic.** The single largest line item is
SKILL.md, and it is charged **before** the gate runs. The gate cannot save the tokens that the
instruction telling it to run the gate already spent. Framing the gate as the answer to the cost
objection is therefore circular: the gate is the second-most-expensive thing you do, after reading
the document that told you to do it.

**Fixes.**

1. **Hard-cap SKILL.md at ~120 lines, not 500.** 500 is Anthropic's ceiling, not a target. Put the
   gate and the `route.py` invocation in the first 40 lines. Everything else — family map details,
   output-mode table, red flags, the verification rationale — goes to linked files.
2. **Make the gate reachable without SKILL.md.** Put the strongest gate predicate into the
   `description` itself, so the cheap check happens at trigger time where it can actually prevent
   the load.
3. **Restate the claim honestly in the spec:** "Per-invocation cost is comparable to the measured
   `bayesian-workflow` precedent. The gate reduces the *frequency* of full invocation, not the cost
   of one." That is still a good argument. It is just a different one.
4. **State the always-on cost.** ~180 description tokens × every session in which the skill is
   installed and unused. The design never names this number and it is the only cost paid
   unconditionally.

---

## Finding 4 — `BASELINE_WINS` prints a number at exit 0 and will be reported as the result

**Ranked #4. The refusal doctrine's own logic, applied inconsistently to the one mode that needed it
most.**

**The problem.** §0.3's central evidence is that agents read the number off a tool and report it even
when the tool said the number is untrustworthy — which is why REFUSED suppresses the number
entirely. `BASELINE_WINS` exits **0** and **prints a number**. It is therefore the mode *most*
exposed to the failure the doctrine was written to prevent, because unlike REFUSED it does not
withhold the thing the agent is skimming for.

**The concrete failure.** Model runs, prints `BASELINE_WINS` and `value: 118.0` (the naive forecast).
Agent, three tool calls deep and wanting to finish, reports "the model estimates 118.0". The user now
believes a statistical model produced a result when in fact the model lost to last-observed-value.
That is *worse* than not running the module at all: the naive answer has acquired false provenance.

Exit 0 is also wrong for machine consumers — it makes "the model won" and "the model lost"
indistinguishable to any script.

**Fixes.**

- Exit **5**, not 0.
- Never print a bare labelled number. Print:
  ```
  BASELINE_WINS
    baseline: last observed value
    baseline_value: 118.0
    model_value: SUPPRESSED — did not beat the declared baseline
  REPORT AS: "The naive baseline (last observed value, 118.0). The statistical model did not
              improve on it, so there is no modelled estimate to report."
  ```
- On `--json`, the payload must contain **no field named like a result** — no `estimate`, no `value`,
  no echoed inputs that could be mistaken for output.
- **Add a `REPORT AS:` line to every mode, including refusals.** This is the highest-leverage single
  addition to the output contract in this review: it converts "interpret this correctly", which
  agents do variably, into "copy this sentence", which they do reliably. It is a positive recipe,
  which per the skill-writing literature is the form that survives competing incentives — unlike the
  prohibition-shaped guidance the spec currently relies on.

---

## Finding 5 — Six output modes is two too many; the split is on the wrong axis

**Ranked #5.**

**The problem.** Six modes over three exit codes, four of them sharing exit 0. But at the moment of
reading, the agent's decision is binary: *is there a number I may report, and what must I say
alongside it?* Six modes over-serve a two-way decision.

Specifically:

- `OK`, `CAVEAT`, and `ROBUSTNESS` all print a number and all print extra text. `CAVEAT` ("strained
  but informative") vs. `ROBUSTNESS` ("assumption is a matter of degree; here is the breakdown
  value") is a distinction about *why the qualifier exists*, not about *what the agent should do*.
  Both collapse to "report the number with its qualifier." Nothing downstream depends on telling them
  apart, and an agent will not reliably do so.
- The scheme is mutually exclusive, so **a model cannot emit both a caveat and a breakdown value** —
  a real expressiveness loss, since those are orthogonal.
- `BASELINE_WINS` sits with the number-printing modes by exit code but belongs with the refusals
  semantically (Finding 4).
- `REFUSED` (3) vs. `NO ANSWER EXISTS` (4) **is worth keeping** — the remedies differ absolutely
  ("get different data" vs. "ask a different question"). Good separation.

**Fix — collapse to four modes, and move the two lost ones to fields:**

| Mode | Exit | Number? | Optional fields |
|---|---|---|---|
| `OK` | 0 | yes | `CAVEAT:` line, `BREAKDOWN:` value — independently, both, or neither |
| `BASELINE_WINS` | 5 | baseline's only, model's suppressed | `REPORT AS:` |
| `REFUSED` | 3 | no | violation + remedy (different data) |
| `NO ANSWER EXISTS` | 4 | no | why + the decidable question to ask instead |

This loses nothing and gains the ability to report a breakdown value alongside a caveat. P4 ("report
breakdown values, not pass/fail") is preserved — it was always about the *content* of the field, not
about deserving its own mode.

---

## Finding 6 — Trigger vs. false-positive tension is relocated, not resolved

**Ranked #6.**

The only `description` ever written (previous revision §5) is good on Anthropic's criteria:
third person, ~700 chars (under 1,024), states what and when, enumerates all 12 family questions, and
— best part — includes linguistic triggers: *"when reaching for 'probably', 'roughly', 'seems like',
'should be fine', or 'that's within noise'"*. That is the highest-value clause in it, because those
are surface-observable in the agent's own draft output. Keep it. It correctly follows §0.4's note
that Claude *under*-triggers and descriptions should be pushy.

Four problems:

1. **It no longer exists in the spec** (Finding 0). Whoever builds Wave 0 will rewrite it ad hoc and
   the linguistic-trigger clause — the part hardest to reinvent — is the most likely casualty.
2. **The tension is asserted, not resolved.** The description fires broadly and correctly; the design
   then relies on the gate for false-positive control; the gate mostly cannot run (Finding 1) and is
   not enforced (Finding 2). So false-positive control rests on a component that will not execute.
   The risk-register downgrade of "Skill over-triggers" is unearned.
3. **"on a decision that is expensive to reverse" is a gate condition smuggled into the trigger.**
   Two harms: (a) it suppresses triggering on cheap-to-reverse questions where the arithmetic floors
   (§9) are exactly the right answer — "you cannot reach p<0.05 at n=3" is valuable regardless of
   reversibility; (b) reversibility is *not observable at trigger time* — the model deciding whether
   to load has strictly less context than the model that would run the gate. Trigger predicates must
   be readable off the surface of the request. Move this clause out of the description and into the
   gate section of SKILL.md.
4. **No eval tests triggering.** L1–L6 covers numerics, models, properties, refusals, routing, and
   behavior. L5 tests `route.py` — which only runs *after* the skill has loaded. **Nothing tests
   whether the skill loads.** That is the one failure that makes every other level moot.

**Fix:** restore the description minus the reversibility clause; add **L0 — trigger evals**: N
transcripts where the skill should load and N adversarial ones where it should not, scored with only
the frontmatter in the system prompt. Run it against Haiku, Sonnet, and Opus per §0.4 — trigger
sensitivity is the property most likely to vary by model.

---

## Finding 7 — `REFUSED` invites flag-shopping and model-shopping

**Ranked #7.**

**The problem.** REFUSED prints "a concrete remedy". A busy agent reads a remedy as a *parameter
suggestion*. Worse, the arithmetic floors (§9) are specified per-model, so the agent has an easy
escape: the router returned three matches, and only one of them checks the floor.

**Concrete failures:**
- Refused for n=3 below the two-sided p<0.05 floor → agent switches to one-sided, or drops to 90%
  confidence, or re-runs with `--confidence 0.8`. Produces a number. No error.
- Same refusal → agent picks match #2 from the router's list, which is a different model in the same
  family without that floor. Produces a number. No error.

**Fixes:**

1. **Floors live in `lib/`, not in models.** Every model in an affected family calls the same floor
   check, so switching models does not switch off the floor. This is a structural constraint, which
   is the kind that holds.
2. **State the invariant, not just the remedy.** "No two-sided test at n₁=n₂=3 can reach p<0.05; the
   minimum attainable p is 0.10. Changing the model or the test will not change this." Kill the
   search before it starts, by making its futility explicit.
3. **Registry field `refusal_is_universal: true`**, and have `route.py` print it on *every* match in
   the family when a floor is implicated — so the agent sees the wall before it starts walking into
   it three times.
4. **Session-local invocation log.** Models detect "a near-identical invocation was refused 90
   seconds ago" and say so. A script can enforce what prose cannot.
5. On `--json` refusal, emit **no numeric fields at all**, not even echoed inputs.

---

## Finding 8 — Progressive disclosure: one real nesting hazard, one dead layer, one loose cap

**Ranked #8.** Mostly compliant; three specific problems.

**(a) `INDEX.md` is a two-level path waiting to happen.** The spec asserts "All reference files link
**directly** from SKILL.md" while shipping a generated global index whose only function is to be an
intermediate. If SKILL.md links INDEX.md and INDEX.md links the families, that is exactly the
`SKILL → advanced → details` pattern Anthropic warns produces `head -100` partial reads.
**Fix:** delete `INDEX.md`, or declare it human-only, state in the spec that SKILL.md must not link
it, and add a CI assertion.

**(b) The family docs are probably dead weight.** If `route.py` works, the agent never opens
`docs/families/*.md`. Anthropic: "If Claude never accesses a bundled file, it might be unnecessary or
poorly signaled." Twelve generated files + `generate_docs.py` + a CI drift check is real maintenance
for a low-probability path.
**Fix:** keep them — grep-over-reference-files is an officially recommended fallback — but make them
*directed* rather than *hoped for*: `route.py` prints the relevant family doc path in its output, and
prints it prominently when confidence is low. That converts the layer from decoration into the
router's own escape hatch.

**(c) 500 lines is a ceiling being used as a target.** The previous revision's ~200 was better; ~120
is better still (Finding 3). At 400+ lines the "run the gate first" instruction is competing with
~4,000 tokens of other instruction for recall, and it is the one instruction that must survive.

**(d) Missing recipe: what to do on `NO CONFIDENT MATCH`.** Specified in the deleted §7 for the
router; never specified for the agent. Without it the failure mode is: router finds nothing, agent
shrugs, answers from intuition — precisely the behavior the module exists to replace. Add a positive
recipe to SKILL.md: consult the family map; if still nothing, say so explicitly in the response —
*"No model in the library addresses this. Here is my unquantified judgment, flagged as unquantified."*
An honest flag is a real deliverable and the agent should be told it counts as success.

**(e) Two sources of usage truth.** The `# WHAT/WHEN/INPUTS/...` header and `--help` duplicate each
other and will drift. Generate one from the other and add a CI check. Keeping the header for grep is
right; the previous revision's note that "normal operation reads zero script bodies" should be
restored, since it is what makes the token argument work.

---

## Finding 9 — Prohibition-shaped guidance is creeping back in

**Ranked #9, but cheap to fix and it prevents regressions in all of the above.**

The revision deleted the paragraph explaining *why* the gate was written as a conditional rather than
a prohibition. Meanwhile the spec now contains: "Never route on an assumption test", "No script ever
emits", "must not be chained", "Does not generate estimates", "no unverified constant may enter".

These are all correct **as implementation constraints enforced in code and tests**. They become
liabilities the moment any of them is copied into SKILL.md as agent-facing guidance, because
prohibition-shaped guidance invites negotiation under competing incentives — which is the entire
premise of this review.

**Fix — add as an explicit spec rule (and promote to P11):**

> Every constraint governing *agent* behavior is enforced by a script's exit code or expressed as a
> positive recipe with a copyable sentence. SKILL.md contains no prohibitions. Prohibitions live in
> `lib/`, in exit codes, and in the test suite.

Applied consistently, this rule generates the fixes in Findings 2 (gate folded into the router), 4
(`REPORT AS:` on every mode), and 7 (floors in `lib/`) on its own.

---

## Ranked summary

| # | Finding | Degradation |
|---|---|---|
| 0 | Revision deleted frontmatter, SKILL.md structure, router contract, guidance-form principle | Cannot build to spec |
| 1 | Gate unpopulable in ~5 of 6 ordinary situations; populating it violates P7 and fabricates authority | Severe |
| 2 | Nothing enforces the gate; skipping it is the efficient path and produces no error | Severe |
| 3 | Token claim dishonest; realistic cost ≈8,000 tokens, same order as the +87% precedent; SKILL.md charged before the gate | High |
| 4 | `BASELINE_WINS` prints a number at exit 0 and will be reported as the model's result | High |
| 5 | Six modes; `CAVEAT`/`ROBUSTNESS` indistinguishable in action and mutually exclusive when they should compose | Medium |
| 6 | Trigger/false-positive tension relocated onto a gate that will not run; no eval tests triggering at all | Medium |
| 7 | `REFUSED` invites flag- and model-shopping; floors are per-model rather than in `lib/` | Medium |
| 8 | `INDEX.md` nesting hazard; family docs likely unread; 500-line cap too generous; no no-match recipe | Low–Medium |
| 9 | Prohibition-shaped guidance creeping back after its counter-principle was deleted | Low, cheap |

## The three changes that matter most

1. **Fold the gate into `route.py`.** Compliance becomes the path of least resistance instead of a
   tax on it. Fixes Finding 2 outright and most of Finding 1's ceremony cost.
2. **Make the default gate form the minimum-interesting-effect question, not the loss table.** It is
   answerable in five of the six scenarios, it is what §1.33 already recommends, and it does not
   require the agent to invent numbers P7 forbids it from inventing.
3. **Put a `REPORT AS:` sentence in every output mode.** Converts interpretation into transcription.
   It is the cheapest change in this document and probably the one with the largest measured effect
   on whether the module changes what the agent actually says.
