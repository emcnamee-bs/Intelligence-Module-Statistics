#!/usr/bin/env python3
# WHAT        Compares two systems scored on the SAME items, using only the items they disagree on.
# WHEN        "A got 40/50, B got 43/50" on one shared test set, eval suite, or benchmark corpus.
#             Reach for this instead of a two-proportion test whenever the items are shared.
# INPUTS      --discordant-b (A right, B wrong) and --discordant-c (A wrong, B right). If you only
#             have totals, pass --a-correct --b-correct --n and it will tell you what that supports.
# OUTPUT      Exact two-sided p from the discordant pairs, or the best case the totals allow.
# ASSUMPTIONS Items are shared and paired. Independent test sets need a two-proportion test instead.
# EXAMPLE     python3 models/design/mcnemar_paired_comparison.py --discordant-b 2 --discordant-c 9
"""Two facts an agent cannot get from training data, both about the inputs rather than the test.

**1. Totals are not enough.** "40/50 versus 43/50 on the same items" does not determine the answer.
Only the *discordant* items matter - the ones where exactly one system was right - and the totals
do not reveal how many there were. Twelve disagreements with a 3-item net, or three disagreements
with a 3-item net, give completely different evidence from identical totals.

**2. Sometimes the totals settle it anyway.** The strongest case consistent with a net difference d
is the minimum-discordance one, b=0 and c=d, giving p = 2 * 0.5^d. For d = 3 that is 0.25 - so a
three-item difference on a shared set **cannot** reach significance no matter how the pairing falls.
No data collection fixes that; only more items would.

Using an unpaired two-proportion test here answers a different question: it treats two measurements
of the same 50 items as 100 independent observations, discarding the pairing that is the entire
source of precision.
"""
import argparse
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.report import answer, emit, refused  # noqa: E402


def exact_mcnemar_p(b: int, c: int) -> float:
    """Two-sided exact p: 2 * P(Bin(b+c, 0.5) <= min(b,c)), capped at 1.

    Conditional on the number of disagreements, each discordant item is a fair coin under the null
    that the systems are equivalent. Concordant items carry no information and are excluded - that
    exclusion is what makes this a paired test.
    """
    n_d = b + c
    if n_d == 0:
        return 1.0
    lo = min(b, c)
    tail = sum(comb(n_d, i) for i in range(lo + 1)) / (2 ** n_d)
    return min(1.0, 2.0 * tail)


def best_case_p_from_totals(net_difference: int) -> float:
    """Smallest p any pairing consistent with this net difference could produce.

    Achieved at minimum discordance (b=0, c=d), where every disagreement points one way.
    """
    d = abs(net_difference)
    if d == 0:
        return 1.0
    return min(1.0, 2.0 * 0.5 ** d)


