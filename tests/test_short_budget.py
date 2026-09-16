import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from probe_short_budget import check, fragments, split_css


class ShortBudgetTests(unittest.TestCase):
    def test_exact_fragments_and_fallbacks(self):
        rows = check(ROOT)
        self.assertEqual(len(rows), len(fragments())+6)
        self.assertEqual(len(rows), len({r['case'] for r in rows}))

    def test_only_owned_pdf_hint_changes_css(self):
        before, panel = split_css((ROOT/'src/layout.css').read_text())
        self.assertNotIn('.pdf-short-budget', before)
        self.assertNotIn('font-', panel)
        self.assertNotIn('line-height', panel)
        self.assertNotIn('break-', panel)
        self.assertEqual(panel.count('html body .pdf-short-budget'), 6)
