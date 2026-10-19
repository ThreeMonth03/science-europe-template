"""Preserve the version-retention meaning of reference-data reuse choices."""
import json
from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from current_support import IDS, PREFIX, environment


class ReferenceVersionTests(unittest.TestCase):
    def test_provider_and_copy_commitments_remain_distinct_in_both_policy_routes(self):
        events = json.loads((ROOT / 'fixtures/pilot/en/populated.events.json').read_text())
        base = {event['path']: event['value']['value'] for event in events}
        choices = [key for key in base if key.endswith(IDS['refDataReproduceQUuid'])]
        conditions = [key for key in base if key.endswith(IDS['refDataConditionsQUuid'])]
        self.assertEqual(2, len(choices))
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(
                PREFIX + "{% include 'src/questions/01-how-data.html.j2' %}")
            for profile in ('review', 'submission'):
                for shared in (False, True):
                    for choice in ('Provider', 'Copy', 'Both', None):
                        replies = dict(base)
                        for key in choices:
                            if choice is None:
                                replies.pop(key, None)
                            else:
                                replies[key] = IDS[f'refDataReproduce{choice}AUuid']
                        if not shared:
                            replies[conditions[1]] = IDS['refDataConditionsCC0AUuid']
                        output = template.render(repliesMap=replies, output_profile=profile)
                        soup = BeautifulSoup(output, 'html.parser')
                        with self.subTest(escape=escape, profile=profile, shared=shared, choice=choice):
                            expected = 1 if shared and choice else 2
                            self.assertEqual(expected if choice in ('Provider', 'Both') else 0,
                                             output.count('will keep old versions'))
                            self.assertEqual(expected if choice in ('Provider', 'Both') else 0,
                                             output.count('used in this project'))
                            self.assertEqual(expected if choice in ('Copy', 'Both') else 0,
                                             output.count('provide it alongside the research results')
                                             + output.count('provide these copies alongside the research results'))
                            self.assertNotIn('available in the long term', output)
                            self.assertFalse(soup.select('p p,p div,p ul'))
                            self.assertEqual(2, len(soup.select('[data-fact-id="reuse-purpose"]')))
                            self.assertEqual(2, len(soup.select('[data-fact-id="dataset-version"]')))
                            if profile == 'submission':
                                self.assertFalse(soup.select('.data-gap'))


if __name__ == '__main__':
    unittest.main()
