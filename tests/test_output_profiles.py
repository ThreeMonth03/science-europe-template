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
    def test_fixtures_review_unchanged_and_only_declared_submission_delta(self):
        rows = check(ROOT, ROOT/'fixtures/pilot/en', 'english', baseline=True)
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
        metadata = json.loads((ROOT/'template.json').read_text())
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
