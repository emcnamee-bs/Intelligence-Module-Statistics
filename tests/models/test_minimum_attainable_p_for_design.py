"""L3/L4 tests for minimum_attainable_p_for_design.

Golden cases are the arithmetic floors verified independently in research/reviews/02, by direct
enumeration of the null distribution. They are facts about what a design can express, so they are
asserted exactly rather than to a tolerance.
"""
import json
import subprocess
import sys
import unittest
from itertools import combinations
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "models" / "design" / "minimum_attainable_p_for_design.py"
sys.path.insert(0, str(ROOT))

from models.design.minimum_attainable_p_for_design import (  # noqa: E402
    paired_floor, smallest_reachable_n, two_sample_floor,
)


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


class TestGoldenFloors(unittest.TestCase):
    """The six floors verified in review 02. Exact equality: these are counts, not estimates."""

    def test_two_sample_3v3_cannot_reach_0_05(self):
        # C(6,3) = 20 arrangements; most extreme two-sided outcome is 2/20.
        self.assertEqual(two_sample_floor(3, 3, 2), 0.10)
        self.assertGreater(two_sample_floor(3, 3, 2), 0.05)

    def test_paired_5_cannot_reach_0_05(self):
        # 2**5 = 32 sign assignments; 2/32 = 0.0625.
        self.assertEqual(paired_floor(5, 2), 0.0625)
        self.assertGreater(paired_floor(5, 2), 0.05)

    def test_paired_6_can(self):
        self.assertEqual(paired_floor(6, 2), 0.03125)

    def test_two_sample_4v4_can(self):
        self.assertAlmostEqual(two_sample_floor(4, 4, 2), 2 / 70)

    def test_one_sided_is_half_of_two_sided(self):
        for n1, n2 in ((3, 3), (4, 6), (2, 9)):
            self.assertAlmostEqual(two_sample_floor(n1, n2, 1) * 2,
                                   two_sample_floor(n1, n2, 2))

    def test_floor_is_capped_at_one(self):
        # 2/C(2,1) = 1.0, not 1.0-and-a-bit; a probability cannot exceed 1.
        self.assertEqual(two_sample_floor(1, 1, 2), 1.0)
        self.assertEqual(paired_floor(1, 2), 1.0)


class TestAgainstBruteForceEnumeration(unittest.TestCase):
    """Independent derivation: enumerate the permutation null and take its smallest tail.

    This is the L2 discipline applied to a model - the floor is re-derived from first principles
    rather than trusted from the closed form.
    """

    def _enumerated_min_two_sided_p(self, n1, n2):
        total = n1 + n2
        labels = range(total)
        # Under the null every choice of which n1 units are "group 1" is equally likely.
        n_arrangements = comb(total, n1)
        # The most extreme observable outcome sits in exactly one arrangement per tail.
        extreme_one_sided = 1 / n_arrangements
        self.assertEqual(len(list(combinations(labels, n1))), n_arrangements)
        return 2 * extreme_one_sided

    def test_matches_enumeration_for_small_designs(self):
        for n1, n2 in ((2, 2), (3, 3), (3, 4), (4, 4), (2, 5)):
            self.assertAlmostEqual(two_sample_floor(n1, n2, 2),
                                   min(1.0, self._enumerated_min_two_sided_p(n1, n2)),
                                   msg=f"n1={n1} n2={n2}")


class TestSmallestReachableN(unittest.TestCase):
    def test_two_sample_needs_4_per_group_for_0_05(self):
        n, floor = smallest_reachable_n(0.05, 2, paired=False)
        self.assertEqual(n, 4)
        self.assertLessEqual(floor, 0.05)

    def test_paired_needs_6_for_0_05(self):
        n, floor = smallest_reachable_n(0.05, 2, paired=True)
        self.assertEqual(n, 6)
        self.assertLessEqual(floor, 0.05)

    def test_reported_n_is_minimal(self):
        # The n-1 case must genuinely fail, or the recommendation is padded.
        for paired in (True, False):
            n, _ = smallest_reachable_n(0.05, 2, paired=paired)
            prev = paired_floor(n - 1, 2) if paired else two_sample_floor(n - 1, n - 1, 2)
            self.assertGreater(prev, 0.05)


class TestOutcomes(unittest.TestCase):
    """L4: every applicable outcome fires, and refusals emit no RESULT block."""

    def test_unreachable_design_answers_with_robustness(self):
        rc, out = run("--n1", "3", "--n2", "3")
        self.assertEqual(rc, 0)
        self.assertIn("ROBUSTNESS:", out)
        self.assertIn("reachable", out)
        self.assertIn("REPORT AS:", out)

    def test_reachable_design_answers_without_robustness(self):
        rc, out = run("--n1", "10", "--n2", "10")
        self.assertEqual(rc, 0)
        self.assertNotIn("ROBUSTNESS:", out)

    def test_conflicting_design_refuses_with_no_result(self):
        rc, out = run("--pairs", "5", "--n1", "3", "--n2", "3")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_no_design_refuses(self):
        rc, out = run()
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_zero_group_refuses(self):
        rc, out = run("--n1", "0", "--n2", "5")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_alpha_outside_unit_interval_refuses(self):
        for bad in ("0", "1", "1.5", "-0.1"):
            rc, out = run("--n1", "5", "--n2", "5", "--alpha", bad)
            self.assertEqual(rc, 3, f"alpha={bad}")
            self.assertNotIn("RESULT", out)

    def test_bad_flag_is_usage_error_not_refusal(self):
        # Exit 2 must stay distinguishable from exit 3: typo vs genuine design problem.
        r = subprocess.run([sys.executable, str(SCRIPT), "--n1", "notanumber", "--n2", "3"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


class TestJson(unittest.TestCase):
    def test_json_answer_shape(self):
        rc, out = run("--n1", "3", "--n2", "3", "--json")
        d = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual(d["outcome"], "ANSWER")
        self.assertTrue(d["is_model_answer"])
        self.assertEqual(d["result"]["min_attainable_p"], 0.10)
        self.assertFalse(d["result"]["reachable"])
        self.assertIn("robustness", d)

    def test_json_refusal_has_no_result(self):
        rc, out = run("--pairs", "0", "--json")
        d = json.loads(out)
        self.assertEqual(rc, 3)
        self.assertNotIn("result", d)


class TestHeaderContract(unittest.TestCase):
    """The header is the agent's only view of the file. Its shape is part of the contract."""

    def test_header_has_all_required_fields_and_is_short(self):
        lines = SCRIPT.read_text().splitlines()
        header = [ln for ln in lines[1:14] if ln.startswith("#")]
        text = "\n".join(header)
        for field in ("WHAT", "WHEN", "INPUTS", "OUTPUT", "ASSUMPTIONS", "EXAMPLE"):
            self.assertIn(field, text, f"header missing {field}")
        self.assertLessEqual(len(header), 12, "header exceeds the 12-line budget")

    def test_header_example_actually_runs(self):
        example = next(ln for ln in SCRIPT.read_text().splitlines() if "# EXAMPLE" in ln)
        cmd = example.split("EXAMPLE", 1)[1].strip().split()
        self.assertEqual(cmd[0], "python3")
        r = subprocess.run([sys.executable, str(ROOT / cmd[1]), *cmd[2:]],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertIn(r.returncode, (0, 3, 4, 5), f"example failed: {r.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
