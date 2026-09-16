import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from probe_short_budget import check, fragments, split_css
from probe_pdf_budget_reading import matrix, render
from generate_pilot_fixtures import IDS


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

    def test_autoescape_still_escapes_author_supplied_title(self):
        _, replies, _ = matrix()[0]
        costs = next(p for p in replies if p.endswith(IDS['costQUuid']))
        first = costs+'.'+replies[costs][0]
        replies[first+'.'+IDS['costCurrencyQUuid']] = ''
        replies[first+'.'+IDS['costTitleQUuid']] = '<b>Author title</b>'
        source = render(ROOT, replies, True, autoescape=True)
        self.assertIn('<table class="resource-table pdf-short-budget">', source)
        self.assertIn('&lt;b&gt;Author title&lt;/b&gt;', source)
        self.assertNotIn('<b>Author title</b>', source)
