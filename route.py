#!/usr/bin/env python3
"""Find the right model for a predicament, and ask the gate question on the way past.

    python3 route.py "is this 8% slowdown real or did I get unlucky"

Discovery costs zero tokens until called: the registry is read from disk, scored, and only the
matches are printed. The agent never loads the catalogue into context.

The gate lives HERE rather than in a separate mandatory step. Three reviews rejected the standalone
value-of-information gate: it was unpopulable in five of six real scenarios, demanded exactly the
numbers principle P7 forbids the module to invent, nothing enforced it, and it relitigated a
decision the agent had made one turn earlier. Folding the question into the router makes complying
the cheapest path rather than an extra one, and the question asked is the minimum-interesting-effect
question, which agents can actually answer.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry.json"

# Words carrying no discriminating signal in this domain. Kept deliberately short: an aggressive
# stoplist removes the very phrasings that distinguish situations ("how many", "how long").
_STOPWORDS = frozenset("""
a an the is are was were be been being do does did doing have has had i me my we our you your it
its this that these those of to in on at for with from by as and or if then than so but not no
can could should would will shall may might must am get got make made use used
explain explains explaining describe tell show work works working thing things way ways
""".split())
# The generic-verb block on the second line is load-bearing. Without it, "explain how tcp
# handshakes work" matched "explain away" in the E-value entry on the strength of one common verb
# and outscored four genuine queries - the routing eval caught it before it shipped.

# BM25 term-frequency saturation. 1.2 is the standard default; with short documents the exact value
# barely moves the ranking, and the calibration test below re-derives the floor for whatever it is.
_BM25_K1 = 1.2
# BM25 length normalisation. 0.75 is the standard default.
_BM25_B = 0.75

# Minimum score to report a match at all. CALIBRATED, not chosen: it is the midpoint between the
# best score any should-match-nothing query achieves and the worst score any should-match query
# achieves, over tests/routing/queries.json. tests/routing/test_route.py recomputes this and fails
# if the constant drifts from the calibration.
#
# The margin is shrinking as the registry grows - +1.23 at 4 models, +0.63 at 7 - because shared
# vocabulary raises the score of near-miss queries. A test guards the margin at 0.2. If it keeps
# closing at this rate, BM25 over a flat registry will stop separating the populations somewhere
# around 15-20 models, and routing will need per-family scoring or a two-stage match rather than a
# lower floor.
NO_MATCH_FLOOR = 3.36

MAX_MATCHES = 3


def _stem(word: str) -> str:
    """Crude suffix stripping, enough to make plurals and tenses match.

    Not a real stemmer, and deliberately so: this only needs "confounders" to reach "confounder"
    and "runs" to reach "run". The routing eval caught the missing case - a query saying
    "confounders" scored 1.2 and missed its model entirely because nothing matched the singular.
    """
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> List[str]:
    raw = [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in _STOPWORDS]
    return [_stem(t) for t in raw]


def load_registry(path: Path = REGISTRY) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        print(f"registry not found at {path}", file=sys.stderr)
        raise SystemExit(1)
    except json.JSONDecodeError as e:
        print(f"registry at {path} is not valid JSON: {e}", file=sys.stderr)
        raise SystemExit(1)


def _document(model: dict) -> List[str]:
    """The searchable text for a model: situations first, since those are how agents phrase it."""
    parts = [model["title"], " ".join(model["situations"]), " ".join(model["keywords"])]
    return tokenize(" ".join(parts))


def score_all(query: str, registry: dict) -> List[Tuple[float, dict]]:
    """BM25 over the registry. Returns (score, model) sorted best first."""
    docs: Dict[str, List[str]] = {m["id"]: _document(m) for m in registry["models"]}
    n = len(docs)
    if n == 0:
        return []
    avgdl = sum(len(d) for d in docs.values()) / n
    q_terms = tokenize(query)

    df: Dict[str, int] = {}
    for terms in docs.values():
        for t in set(q_terms):
            if t in terms:
                df[t] = df.get(t, 0) + 1

    scored = []
    for model in registry["models"]:
        terms = docs[model["id"]]
        dl = len(terms) or 1
        s = 0.0
        for t in q_terms:
            f = terms.count(t)
            if f == 0:
                continue
            # The +1 keeps IDF strictly positive even when a term appears in most documents;
            # with a small registry the classic form can go negative and invert the ranking.
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * (f * (_BM25_K1 + 1)) / (f + _BM25_K1 * (1 - _BM25_B + _BM25_B * dl / avgdl))
        scored.append((s, model))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    return scored


PRECHECK = """BEFORE YOU COMPUTE
  What size difference would change what you do? If every plausible answer leads
  to the same action, stop - you do not need this."""


def format_match(i: int, model: dict) -> str:
    lines = [f"  {i}. {model['title']}  [{model['tier']}]",
             f"     {model['output']}",
             f"     python3 {model['path']} {model['usage']}"]
    for hazard in model.get("composition_hazards") or []:
        lines.append(f"     HAZARD: {hazard}")
    if model.get("data_provenance_required"):
        lines.append(f"     REQUIRES: {model['data_provenance_required']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Find the right statistical model for a situation.")
    ap.add_argument("query", nargs="?", help="your predicament, in plain words")
    ap.add_argument("--family", help="list one family instead of searching")
    ap.add_argument("--id", dest="model_id", help="print the usage block for one model")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    reg = load_registry()

    if a.model_id:
        for m in reg["models"]:
            if m["id"] == a.model_id:
                print(json.dumps(m, indent=2) if a.json else format_match(1, m))
                return 0
        print(f"no model with id {a.model_id!r}", file=sys.stderr)
        return 1

    if a.family:
        members = [m for m in reg["models"] if m["family"] == a.family]
        if not members:
            fams = ", ".join(f["id"] for f in reg["families"])
            print(f"no family {a.family!r}. Families: {fams}", file=sys.stderr)
            return 1
        if a.json:
            print(json.dumps(members, indent=2))
        else:
            for i, m in enumerate(members, 1):
                print(format_match(i, m))
        return 0

    if not a.query:
        ap.error("a query is required unless --family or --id is given")

    scored = [(s, m) for s, m in score_all(a.query, reg) if s >= NO_MATCH_FLOOR][:MAX_MATCHES]

    if a.json:
        print(json.dumps({"query": a.query,
                          "matches": [{"score": round(s, 4), **m} for s, m in scored]}, indent=2))
        return 0

    print(PRECHECK)
    print()
    if not scored:
        fams = "\n".join(f"  {f['id']:<12} {f['question']}" for f in reg["families"])
        print("NO CONFIDENT MATCH\n"
              "  Nothing in the registry clearly fits. Either this is not a question statistics\n"
              "  answers, or it needs different words. Families available:\n" + fams)
        return 0
    print("MATCHES")
    for i, (_, m) in enumerate(scored, 1):
        print(format_match(i, m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
