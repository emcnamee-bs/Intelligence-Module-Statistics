"""The output contract every model script uses.

Four outcomes. Anything whose printed number is not the model's own answer gets its own exit code,
so `if rc == 0: use the number` can never hand an agent someone else's number wearing the module's
authority.

    0  ANSWER        the model's answer          (may carry CAVEAT / ROBUSTNESS annotations)
    2  usage error   argparse's own              (never used here - reserved so it stays distinct)
    3  REFUSED       inputs violate the model    no RESULT block, structurally
    4  UNANSWERABLE  the question has no answer  no RESULT block, structurally
    5  USE_SIMPLER   a simpler answer is better  RESULT block is the SIMPLER answer, labelled

Every outcome ends with REPORT AS: the sentence to say. Agents have been observed reporting numbers
their tools flagged as unreliable, so the contract converts interpretation into transcription rather
than trusting the agent to interpret correctly.
"""
import json
import math
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = [
    "Outcome", "ANSWER", "REFUSED", "UNANSWERABLE", "USE_SIMPLER",
    "Report", "answer", "refused", "unanswerable", "use_simpler",
    "render", "emit", "fmt",
]


@dataclass(frozen=True)
class Outcome:
    name: str
    code: int


# Exit codes are contract, not convention. 2 is skipped because argparse owns it: overloading it
# would make "you typed the flag wrong" indistinguishable from "your data violates the model", and
# those demand opposite responses from the caller.
ANSWER = Outcome("ANSWER", 0)
REFUSED = Outcome("REFUSED", 3)
UNANSWERABLE = Outcome("UNANSWERABLE", 4)
USE_SIMPLER = Outcome("USE_SIMPLER", 5)


def fmt(v: Any) -> str:
    """Render a value with enough resolution to be acted on, without float noise.

    Rule: three significant figures, but never fewer digits than the integer part requires.
    One rule, no special cases. Three significant figures because model outputs are decisions, not
    physics - and the integer-part floor because 12345.6789 must render as "12346", not "12300".
    Sub-unit values therefore keep resolution automatically: 0.002386 -> "0.00239", not "0.002".
    """
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(fmt(x) for x in v) + "]"
    if isinstance(v, float):
        if math.isnan(v):
            return "nan"
        if math.isinf(v):
            return "inf" if v > 0 else "-inf"
        if v == 0:
            return "0"
        mag = abs(v)
        if mag < 1e-4 or mag >= 1e7:
            return f"{v:.2g}"
        # decimals = however many are needed for 3 significant figures; clamped at 0 so the
        # integer part is never rounded away.
        decimals = max(0, 3 - int(math.floor(math.log10(mag))) - 1)
        s = f"{v:.{decimals}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s if s else "0"
    return str(v)


@dataclass
class Report:
    outcome: Outcome
    model: str
    report_as: str
    result: Optional[Dict[str, Any]] = None
    result_source: Optional[str] = None  # set only when result is NOT the model's answer
    caveat: Optional[str] = None
    robustness: Optional[str] = None
    lines: List[str] = field(default_factory=list)  # outcome-specific prose, in print order

    @property
    def is_model_answer(self) -> bool:
        return self.outcome is ANSWER


def _require(text: str, what: str) -> str:
    if not text or not text.strip():
        raise ValueError(f"{what} must be a non-empty sentence")
    return text.strip()


def answer(*, model: str, result: Dict[str, Any], report_as: str,
           caveat: Optional[str] = None, robustness: Optional[str] = None) -> Report:
    """The model computed an answer and its assumptions hold.

    caveat: assumptions strained but the number is still informative.
    robustness: how large a violation would have to be to overturn the conclusion. Preferred over
    an assumption test - screening on a low-power check is worse than not checking (principle P2).
    """
    if not result:
        raise ValueError("ANSWER requires a non-empty result")
    return Report(ANSWER, model, _require(report_as, "report_as"), result=result,
                  caveat=caveat, robustness=robustness)


