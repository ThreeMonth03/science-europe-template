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
    def test_bounded_budget_spacing_and_fixed_lead_are_owned(self):
        css = (ROOT / 'src/layout.css').read_text()
        scoped = [line for line in css.splitlines() if line.startswith('html body #q-required-resources > .answer > .project-resources > table.resource-table.pdf-bounded-budget')]
        self.assertEqual([line.split(' {', 1)[1].lstrip() for line in scoped], [
            'margin: .3em 0; }', 'padding-top: .25em; padding-bottom: .25em; }',
            'margin-bottom: .2em; }', 'margin: .2em 0; }'])
        rule = next(line for line in css.splitlines() if line.startswith('html body #q-required-resources > .answer:has(table.resource-table.pdf-bounded-budget'))
        selector, properties = rule.split(' {', 1)
        self.assertEqual(properties.lstrip(), 'break-after: avoid; }')
        source = ('<html><body><div id="q-required-resources"><div class="answer">'
                  '<div class="answer-detail"><p>Training remains breakable.</p></div>'
                  '<p data-requirement-id="SE-6b" data-fact-id="hardware-software" data-status="explicit-no">Known hardware fact. '
                  '<span data-fact-id="repository-charges" data-status="complete">Known charge.</span></p>'
                  '<h4>Budget</h4><div class="project-resources"><table class="resource-table pdf-bounded-budget">'
                  '<tbody><tr><td>Original purpose.</td><td>0 TWD</td><td></td></tr></tbody></table></div>'
                  '</div></div></body></html>')
        self.assertEqual(len(BeautifulSoup(source, 'html.parser').select(selector)), 1)
        for invalid in [source.replace('q-required-resources', 'q-other'),
                        source.replace('pdf-bounded-budget', 'other-budget'),
                        source.replace('data-status="explicit-no"', 'data-status="partial"'),
                        source.replace('data-status="complete"', 'data-status="unknown"'),
                        source.replace('<h4>Budget</h4>', '<p>Intervening authored prose.</p><h4>Budget</h4>'),
                        source.replace('</table></div>', '</table><p>Extra authored prose.</p></div>'),
                        source.replace('</div></div></body>', '<div class="project-resources"></div></div></div></body>')]:
            self.assertFalse(BeautifulSoup(invalid, 'html.parser').select(selector))

    def test_terminal_training_spacing_is_local_and_keeps_long_answers_breakable(self):
        css = (ROOT / 'src/layout.css').read_text()
        lines = [line for line in css.splitlines() if line.endswith('{ padding-top: .3em; padding-bottom: .3em; }')]
        self.assertEqual(len(lines), 1)
        selector = lines[0].split(' {', 1)[0]
        self.assertIn(':has(thead > tr:only-child):has(tbody > tr:nth-child(2):last-child)', selector)
        self.assertIn(':not(:has(tr > :nth-child(3), tr > :only-child, tfoot, th *, td *, [colspan], [rowspan]))', selector)
        table = '<table><thead><tr><th>Training</th><th>Evidence</th></tr></thead><tbody><tr><td>Data stewardship</td><td>Reviewed plan</td></tr><tr><td>Record validation</td><td>0 unresolved checks</td></tr></tbody></table>'
        source = ('<html><body><div id="q-required-resources"><div class="answer">'
                  '<div class="answer-detail" data-fact-id="specialist-expertise-detail" data-status="complete">'
                  + table + '<ol><li>Preserve the original records.</li></ol><p>Keep the literal A&lt;B&amp;C&gt;D.</p></div>'
                  '<p data-requirement-id="SE-6b" data-fact-id="hardware-software" data-status="partial">Known hardware requirement.</p>'
                  '</div></div></body></html>')
        self.assertEqual(len(BeautifulSoup(source, 'html.parser').select(selector)), 6)
        for value in [source.replace('Keep the literal A&lt;B&amp;C&gt;D.', 'Long authored paragraph. ' * 1000),
                      source.replace('Reviewed plan', 'Long cell text. ' * 1000)]:
            self.assertEqual(len(BeautifulSoup(value, 'html.parser').select(selector)), 6)
        for value in [source.replace('q-required-resources', 'q-other'),
                      source.replace('data-status="partial"', 'data-status="complete"'),
                      source.replace('data-fact-id="specialist-expertise-detail"', 'data-fact-id="authored-other"'),
                      source.replace('</div></div></body>', '<p class="data-gap">Next fact.</p></div></div></body>'),
                      source.replace('<p data-requirement-id="SE-6b"', '<div class="answer-detail" data-requirement-id="SE-6b"').replace('Known hardware requirement.</p>', '<p>Long hardware details.</p></div>'),
                      source.replace('<td>Reviewed plan</td>', '<td><a href="https://example.org/">Original link</a></td>'),
                      source.replace('<td>Reviewed plan</td>', '<td colspan="2">Original span</td>'),
                      source.replace('</tbody>', '<tr><td>Next row</td><td>Keep</td></tr></tbody>'),
                      source.replace('<th>Evidence</th>', '<th>Evidence</th><th>Third column</th>'),
                      source.replace(table, '<div>' + table + '</div>')]:
            self.assertFalse(BeautifulSoup(value, 'html.parser').select(selector))
        # The new rules only change margins/padding: never bind a long free answer,
        # lock an authored table, change type size or alter the page geometry.
        scoped = [line for line in css.splitlines() if line.startswith('html body #q-required-resources > .answer > .answer-detail[data-fact-id="specialist-expertise-detail"]')]
        self.assertEqual(len(scoped), 3)
        self.assertEqual([line.split(' {', 1)[1].lstrip() for line in scoped],
                         ['margin-bottom: 0; }', 'margin-bottom: 0; }', 'padding-top: .3em; padding-bottom: .3em; }'])

    def test_list_closing_keep_is_scoped_without_locking_whole_resource(self):
        selector = ('html body #q-required-resources .resource-table > tbody > '
                    'tr[data-item-id] > td:first-child > '
                    '.answer-detail[data-fact-id="resource-justification"]:has(+ p:not(.data-gap)) > '
                    ':is(ol, ul) + p:last-child')
        css = (ROOT / 'src/layout.css').read_text()
        self.assertIn(selector + ' { break-before: avoid; }', css)
        for tag in ['ol', 'ul']:
            for closing in ['Retain original records.', '保留原始紀錄。']:
                source = ('<html><body><div id="q-required-resources"><table class="resource-table">'
                          '<tbody><tr data-item-id="resource-2"><td><strong>Resource 2</strong>'
                          '<div class="answer-detail" data-fact-id="resource-justification">'
                          '<p>Steps:</p><' + tag + '><li>' + ('Long item. ' * 150) + '</li></' + tag + '>'
                          '<p>' + closing + '</p></div><p>Allocation.</p></td>'
                          '<td>0 TWD</td><td>Funder.</td></tr></tbody></table></div></body></html>')
                soup = BeautifulSoup(source, 'html.parser')
                self.assertEqual([n.get_text() for n in soup.select(selector)], [closing])
                # No whole-row/list keep is introduced; only this final p matches.
                for absent in [source.replace('<p>Allocation.</p>', ''),
                               source.replace('<p>Allocation.</p>', '<p class="data-gap">Missing.</p>'),
                               source.replace('<p>Steps:</p><' + tag + '>', '<p>Steps:</p></div><div><' + tag + '>'),
                               source.replace('id="q-required-resources"', 'id="q-other"'),
                               source.replace('data-item-id="resource-2"', ''),
                               source.replace('<p>' + closing + '</p></div>', '<p>' + closing + '</p><p>More.</p></div>')]:
                    self.assertFalse(BeautifulSoup(absent, 'html.parser').select(selector))
                soup.select_one('.answer-detail').clear()
                soup.select_one('.answer-detail').append(soup.new_tag('p'))
                soup.select_one('.answer-detail > p').string = closing
                self.assertFalse(soup.select(selector))

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
