import json
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from output_profile_contract import CONTRACT, WRAPPER, check, environment
from generate_pilot_fixtures import IDS, path


class OutputProfilesTests(unittest.TestCase):
    def test_package_overrides_retain_the_synthetic_markdown_adapter(self):
        overrides = {
            'src/answer-markdown.html.j2': (ROOT / 'src/answer-markdown.html.j2').read_text(),
            'probe.html.j2': '{% import "src/answer-markdown.html.j2" as answer with context %}{{ answer.markdown(value) }}',
        }
        for escape in (False, True):
            with self.subTest(autoescape=escape):
                rendered = environment(ROOT, escape, overrides).get_template('probe.html.j2').render(
                    value='<p>Pre-rendered fixture answer.</p>')
                self.assertEqual(rendered, '<p>Pre-rendered fixture answer.</p>')

    def test_fixtures_review_unchanged_and_only_declared_submission_delta(self):
        # Keep the historical partial-profile oracle, on verified 0.3.43 bytes.
        # Current 0.3.44 behavior is covered by test_submission_preview.py.
        from submission_preview_contract import historical_overrides
        rows = check(ROOT, ROOT/'fixtures/pilot/en', 'english', baseline=True,
                     source_overrides=historical_overrides())
        self.assertEqual(len(rows), 2*len(list((ROOT/'fixtures/pilot/en').glob('*.events.json'))))
        self.assertTrue(any(r['remaining_diagnostic_nodes'] for r in rows))  # Deliberately partial.

    def test_storage_capacity_gap_does_not_leave_a_bare_subheading(self):
        prefix = path('processingCUuid', 'storageConvQUuid')
        replies = {prefix: IDS['storageConvExploreAUuid'],
            path(prefix, 'storageConvExploreAUuid', 'storageSpaceQUuid'): IDS['storageSpaceSpecifyAUuid']}
        template = environment(ROOT).from_string(WRAPPER)
        soup = BeautifulSoup(template.render(repliesMap=replies, output_profile='submission'), 'html.parser')
        answer = soup.select_one('#q-docs-metadata > .answer')
        self.assertFalse(answer.get_text().strip()); self.assertFalse(answer.select('h4'))

    def test_stable_identities_and_same_conversion_engines(self):
        # The old formats shared every conversion step; 0.3.47's scoped Word
        # suffix is checked exactly by the new integration metadata contract.
        from submission_flow_contract import project_source
        _, metadata = project_source()
        formats = {v['uuid']: v for v in metadata['formats']}
        self.assertEqual(len(formats), len(metadata['formats']))
        for fmt in ('html', 'pdf', 'docx'):
            review = formats[CONTRACT['formats']['review'][fmt]]
            submit = formats[CONTRACT['formats']['submission'][fmt]]
            self.assertEqual(review['steps'][1:], submit['steps'][1:])
            entry = (ROOT/submit['steps'][0]['options']['template']).read_text()
            self.assertIn("set output_profile = 'submission'", entry)
            self.assertIn(review['steps'][0]['options']['template'], entry)
            self.assertIn('pilot', submit['name'])