def refused(*, model: str, violation: str, why_it_matters: str, do_instead: str) -> Report:
    """Inputs structurally violate the model, so any number would mislead.

    There is deliberately no `result` parameter: no code path can smuggle a headline number into a
    refusal. A warning printed beside a number does not work - agents report the number anyway.
    """
    v = _require(violation, "violation")
    return Report(
        REFUSED, model,
        report_as=f"I can't answer that from these inputs: {v.rstrip('.')}. {do_instead.strip()}",
        lines=[f"REFUSED: {v}",
               f"WHY IT MATTERS: {_require(why_it_matters, 'why_it_matters')}",
               f"DO INSTEAD: {_require(do_instead, 'do_instead')}"],
    )


def unanswerable(*, model: str, why: str, ask_instead: str) -> Report:
    """The inputs are fine and the model is right, but the question as posed has no answer.

    Distinct from REFUSED: no data would help. Arguably the highest-value thing the module does,
    because it is the failure no amount of computation fixes.
    """
    w = _require(why, "why")
    return Report(
        UNANSWERABLE, model,
        report_as=f"That question doesn't have an answer as posed: {w.rstrip('.')}. "
                  f"{ask_instead.strip()}",
        lines=[f"UNANSWERABLE: {w}",
               f"ASK INSTEAD: {_require(ask_instead, 'ask_instead')}"],
    )


def use_simpler(*, model: str, simpler_name: str, simpler_result: Dict[str, Any],
                why: str) -> Report:
    """The model does not beat a simpler approach, so the simpler answer is what to use.

    The printed number is the SIMPLER answer. It gets exit code 5 and an explicit attribution so it
    cannot be transcribed as the model's output - a naive estimate carrying statistical provenance
    is worse than not running the module at all.
    """
    if not simpler_result:
        raise ValueError("USE_SIMPLER requires the simpler answer's result")
    n = _require(simpler_name, "simpler_name")
    return Report(
        USE_SIMPLER, model, result=simpler_result, result_source=n,
        report_as=f"The model doesn't beat {n} here, so use that: "
                  f"{', '.join(f'{k} {fmt(v)}' for k, v in simpler_result.items())}.",
        lines=[f"USE_SIMPLER: {n}",
               f"WHY: {_require(why, 'why')}",
               f"NOTE: the figure below is from {n} — it is NOT the model's answer."],
    )


def render(r: Report, as_json: bool = False) -> str:
    if as_json:
        d: Dict[str, Any] = {
            "outcome": r.outcome.name,
            "exit_code": r.outcome.code,
            "model": r.model,
            "is_model_answer": r.is_model_answer,
            "report_as": r.report_as,
        }
        if r.result is not None:
            d["result"] = r.result
            d["result_source"] = r.result_source or "model"
        if r.caveat:
            d["caveat"] = r.caveat
        if r.robustness:
            d["robustness"] = r.robustness
        if r.lines:
            d["detail"] = r.lines
        return json.dumps(d, indent=2, sort_keys=False)

    out = [f"MODEL: {r.model}"]
    out.extend(r.lines)
    if r.result is not None:
        out.append("RESULT" if r.is_model_answer else f"RESULT (from {r.result_source})")
        width = max(len(k) for k in r.result)
        out.extend(f"  {k.ljust(width)}: {fmt(v)}" for k, v in r.result.items())
    if r.caveat:
        out.append(f"CAVEAT: {r.caveat}")
    if r.robustness:
        out.append(f"ROBUSTNESS: {r.robustness}")
    out.append(f"REPORT AS: {r.report_as}")
    return "\n".join(out)


def emit(r: Report, as_json: bool = False) -> None:
    """Print the report and exit with the outcome's code. Terminal - does not return."""
    print(render(r, as_json=as_json))
    sys.exit(r.outcome.code)
