import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import render_question
from test_answer_states import support_replies
from test_answer_retention import IDS, path

Q13 = 'src/questions/13-persistent-identifier.html.j2'


def identifier_replies(identifier='Yes', assigns='Repository', resolves='Yes', repository='Institutional', count=2):
    replies = support_replies(('Yes',) * count, repository='Institutional')
    for kind in [p for p in replies if p.endswith(IDS['publishedDataRepositoryKindQUuid'])]:
        base = kind.rsplit('.', 1)[0]
        if repository: replies[kind] = IDS.get('publishedDataRepository' + repository + 'AUuid', repository)
        else: replies.pop(kind, None)
        question = path(base, 'publishedDataIdentifierQUuid')
        if identifier: replies[question] = IDS.get('publishedDataIdentifier' + identifier + 'AUuid', identifier)
        else: replies.pop(question, None)
        for name, value in [('Assigns', assigns), ('Resolvable', resolves)]:
            key = path(question, 'publishedDataIdentifierYesAUuid', 'publishedDataIdentifier' + name + 'QUuid')
            if value: replies[key] = IDS.get('publishedDataIdentifier' + name + value + 'AUuid', value)
            else: replies.pop(key, None)
    return replies


def render(replies): return BeautifulSoup(render_question(Q13, replies), 'html.parser')


class IdentifierReadingTests(unittest.TestCase):
    def test_known_assigner_states_assignment_once_with_both_facts(self):
        soup = render(identifier_replies())
        for index, distro in enumerate(soup.select('.distribution-section'), 1):
            heading = distro.select_one('.identifier-heading')
            self.assertEqual([f'Distribution {index}', 'Institutional repository'],
                             [p.get_text(strip=True) for p in heading.find_all('p', recursive=False)])
            policy = distro.select_one('.identifier-arrangement.dataset-policy')
            self.assertEqual(2, len(policy.find_all('p', recursive=False)))
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
        self.assertEqual(2, soup.get_text().count('will not make sure'))

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
