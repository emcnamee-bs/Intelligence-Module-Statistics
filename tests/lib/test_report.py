"""L1 tests for the output contract.

The contract is the project's load-bearing safety property: when a number would mislead, no number is
printed and the exit code says so unmissably. Agents have been observed reporting numbers their tools
flagged as unreliable (RESEARCH.md 0.3), so these are structural tests, not style checks.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lib.report import (  # noqa: E402
    ANSWER, REFUSED, UNANSWERABLE, USE_SIMPLER,
    answer, refused, unanswerable, use_simpler, render, fmt,
)


class TestExitCodes(unittest.TestCase):
    """Every outcome whose printed number is NOT the model's own answer gets a distinct code."""

    def test_codes_are_the_specified_values(self):
        self.assertEqual(ANSWER.code, 0)
        self.assertEqual(REFUSED.code, 3)
        self.assertEqual(UNANSWERABLE.code, 4)
        self.assertEqual(USE_SIMPLER.code, 5)

    def test_no_outcome_collides_with_argparse(self):
        # argparse exits 2 on bad arguments. Overloading it would make "you typed the flag wrong"
        # indistinguishable from "your data violates the model" - opposite required responses.
        for o in (ANSWER, REFUSED, UNANSWERABLE, USE_SIMPLER):
            self.assertNotEqual(o.code, 2, f"{o.name} collides with argparse")

    def test_use_simpler_is_not_zero(self):
        # The review finding: `if rc == 0: use the number` must never yield a baseline's answer
        # carrying the module's authority.
        self.assertNotEqual(USE_SIMPLER.code, ANSWER.code)


class TestNoNumberWhenNumberWouldMislead(unittest.TestCase):
    """REFUSED and UNANSWERABLE must not emit a RESULT block. Structural, not advisory."""

    def test_refused_has_no_result_block(self):
        out = render(refused(
            model="Two-proportion comparison",
            violation="b_success (12) exceeds b_total (10)",
            why_it_matters="The inputs are inconsistent, so any posterior would be meaningless.",
            do_instead="Re-check which number is the denominator, then re-run.",
        ))
        self.assertNotIn("RESULT", out)
        self.assertIn("REFUSED:", out)
        self.assertIn("REPORT AS:", out)

    def test_unanswerable_has_no_result_block(self):
        out = render(unanswerable(
            model="Give-up threshold",
            why="Under decreasing hazard the optimal policy is degenerate: never abandon.",
            ask_instead="Ask what the hazard shape is, then whether it is decreasing.",
        ))
        self.assertNotIn("RESULT", out)
        self.assertIn("UNANSWERABLE:", out)

    def test_refused_cannot_be_constructed_with_a_result(self):
        # Structural guarantee: the constructor has no result parameter at all, so no code path
        # can smuggle a headline number into a refusal.
        with self.assertRaises(TypeError):
            refused(model="m", violation="v", why_it_matters="w",
                    do_instead="d", result={"estimate": 0.5})


class TestUseSimplerLabelsItsSource(unittest.TestCase):
    def test_output_names_the_simpler_answer_as_not_the_models(self):
        out = render(use_simpler(
            model="Damped trend forecast",
            simpler_name="the naive forecast (last observed value)",
            simpler_result={"forecast": 41.0},
            why="MASE 1.08 - the model does not beat the naive forecast on this series.",
        ))
        self.assertIn("USE_SIMPLER", out)
        self.assertIn("naive forecast", out)
        # The number must be attributed, so it cannot be transcribed as the model's output.
        self.assertIn("NOT the model's", out)


class TestReportAsIsMandatory(unittest.TestCase):
    """REPORT AS converts interpretation into transcription - the counter to observed misreporting."""

    def test_every_outcome_emits_report_as(self):
        outs = [
            answer(model="m", result={"x": 1.0}, report_as="X is one."),
            refused(model="m", violation="v", why_it_matters="w", do_instead="d"),
            unanswerable(model="m", why="w", ask_instead="a"),
            use_simpler(model="m", simpler_name="n", simpler_result={"x": 1.0}, why="w"),
        ]
        for o in outs:
            self.assertIn("REPORT AS:", render(o), f"{o.outcome.name} missing REPORT AS")

    def test_answer_requires_a_nonempty_report_as(self):
        with self.assertRaises(ValueError):
            answer(model="m", result={"x": 1.0}, report_as="   ")


