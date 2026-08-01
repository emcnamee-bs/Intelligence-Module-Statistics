"""L2/L3/L4 tests for three_point_estimate_to_range.

The variance identity is the reason this model exists, so it is verified three independent ways:
symbolically against the general beta variance, numerically against a large Monte Carlo sample, and
against the R(delta) closed form at the two crossover points where the textbook formula is
accidentally correct. Nothing is taken from the research log on trust.
"""
import json
import random
import subprocess
import sys
import unittest
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "models" / "estimation" / "three_point_estimate_to_range.py"
sys.path.insert(0, str(ROOT))

from models.estimation.three_point_estimate_to_range import (  # noqa: E402
    pert_mean, pert_percentile, pert_shapes, pert_variance, variance_ratio,
)


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


class TestTheVarianceIdentity(unittest.TestCase):
    """(mu-a)(b-mu)/7 is the whole point. Verified from the general beta variance, not asserted."""

    def test_shapes_always_sum_to_six(self):
        for lo, m, hi in ((0, 0, 1), (0, 1, 1), (3, 6, 20), (4, 11, 18), (-5, 2.5, 9)):
            al, be = pert_shapes(lo, m, hi)
            self.assertAlmostEqual(al + be, 6.0, places=12, msg=f"{lo},{m},{hi}")

    def test_identity_matches_general_beta_variance(self):
        # Var of Beta(al,be) scaled to [lo,hi] is span^2 * al*be / ((al+be)^2 (al+be+1)).
        for lo, m, hi in ((0, 0.5, 1), (3, 6, 20), (4, 11, 18), (0, 0, 10), (0, 10, 10),
                          (-2, 0, 7), (100, 130, 900)):
            al, be = pert_shapes(lo, m, hi)
            span = hi - lo
            general = span ** 2 * al * be / ((al + be) ** 2 * (al + be + 1))
            self.assertAlmostEqual(pert_variance(lo, m, hi), general, places=10,
                                   msg=f"{lo},{m},{hi}")

    def test_identity_matches_monte_carlo(self):
        random.seed(20260731)
        lo, m, hi = 4.0, 11.0, 18.0
        al, be = pert_shapes(lo, m, hi)
        n = 400_000
        s = s2 = 0.0
        for _ in range(n):
            x = lo + (hi - lo) * random.betavariate(al, be)
            s += x
            s2 += x * x
        mc_var = s2 / n - (s / n) ** 2
        self.assertAlmostEqual(pert_mean(lo, m, hi), s / n, places=1)
        self.assertAlmostEqual(pert_variance(lo, m, hi), mc_var, delta=0.05)


class TestTheTextbookErrorIsReal(unittest.TestCase):
    """R(delta) = 5/7 + (16/7)d(1-d), equal to 1 at exactly two mode positions."""

    def test_ratio_closed_form_matches_computed_variance(self):
        for lo, m, hi in ((0, 0, 1), (0, 0.25, 1), (0, 0.5, 1), (0, 0.9, 1), (3, 6, 20)):
            textbook_var = ((hi - lo) / 6.0) ** 2
            self.assertAlmostEqual(variance_ratio(lo, m, hi),
                                   pert_variance(lo, m, hi) / textbook_var, places=12)

    def test_symmetric_mode_textbook_sd_is_11_8_percent_low(self):
        lo, m, hi = 0.0, 0.5, 1.0
        true_sd = sqrt(pert_variance(lo, m, hi))
        textbook = (hi - lo) / 6.0
        # Asserted against exact values, not rounded decimals: an earlier version compared to
        # -0.1180 at four places and failed on the true -0.118083 - a defect in the assertion,
        # not in the identity. At delta=0.5, R = 9/7 exactly.
        self.assertAlmostEqual(variance_ratio(lo, m, hi), 9.0 / 7.0, places=13)
        self.assertAlmostEqual(textbook / true_sd, sqrt(7.0 / 9.0), places=13)
        self.assertAlmostEqual(true_sd / textbook, sqrt(9.0 / 7.0), places=13)
        # The headline percentages, at the precision they are quoted.
        self.assertEqual(round((1 - textbook / true_sd) * 100, 1), 11.8)
        self.assertEqual(round((true_sd / textbook - 1) * 100, 1), 13.4)

    def test_crossover_points_are_where_textbook_is_exact(self):
        # d(1-d) = 1/8  =>  d = (1 +/- sqrt(0.5))/2
        for d in (0.1464466094, 0.8535533906):
            self.assertAlmostEqual(variance_ratio(0.0, d, 1.0), 1.0, places=8)

    def test_extreme_mode_textbook_sd_is_too_wide(self):
        # At d=0 or 1 the ratio is 5/7, so the textbook sd OVERSTATES by ~18.3%.
        for m in (0.0, 1.0):
            self.assertAlmostEqual(variance_ratio(0.0, m, 1.0), 5.0 / 7.0, places=12)
            true_sd = sqrt(pert_variance(0.0, m, 1.0))
            self.assertAlmostEqual((1 / 6.0) / true_sd - 1.0, 0.1832, places=3)

    def test_the_s5_baseline_scenario_is_a_weak_detector(self):
        """Documents why the recorded S5 scenario could not catch the bug it existed to catch.

        With 3/6/20 the mode sits at delta = 0.176, beside the crossover at 0.146, so the textbook
        formula is accidentally almost right and the error is ~2%. The re-specified scenario
        (4/11/18) sits near symmetry where the error is the full ~11%.
        """
        weak = abs((20 - 3) / 6.0 / sqrt(pert_variance(3, 6, 20)) - 1.0)
        strong = abs((18 - 4) / 6.0 / sqrt(pert_variance(4, 11, 18)) - 1.0)
        self.assertLess(weak, 0.03, "3/6/20 should barely show the error")
        self.assertGreater(strong, 0.10, "4/11/18 should show it clearly")


