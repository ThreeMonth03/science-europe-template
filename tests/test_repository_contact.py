"""One full answer per field, not global deduplication by text or dataset name."""
import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import render_question
from test_answer_states import support_replies
from generate_pilot_fixtures import IDS, path


def contact_replies(value, publication='Yes', repository='DomainSpecific', choice='Other'):
    replies = support_replies((None, None, None), repository=repository, publication=publication)
    for kind in [k for k in replies if k.endswith(IDS['publishedDataRepositoryKindQUuid'])]:
        contact = path(kind, 'publishedDataRepositoryDomainSpecificAUuid', 'domainSpecificRepoContactBeforeQUuid')
        if choice: replies[contact] = IDS.get(f'domainSpecificRepoContactBefore{choice}AUuid', choice)
        if value is not None:
            replies[path(contact, 'domainSpecificRepoContactBeforeOtherAUuid', 'domainSpecificRepoContactBeforeOtherQUuid')] = value
    return replies


def render_pair(replies):
    return BeautifulSoup(''.join(render_question(f'src/questions/{q}.html.j2', replies)
                                for q in ['10-share-restrictions', '11-data-preservation']), 'html.parser')


class RepositoryContactTests(unittest.TestCase):
    def test_full_answer_only_in_q11_with_precise_same_item_targets(self):
        value = '<p>Contact-2027.csv.</p><ul><li>Ask first.</li></ul><p>Keep the final paragraph.</p>'
        soup = render_pair(contact_replies(value))
        self.assertNotIn('Contact-2027.csv', soup.find(id='q-share-restrictions').get_text())
        refs = soup.select('.repository-contact-reference a')
        self.assertEqual(3, len(refs))
        for i, ref in enumerate(refs, 1):
            self.assertEqual(f'#repository-contact-1-{i}', ref['href'])
            target = soup.select(ref['href']); self.assertEqual(1, len(target))
            self.assertEqual(ref.find_parent(class_='distribution-section')['data-item-id'], target[0].find_parent(class_='repository-distribution')['data-item-id'])
            detail = target[0].select_one('.answer-detail')
            heading = target[0].find_parent(class_='repository-distribution').select_one('.repository-contact-heading')
            self.assertIn('answer-lead', heading['class'])
            self.assertEqual(1, len(heading.find_all('p', recursive=False)))
            self.assertFalse(heading.select('.answer-detail, ul, table'))
            self.assertEqual('complete', detail['data-status'])
            self.assertEqual(value, detail.decode_contents())
        self.assertEqual(3, soup.get_text().count('Contact-2027.csv'))  # Three different supplied fields.
        self.assertNotIn('instead of contacting', soup.get_text())
        self.assertFalse(soup.select('p p, p div, p ul, p table'))

    def test_blank_other_answer_has_target_and_missing_not_complete(self):
        for value in [None, '', '  \n ']:
            soup = render_pair(contact_replies(value))
            self.assertEqual(3, len(soup.select('.repository-contact-reference')))
            self.assertEqual(['missing'] * 3, [n['data-status'] for n in soup.select('[data-fact-id="repository-contact-arrangements"]')])
            self.assertFalse(soup.select('.repository-contact .answer-detail'))

    def test_inactive_parents_and_other_choices_do_not_leak_stale_answers(self):
        for pub, repo, choice in [(None, 'DomainSpecific', 'Other'), ('No', 'DomainSpecific', 'Other'), ('Yes', 'National', 'Other'), ('Yes', 'DomainSpecific', None), ('Yes', 'DomainSpecific', 'YesAlready'), ('Yes', 'DomainSpecific', 'future-choice')]:
            soup = render_pair(contact_replies('Stale-contact.csv', pub, repo, choice))
            self.assertFalse(soup.select('.repository-contact-reference, .repository-contact'))
            self.assertNotIn('Stale-contact.csv', soup.get_text())

    def test_single_distribution_reference_has_no_misleading_number(self):
        replies = contact_replies('Single.csv')
        key = next(k for k in replies if k.endswith(IDS['publishedDistrosQUuid']))
        replies[key] = replies[key][:1]
        ref = render_pair(replies).select_one('.repository-contact-reference a')
        self.assertEqual('For repository contact arrangements, see Question 11 under this dataset.', ref.get_text())
        self.assertEqual('#repository-contact-1-1', ref['href'])

    def test_duplicate_dataset_names_and_missing_middle_keep_distinct_targets(self):
        replies = contact_replies('<p>Same field text.csv</p>')
        root = path('preservingCUuid', 'producedDataQUuid')
        replies[root].append('dataset-b')
        for k, v in list(replies.items()):
            if '.dataset-a.' in k: replies[k.replace('.dataset-a.', '.dataset-b.')] = v
        for item in replies[root]: replies[path(root, item, 'producedDataNameQUuid')] = 'Same name'
        key = next(k for k in replies if '.dataset-a.' in k and 'distro-1' in k and k.endswith(IDS['publishedDataRepositoryKindQUuid']))
        del replies[key]
        soup = render_pair(replies)
        refs = soup.select('.repository-contact-reference a')
        self.assertEqual(['#repository-contact-1-1', '#repository-contact-1-3', '#repository-contact-2-1', '#repository-contact-2-2', '#repository-contact-2-3'], [n['href'] for n in refs])
        self.assertEqual(5, soup.get_text().count('Same field text.csv'))
        for ref in refs:
            target = soup.select(ref['href']); self.assertEqual(1, len(target))
            self.assertEqual(ref.find_parent(class_='dataset-section')['data-item-id'], target[0].find_parent(class_='dataset-section')['data-item-id'])
