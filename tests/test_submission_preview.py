import json
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from submission_preview_contract import CONTRACT, historical_overrides, project_source
from output_profile_contract import environment, WRAPPER
from test_answer_retention import path
from test_science_europe_contract import render_question


class SubmissionPreviewTests(unittest.TestCase):
    def test_exact_approved_source_and_unchanged_rendering_assets(self):
        sources, metadata = project_source()
        self.assertEqual(metadata['version'], '0.3.43')
        self.assertEqual(len(CONTRACT['files']), 21)
        self.assertTrue(all(name.endswith('.j2') for name in CONTRACT['files']))
        current = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
        for name in ['src/projects.html.j2', 'src/layout.css', 'src/word/pilot.lua']:
            with self.subTest(name=name), self.assertRaises(AssertionError):
                project_source({**current, name: current[name] + b'\n'})
        with self.assertRaises(AssertionError):
            project_source({**current, 'src/unreviewed.j2': b''})

    def test_review_and_unknown_mode_are_byte_identical_for_all_fixtures(self):
        overrides = historical_overrides()
        # Keep the original byte oracle on its exact, verified historical scope.
        # Actual 0.3.46 behavior is checked by test_full_km_followup_integration.
        from full_km_followups_contract import project_source as before_followups
        verified, _ = before_followups()
        current_overrides = {n: v.decode() for n, v in verified.items() if n.endswith('.j2')}
        for escape in [False, True]:
            prior = environment(ROOT, escape, overrides).from_string(WRAPPER)
            current = environment(ROOT, escape, current_overrides).from_string(WRAPPER)
            for fixture in sorted((ROOT / 'fixtures/pilot/en').glob('*.events.json')):
                replies = {e['path']: ({'value': {'value': e['value']['value']}}
                    if e['value']['type'] == 'IntegrationReply' else e['value']['value'])
                    for e in json.loads(fixture.read_text())}
                with self.subTest(escape=escape, fixture=fixture.name):
                    old = prior.render(repliesMap=replies)
                    self.assertEqual(current.render(repliesMap=replies), old)
                    for mode in ['review', 'unknown']:
                        self.assertEqual(current.render(repliesMap=replies, output_profile=mode), old)
                    result = BeautifulSoup(current.render(repliesMap=replies, output_profile='submission'), 'html.parser')
                    self.assertEqual(len(result.select('.question')), 15)
                    self.assertEqual(len(result.select('.dmp-section')), 6)
                    self.assertFalse(result.select('p p, p div, p ul, p table'))
                    owned = [n for n in result.select('p.data-gap') if not n.find_parent(class_='answer-detail')]
                    self.assertFalse(owned)
                    if fixture.name == 'profile-partial.events.json':
                        self.assertIn('Information not provided: this is authored', result.get_text())
                        self.assertIn('Original.csv', result.get_text())

    def test_empty_submission_does_not_invent_overview_or_answers(self):
        template = environment(ROOT).from_string(WRAPPER)
        review = BeautifulSoup(template.render(repliesMap={}), 'html.parser')
        submission = BeautifulSoup(template.render(repliesMap={}, output_profile='submission'), 'html.parser')
        self.assertTrue(review.select('.data-gap'))
        self.assertFalse(submission.select('#dmp-projects, #dmp-contributors, .data-gap'))
        self.assertTrue(all(not answer.get_text().strip() for answer in submission.select('.question > .answer')))

    def test_empty_contributor_records_do_not_leave_submission_diagnostics_or_heading(self):
        parent = path('adminDetailsCUuid', 'contributorsQUuid')
        dc = {'project': {'created_by': None}, 'e': {'choices': {}}}
        diagnostic = 'There are no contributors described for this DMP.'
        for blank in (None, '', ' \t\n\u3000'):
            values = {parent: ['person']}
            if blank is not None:
                for field in ('contributorNameQUuid', 'contributorEmailQUuid'):
                    values[path(parent, 'person', field)] = blank
                for field in ('contributorOrcidQUuid', 'contributorAffiliationQUuid'):
                    values[path(parent, 'person', field)] = {
                        'value': {'value': {'type': 'PlainType', 'value': blank}}}
                values[path(parent, 'person', 'contributorRoleQUuid')] = []
            with self.subTest(blank=blank):
                submission = BeautifulSoup(render_question('src/contributors.html.j2', values,
                    dc=dc, output_profile='submission'), 'html.parser')
                self.assertFalse(submission.select('#dmp-contributors, .data-gap, .data-review, .empty-value'))
                self.assertNotIn('People and responsibilities', submission.get_text())
                self.assertNotIn(diagnostic, submission.get_text())
                review = BeautifulSoup(render_question('src/contributors.html.j2', values,
                    dc=dc, output_profile='review'), 'html.parser')
                self.assertIsNotNone(review.select_one('#dmp-contributors > h2'))
                self.assertIn(diagnostic, review.get_text())
        values = {parent: ['person'], path(parent, 'person', 'contributorNameQUuid'): 'Research team'}
        submission = BeautifulSoup(render_question('src/contributors.html.j2', values,
            dc=dc, output_profile='submission'), 'html.parser')
        self.assertEqual('Research team', submission.select_one('.contributor .name').get_text())
        self.assertNotIn(diagnostic, submission.get_text())
