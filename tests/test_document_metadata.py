"""Business titles stay on the cover; system trace fields are review-only."""
from pathlib import Path
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

    def render(self, entry, name=PROJECT, escape=False, phase='phase-end', profile=None):
        km, replies = fixture(None, name)
        km['entities']['phases'] = {'phase-end': {'title': self.PHASE}}
        dc = dict(project=dict(name=self.WORKSPACE, versions=[dict(uuid='selected',
            name=self.VERSION, description='Checked revision.', created_at='2001-02-03T00:00:00Z')]),
            document=dict(created_at='1999-12-31T23:59:00Z'),
            pkg=dict(name='MODEL-TRACE', version='2.7.0', organization_id='dsw', km_id='root'),
            config=dict(service_name='SERVICE-TRACE', service_url='https://example.org/tool'))
        ctx = dict(knowledgeModel=km, project=dict(name=self.WORKSPACE, replies=replies,
            versionUuid='selected'), report={}, phaseUuid=phase)
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
                        for trace in (self.WORKSPACE, 'Created on 1999-12-31',
                                      'MODEL-TRACE', 'SERVICE-TRACE'):
                            self.assertIn(trace, text)
                        self.assertEqual(phase == 'phase-end', self.PHASE in text)
                        self.assertNotIn(self.WORKSPACE, soup.header.get_text())
                        self.assertNotIn('1999-12-31', soup.header.get_text())
                        self.assertNotIn(self.PHASE, soup.header.get_text())
                        self.assertEqual('Data Management Plan', soup.title.get_text())
                        self.assertFalse(tracking.select('label, script, img'))

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


if __name__ == '__main__':
    unittest.main()
