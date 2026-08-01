# L6 — Wave 0 measured against the recorded baselines

Run 2026-07-31, after the four Wave 0 pilots. Rubrics in `evals/scenarios.md` were written before
any baseline was recorded and were not modified for this comparison.

## Result

| Scenario | Baseline | With module | Criterion that flipped |
|---|---|---|---|
| S1 benchmark regression | 3/4 | **4/4** | asked what size regression matters, and how many runs would settle it |
| S5 duration estimate (4/9/18) | 3/4 | **4/4** | used the correct PERT variance |
| S8 embedded perf claim | 3/4 | **4/4** | recognised p<0.05 is unreachable at n=3 |
| **Total** | **9/12** | **12/12** | |

Three for three, and in each case **the criterion that flipped is the one the model was built to
address.** That is the result the selection principle predicts, so it is confirmation of the design
rule rather than a surprise.

The effect size is one criterion per scenario. Real, but modest — this is not a transformation of
agent judgment, and the write-up below is deliberately careful not to describe it as one.

---

## S5 — the formula correction, working

| | Baseline | With module |
|---|---|---|
| PERT sd | **2.3** — the textbook `(b−a)/6` | **2.6** — correct `(μ−a)(b−μ)/7` |
| 80% date | ~15 weeks (padded by judgment) | 12.0 weeks (computed) |

Second baseline in a row to reproduce the textbook error, which is the strongest available evidence
that it is reproduced from training data rather than mistyped. The module arm named the trap
unprompted:

> "Do not use the (b−a)/6 shortcut... it is 10% too narrow. If someone on your team produced a
> tighter range from the same three numbers, that formula is why."

It also declined to inflate the estimate for unmodelled risk — *"I'd be making that multiplier up,
and a fabricated adjustment is worse than your judgment"* — which is principle P7 appearing in the
agent's reasoning rather than in the documentation.

**A gap both arms found and the module does not cover:** whether the 40 services are independent
estimates or one estimate multiplied by 40 (common-mode uncertainty), and whether parallel
workstreams make the finish a maximum rather than a sum. The registry records the second as a
composition hazard; neither is modelled. Wave 1 candidate.

## S1 — the module changed the order of reasoning

Score moved 3/4 → 4/4, but the score understates what happened. Four behaviours appeared that the
baseline had no way to produce:

1. **Checked the design floor first.** *"I checked the design floor first, since with samples this
   small the conclusion is sometimes unreachable regardless of the data. It isn't here."*
2. Ran an **exact permutation test** over all 252 splits (p = 0.024) and preferred it to Welch at n=5.
3. **Handled `USE_SIMPLER` correctly in the wild** — *"the module declined to beat the standard rule
   ... so use that — 30 runs per arm"* — attributing the 30 to the default rather than reporting it
   as the model's output. This was review 01's most serious objection to the previous design, and
   the exit-5 fix holds under real use.
4. **Surfaced the registry's composition hazard verbatim**: *"don't fold these 10 runs into the new
   comparison. Reusing pilot data in the test it sized makes the test optimistic."*

It also raised implicit multiplicity unprompted, which comes from SKILL.md rather than any model.

**Marginal call, recorded rather than hidden:** criterion 4 asks for the minimum-interesting-effect
question *before* judging. Both arms judged first. The module arm was scored ✅ because it
operationalised the pre-commitment (*"apply a decision rule you set now, before you see the
result"*), which is the substance of the criterion. A stricter reading gives 3/4 and leaves S1
unchanged from baseline. **The headline would then be 11/12, not 12/12.**

## S8 — the embedded question, and a hypothesis half-refuted

The premise behind S8 was that agents ignore statistics buried inside other work. **That is wrong as
stated.** The baseline noticed unprompted: *"3 runs on a staging box, no variance or confidence
interval."*

What it did not do was treat that as decisive. It filed the observation as a soft caveat — *"Not
fatal on its own"* — and never asked what would settle it. The module arm reached the opposite
verdict on the same evidence, quoting the tool directly:

> "With this design no result can reach p<0.05 — the smallest p it can produce is 0.1... to get
> there, collect at least 4 per group."

and then drawing the conclusion the baseline missed:

> **"Three runs is below the floor at which the comparison can distinguish a real 18% from noise, so
> the repetition adds confidence without adding evidence."**

That sentence is the clearest statement of what this module is for that has come out of the project.

It also **refused to size the follow-up** rather than inventing an input: *"that needs the six raw
timings or an sd, and I won't invent one."* P7 again, in behaviour.

**Confound, stated plainly:** the with-module arm had shell and file access (it needs them to run
the scripts); the baseline was explicitly denied both. The module arm consequently *executed* the PR
code and reproduced the bugs empirically, measuring a 72× read-path slowdown. **That depth
difference is attributable to tool access, not to this module.** The three statistical criteria are
not affected — none of them requires running anything but the module — but the code-review quality
comparison is not clean and should not be cited as evidence for the module.

---

## What this does and does not establish

**Establishes:** each pilot moved the specific criterion it was built for, on a rubric written before
the baselines existed. The selection principle predicted which criterion would move, and it did, in
all three cases. Two mechanisms flagged as risks by review 01 — `USE_SIMPLER` misattribution and
composition hazards being stranded in registry fields nobody reads — both worked under real use.

**Does not establish:**

1. **n = 1 per arm per scenario.** These are single samples, not distributions. Nothing here supports
   a percentage claim, and none is made.
2. **Same base model in both arms**, so the baseline is not an independent yardstick (`RESEARCH.md`
   §1.16).
3. **Coverage is 3 of 7 scenarios.** S2, S3, S4, S6 and S7 have no models yet, and three of those
   were the baselines' strongest performances — S3, S4 and S7 all scored full marks unaided. There
   is no evidence the module would help there, and some evidence it would not.
4. **I wrote both the rubrics and the module.** The rubrics predate the baselines, which controls the
   worst version of this, but not all of it.
5. **Token cost is unmeasured here.** The module arms used 8–9 tool calls each. Against the ~4,600–8,000
   estimate in review 03, this is a real cost for a one-criterion gain.

## Implication for Wave 1

The measured delta supports **building the remaining entry points, at the reduced scope, and no
more**. It does not support returning to 30+ models:

- The gain is one criterion per scenario, concentrated in exactly the cases the selection principle
  identified. Models outside that principle have no measured support at all.
- Three of the four scenarios with no module coverage were **baseline full marks**. Building models
  for those would be building where the evidence says there is no gap.
- The strongest single result — S8 — came from `minimum_attainable_p_for_design`, the cheapest model
  in the catalogue and the one that does no statistics at all. That is worth weighting when ordering
  Wave 1: **the facts an agent cannot know outperformed the computations.**
