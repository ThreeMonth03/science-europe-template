"""Business/version dates stay; export timestamps never enter active outputs."""
from pathlib import Path
import re
import sys
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_project_acronym import fixture
from current_support import environment


class DocumentMetadataTests(unittest.TestCase):
    WORKSPACE = 'Workspace <label> & internal'
    PROJECT = 'Coastal <study> & observations'
    VERSION = 'Approved <v2> & checked'
    PHASE = 'Before final project end'

    def render(self, entry, name=PROJECT, escape=False, phase='phase-end', profile=None,
               versions=None, document_created_at='1999-12-31T23:59:00Z', trace_fields=None):
        km, replies = fixture(None, name)
        km['entities']['phases'] = {'phase-end': {'title': self.PHASE}}
        if versions is None:
            versions = [dict(uuid='selected', name=self.VERSION,
                description='Checked revision.', created_at='2001-02-03T00:00:00Z')]
        dc = dict(project=dict(name=self.WORKSPACE, versions=versions),
            document=dict(created_at=document_created_at),
            pkg=dict(name='MODEL-TRACE', version='2.7.0', organization_id='dsw', km_id='root'),
            config=dict(service_name='SERVICE-TRACE', service_url='https://example.org/tool'))
        for section, values in (trace_fields or {}).items():
            dc[section].update(values)
        # Mirror the worker timestamp and its to_context_obj view above.
        ctx = dict(knowledgeModel=km, project=dict(name=self.WORKSPACE, replies=replies,
            versionUuid='selected'), document=dict(createdAt=document_created_at), report={}, phaseUuid=phase)
        env = environment(ROOT, escape, {'src/style.css': '', 'src/layout.css': ''})
        env.filters['to_context_obj'] = lambda value: dc
        env.filters['datetime_format'] = lambda value, fmt: value.split('T')[0]
        values = dict(ctx=ctx)
        if profile is not None:
            values['output_profile'] = profile
        return BeautifulSoup(env.get_template(entry).render(**values), 'html.parser')

    def test_submission_has_business_title_and_version_without_system_trace(self):
        for entry in ('src/submission/pdf.html.j2', 'src/submission/word.html.j2'):
            for escape in (False, True):
                with self.subTest(entry=entry, escape=escape):
                    soup = self.render(entry, escape=escape)
                    self.assertEqual(self.PROJECT, soup.header.h1.get_text())
                    self.assertIn(self.VERSION, soup.header.get_text())
                    self.assertIn('2001-02-03', soup.header.get_text())
                    history = soup.select_one('table.version-history' if 'word' in entry
                                              else '#dmp-versions > table')
                    self.assertIsNotNone(history)
                    self.assertIn('Checked revision.', history.get_text())
                    self.assertEqual('Data Management Plan', soup.title.get_text())
                    self.assertFalse(soup.select('.document-provenance, #dmp-provenance'))
                    for trace in (self.WORKSPACE, '1999-12-31', self.PHASE,
                                  'MODEL-TRACE', 'SERVICE-TRACE', 'Generated on', 'Created on'):
                        self.assertNotIn(trace, soup.get_text())
                    self.assertEqual(15, len(soup.select('.question > h3')))
                    self.assertFalse(soup.header.select('study, v2, script, img'))

    def test_review_trace_is_after_questionnaire_with_optional_phase(self):
        for entry in ('src/pdf/index.html.j2', 'src/word/index.html.j2'):
            for profile in (None, 'review', 'unknown'):
                for phase in ('phase-end', 'missing-phase', None):
                    with self.subTest(entry=entry, profile=profile, phase=phase):
                        soup = self.render(entry, escape=True, phase=phase, profile=profile)
                        tracking = soup.select_one('aside.document-provenance')
                        self.assertIsNotNone(tracking)
                        self.assertIs(tracking.find_previous('div', class_='question'),
                                      soup.select('.question')[-1])
                        text = tracking.get_text()
                        for trace in (self.WORKSPACE, 'MODEL-TRACE', 'SERVICE-TRACE'):
                            self.assertIn(trace, text)
                        for export_trace in ('1999-12-31', 'Generated on', 'Created on'):
                            self.assertNotIn(export_trace, soup.get_text())
                        self.assertEqual(phase == 'phase-end', self.PHASE in text)
                        self.assertNotIn(self.WORKSPACE, soup.header.get_text())
                        self.assertNotIn('1999-12-31', soup.header.get_text())
                        self.assertNotIn(self.PHASE, soup.header.get_text())
                        self.assertEqual('Data Management Plan', soup.title.get_text())
                        self.assertFalse(tracking.select('label, script, img'))

    def test_named_version_dates_and_real_change_history_survive_both_profiles(self):
        versions = [
            dict(uuid='previous', name='Draft v1', created_at='2000-01-02T00:00:00Z',
                 description='Initial data plan.'),
            dict(uuid='selected', name='Approved v2', created_at='2001-02-03T00:00:00Z',
                 description='Approved retention changes.'),
        ]
        expected = [['Approved v2', '2001-02-03', 'Approved retention changes.'],
                    ['Draft v1', '2000-01-02', 'Initial data plan.']]
        for entry in ('src/index.html.j2', 'src/pdf/index.html.j2', 'src/word/index.html.j2'):
            for profile in ('review', 'submission'):
                for escape in (False, True):
                    with self.subTest(entry=entry, profile=profile, escape=escape):
                        soup = self.render(entry, profile=profile, escape=escape, versions=versions)
                        self.assertEqual('Version: Approved v2 (2001-02-03)',
                                         soup.header.select_one('.document-meta').get_text())
                        history = soup.select_one('table.version-history' if 'word' in entry
                                                  else '#dmp-versions > table')
                        self.assertIsNotNone(history)
                        self.assertEqual(expected, [[cell.get_text(strip=True) for cell in row.select('td')]
                                                    for row in history.select('tbody > tr')])

    def test_export_timestamp_never_changes_active_outputs_or_supplies_a_version_date(self):
        entries = ('src/index.html.j2', 'src/pdf/index.html.j2', 'src/word/index.html.j2',
                   'src/submission/index.html.j2', 'src/submission/pdf.html.j2',
                   'src/submission/word.html.j2')
        timestamps = ('1999-12-31T23:59:00Z', '2042-06-07T08:09:10Z')
        for entry in entries:
            profile = 'submission' if '/submission/' in entry else 'review'
            for escape in (False, True):
                for versions in (None, []):
                    with self.subTest(entry=entry, profile=profile, escape=escape,
                                      named_version=versions is None):
                        documents = [self.render(entry, profile=profile, escape=escape,
                            versions=versions, document_created_at=stamp) for stamp in timestamps]
                        self.assertEqual(str(documents[0]), str(documents[1]))
                        for soup in documents:
                            for export_trace in ('1999-12-31', '2042-06-07', 'Generated on', 'Created on'):
                                self.assertNotIn(export_trace, soup.get_text())
                            if versions == []:
                                self.assertFalse(soup.select('.document-meta, #dmp-versions, table.version-history'))
                                self.assertNotIn('History of changes', soup.get_text())

    def test_missing_project_title_uses_generic_cover_not_workspace_fallback(self):
        for entry in ('src/pdf/index.html.j2', 'src/word/index.html.j2',
                      'src/submission/pdf.html.j2', 'src/submission/word.html.j2'):
            for name in (None, '', ' \t\n\u3000'):
                for escape in (False, True):
                    with self.subTest(entry=entry, name=name, escape=escape):
                        soup = self.render(entry, name=name, escape=escape)
                        self.assertEqual('Data Management Plan', soup.header.h1.get_text())
                        self.assertIsNone(soup.header.select_one('.document-kind'))
                        self.assertNotIn(self.WORKSPACE, soup.header.get_text())
                        self.assertIn(self.VERSION, soup.header.get_text())

    def test_pdf_empty_cover_release_requires_all_owned_sections_and_questions(self):
        sections = {
            'sec-data-collection': ['q-how-data', 'q-what-data'],
            'sec-docs-metadata': ['q-docs-metadata', 'q-quality-control'],
            'sec-storage-backup': ['q-store-backup', 'q-access-security'],
            'sec-ethics-legal': ['q-personal-data', 'q-copyright-ipr', 'q-ethical-issues'],
            'sec-sharing-preservation': ['q-share-restrictions', 'q-data-preservation', 'q-access-data', 'q-persistent-identifier'],
            'sec-responsibilities-resources': ['q-dm-responsible', 'q-required-resources'],
        }
        content = ''.join('<section id="' + sid + '" class="dmp-section"><h2>Original section</h2>' +
            ''.join('<div id="' + qid + '" class="question compact-empty-question"><h3>Original question</h3>'
                    '<div class="answer"></div></div>' for qid in questions) + '</section>'
            for sid, questions in sections.items())
        original = '<html><body><article class="dmp"><div id="dmp-content">' + content + '</div></article></body></html>'
        question = '<div id="q-how-data" class="question compact-empty-question">'
        variants = {
            'complete': (original, True),
            'one-unmarked': (original.replace(question, question.replace(' compact-empty-question', ''), 1), False),
            'unknown-question': (original.replace('id="q-how-data"', 'id="q-unknown"', 1), False),
            'missing-question': (original.replace(question + '<h3>Original question</h3><div class="answer"></div></div>', '', 1), False),
            'extra-question': (original.replace('</article>', question + '<h3>Extra</h3><div class="answer"></div></div></article>'), False),
            'duplicate-question': (original.replace('id="q-what-data"', 'id="q-how-data"', 1), False),
            'unknown-section': (original.replace('id="sec-data-collection"', 'id="sec-unknown"', 1), False),
            'extra-section': (original.replace('</article>', '<section id="other"></section></article>'), False),
            'duplicate-section': (original.replace('id="sec-docs-metadata"', 'id="sec-data-collection"', 1), False),
        }
        for escape in (False, True):
            for profile in ('submission', 'review', 'unknown'):
                for case, (source, eligible) in variants.items():
                    with self.subTest(escape=escape, profile=profile, case=case):
                        env = environment(ROOT, escape, {'src/index.html.j2': source})
                        rendered = env.get_template('src/pdf/index.html.j2').render(output_profile=profile)
                        document = BeautifulSoup(rendered, 'html.parser')
                        self.assertEqual(eligible and profile == 'submission',
                            'pdf-all-empty-submission' in document.article['class'])
                        self.assertIn('pdf-flow-layout', document.article['class'])
                        # The only change is a PDF article marker, never content.
                        document.article['class'] = ['dmp']
                        self.assertEqual(str(BeautifulSoup(source, 'html.parser')), str(document))

    def test_pdf_empty_cover_marker_uses_real_empty_classifier_not_authored_text(self):
        source = (ROOT / 'src/content.html.j2').read_text()
        cases = ['', ' \t\n', '<p>Original answer.</p>', '<p></p>', '<img src="original.png">',
                 '<table><tbody><tr><td>Original row</td></tr></tbody></table>']
        for escape in (False, True):
            for body in cases:
                with self.subTest(escape=escape, body=body):
                    overrides = {'src/index.html.j2': '<html><body><article class="dmp">' + source + '</article></body></html>'}
                    for identifier, filename in re.findall(r'questionSpacing.question\("([^"]+)"\).*?include "([^"]+)"', source):
                        answer = body if identifier == 'q-how-data' else ''
                        overrides[filename] = ('<div id="' + identifier + '" class="question"><h3>Original question</h3>' +
                            '<div class="answer">' + answer + '</div></div>')
                    env = environment(ROOT, escape, overrides)
                    document = BeautifulSoup(env.get_template('src/pdf/index.html.j2').render(output_profile='submission'), 'html.parser')
                    self.assertEqual(not body.strip(), 'pdf-all-empty-submission' in document.article['class'])
                    self.assertEqual(15, len(document.select('.question > h3')))
                    expected = BeautifulSoup('<div>' + body + '</div>', 'html.parser').div.decode_contents().strip()
                    self.assertEqual(expected, document.select_one('#q-how-data > .answer').decode_contents().strip())
        for entry in ('src/submission/word.html.j2', 'src/word/index.html.j2'):
            self.assertNotIn('pdf-flow-layout', self.render(entry, profile='submission').article['class'])

    def test_pdf_review_boundary_hint_requires_short_owned_metadata(self):
        for fields, expected in (({}, True),
                ({'project': {'name': 'Original ' * 100}}, False),
                ({'project': {'name': '中' * 300}}, False),
                ({'pkg': {'name': 'Long model ' * 100}}, False),
                ({'config': {'service_name': 'Long service ' * 100}}, False)):
            for entry in ('src/pdf/index.html.j2', 'src/word/index.html.j2', 'src/index.html.j2'):
                with self.subTest(fields=fields, entry=entry):
                    document = self.render(entry, profile='review', trace_fields=fields)
                    self.assertEqual(expected and entry == 'src/pdf/index.html.j2',
                                     bool(document.select('aside.pdf-short-provenance')))
                    for values in fields.values():
                        for value in values.values():
                            self.assertIn(value, document.select_one('aside.document-provenance').get_text())
        self.assertFalse(self.render('src/pdf/index.html.j2', profile='submission').select('.pdf-short-provenance'))

    def test_sparse_pdf_print_rules_preserve_type_and_only_keep_the_metadata_boundary(self):
        css = (ROOT / 'src/layout.css').read_text().split('/* PDF-only sparse endings.', 1)[1]
        self.assertIn('@media print {', css)
        self.assertEqual(4, css.count('html body article.dmp.pdf-flow-layout'))
        self.assertIn('.pdf-all-empty-submission > #dmp-content { break-before: auto; page-break-before: auto; }', css)
        self.assertIn('> aside.document-provenance > p { margin-bottom: .1em; }', css)
        self.assertIn('> aside.document-provenance.pdf-short-provenance { break-before: avoid; }', css)
        for forbidden in ('font-', 'line-height:', 'display:', 'height:', 'overflow:',
                          'break-after:', 'break-inside:', '+ aside', '~ aside', '> .answer'):
            self.assertNotIn(forbidden, css)


if __name__ == '__main__':
    unittest.main()
