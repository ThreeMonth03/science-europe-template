"""Selector scope and style-only spacing regression checks."""
import shutil
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from test_layout import module

ROOT = Path(__file__).resolve().parents[1]
SELECTOR = 'html body #q-required-resources .resource-table:has(tbody > tr > td:first-child > .answer-detail > :nth-child(12))'


def fixture(n=12, question='q-required-resources', table='resource-table', detail='answer-detail'):
    return '<html><body><div id="' + question + '"><table class="' + table + '"><tbody><tr><td><div class="' + detail + '">' + '<p>原始用途。</p>' * n + '</div></td><td>0 TWD</td><td>Funder.</td></tr></tbody></table></div></body></html>'


class BudgetSpacingTests(unittest.TestCase):
    def test_pdf_selector_matches_only_owned_long_purposes(self):
        self.assertIn(SELECTOR + ' { break-inside: auto; }', (ROOT / 'src/layout.css').read_text())
        for n in [0, 1, 11, 12, 60]:
            self.assertEqual(int(n >= 12), len(BeautifulSoup(fixture(n), 'html.parser').select(SELECTOR)))
        for args in [{'question': 'q-other'}, {'table': 'other-table'}, {'detail': 'other-detail'}]:
            self.assertFalse(BeautifulSoup(fixture(**args), 'html.parser').select(SELECTOR))
        # A nested table or funding prose must not masquerade as owned purpose.
        for html in [fixture().replace('<td><div', '<td><section><div').replace('</div></td>', '</div></section></td>'),
                     fixture().replace('<tr><td>', '<tr><td>Title.</td><td>', 1)]:
            self.assertFalse(BeautifulSoup(html, 'html.parser').select(SELECTOR))

    def test_only_long_budget_style_has_reduced_cell_margins(self):
        for language in ['en', 'zh-Hant']:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp); (path / 'src/word').mkdir(parents=True)
                for name in ['layout.css', 'word/reference.docx']:
                    shutil.copyfile(ROOT / 'src' / name, path / 'src' / name)
                font = path / 'font.ttf'; font.write_bytes(b'test font')
                module.prepare_layout(path, font, language)
                document = Document(path / 'src/word/reference.docx')
                for name, value in [('Table', '57'), ('Pilot Long Budget', '28')]:
                    style = document.styles[name].element
                    margins = style.find(qn('w:tcPr')).find(qn('w:tcMar'))
                    self.assertEqual(['top', 'bottom'], [node.tag.split('}')[1] for node in margins])
                    for node in margins:
                        self.assertEqual({qn('w:w'): value, qn('w:type'): 'dxa'}, dict(node.attrib))
                style = document.styles['Pilot Long Budget'].element
                self.assertIsNone(style.find(qn('w:pPr')))
                self.assertIsNone(style.find(qn('w:rPr')))
                self.assertEqual('nil', style.find('.//' + qn('w:insideH')).get(qn('w:val')))
                self.assertLess(list(style).index(style.find(qn('w:tcPr'))), list(style).index(style.find(qn('w:tblStylePr'))))
