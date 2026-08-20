import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bot.score import score_job  # noqa: E402


class TitleRelevanceGateTests(unittest.TestCase):
    """Regression test: a job with a disclosed salary above the floor (or a
    company matched as mega-cap) used to pass the skip filter regardless of
    whether the title had anything to do with program management -- e.g.
    "Head of Marketing & Communications" with a $150k-$230k salary sailed
    through untouched. score_job() must skip on title irrelevance first,
    before salary/company logic ever runs."""

    def test_unrelated_title_with_high_disclosed_salary_is_skipped(self):
        _, skip = score_job("Head of Marketing & Communications", "garden3d", "", "$150k - $230k")
        self.assertTrue(skip)

    def test_unrelated_title_at_mega_cap_is_skipped(self):
        _, skip = score_job("Head of Marketing & Communications", "Google", "", "")
        self.assertTrue(skip)

    def test_unrelated_title_with_salary_looking_text_in_description_is_skipped(self):
        # A JD that happens to mention a dollar figure (revenue, contract
        # value, product price -- not compensation) must not accidentally
        # look like a passing salary match for an unrelated role.
        _, skip = score_job("SaaS Product Support Jedi", "Creative Force",
                             "Our platform processes over $150,000 in transactions daily.", "")
        self.assertTrue(skip)

    def test_relevant_title_with_salary_above_floor_is_not_skipped(self):
        _, skip = score_job("Senior Technical Program Manager", "Acme Corp", "", "$180,000")
        self.assertFalse(skip)

    def test_relevant_title_without_salary_at_mega_cap_is_not_skipped(self):
        _, skip = score_job("Staff TPM", "Google", "", "")
        self.assertFalse(skip)

    def test_relevant_title_without_salary_not_mega_cap_is_skipped(self):
        _, skip = score_job("Technical Program Manager", "Some Startup Inc", "", "")
        self.assertTrue(skip)

    def test_relevant_title_with_below_floor_salary_is_skipped(self):
        _, skip = score_job("Technical Program Manager", "Acme Corp", "", "$90,000")
        self.assertTrue(skip)

    def test_generic_program_manager_title_still_passes_gate(self):
        # "program manager" is a legitimate, if lower-scored, TITLE_KEYWORDS
        # match -- must not be swept up by the irrelevance gate.
        _, skip = score_job("Program Manager", "Acme Corp", "", "$160,000")
        self.assertFalse(skip)


if __name__ == "__main__":
    unittest.main()
