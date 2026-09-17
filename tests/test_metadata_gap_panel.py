import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from metadata_gap_panel_contract import SELECTOR, prior_css, historical_css
from probe_metadata_gap_panel import branch_rows, cases
from storage_context_contract import without_reviewed_context
from probe_identifier_spacing import frozen_prepared_css, baseline, without_reviewed_archive_panels, CSS_BEGIN, CSS_END


class MetadataGapPanelTests(unittest.TestCase):
    def test_q13_prepared_gate_strips_only_exact_reviewed_later_additions(self):
        source = historical_css((ROOT / 'src/layout.css').read_text())
        prefix = '/* Simulated prepared font/profile prefix. */\n'
        expected = prefix + baseline(without_reviewed_archive_panels(without_reviewed_context(source, 'css')), CSS_BEGIN, CSS_END)
        self.assertEqual(frozen_prepared_css(prefix + source), expected)
        with self.assertRaises(AssertionError):
            frozen_prepared_css((prefix + source).replace('margin-bottom: .25em; }\n}\n/* END metadata gap', 'margin-bottom: .35em; }\n}\n/* END metadata gap'))
        self.assertNotEqual(frozen_prepared_css(prefix + source + '\n'), expected)

    def test_reachable_missing_no_and_unknown_branches(self):
        rows = list(branch_rows(ROOT))
        self.assertEqual(len(rows), 30)
        self.assertEqual(sum(selected for _, _, selected in rows), 4)
        for name, source, selected in rows + cases(ROOT):
            soup = BeautifulSoup('<html><body>' + source + '</body></html>', 'html.parser')
            self.assertEqual(len(soup.select(SELECTOR)), int(selected), name)

    def test_exact_delta_and_historic_gate(self):
        source = historical_css((ROOT / 'src/layout.css').read_text())
        before = prior_css(source)
        self.assertNotIn('BEGIN metadata gap panel:', before)
        without_reviewed_context(source, 'css')
        with self.assertRaises(AssertionError):
            prior_css(source.replace('margin-bottom: .25em; }\n}\n/* END metadata gap', 'margin-bottom: .35em; }\n}\n/* END metadata gap'))
        with self.assertRaises(AssertionError):
            without_reviewed_context(source + '\n', 'css')
