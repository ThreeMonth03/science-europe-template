import sys
import unittest
from copy import deepcopy
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
sys.path.insert(0, str(ROOT / 'scripts'))
from test_answer_states import support_replies, Q11
from generate_pilot_fixtures import IDS, path


def render(replies): return BeautifulSoup(render_question(Q11, replies), 'html.parser')

MAINTENANCE = {
    'Yes': 'We have arranged system administration (at least security updates) and hardware maintenance for the repository servers.',
    'NotYet': 'We have not yet completed the arrangements for system administration (at least security updates) and hardware maintenance for the repository servers.',
}


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
            selector = ('.identifier-heading > .answer-lead:first-child strong' if q.startswith('13-') else
                        '.distribution-section > .answer-lead:first-child strong, .distribution-reading-unit > .answer-lead:first-child strong')
            self.assertEqual(['Distribution 1', 'Distribution 2', 'Distribution 3'], [n.get_text() for n in other.select(selector)])

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

    def test_special_repository_sentences_have_one_explicit_english_separator(self):
        row = render(support_replies(('Yes',), repository='Special')).select_one('.repository-distribution')
        self.assertIn(
            'Special-purpose repository for the project. We will be able to support this repository '
            'for a sufficiently long time. The repository will provide an advanced processing service.',
            row.get_text(' ', strip=True),
        )
        replies = support_replies(('Yes', 'Yes'), repository='Special')
        for index, choice in enumerate(MAINTENANCE):
            kind = next(p for p in replies if f'distro-{index}' in p and p.endswith(IDS['publishedDataRepositoryKindQUuid']))
            replies[path(kind, 'publishedDataRepositorySpecialAUuid', 'specialRepoMaintenanceQUuid')] = IDS[f'specialRepoMaintenance{choice}AUuid']
        for profile in ('review', 'submission'):
            rows = BeautifulSoup(render_question(Q11, replies, output_profile=profile), 'html.parser').select('.repository-distribution')
            self.assertEqual(2, len(rows))
            for index, (row, choice) in enumerate(zip(rows, MAINTENANCE)):
                self.assertEqual(f'distro-{index}', row['data-item-id'])
                self.assertEqual(MAINTENANCE[choice], row.select_one('[data-fact-id="repository-server-maintenance"]').get_text())
                self.assertIn('advanced processing service. ' + MAINTENANCE[choice], row.get_text(' ', strip=True))
                self.assertEqual(1, row.get_text().count(MAINTENANCE[choice]))
                self.assertNotIn(MAINTENANCE['NotYet' if choice == 'Yes' else 'Yes'], row.get_text())
                self.assertFalse(row.select('p, div, ul, ol, table'))

    def test_maintenance_requires_an_active_known_special_repository_answer(self):
        from check_answer_mapping import question
        from check_repository_profiles import preservation_schema
        from current_support import PREFIX, environment
        km = preservation_schema()
        children = km['entities']['answers'][IDS['isPublishedDataYesAUuid']]['followUpUuids']
        children = question(km, children, IDS['publishedDistrosQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
        question(km, children, IDS['publishedDataRepositoryKindQUuid'], 'OptionsQuestion',
                 [IDS['publishedDataRepositorySpecialAUuid'], IDS['publishedDataRepositoryNationalAUuid']])
        children = km['entities']['answers'][IDS['publishedDataRepositorySpecialAUuid']]['followUpUuids']
        question(km, children, IDS['specialRepoMaintenanceQUuid'], 'OptionsQuestion',
                 [IDS['specialRepoMaintenance' + choice + 'AUuid'] for choice in MAINTENANCE])
        base = support_replies(('Yes',), repository='Special')
        data = path('preservingCUuid', 'producedDataQUuid')
        publication = path(data, 'dataset-a', 'isPublishedDataQUuid')
        listing = path(publication, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
        kind = path(listing, 'distro-0', 'publishedDataRepositoryKindQUuid')
        leaf = path(kind, 'publishedDataRepositorySpecialAUuid', 'specialRepoMaintenanceQUuid')
        # The local adapter decodes typed leaves; the production guard must reject
        # a wrong reply kind even when its scalar happens to contain a valid UUID.
        env = environment(ROOT)
        fallback = env.filters['reply_str_value']
        env.filters['reply_str_value'] = lambda reply: reply['value']['value'] if isinstance(reply, dict) else fallback(reply)
        template = env.from_string(PREFIX + "{% include '" + Q11 + "' %}")
        controls = ('active', 'missing', 'empty', 'unknown', 'publication-missing', 'publication-no',
                    'repository-missing', 'repository-other', 'dataset-removed', 'distribution-removed',
                    'removed-question', 'removed-choice', 'dangling-choice', 'wrong-question-type', 'removed-followup')
        for profile in ('review', 'submission'):
            for choice in MAINTENANCE:
                for control in controls:
                    values, schema = dict(base, **{leaf: IDS['specialRepoMaintenance' + choice + 'AUuid']}), deepcopy(km)
                    if control == 'missing': del values[leaf]
                    elif control == 'empty': values[leaf] = ''
                    elif control == 'unknown': values[leaf] = 'future-choice'
                    elif control == 'publication-missing': del values[publication]
                    elif control == 'publication-no': values[publication] = IDS['isPublishedDataNoAUuid']
                    elif control == 'repository-missing': del values[kind]
                    elif control == 'repository-other': values[kind] = IDS['publishedDataRepositoryNationalAUuid']
                    elif control == 'dataset-removed': values[data] = []
                    elif control == 'distribution-removed': values[listing] = []
                    elif control == 'removed-question': del schema['entities']['questions'][IDS['specialRepoMaintenanceQUuid']]
                    elif control == 'removed-choice': schema['entities']['questions'][IDS['specialRepoMaintenanceQUuid']]['answerUuids'].remove(values[leaf])
                    elif control == 'dangling-choice': del schema['entities']['answers'][values[leaf]]
                    elif control == 'wrong-question-type': schema['entities']['questions'][IDS['specialRepoMaintenanceQUuid']]['questionType'] = 'ValueQuestion'
                    elif control == 'removed-followup': schema['entities']['answers'][IDS['publishedDataRepositorySpecialAUuid']]['followUpUuids'].clear()
                    with self.subTest(profile=profile, choice=choice, control=control):
                        soup = BeautifulSoup(template.render(repliesMap=values, km=schema, output_profile=profile), 'html.parser')
                        self.assertEqual(control == 'active', bool(soup.select('[data-fact-id="repository-server-maintenance"]')))
                        if control in ('missing', 'empty', 'unknown', 'removed-question', 'removed-choice', 'dangling-choice', 'wrong-question-type', 'removed-followup'):
                            self.assertIn('We will be able to support this repository for a sufficiently long time.', soup.get_text())
                            self.assertIn('The repository will provide an advanced processing service.', soup.get_text())
                for reply_type in ('AnswerReply', 'StringReply', 'ItemListReply'):
                    values = dict(base, **{leaf: {'value': {'type': reply_type, 'value': IDS['specialRepoMaintenance' + choice + 'AUuid']}}})
                    with self.subTest(profile=profile, choice=choice, reply_type=reply_type):
                        soup = BeautifulSoup(template.render(repliesMap=values, km=km, output_profile=profile), 'html.parser')
                        self.assertEqual(reply_type == 'AnswerReply', MAINTENANCE[choice] in soup.get_text())

    def test_long_or_block_repository_name_cannot_enable_keep_hint(self):
        replies = support_replies(repository='GeneralPurpose')
        kind = next(p for p in replies if p.endswith(IDS['publishedDataRepositoryKindQUuid']))
        name = path(kind, 'publishedDataRepositoryGeneralPurposeAUuid', 'generalPurposeRepoNameQUuid')
        for value in ['Name ' * 200, '<p>Unusual name markup</p>']:
            replies[name] = {'value': {'value': {'type': 'PlainType', 'value': value}}}
            self.assertFalse(render(replies).select('.short-repository-list'))
