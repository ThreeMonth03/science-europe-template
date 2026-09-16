import itertools
import sys
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from test_identifier_reading import identifier_replies, render, IDS
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from identifier_concise_contract import ASSIGNERS, AFFIRMATIVE, compare


class IdentifierConciseTests(unittest.TestCase):
    def test_all_parent_and_child_states_keep_independent_facts(self):
        for parent, actor, resolution in itertools.product(['Yes', 'No', None, 'future'],
                ['Repository', 'ProjectDataSteward', 'InstitDataSteward', None, 'future'], ['Yes', 'No', None, 'future']):
            with self.subTest(parent=parent, actor=actor, resolution=resolution):
                soup = render(identifier_replies(identifier=parent, assigns=actor, resolves=resolution))
                for distro in soup.select('.distribution-section'):
                    if parent != 'Yes':
                        self.assertFalse(distro.select('[data-fact-id="persistent-identifier"], [data-fact-id="identifier-assigner"]'))
                        continue
                    policies = distro.select('[data-fact-id="persistent-identifier"]')
                    self.assertEqual(len(policies), 1)
                    first = policies[0]
                    self.assertEqual(first['data-status'], 'complete')
                    if actor in ['Repository', 'ProjectDataSteward', 'InstitDataSteward']:
                        self.assertIn(first.get_text(), ASSIGNERS['english'])
                        self.assertEqual(first.span['data-fact-id'], 'identifier-assigner')
                        self.assertNotIn(AFFIRMATIVE['english'], distro.get_text())
                    else:
                        self.assertEqual(first.get_text(), AFFIRMATIVE['english'])
                        self.assertEqual(distro.select_one('[data-fact-id="identifier-assigner"]')['data-status'],
                                         'missing' if actor is None else 'needs-review')
                    self.assertEqual(distro.select_one('[data-fact-id="identifier-resolution"]')['data-status'],
                                     {'Yes': 'complete', 'No': 'explicit-no', None: 'missing', 'future': 'needs-review'}[resolution])

    def test_delta_oracle_rejects_changed_actor_state_and_authored_text(self):
        for language in ['english', 'chinese']:
            affirmative, actor = AFFIRMATIVE[language], ASSIGNERS[language][-1]
            pre = '<div id="q-persistent-identifier"><div class="identifier-arrangement">'
            parent = '<p data-fact-id="persistent-identifier" data-status="complete">'
            attrs = ' data-requirement-id="SE-5d" data-fact-id="identifier-assigner" data-status="complete"'
            tail = '</div><div class="answer-detail"><p>Original.csv</p></div></div>'
            before = BeautifulSoup(pre + parent + affirmative + '</p><p' + attrs + '>' + actor + '</p>' + tail, 'html.parser')
            html = pre + parent + '<span' + attrs + '>' + actor + '</span></p>' + tail
            self.assertEqual(compare(before, BeautifulSoup(html, 'html.parser'), language), 1)
            for changed in [html.replace(actor, 'Invented actor.'), html.replace('complete', 'missing', 1),
                            html.replace('Original.csv', 'Changed.csv'), html.replace('identifier-assigner', 'other-fact')]:
                with self.assertRaises(AssertionError):
                    compare(before, BeautifulSoup(changed, 'html.parser'), language)


if __name__ == '__main__':
    unittest.main()
