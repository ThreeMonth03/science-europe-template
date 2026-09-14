import sys
import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
sys.path.insert(0, str(ROOT / 'scripts'))
from test_answer_states import support_replies, Q11
from generate_pilot_fixtures import IDS, path


def render(replies): return BeautifulSoup(render_question(Q11, replies), 'html.parser')


class RepositoryReadingTests(unittest.TestCase):
    def test_numbering_matches_q10_and_q13_and_keeps_missing_middle(self):
        replies = support_replies(('Yes', 'No', None))
        key = next(p for p in replies if 'distro-1' in p and p.endswith(IDS['publishedDataRepositoryKindQUuid']))
        del replies[key]  # Leave a stale support child: it must not escape.
        soup = render(replies)
        self.assertEqual(['Distribution 1:', 'Distribution 2:', 'Distribution 3:'], [n.get_text() for n in soup.select('.repository-label')])
        self.assertEqual(['distro-0', 'distro-1', 'distro-2'], [n['data-item-id'] for n in soup.select('.repository-distribution')])
        middle = soup.select('.repository-distribution')[1]
        self.assertEqual('missing', middle.select_one('[data-fact-id="repository-destination"]')['data-status'])
        self.assertFalse(middle.select('[data-fact-id="repository-long-term-support"]'))
        for q in ['10-share-restrictions', '13-persistent-identifier']:
            other = BeautifulSoup(render_question(f'src/questions/{q}.html.j2', replies), 'html.parser')
            self.assertEqual(['Distribution 1', 'Distribution 2', 'Distribution 3'], [n.get_text() for n in other.select('.distribution-section > .answer-lead:first-child strong, .distribution-reading-unit > .answer-lead:first-child strong')])

    def test_single_repository_has_no_redundant_number_and_inactive_parent_has_no_list(self):
        self.assertFalse(render(support_replies()).select('.repository-label'))
        for publication in [None, 'No']:
            self.assertFalse(render(support_replies(('Yes', 'No'), publication=publication)).select('.repository-destinations'))

    def test_unknown_choice_is_review_not_missing_or_silent(self):
        replies = support_replies()
        key = next(p for p in replies if p.endswith(IDS['publishedDataRepositoryKindQUuid']))
        replies[key] = 'future-choice'
        soup = render(replies)
        self.assertEqual('needs-review', soup.select_one('[data-fact-id="repository-destination"]')['data-status'])
        self.assertFalse(soup.select('[data-fact-id="repository-long-term-support"]'))

    def test_short_hint_has_count_length_and_authored_structure_limits(self):
        self.assertTrue(render(support_replies(('Yes', 'No', None))).select('.short-repository-list'))
        self.assertFalse(render(support_replies(('Yes',) * 4)).select('.short-repository-list'))
        replies = support_replies(repository='DomainSpecific')
        kind = next(p for p in replies if p.endswith(IDS['publishedDataRepositoryKindQUuid']))
        contact = path(kind, 'publishedDataRepositoryDomainSpecificAUuid', 'domainSpecificRepoContactBeforeQUuid')
        replies[contact] = IDS['domainSpecificRepoContactBeforeOtherAUuid']
        detail = path(contact, 'domainSpecificRepoContactBeforeOtherAUuid', 'domainSpecificRepoContactBeforeOtherQUuid')
        for value in ['Short authored answer.', '<p>First.</p><p>Second.</p>', 'Long-2027.csv ' * 100]:
            replies[detail] = value
            soup = render(replies)
            self.assertFalse(soup.select('.short-repository-list'))
            self.assertIn(value, str(soup))

    def test_fixed_inline_labels_do_not_create_extra_paragraphs(self):
        soup = render(support_replies(('Yes', 'No', None)))
        for row in soup.select('.repository-distribution'):
            self.assertFalse(row.select('p, div, ul, ol, table'))
            self.assertEqual(1, len(row.select('.repository-label')))

    def test_long_or_block_repository_name_cannot_enable_keep_hint(self):
        replies = support_replies(repository='GeneralPurpose')
        kind = next(p for p in replies if p.endswith(IDS['publishedDataRepositoryKindQUuid']))
        name = path(kind, 'publishedDataRepositoryGeneralPurposeAUuid', 'generalPurposeRepoNameQUuid')
        for value in ['Name ' * 200, '<p>Unusual name markup</p>']:
            replies[name] = {'value': {'value': {'type': 'PlainType', 'value': value}}}
            self.assertFalse(render(replies).select('.short-repository-list'))
