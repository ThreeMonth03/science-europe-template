import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
from test_answer_retention import IDS, path
from current_support import environment, identifier_replies
from check_access_reading import reuse_schema

Q13 = 'src/questions/13-persistent-identifier.html.j2'


def render(replies): return BeautifulSoup(render_question(Q13, replies, km=reuse_schema()), 'html.parser')


class IdentifierReadingTests(unittest.TestCase):
    def test_known_assigner_states_assignment_once_with_both_facts(self):
        soup = render(identifier_replies())
        for index, distro in enumerate(soup.select('.distribution-section'), 1):
            heading = distro.select_one('.identifier-heading')
            self.assertEqual([f'Distribution {index}', 'Institutional repository'],
                             [p.get_text(strip=True) for p in heading.find_all('p', recursive=False)])
            policy = distro.select_one('.identifier-arrangement.dataset-policy')
            self.assertEqual(1, len(policy.find_all('p', recursive=False)))
            parent = policy.select_one('[data-fact-id="persistent-identifier"]')
            self.assertIs(parent.parent, policy)
            self.assertIs(parent.select_one('[data-fact-id="identifier-assigner"]').parent, parent)
            self.assertNotIn('Persistent identifiers will be assigned.', policy.get_text())
            unit=distro.select_one('.identifier-followup-unit.short-reading-unit')
            self.assertIs(heading.find_next_sibling(), unit)
            self.assertIs(policy.parent,unit)
        self.assertFalse(soup.select('p p, p div, p ul'))

    def test_single_distribution_retains_type_without_number(self):
        soup = render(identifier_replies(count=1))
        self.assertNotIn('Distribution 1', soup.get_text())
        self.assertEqual('Institutional repository', soup.select_one('.identifier-heading').get_text(strip=True))

    def test_whitespace_name_and_missing_repository_do_not_emit_empty_headings(self):
        replies = identifier_replies(repository=None, count=1)
        dataset = path('preservingCUuid', 'producedDataQUuid')
        replies[path(dataset, 'dataset-a', 'producedDataNameQUuid')] = '  \n '
        review = render(replies)
        self.assertEqual('(no name given)', review.select_one('.dataset-section > h5').get_text(strip=True))
        self.assertFalse(review.select('.identifier-heading'))
        self.assertFalse([node for node in review.find_all(['p', 'h5']) if not node.get_text(strip=True)])

        env = environment(ROOT)
        wrapper = env.from_string(
            "{% import 'src/macros.html.j2' as macros with context %}"
            "{% import 'src/uuids.j2' as uuids with context %}"
            "{% include 'src/questions/13-persistent-identifier.html.j2' with context %}"
        )
        submission = BeautifulSoup(
            wrapper.render(repliesMap=replies, output_profile='submission'), 'html.parser'
        )
        self.assertEqual('Produced dataset 1', submission.select_one('.dataset-section > h5').get_text(' ', strip=True))
        self.assertFalse([node for node in submission.find_all(['p', 'h5']) if not node.get_text(strip=True)])

    def test_no_missing_and_unknown_identifier_do_not_leak_stale_yes_children(self):
        for choice in ['No', None, 'unsupported']:
            soup = render(identifier_replies(identifier=choice))
            self.assertFalse(soup.select('.identifier-arrangement'))
            self.assertNotIn('will assign the persistent identifier', soup.get_text())
            self.assertNotIn('can be resolved', soup.get_text())
            self.assertEqual(choice != 'No', bool(soup.select('.distribution-section .data-gap')))

    def test_missing_or_negative_children_are_not_inferred_positive(self):
        soup = render(identifier_replies(assigns=None, resolves=None))
        self.assertTrue(all(len(p.find_all('p')) == 1 for p in soup.select('.identifier-arrangement')))
        soup = render(identifier_replies(resolves='No'))
        self.assertEqual(2, soup.get_text().count('will not guarantee'))

    def test_inactive_publication_discards_identifier_headings_and_stale_answers(self):
        for choice in [None, 'No']:
            replies = identifier_replies()
            key = next(p for p in replies if p.endswith(IDS['isPublishedDataQUuid']))
            replies[key] = IDS['isPublishedDataNoAUuid'] if choice else ''
            soup = render(replies)
            self.assertFalse(soup.select('.identifier-heading, .identifier-arrangement, .distribution-section'))

    def test_unrelated_authored_reuse_blocks_and_duplicate_names_are_not_joined(self):
        replies = identifier_replies()
        measured = path('creatingCUuid', 'measuredQUuid')
        replies[measured] = IDS['measuredYesAUuid']
        items = path(measured, 'measuredYesAUuid', 'measuredDataQUuid')
        replies[items] = ['first', 'second']
        authored = '<p>First author paragraph.</p><ul><li>Author item.</li></ul><p>Last author paragraph.</p>'
        for item in replies[items]:
            base = path(items, item)
            replies[path(base, 'measuredDataNameQUuid')] = 'Same name'
            reuse = path(base, 'measuredDataReuseQUuid')
            replies[reuse] = IDS['measuredDataReuseOtherFieldAUuid']
            replies[path(reuse, 'measuredDataReuseOtherFieldAUuid', 'measuredDataReuseOtherFieldHowQUuid')] = authored
        soup = render(replies)
        self.assertEqual(2, len(soup.select('.answer-detail')))
        for node in soup.select('.answer-detail'):
            self.assertIn(authored, node.decode_contents())
            self.assertIsNone(node.find_parent(class_='identifier-arrangement'))
            self.assertIsNone(node.find_parent(class_='identifier-heading'))
