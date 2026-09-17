import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from metadata_gap_panel_contract import SELECTOR, prior_css
from probe_metadata_gap_panel import branch_rows, cases
from storage_context_contract import without_reviewed_context


class MetadataGapPanelTests(unittest.TestCase):
    def test_reachable_missing_no_and_unknown_branches(self):
        rows = list(branch_rows(ROOT))
        self.assertEqual(len(rows), 30)
        self.assertEqual(sum(selected for _, _, selected in rows), 4)
        for name, source, selected in rows + cases(ROOT):
            soup = BeautifulSoup('<html><body>' + source + '</body></html>', 'html.parser')
            self.assertEqual(len(soup.select(SELECTOR)), int(selected), name)

    def test_exact_delta_and_historic_gate(self):
        source = (ROOT / 'src/layout.css').read_text()
        before = prior_css(source)
        self.assertNotIn('BEGIN metadata gap panel:', before)
        without_reviewed_context(source, 'css')
        with self.assertRaises(AssertionError):
            prior_css(source.replace('margin-bottom: .25em; }\n}\n/* END metadata gap', 'margin-bottom: .35em; }\n}\n/* END metadata gap'))
        with self.assertRaises(AssertionError):
            without_reviewed_context(source + '\n', 'css')
