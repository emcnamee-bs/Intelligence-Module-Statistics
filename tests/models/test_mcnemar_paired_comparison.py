"""L2/L3/L4 tests for mcnemar_paired_comparison.

The exact p is verified by enumerating the conditional null directly - every sign assignment of the
discordant items, counted - rather than by restating the binomial formula. The best-case bound is
verified by brute-force search over every pairing consistent with the totals, which is the claim
that makes the totals-only mode meaningful.
"""
import json
import subprocess
import sys
import unittest
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "models" / "design" / "mcnemar_paired_comparison.py"
sys.path.insert(0, str(ROOT))

from models.design.mcnemar_paired_comparison import (  # noqa: E402
    best_case_p_from_totals, exact_mcnemar_p, min_net_difference_for_significance,
)


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


class TestExactPByEnumeration(unittest.TestCase):
    """Enumerate all 2^n_d sign assignments of the discordant items under the null."""

    def _enumerated_p(self, b, c):
        n_d = b + c
        if n_d == 0:
            return 1.0
        observed = min(b, c)
        hits = sum(1 for signs in product((0, 1), repeat=n_d)
                   if min(sum(signs), n_d - sum(signs)) <= observed)
        return hits / 2 ** n_d

    def test_matches_full_enumeration(self):
        for b in range(0, 8):
            for c in range(0, 8):
                self.assertAlmostEqual(exact_mcnemar_p(b, c), self._enumerated_p(b, c),
                                       places=12, msg=f"b={b} c={c}")

    def test_hand_derived_cases(self):
        # b=0, c=3: only the all-one-way assignment is as extreme; 2 * (1/8).
        self.assertAlmostEqual(exact_mcnemar_p(0, 3), 0.25, places=14)
        # b=0, c=5: 2 * (1/32).
        self.assertAlmostEqual(exact_mcnemar_p(0, 5), 2 / 32, places=14)
        # b=2, c=9: 2 * P(X<=2 | n=11) = 2 * (1+11+55)/2048.
        self.assertAlmostEqual(exact_mcnemar_p(2, 9), 2 * (1 + 11 + 55) / 2048, places=14)


class TestProperties(unittest.TestCase):
    def test_symmetric_in_its_arguments(self):
        for b, c in ((0, 4), (3, 7), (10, 2)):
            self.assertAlmostEqual(exact_mcnemar_p(b, c), exact_mcnemar_p(c, b), places=14)

    def test_equal_counts_give_no_evidence(self):
        for k in range(0, 12):
            self.assertEqual(exact_mcnemar_p(k, k), 1.0)

    def test_no_disagreements_gives_p_one(self):
        self.assertEqual(exact_mcnemar_p(0, 0), 1.0)

    def test_never_exceeds_one(self):
        for b in range(0, 15):
            for c in range(0, 15):
                self.assertLessEqual(exact_mcnemar_p(b, c), 1.0)

    def test_concordant_items_are_irrelevant(self):
        # The whole point of a paired test: 3-vs-0 on 10 items and on 10,000 items are identical.
        self.assertEqual(exact_mcnemar_p(0, 3), exact_mcnemar_p(0, 3))

    def test_more_lopsided_is_more_significant(self):
        prev = 1.1
        for c in range(1, 15):
            p = exact_mcnemar_p(0, c)
            self.assertLess(p, prev)
            prev = p


