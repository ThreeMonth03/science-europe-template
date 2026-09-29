import itertools
import sys
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from test_identifier_reading import identifier_replies, render, IDS
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from identifier_concise_contract import ASSIGNERS, AFFIRMATIVE, REPOSITORY_COMPOUND, RESOLUTIONS, compare


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
                        if actor == 'Repository' and resolution in ['Yes', 'No']:
                            self.assertEqual(first.get_text(strip=True), REPOSITORY_COMPOUND['english'][resolution])
                            self.assertIs(first.select_one('[data-fact-id="identifier-resolution"]'),
                                          distro.select_one('[data-fact-id="identifier-resolution"]'))
                        else:
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

    def test_repository_compound_preserves_assigner_and_resolution_facts(self):
        for language in ['english', 'chinese']:
            for choice, status in [('Yes', 'complete'), ('No', 'explicit-no')]:
                pre = '<div id="q-persistent-identifier"><div class="identifier-arrangement">'
                parent = '<p data-fact-id="persistent-identifier" data-status="complete">'
                assign = ' data-requirement-id="SE-5d" data-fact-id="identifier-assigner" data-status="complete"'
                resolve = f' data-requirement-id="SE-5d" data-fact-id="identifier-resolution" data-status="{status}"'
                before = BeautifulSoup(
                    pre + parent + AFFIRMATIVE[language] + '</p><p' + assign + '>' + ASSIGNERS[language][-1]
                    + '</p><p' + resolve + '>' + RESOLUTIONS[language][choice] + '</p></div></div>',
                    'html.parser',
                )
                after = BeautifulSoup(
                    pre + parent + '<span' + assign + '><span' + resolve + '>'
                    + REPOSITORY_COMPOUND[language][choice] + '</span></span></p></div></div>',
                    'html.parser',
                )
                self.assertEqual(compare(before, after, language, repository_compound=True), 1)
                with self.assertRaises(AssertionError):
                    compare(before, BeautifulSoup(str(after).replace(
                        REPOSITORY_COMPOUND[language][choice], REPOSITORY_COMPOUND[language][choice] + 'X'
                    ), 'html.parser'), language, repository_compound=True)


if __name__ == '__main__':
    unittest.main()
