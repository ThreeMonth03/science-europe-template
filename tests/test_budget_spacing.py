"""Selector scope and style-only spacing regression checks."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from test_layout import module

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SELECTOR = 'html body .resource-table.pdf-bounded-budget, html body .resource-table.pdf-short-budget'


def fixture(n=12, question='q-required-resources', table='resource-table', detail='answer-detail'):
    return '<html><body><div id="' + question + '"><table class="' + table + '"><tbody><tr><td><div class="' + detail + '">' + '<p>原始用途。</p>' * n + '</div></td><td>0 TWD</td><td>Funder.</td></tr></tbody></table></div></body></html>'


class BudgetSpacingTests(unittest.TestCase):
    def test_native_probe_covers_current_hints_and_unbounded_controls(self):
        from probe_budget_pdf import cases
        rows = cases()
        self.assertEqual(len(rows), 22)
        self.assertEqual(len({name for name, _, _ in rows}), len(rows))
        for name, source, keep in rows:
            soup = BeautifulSoup(source, 'html.parser')
            self.assertEqual(len(soup.select('#budget-probe')), 1, name)
            self.assertEqual(len(soup.select(SELECTOR)), int(keep), name)
        by_name = {name: BeautifulSoup(source, 'html.parser') for name, source, _ in rows}
        for language, sentence in [('en', 'Retain original data.'), ('zh', '保留原始資料。')]:
            self.assertIn('pdf-bounded-budget', by_name[language+'-bounded'].table['class'])
            self.assertIn('pdf-short-budget', by_name[language+'-missing-amount'].table['class'])
            self.assertEqual(by_name[language+'-single-long-paragraph'].get_text().count(sentence), 150)
            self.assertEqual(by_name[language+'-many-paragraphs'].get_text().count(sentence), 16)

    def test_pdf_keep_requires_bounded_content_hint_not_just_row_count(self):
        css = (ROOT / 'src/layout.css').read_text()
        self.assertIn(SELECTOR + ' { break-inside: avoid; }', css)
        self.assertNotIn('.resource-table:has(tbody > tr:last-child:nth-child(-n+3))', css)
        self.assertIn('html body .resource-table tr { break-inside: auto; }', css)
        for table in ['resource-table pdf-bounded-budget', 'resource-table pdf-short-budget']:
            self.assertEqual(len(BeautifulSoup(fixture(table=table), 'html.parser').select(SELECTOR)), 1)
        for table in ['resource-table', 'other-table', 'pdf-bounded-budget']:
            self.assertFalse(BeautifulSoup(fixture(table=table), 'html.parser').select(SELECTOR))

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