def min_net_difference_for_significance(alpha: float) -> int:
    """Smallest net difference whose best case clears alpha. 2*0.5^d < alpha."""
    d = 1
    while best_case_p_from_totals(d) >= alpha and d < 1000:
        d += 1
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description="Paired comparison of two systems on shared items.")
    ap.add_argument("--discordant-b", type=int, help="items where A was right and B was wrong")
    ap.add_argument("--discordant-c", type=int, help="items where A was wrong and B was right")
    ap.add_argument("--a-correct", type=int, help="A's total correct (totals-only mode)")
    ap.add_argument("--b-correct", type=int, help="B's total correct (totals-only mode)")
    ap.add_argument("--n", type=int, help="number of shared items (totals-only mode)")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    model = "Paired comparison on shared items (exact McNemar)"
    have_discordant = a.discordant_b is not None and a.discordant_c is not None
    have_totals = a.a_correct is not None and a.b_correct is not None and a.n is not None

    if not 0 < a.alpha < 1:
        emit(refused(model=model, violation=f"--alpha is {a.alpha}, outside (0, 1)",
                     why_it_matters="alpha is a probability.",
                     do_instead="Use e.g. --alpha 0.05."), a.json)
    if have_discordant and have_totals:
        emit(refused(
            model=model, violation="both discordant counts and totals were given",
            why_it_matters="The discordant counts are strictly more informative; mixing the two "
                           "risks reporting the weaker analysis when the stronger is available.",
            do_instead="Pass only --discordant-b and --discordant-c."), a.json)
    if not have_discordant and not have_totals:
        emit(refused(
            model=model, violation="neither the discordant counts nor the totals were given",
            why_it_matters="Only the items where exactly one system was right carry information.",
            do_instead="Pass --discordant-b and --discordant-c, or --a-correct --b-correct --n."),
            a.json)

    if have_discordant:
        b, c = a.discordant_b, a.discordant_c
        if b < 0 or c < 0:
            emit(refused(model=model, violation=f"a discordant count is negative (b={b}, c={c})",
                         why_it_matters="Counts of items cannot be negative.",
                         do_instead="Recount the items where exactly one system was right."), a.json)
        p = exact_mcnemar_p(b, c)
        n_d = b + c
        result = {"discordant_b": b, "discordant_c": c, "discordant_total": n_d,
                  "exact_two_sided_p": p, "alpha": a.alpha, "significant": p < a.alpha}

        if n_d == 0:
            emit(answer(
                model=model, result=result,
                robustness="With no disagreements there is no evidence either way, however many "
                           "items agreed. Concordant items are uninformative by construction.",
                report_as="The two systems agreed on every item, so this comparison provides no "
                          "evidence that either is better.",
            ), a.json)

        better = "B" if c > b else "A"
        min_d = min_net_difference_for_significance(a.alpha)
        emit(answer(
            model=model, result=result,
            robustness=f"Only the {n_d} disagreements carry information; the concordant items are "
                       f"excluded by construction. A net difference of at least {min_d} "
                       f"disagreements is needed to reach p<{a.alpha:g} at all.",
            report_as=(f"{better} is better on {max(b, c)} of the {n_d} items where they "
                       f"disagreed: exact p = {p:.4g}, "
                       + ("significant" if p < a.alpha else "not significant")
                       + f" at {a.alpha:g}."),
        ), a.json)

    # Totals-only mode.
    n, ac, bc = a.n, a.a_correct, a.b_correct
    if n < 1:
        emit(refused(model=model, violation=f"--n is {n}, below 1",
                     why_it_matters="There are no items to compare.",
                     do_instead="Pass the number of shared items."), a.json)
    if not 0 <= ac <= n or not 0 <= bc <= n:
        emit(refused(
            model=model, violation=f"a correct count is outside 0..{n} (A={ac}, B={bc})",
            why_it_matters="A system cannot score above the number of items or below zero.",
            do_instead="Check the totals against the item count."), a.json)

    net = bc - ac
    best_p = best_case_p_from_totals(net)
    min_d = min_net_difference_for_significance(a.alpha)
    result = {"n_items": n, "a_correct": ac, "b_correct": bc, "net_difference": net,
              "best_case_p": best_p, "alpha": a.alpha,
              "min_net_difference_for_significance": min_d}

    if best_p >= a.alpha:
        emit(answer(
            model=model, result=result,
            robustness=f"This holds for every pairing consistent with the totals. The best case is "
                       f"minimum discordance ({abs(net)} disagreements all pointing one way), "
                       f"giving p = {best_p:.4g}. A net difference of {min_d} would be needed.",
            report_as=f"A {abs(net)}-item difference on {n} shared items cannot reach "
                      f"p<{a.alpha:g} however the disagreements fall — the best possible p is "
                      f"{best_p:.4g}. More items would help; re-analysing these will not.",
        ), a.json)

    emit(refused(
        model=model,
        violation=f"totals alone ({ac}/{n} vs {bc}/{n}) do not determine the paired comparison",
        why_it_matters=f"Only the items where exactly one system was right carry information, and "
                       f"the totals do not say how many there were. Consistent pairings here range "
                       f"from p = {best_p:.4g} to p = 1. A two-proportion test would paper over "
                       f"this by treating {2 * n} measurements of {n} items as independent.",
        do_instead="Count the items where A was right and B was wrong, and vice versa, then pass "
                   "--discordant-b and --discordant-c.",
    ), a.json)


if __name__ == "__main__":
    main()
