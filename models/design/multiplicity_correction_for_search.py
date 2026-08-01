#!/usr/bin/env python3
# WHAT        Corrects a p-value for how many things you looked at before one stood out.
# WHEN        You noticed a pattern after examining several metrics, tests, configs or time
#             windows. The p-value of the winner is not the p-value of your procedure.
# INPUTS      --p smallest observed p-value, --comparisons K how many you made OR could have made.
#             Or --p-values p1,p2,... to correct a whole set. --post-hoc if K is unbounded.
# OUTPUT      Corrected p, whether it survives, and the raw p you would have needed.
# ASSUMPTIONS Sidak assumes the comparisons are independent; Bonferroni assumes nothing and is
#             reported alongside. Both are exact only if K is honest.
# EXAMPLE     python3 models/design/multiplicity_correction_for_search.py --p 0.03 --comparisons 12
"""Forces the count. That is the whole value; the arithmetic is one line.

The correction is `1 - (1-p)^k` (Sidak) - cluster C5, the same identity as fan-out failure
amplification and the return-period formula. An agent can compute it trivially. What an agent
reliably does not do is *count the comparisons it made*, including the ones it abandoned, before
quoting the p-value of the one that survived.

So this model requires --comparisons and refuses without it. Refusing to guess K is the feature: a
default of 1 would silently reproduce the error the model exists to catch.

If the pattern was noticed after open-ended exploration and K genuinely cannot be bounded, no
correction is valid and the model says so rather than inventing one.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.report import answer, emit, refused, unanswerable, use_simpler  # noqa: E402


def sidak(p: float, k: int) -> float:
    """Family-wise error rate for the smallest of k independent p-values: 1 - (1-p)^k."""
    return 1.0 - (1.0 - p) ** k


def bonferroni(p: float, k: int) -> float:
    """Assumption-free and always at least as large as Sidak. Capped at 1."""
    return min(1.0, p * k)


def raw_p_needed(alpha: float, k: int) -> float:
    """The per-comparison threshold that yields family-wise alpha: 1 - (1-alpha)^(1/k)."""
    return 1.0 - (1.0 - alpha) ** (1.0 / k)


def holm_adjusted(pvals):
    """Holm-Bonferroni step-down adjusted p-values, returned in the input order.

    Uniformly more powerful than Bonferroni and valid under any dependence. The enforced
    monotonicity is part of the definition, not a tidy-up: without it an adjusted p could fall
    below a smaller raw p and invert the ordering.
    """
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, (m - rank) * pvals[idx])
        running = max(running, val)
        adjusted[idx] = running
    return adjusted


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Correct a p-value for the number of comparisons behind it.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--p", type=float, help="the smallest observed p-value")
    g.add_argument("--p-values", help="comma-separated p-values to correct as a set")
    ap.add_argument("--comparisons", type=int,
                    help="how many comparisons you made, or could have made")
    ap.add_argument("--post-hoc", action="store_true",
                    help="the pattern was found by open-ended exploration; K cannot be bounded")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    model = "Multiplicity correction for a search"

    if not 0 < a.alpha < 1:
        emit(refused(
            model=model, violation=f"--alpha is {a.alpha}, outside (0, 1)",
            why_it_matters="alpha is a probability.", do_instead="Use e.g. --alpha 0.05."), a.json)

    if a.post_hoc:
        emit(unanswerable(
            model=model,
            why="the number of comparisons is unbounded. If the pattern was found by open-ended "
                "exploration, every metric, window, subgroup and cut you could have examined "
                "counts, and no correction is valid over a search space you cannot enumerate",
            ask_instead="Treat this as hypothesis generation, not evidence. State the pattern as a "
                        "specific prediction and test it on data you have not looked at — held-out "
                        "records, the next time window, or a fresh run. That converts an "
                        "uncorrectable p-value into a real one.",
        ), a.json)

    if a.comparisons is None:
        emit(refused(
            model=model, violation="--comparisons was not given",
            why_it_matters="The count is the entire input. Assuming 1 would silently reproduce the "
                           "error this model exists to catch, so it is not assumed.",
            do_instead="Count every comparison you made, including ones you abandoned and metrics "
                       "you glanced at and dropped, then pass --comparisons N. If you cannot bound "
                       "the count, pass --post-hoc instead.",
        ), a.json)
    if a.comparisons < 1:
        emit(refused(
            model=model, violation=f"--comparisons is {a.comparisons}, which is below 1",
            why_it_matters="You made at least one comparison to have a p-value at all.",
            do_instead="Pass the true count, at least 1."), a.json)

    if a.p_values is not None:
        try:
            pvals = [float(x) for x in a.p_values.split(",") if x.strip()]
        except ValueError:
            emit(refused(
                model=model, violation=f"--p-values could not be parsed: {a.p_values!r}",
                why_it_matters="The set of p-values is the input.",
                do_instead="Pass numbers separated by commas, e.g. --p-values 0.01,0.04,0.2."),
                a.json)
        if not pvals or any(not 0 <= v <= 1 for v in pvals):
            emit(refused(
                model=model, violation="a p-value is outside [0, 1]",
                why_it_matters="p-values are probabilities.",
                do_instead="Check the values; a test statistic is not a p-value."), a.json)
        if len(pvals) > a.comparisons:
            emit(refused(
                model=model,
                violation=f"{len(pvals)} p-values given but --comparisons is {a.comparisons}",
                why_it_matters="You cannot have made fewer comparisons than you have p-values; "
                               "correcting against too small a count understates the problem.",
                do_instead=f"Set --comparisons to at least {len(pvals)}."), a.json)

        adj = holm_adjusted(pvals)
        survivors = [i for i, v in enumerate(adj) if v < a.alpha]
        result = {"n_p_values": len(pvals), "comparisons": a.comparisons,
                  "holm_adjusted": [round(v, 6) for v in adj],
                  "surviving_indices": survivors, "alpha": a.alpha}
        emit(answer(
            model=model, result=result,
            robustness=f"Holm is valid under any dependence between the comparisons, so this "
                       f"survives whatever correlation exists among them.",
            report_as=f"After correcting for {a.comparisons} comparisons, "
                      f"{len(survivors)} of {len(pvals)} results remain significant at "
                      f"{a.alpha:g}" + (f" (positions {survivors})." if survivors else "."),
        ), a.json)

    p = a.p
    if not 0 <= p <= 1:
        emit(refused(
            model=model, violation=f"--p is {p}, outside [0, 1]",
            why_it_matters="A p-value is a probability.",
            do_instead="Check whether you passed a test statistic by mistake."), a.json)

    if a.comparisons == 1:
        emit(use_simpler(
            model=model, simpler_name="your uncorrected p-value",
            simpler_result={"p": p},
            why="With a single pre-specified comparison there is no multiplicity to correct for. "
                "But confirm the count is really 1: if you looked at other metrics first and "
                "dropped them, they count.",
        ), a.json)

    sid = sidak(p, a.comparisons)
    bon = bonferroni(p, a.comparisons)
    needed = raw_p_needed(a.alpha, a.comparisons)
    survives = sid < a.alpha

    result = {"raw_p": p, "comparisons": a.comparisons,
              "sidak_corrected_p": sid, "bonferroni_corrected_p": bon,
              "raw_p_needed_for_alpha": needed, "alpha": a.alpha, "survives": survives}

    if survives:
        emit(answer(
            model=model, result=result,
            robustness=f"Bonferroni, which assumes nothing about dependence between the "
                       f"comparisons, gives {bon:.4g} — also below {a.alpha:g}, so the conclusion "
                       f"does not rest on the comparisons being independent.",
            report_as=f"Corrected for {a.comparisons} comparisons, p = {sid:.4g} — still "
                      f"significant at {a.alpha:g}.",
        ), a.json)

    emit(answer(
        model=model, result=result,
        robustness=f"To survive {a.comparisons} comparisons at {a.alpha:g} the raw p would have "
                   f"had to be below {needed:.4g}; it was {p:.4g}.",
        report_as=f"Corrected for {a.comparisons} comparisons, p = {sid:.4g} — this is no longer "
                  f"significant at {a.alpha:g}. The raw {p:.4g} is the p-value of the winner, not "
                  f"of the procedure that picked it.",
    ), a.json)


if __name__ == "__main__":
    main()
