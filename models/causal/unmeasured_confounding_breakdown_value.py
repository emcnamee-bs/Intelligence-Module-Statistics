#!/usr/bin/env python3
# WHAT        How strong an unmeasured confounder would have to be to explain away an association.
# WHEN        You have an observed effect and a causal story, and want to know how fragile the
#             causal reading is. Use instead of asserting "we controlled for the obvious things".
# INPUTS      One of --rr --or --hr --smd (the observed effect). Optional --ci-low --ci-high.
#             --rare if an odds ratio came from a rare outcome (<15%).
# OUTPUT      e_value: the confounder-association strength, on the risk-ratio scale, needed with
#             BOTH exposure and outcome to nullify the effect. Higher means more robust.
# ASSUMPTIONS Effect is already adjusted for measured confounders. The E-value bounds confounding
#             only; it says nothing about selection bias, measurement error, or reverse causation.
# EXAMPLE     python3 models/causal/unmeasured_confounding_breakdown_value.py --rr 2.0 --ci-low 1.2
"""Reports a breakdown value instead of an assumption test (principle P4).

Screening on a low-power assumption check is worse than not checking: conditioning on having passed
it selects for datasets where the violation happened to be invisible (Roth 2022, RESEARCH.md 1.1).
So this model never asserts "no unmeasured confounding". It answers the quantitative question -
how strong would it have to be? - and lets that number carry the argument.

E = RR + sqrt(RR*(RR-1)), the solution of E^2/(2E-1) = RR, where E^2/(2E-1) is the Ding-VanderWeele
bounding factor when confounder-exposure and confounder-outcome associations both equal E.
"""
import argparse
import sys
from math import exp, sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.report import answer, emit, refused, unanswerable  # noqa: E402

# An odds ratio approximates a risk ratio only when the outcome is uncommon. 15% is VanderWeele's
# conventional cut; above it the square-root transform is the better approximation.
RARE_OUTCOME_CEILING = 0.15
# Chinn's factor converting a standardized mean difference to an approximate log risk ratio.
SMD_TO_LOG_RR = 0.91


def e_value(rr: float) -> float:
    """Breakdown value on the risk-ratio scale. Symmetric about the null: RR and 1/RR agree."""
    if rr < 1.0:
        rr = 1.0 / rr
    return rr + sqrt(rr * (rr - 1.0))


def e_value_for_limit(limit: float, estimate: float) -> float:
    """E-value for a confidence limit. 1.0 when the interval already includes the null."""
    if (estimate > 1.0 and limit <= 1.0) or (estimate < 1.0 and limit >= 1.0):
        return 1.0
    return e_value(limit)


def to_risk_ratio(args) -> (float, str):
    if args.rr is not None:
        return args.rr, "risk ratio"
    if args.odds_ratio is not None:
        if args.rare:
            return args.odds_ratio, "odds ratio (rare outcome, RR ~ OR)"
        return sqrt(args.odds_ratio), "odds ratio (RR ~ sqrt(OR))"
    if args.hr is not None:
        hr = args.hr
        return ((1 - 0.5 ** sqrt(hr)) / (1 - 0.5 ** sqrt(1 / hr))), "hazard ratio"
    return exp(SMD_TO_LOG_RR * args.smd), "standardized mean difference"


def main(argv=None):
    ap = argparse.ArgumentParser(description="How strong must confounding be to explain this away?")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rr", type=float, help="observed risk ratio")
    g.add_argument("--or", dest="odds_ratio", type=float, help="observed odds ratio")
    g.add_argument("--hr", type=float, help="observed hazard ratio")
    g.add_argument("--smd", type=float, help="standardized mean difference (Cohen's d)")
    ap.add_argument("--ci-low", type=float)
    ap.add_argument("--ci-high", type=float)
    # Note: argparse parses "%" in help strings as a format specifier, so state the ceiling as a
    # fraction rather than a percentage.
    ap.add_argument("--rare", action="store_true",
                    help=f"outcome prevalence below {RARE_OUTCOME_CEILING} (odds ratio only)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    model = "Unmeasured-confounding breakdown value (E-value)"

    for name, v in (("--rr", a.rr), ("--or", a.odds_ratio), ("--hr", a.hr)):
        if v is not None and v <= 0:
            emit(refused(
                model=model, violation=f"{name} is {v}, which is not positive",
                why_it_matters="Ratio measures are strictly positive; a non-positive value is not "
                               "an effect estimate.",
                do_instead="Check whether you meant a log-scale value, and pass the ratio itself.",
            ), a.json)
    if a.rare and a.odds_ratio is None:
        emit(refused(
            model=model, violation="--rare was given without --or",
            why_it_matters="The rare-outcome approximation only applies to odds ratios; applying "
                           "it elsewhere would silently change the estimate.",
            do_instead="Drop --rare, or pass the effect as --or.",
        ), a.json)
    if (a.ci_low is None) != (a.ci_high is None):
        emit(refused(
            model=model, violation="only one confidence limit was given",
            why_it_matters="The E-value for an interval uses the limit nearer the null; with one "
                           "limit there is no interval.",
            do_instead="Pass both --ci-low and --ci-high, or neither.",
        ), a.json)
    if a.ci_low is not None and a.ci_low > a.ci_high:
        emit(refused(
            model=model, violation=f"--ci-low ({a.ci_low}) exceeds --ci-high ({a.ci_high})",
            why_it_matters="A reversed interval would make the wrong limit the one nearer the null.",
            do_instead="Swap the two limits.",
        ), a.json)

    rr, scale = to_risk_ratio(a)

    if rr == 1.0:
        emit(unanswerable(
            model=model,
            why="the observed effect is exactly at the null, so there is no association for a "
                "confounder to explain away",
            ask_instead="Ask whether the study could have detected an effect worth caring about — "
                        "run minimum_attainable_p_for_design, or a power calculation, instead.",
        ), a.json)

    ev = e_value(rr)
    result = {"input_scale": scale, "risk_ratio_used": rr, "e_value_point": ev}

    ci_note = ""
    if a.ci_low is not None:
        nearer = a.ci_low if rr > 1.0 else a.ci_high
        ev_ci = e_value_for_limit(nearer, rr)
        result["ci_limit_nearer_null"] = nearer
        result["e_value_ci"] = ev_ci
        if ev_ci == 1.0:
            ci_note = (" The confidence interval already includes the null, so no unmeasured "
                       "confounding at all is needed to make the effect non-significant.")
        else:
            ci_note = (f" To push the interval to include the null, confounding of {ev_ci:.3g} "
                       f"suffices.")

    robustness = (
        f"An unmeasured confounder would need a risk ratio of {ev:.3g} with BOTH the exposure and "
        f"the outcome, above all measured covariates, to move the estimate to the null. Weaker "
        f"confounding could not explain it away.{ci_note}"
    )

    emit(answer(
        model=model, result=result, robustness=robustness,
        report_as=f"Explaining this away would take unmeasured confounding of {ev:.3g} on the "
                  f"risk-ratio scale with both exposure and outcome — judge against the strongest "
                  f"measured covariate you already adjusted for.{ci_note}",
    ), a.json)


if __name__ == "__main__":
    main()
