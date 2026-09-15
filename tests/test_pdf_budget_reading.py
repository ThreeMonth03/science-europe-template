import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from probe_pdf_budget_reading import check, matrix, normalize_owned_allocation_indent


class PdfBudgetReadingTests(unittest.TestCase):
    def test_only_owned_allocation_outer_space_is_normalized(self):
        source = '<table class="resource-table"><tbody><tr><td><div class="answer-detail"><p>  支援項目：原始  文字。  </p></div><p>\n 支援項目：資料管理。\n</p></td></tr></tbody></table>'
        result = normalize_owned_allocation_indent(source)
        self.assertIn('<p>  支援項目：原始  文字。  </p>', result)
        self.assertIn('<p>支援項目：資料管理。</p>', result)

    def test_fragments_scopes_and_historic_non_pdf_output(self):
        result = check(ROOT, (ROOT/'tests/fixtures/budget-0.3.18.html.j2').read_text())
        self.assertEqual(32, len(result)); self.assertEqual(32, len({name for name, _, _ in matrix()}))

    def test_only_pdf_uses_the_pdf_entry(self):
        formats = json.loads((ROOT/'template.json').read_text())['formats']
        for fmt in formats:
            template = fmt['steps'][0]['options']['template']
            self.assertEqual(template == 'src/pdf/index.html.j2', fmt['name'] == 'PDF Document')
