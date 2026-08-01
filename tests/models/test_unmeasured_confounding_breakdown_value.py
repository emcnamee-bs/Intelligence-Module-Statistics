"""L2/L3/L4 tests for unmeasured_confounding_breakdown_value.

The E-value is verified by solving its defining equation numerically rather than by asserting the
closed form against itself: E is the value at which the Ding-VanderWeele bounding factor
E^2/(2E-1) equals the observed risk ratio. Recovering E by bisection on that equation is an
independent derivation, so a transcription error in the closed form would be caught.
"""
import json
import subprocess
import sys
import unittest
from math import exp, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "models" / "causal" / "unmeasured_confounding_breakdown_value.py"
sys.path.insert(0, str(ROOT))

from models.causal.unmeasured_confounding_breakdown_value import (  # noqa: E402
    e_value, e_value_for_limit,
)


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def bounding_factor(e: float) -> float:
    """Ding-VanderWeele bound when both confounder associations equal e."""
    return e * e / (2 * e - 1)


def e_by_bisection(rr: float) -> float:
    """Solve bounding_factor(E) = rr for E >= 1, independently of the closed form."""
    if rr < 1.0:
        rr = 1.0 / rr
    lo, hi = 1.0, 1e9
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if bounding_factor(mid) < rr:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


class TestEValueAgainstItsDefiningEquation(unittest.TestCase):
    def test_closed_form_solves_the_bounding_equation(self):
        for rr in (1.01, 1.1, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0, 40.0):
            e = e_value(rr)
            self.assertAlmostEqual(bounding_factor(e), rr, places=9, msg=f"RR={rr}")

    def test_closed_form_matches_independent_bisection(self):
        for rr in (1.05, 1.5, 2.0, 3.0, 7.5, 25.0):
            self.assertAlmostEqual(e_value(rr), e_by_bisection(rr), places=7, msg=f"RR={rr}")

    def test_spot_values_derived_not_recalled(self):
        """Each target is written as the arithmetic that produces it, not as a remembered decimal.

        An earlier version of this test listed these as "published reference values" and gave
        1.807 for RR=1.25. The correct value is 1.25 + sqrt(0.3125) = 1.809017 - a constant
        recalled wrongly, which is exactly the failure mode that made "no number ships unverified"
        a project rule (RESEARCH.md 3.15). Writing the derivation in place of the decimal makes
        that error unavailable.
        """
        for rr in (1.25, 1.5, 2.0, 3.0):
            want = rr + sqrt(rr * (rr - 1.0))
            self.assertAlmostEqual(e_value(rr), want, places=12, msg=f"RR={rr}")
        # The widely-quoted pair, at the precision it is usually quoted.
        self.assertEqual(round(e_value(2.0), 2), 3.41)
        self.assertEqual(round(e_value(1.25), 3), 1.809)

    def test_null_gives_unity(self):
        self.assertEqual(e_value(1.0), 1.0)

    def test_symmetric_about_the_null(self):
        # An effect and its reciprocal are equally fragile.
        for rr in (1.5, 2.0, 4.0):
            self.assertAlmostEqual(e_value(rr), e_value(1.0 / rr), places=12)

    def test_monotone_in_effect_size(self):
        prev = 0.0
        for i in range(1, 200):
            v = e_value(1.0 + i / 20)
            self.assertGreater(v, prev)
            prev = v

    def test_e_value_always_exceeds_the_risk_ratio(self):
        # sqrt(RR(RR-1)) > 0 for RR > 1, so the confounder must be stronger than the effect itself.
        for rr in (1.2, 2.0, 6.0):
            self.assertGreater(e_value(rr), rr)


class TestConfidenceLimits(unittest.TestCase):
    def test_interval_crossing_the_null_gives_unity(self):
        self.assertEqual(e_value_for_limit(0.9, 1.6), 1.0)   # protective limit, harmful estimate
        self.assertEqual(e_value_for_limit(1.1, 0.7), 1.0)   # harmful limit, protective estimate

    def test_interval_excluding_the_null_uses_the_limit(self):
        self.assertAlmostEqual(e_value_for_limit(1.2, 2.0), e_value(1.2), places=12)

    def test_ci_e_value_never_exceeds_the_point_e_value(self):
        for est, lo in ((2.0, 1.2), (3.0, 2.5), (1.4, 1.05)):
            self.assertLessEqual(e_value_for_limit(lo, est), e_value(est) + 1e-12)