class TestAnnotations(unittest.TestCase):
    """CAVEAT and ROBUSTNESS annotate ANSWER; they are not separate outcomes."""

    def test_annotations_do_not_change_the_exit_code(self):
        a = answer(model="m", result={"x": 1.0}, report_as="r",
                   caveat="Wide interval at n=5.", robustness="Overturned only if bias > 0.3.")
        self.assertEqual(a.outcome.code, 0)
        out = render(a)
        self.assertIn("CAVEAT:", out)
        self.assertIn("ROBUSTNESS:", out)

    def test_absent_annotations_are_omitted_entirely(self):
        out = render(answer(model="m", result={"x": 1.0}, report_as="r"))
        self.assertNotIn("CAVEAT:", out)
        self.assertNotIn("ROBUSTNESS:", out)


class TestJson(unittest.TestCase):
    def test_every_outcome_serialises_with_outcome_and_report_as(self):
        for o in (
            answer(model="m", result={"x": 1.0}, report_as="r"),
            refused(model="m", violation="v", why_it_matters="w", do_instead="d"),
            unanswerable(model="m", why="w", ask_instead="a"),
            use_simpler(model="m", simpler_name="n", simpler_result={"x": 1.0}, why="w"),
        ):
            d = json.loads(render(o, as_json=True))
            self.assertIn("outcome", d)
            self.assertIn("report_as", d)
            self.assertIn("exit_code", d)
            self.assertEqual(d["exit_code"], o.outcome.code)

    def test_refused_json_carries_no_result_key(self):
        d = json.loads(render(refused(model="m", violation="v", why_it_matters="w",
                                      do_instead="d"), as_json=True))
        self.assertNotIn("result", d)

    def test_use_simpler_json_marks_the_source(self):
        d = json.loads(render(use_simpler(model="m", simpler_name="naive",
                                          simpler_result={"x": 1.0}, why="w"), as_json=True))
        self.assertEqual(d["result_source"], "naive")
        self.assertFalse(d["is_model_answer"])

    def test_answer_json_marks_itself_as_the_model_answer(self):
        d = json.loads(render(answer(model="m", result={"x": 1.0}, report_as="r"), as_json=True))
        self.assertTrue(d["is_model_answer"])


class TestNumberFormatting(unittest.TestCase):
    """The rule: three significant figures, never fewer digits than the integer part requires.

    One rule, no special cases. An earlier draft of these tests encoded two different implicit
    rules (three decimals for large values, two significant figures for small ones) with no
    principle behind either; the expectations below state the rule instead.
    """

    def test_three_significant_figures(self):
        self.assertEqual(fmt(0.1 + 0.2), "0.3")      # float noise suppressed
        self.assertEqual(fmt(1 / 3), "0.333")

    def test_integer_part_is_never_truncated(self):
        # 12345.6789 must not become "12300". Losing 0.68 of 12345 is fine; losing 45 is not.
        self.assertEqual(fmt(12345.6789), "12346")
        self.assertEqual(fmt(1200.0), "1200")

    def test_small_probabilities_keep_resolution(self):
        # A p-value of 0.002386 must not collapse to "0.002" - the difference carries an argument.
        self.assertEqual(fmt(0.002386), "0.00239")
        self.assertEqual(fmt(1.7e-05), "1.7e-05")

    def test_integers_and_bools_survive_intact(self):
        self.assertEqual(fmt(4), "4")
        self.assertEqual(fmt(True), "true")
        self.assertEqual(fmt(False), "false")

    def test_intervals_render_as_pairs(self):
        self.assertEqual(fmt([0.021, 0.281]), "[0.021, 0.281]")


class TestEmitExitsWithTheOutcomeCode(unittest.TestCase):
    """End-to-end: a script using emit() must actually exit with the contract's code."""

    def _run(self, snippet):
        code = (
            "import sys; sys.path.insert(0, %r)\n" % str(ROOT)
            + "from lib.report import *\n" + snippet
        )
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    def test_answer_exits_zero(self):
        r = self._run("emit(answer(model='m', result={'x':1.0}, report_as='r'))")
        self.assertEqual(r.returncode, 0)

    def test_refused_exits_three_and_prints_no_result(self):
        r = self._run("emit(refused(model='m', violation='v', why_it_matters='w', do_instead='d'))")
        self.assertEqual(r.returncode, 3)
        self.assertNotIn("RESULT", r.stdout)

    def test_unanswerable_exits_four(self):
        r = self._run("emit(unanswerable(model='m', why='w', ask_instead='a'))")
        self.assertEqual(r.returncode, 4)

    def test_use_simpler_exits_five(self):
        r = self._run(
            "emit(use_simpler(model='m', simpler_name='n', simpler_result={'x':1.0}, why='w'))")
        self.assertEqual(r.returncode, 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