class TestBestCaseBoundByBruteForce(unittest.TestCase):
    """The claim that makes totals-only mode useful: no pairing beats minimum discordance."""

    def test_no_consistent_pairing_beats_the_reported_best_case(self):
        for n, ac, bc in ((50, 40, 43), (20, 15, 17), (100, 80, 88)):
            net = bc - ac
            best = best_case_p_from_totals(net)
            # Every (b, c) with c - b == net and b + c <= n is a consistent pairing.
            for b in range(0, n + 1):
                c = b + net
                if c < 0 or b + c > n:
                    continue
                self.assertGreaterEqual(exact_mcnemar_p(b, c), best - 1e-12,
                                        f"n={n} b={b} c={c} beats the claimed best case")

    def test_best_case_is_attained(self):
        for net in (1, 3, 5, 8):
            self.assertAlmostEqual(best_case_p_from_totals(net), exact_mcnemar_p(0, net),
                                   places=14)

    def test_a_three_item_difference_can_never_be_significant(self):
        # The headline fact: 2 * 0.5^3 = 0.25, whatever the pairing.
        self.assertAlmostEqual(best_case_p_from_totals(3), 0.25, places=14)
        self.assertGreater(best_case_p_from_totals(3), 0.05)

    def test_minimum_net_difference_for_significance(self):
        # 2*0.5^d < 0.05  =>  0.5^d < 0.025  =>  d >= 6 (0.5^6 = 0.015625, 2x = 0.03125).
        self.assertEqual(min_net_difference_for_significance(0.05), 6)
        self.assertAlmostEqual(best_case_p_from_totals(6), 0.03125, places=14)
        self.assertGreater(best_case_p_from_totals(5), 0.05)

    def test_zero_difference_gives_p_one(self):
        self.assertEqual(best_case_p_from_totals(0), 1.0)


class TestOutcomes(unittest.TestCase):
    def test_discordant_counts_answer(self):
        rc, out = run("--discordant-b", "2", "--discordant-c", "9")
        self.assertEqual(rc, 0)
        self.assertIn("disagreed", out)
        self.assertIn("ROBUSTNESS:", out)

    def test_the_40_vs_43_case_is_settled_by_the_totals(self):
        # The scenario the model was written for: totals alone are enough to say "cannot".
        rc, out = run("--a-correct", "40", "--b-correct", "43", "--n", "50")
        self.assertEqual(rc, 0)
        self.assertIn("cannot reach", out)
        self.assertIn("0.25", out)
        self.assertIn("More items would help", out)

    def test_totals_that_could_be_significant_refuse_and_ask_for_the_pairing(self):
        rc, out = run("--a-correct", "30", "--b-correct", "40", "--n", "50")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)
        self.assertIn("discordant", out)
        self.assertIn("independent", out)

    def test_total_agreement_answers_with_no_evidence(self):
        rc, out = run("--discordant-b", "0", "--discordant-c", "0")
        self.assertEqual(rc, 0)
        self.assertIn("no evidence", out)

    def test_negative_counts_refuse(self):
        rc, _ = run("--discordant-b", "-1", "--discordant-c", "3")
        self.assertEqual(rc, 3)

    def test_correct_count_above_n_refuses(self):
        rc, _ = run("--a-correct", "60", "--b-correct", "40", "--n", "50")
        self.assertEqual(rc, 3)

    def test_both_input_modes_refuses(self):
        rc, out = run("--discordant-b", "1", "--discordant-c", "2",
                      "--a-correct", "40", "--b-correct", "43", "--n", "50")
        self.assertEqual(rc, 3)
        self.assertIn("strictly more informative", out)

    def test_no_input_refuses(self):
        rc, _ = run()
        self.assertEqual(rc, 3)

    def test_json_shape(self):
        rc, out = run("--discordant-b", "2", "--discordant-c", "9", "--json")
        d = json.loads(out)
        self.assertEqual(d["outcome"], "ANSWER")
        self.assertEqual(d["result"]["discordant_total"], 11)


class TestHeaderContract(unittest.TestCase):
    def test_header_fields_and_budget(self):
        header = [ln for ln in SCRIPT.read_text().splitlines()[1:14] if ln.startswith("#")]
        text = "\n".join(header)
        for field in ("WHAT", "WHEN", "INPUTS", "OUTPUT", "ASSUMPTIONS", "EXAMPLE"):
            self.assertIn(field, text)
        self.assertLessEqual(len(header), 12)

    def test_assumptions_name_the_unpaired_alternative(self):
        header = "\n".join(SCRIPT.read_text().splitlines()[1:14])
        self.assertIn("two-proportion", header)

    def test_header_example_runs(self):
        example = next(ln for ln in SCRIPT.read_text().splitlines() if "# EXAMPLE" in ln)
        cmd = example.split("EXAMPLE", 1)[1].strip().split()
        r = subprocess.run([sys.executable, str(ROOT / cmd[1]), *cmd[2:]],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertIn(r.returncode, (0, 3, 4, 5), r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