class TestScaleConversions(unittest.TestCase):
    def test_rare_odds_ratio_is_used_directly(self):
        rc, out = run("--or", "2.0", "--rare", "--json")
        d = json.loads(out)
        self.assertAlmostEqual(d["result"]["risk_ratio_used"], 2.0, places=12)

    def test_common_odds_ratio_uses_square_root(self):
        rc, out = run("--or", "4.0", "--json")
        d = json.loads(out)
        self.assertAlmostEqual(d["result"]["risk_ratio_used"], 2.0, places=12)

    def test_standardized_mean_difference_uses_chinn(self):
        rc, out = run("--smd", "0.5", "--json")
        d = json.loads(out)
        self.assertAlmostEqual(d["result"]["risk_ratio_used"], exp(0.91 * 0.5), places=12)

    def test_hazard_ratio_of_one_maps_to_risk_ratio_of_one(self):
        # The HR conversion must be continuous at the null, or the UNANSWERABLE branch misfires.
        rc, out = run("--hr", "1.0")
        self.assertEqual(rc, 4)


class TestOutcomes(unittest.TestCase):
    def test_normal_case_answers_with_robustness(self):
        rc, out = run("--rr", "2.0")
        self.assertEqual(rc, 0)
        self.assertIn("ROBUSTNESS:", out)
        self.assertIn("3.41", out)

    def test_exact_null_is_unanswerable_with_no_result(self):
        rc, out = run("--rr", "1.0")
        self.assertEqual(rc, 4)
        self.assertNotIn("RESULT", out)
        self.assertIn("UNANSWERABLE:", out)
        self.assertIn("ASK INSTEAD:", out)

    def test_interval_including_null_is_reported_not_hidden(self):
        rc, out = run("--rr", "1.6", "--ci-low", "0.9", "--ci-high", "2.8")
        self.assertEqual(rc, 0)
        self.assertIn("already includes the null", out)

    def test_nonpositive_ratio_refuses(self):
        for flag, val in (("--rr", "0"), ("--rr", "-1.5"), ("--or", "0")):
            rc, out = run(flag, val)
            self.assertEqual(rc, 3, f"{flag} {val}")
            self.assertNotIn("RESULT", out)

    def test_rare_without_odds_ratio_refuses(self):
        rc, out = run("--rr", "2.0", "--rare")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_half_an_interval_refuses(self):
        rc, out = run("--rr", "2.0", "--ci-low", "1.2")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_reversed_interval_refuses(self):
        rc, out = run("--rr", "2.0", "--ci-low", "2.5", "--ci-high", "1.2")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_two_effect_measures_is_a_usage_error_not_a_refusal(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--rr", "2", "--or", "3"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_report_line_tells_the_agent_what_to_compare_against(self):
        rc, out = run("--rr", "2.0")
        report = next(ln for ln in out.splitlines() if ln.startswith("REPORT AS:"))
        self.assertIn("measured covariate", report)


class TestHeaderContract(unittest.TestCase):
    def test_header_fields_and_budget(self):
        header = [ln for ln in SCRIPT.read_text().splitlines()[1:14] if ln.startswith("#")]
        text = "\n".join(header)
        for field in ("WHAT", "WHEN", "INPUTS", "OUTPUT", "ASSUMPTIONS", "EXAMPLE"):
            self.assertIn(field, text)
        self.assertLessEqual(len(header), 12)

    def test_assumptions_name_what_the_e_value_does_not_cover(self):
        # The commonest misuse is reading it as robustness to all bias, not just confounding.
        header = "\n".join(SCRIPT.read_text().splitlines()[1:14])
        self.assertIn("selection bias", header)

    def test_header_example_runs(self):
        example = next(ln for ln in SCRIPT.read_text().splitlines() if "# EXAMPLE" in ln)
        cmd = example.split("EXAMPLE", 1)[1].strip().split()
        r = subprocess.run([sys.executable, str(ROOT / cmd[1]), *cmd[2:]],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertIn(r.returncode, (0, 3, 4, 5), r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