class TestPercentiles(unittest.TestCase):
    def test_are_ordered_and_inside_the_support(self):
        lo, m, hi = 4.0, 11.0, 18.0
        vals = [pert_percentile(lo, m, hi, q) for q in (0.05, 0.25, 0.5, 0.8, 0.95)]
        self.assertEqual(vals, sorted(vals))
        self.assertGreater(vals[0], lo)
        self.assertLess(vals[-1], hi)

    def test_symmetric_estimate_has_median_at_the_mode(self):
        self.assertAlmostEqual(pert_percentile(0.0, 0.5, 1.0, 0.5), 0.5, places=10)

    def test_right_skew_puts_mean_above_mode(self):
        lo, m, hi = 3.0, 6.0, 20.0
        self.assertGreater(pert_mean(lo, m, hi), m)


class TestOutcomes(unittest.TestCase):
    def test_normal_case_answers_with_caveat_about_the_textbook_formula(self):
        rc, out = run("-o", "4", "-m", "11", "-p", "18")
        self.assertEqual(rc, 0)
        self.assertIn("CAVEAT:", out)
        self.assertIn("too narrow", out)
        self.assertIn("REPORT AS:", out)

    def test_no_caveat_at_the_crossover_where_textbook_is_right(self):
        # delta ~ 0.1464 -> the textbook formula is correct, so warning about it would be noise.
        rc, out = run("-o", "0", "-m", "0.1464466", "-p", "1")
        self.assertEqual(rc, 0)
        self.assertNotIn("CAVEAT:", out)

    def test_misordered_estimates_refuse_with_no_result(self):
        rc, out = run("-o", "20", "-m", "6", "-p", "3")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_zero_range_refuses(self):
        rc, out = run("-o", "5", "-m", "5", "-p", "5")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_bad_percentile_refuses(self):
        rc, out = run("-o", "1", "-m", "2", "-p", "3", "--percentiles", "0,50")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_report_line_names_a_commit_value_not_just_the_mean(self):
        rc, out = run("-o", "3", "-m", "6", "-p", "20", "--unit", "weeks")
        report = next(ln for ln in out.splitlines() if ln.startswith("REPORT AS:"))
        self.assertIn("commit to", report)
        self.assertIn("weeks", report)

    def test_json_exposes_the_textbook_error(self):
        rc, out = run("-o", "4", "-m", "11", "-p", "18", "--json")
        d = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertLess(d["result"]["textbook_sd_error"], -0.10)
        self.assertIn("caveat", d)


class TestHeaderContract(unittest.TestCase):
    def test_header_fields_and_budget(self):
        lines = SCRIPT.read_text().splitlines()
        header = [ln for ln in lines[1:14] if ln.startswith("#")]
        text = "\n".join(header)
        for field in ("WHAT", "WHEN", "INPUTS", "OUTPUT", "ASSUMPTIONS", "EXAMPLE"):
            self.assertIn(field, text)
        self.assertLessEqual(len(header), 12)

    def test_header_example_runs(self):
        example = next(ln for ln in SCRIPT.read_text().splitlines() if "# EXAMPLE" in ln)
        cmd = example.split("EXAMPLE", 1)[1].strip().split()
        r = subprocess.run([sys.executable, str(ROOT / cmd[1]), *cmd[2:]],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertIn(r.returncode, (0, 3, 4, 5), r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
