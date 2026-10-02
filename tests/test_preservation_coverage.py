import copy
import itertools
import json
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_pilot_fixtures import IDS, path
from generate_preservation_fixtures import preservation_cases
from check_repository_profiles import preservation_schema

Q11 = 'src/questions/11-data-preservation.html.j2'
AUTHORED = '<p>Keep Selection-2027-12-31.csv.</p><p>Do not merge this paragraph.</p><ul><li>First.</li><li>Second.</li></ul>'


def plain(case='preservation-complete'):
    return {p: v['value'] for p,v in preservation_cases('en')[case].items()}


def render(replies): return BeautifulSoup(render_question(Q11, replies, km=preservation_schema()), 'html.parser')


def grouping_fixture(count=3):
    """Local complete-choice schema; do not broaden the existing fixtures."""
    from check_answer_mapping import question
    km = preservation_schema()
    children = km['entities']['questions'][IDS['producedDataQUuid']]['itemTemplateQuestionUuids']
    question(km, children, IDS['publishedDataHowLongQUuid'], 'OptionsQuestion',
             [IDS['publishedDataHowLong' + option + 'AUuid'] for option in ('Technical', 'Deleted', 'Fixed')])
    data = path('preservingCUuid', 'producedDataQUuid')
    replies = {data: ['group-' + str(i) for i in range(1, count + 1)]}
    for item in replies[data]:
        base = path(data, item)
        replies.update({path(base, 'producedDataNameQUuid'): 'Same dataset name',
            path(base, 'isPublishedDataQUuid'): IDS['isPublishedDataYesAUuid'],
            path(base, 'publishedDataHowLongQUuid'): IDS['publishedDataHowLongTechnicalAUuid'],
            path(base, 'publishedDataMetadataPersistentQUuid'): IDS['publishedDataMetadataPersistentYesAUuid'],
            path(base, 'isPublishedDataQUuid', 'isPublishedDataYesAUuid', 'publishedDataCatalogueQUuid'):
                IDS['publishedDataCatalogueYesAUuid']})
    return km, replies


def render_grouping(replies, km, profile):
    return BeautifulSoup(render_question(Q11, replies, km=km, output_profile=profile), 'html.parser')


def archive_matrix():
    base = plain(); ap = path('preservingCUuid', 'archivedAfterQUuid', 'archivedAfterYesAUuid')
    for period, payer in itertools.product(
        [None, 'archivedAfterPeriodFiveAUuid', 'archivedAfterPeriodTenAUuid', 'archivedAfterPeriodFifteenAUuid', 'archivedAfterPeriodYearsAUuid', 'archivedAfterPeriodOtherAUuid'],
        [None, 'archivedAfterPayerGrantAUuid', 'archivedAfterPayerDepartmentAUuid', 'archivedAfterPayerInstituteAUuid']):
        replies = copy.deepcopy(base)
        for p in list(replies):
            if p.startswith(path(ap, 'archivedAfterPeriodQUuid')): replies.pop(p)
        if period: replies[path(ap, 'archivedAfterPeriodQUuid')] = IDS[period]
        pp = path(ap, 'archivedAfterPayerQUuid')
        if payer: replies[pp] = IDS[payer]
        else: replies.pop(pp)
        yield replies, period, payer


class PreservationCoverageTests(unittest.TestCase):
    def test_shared_policy_requires_three_complete_records_in_both_profiles(self):
        for profile, count in itertools.product(('review', 'submission'), (1, 2, 3, 4)):
            with self.subTest(profile=profile, count=count):
                km, replies = grouping_fixture(count)
                replies[path('preservingCUuid', 'repoChargesQUuid')] = IDS['repoChargesNoAUuid']
                soup = render_grouping(replies, km, profile)
                shared = soup.select('.preservation-shared-policy')
                self.assertEqual(int(count >= 3), len(shared))
                self.assertEqual(count if count >= 3 else 0, len(soup.select('.preservation-policy-reference')))
                self.assertEqual(1 if count >= 3 else count, soup.get_text().count('This dataset will be published.'))
                self.assertEqual(replies[path('preservingCUuid', 'producedDataQUuid')],
                                 [node['data-item-id'] for node in soup.select('.dataset-section')])
                if shared:
                    resources = soup.select_one('.preservation-resources')
                    self.assertFalse(resources.find_parent(class_='preservation-shared-policy'))
                    self.assertEqual('Repository costs and publication preparation',
                                     resources.find_previous('h4').get_text())
                    self.assertEqual(' '.join(replies[path('preservingCUuid', 'producedDataQUuid')]), shared[0]['data-member-ids'])
                    self.assertEqual(4, len(shared[0].select('.dataset-policy > p')))
                    for ref in soup.select('.preservation-policy-reference a'):
                        self.assertEqual([shared[0]], soup.select(ref['href']))
        for profile in ('review', 'submission'):
            km, replies = grouping_fixture(4)
            replies.pop(path('preservingCUuid', 'producedDataQUuid', 'group-2', 'publishedDataMetadataPersistentQUuid'))
            soup = render_grouping(replies, km, profile)
            shared = soup.select('.preservation-shared-policy')
            self.assertEqual(1, len(shared))
            self.assertEqual('group-1 group-3 group-4', shared[0]['data-member-ids'])
            self.assertEqual(3, len(soup.select('.preservation-policy-reference')))
            self.assertFalse(soup.select('.dataset-section[data-item-id="group-2"] .preservation-policy-reference'))
            self.assertEqual(['group-1', 'group-2', 'group-3', 'group-4'],
                             [node['data-item-id'] for node in soup.select('.dataset-section')])

    def test_incomplete_inactive_and_custom_policies_never_share(self):
        fields = ('isPublishedDataQUuid', 'publishedDataHowLongQUuid',
                  'publishedDataMetadataPersistentQUuid', 'publishedDataCatalogueQUuid')
        variants = [(field, state) for field in fields for state in
                    ('missing', 'unknown', 'question-filtered', 'answer-filtered', 'answer-deleted', 'wrong-type')]
        variants += [('publishedDataHowLongQUuid', 'custom'), ('isPublishedDataQUuid', 'explicit-no')]
        for profile, (field, state) in itertools.product(('review', 'submission'), variants):
            with self.subTest(profile=profile, field=field, state=state):
                km, replies = grouping_fixture()
                keys = [key for key in replies if key.endswith(IDS[field])]
                selected = replies[keys[0]]
                if state in ('question-filtered', 'answer-filtered', 'answer-deleted', 'wrong-type'):
                    question = km['entities']['questions'][IDS[field]]
                    if state == 'question-filtered':
                        children = (km['entities']['answers'][IDS['isPublishedDataYesAUuid']]['followUpUuids']
                                    if field == 'publishedDataCatalogueQUuid' else
                                    km['entities']['questions'][IDS['producedDataQUuid']]['itemTemplateQuestionUuids'])
                        children.remove(IDS[field])
                    elif state == 'answer-filtered': question['answerUuids'].remove(selected)
                    elif state == 'answer-deleted': km['entities']['answers'].pop(selected)
                    else: question['questionType'] = 'ValueQuestion'
                else:
                    for key in keys:
                        if state == 'missing': replies.pop(key)
                        elif state == 'unknown': replies[key] = 'obsolete-choice'
                        elif state == 'custom':
                            replies[key] = IDS['publishedDataHowLongFixedAUuid']
                            replies[path(key, 'publishedDataHowLongFixedAUuid', 'publishedDataHowLongFixedQUuid')] = '7 years'
                        else:
                            replies[key] = IDS['isPublishedDataNoAUuid']
                            replies[path(key, 'isPublishedDataNoAUuid', 'notPublishedReasonQUuid')] = IDS['notPublishedReasonCostAUuid']
                soup = render_grouping(replies, km, profile)
                self.assertFalse(soup.select('.preservation-shared-policy, .preservation-policy-reference'))
                self.assertEqual(3, len(soup.select('.dataset-section')))
                if field != 'publishedDataHowLongQUuid':
                    self.assertEqual(3, soup.get_text().count('as long as technically possible.'))
                if state == 'custom': self.assertEqual(3, soup.get_text().count('Retention period (prepaid): 7 years.'))
                if state == 'explicit-no': self.assertEqual(3, soup.get_text().count('The stated reason for not publishing is the cost.'))
                if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))

    def test_distinct_policy_keys_keep_interleaved_members_and_all_choices(self):
        choices = list(itertools.product(('Technical', 'Deleted'), ('Yes', 'No'), ('Yes', 'No', 'Prime')))
        km, replies = grouping_fixture(3 * len(choices))
        data = path('preservingCUuid', 'producedDataQUuid')
        for index, item in enumerate(replies[data]):
            duration, metadata, catalogue = choices[index % len(choices)]
            base = path(data, item)
            replies[path(base, 'publishedDataHowLongQUuid')] = IDS['publishedDataHowLong' + duration + 'AUuid']
            replies[path(base, 'publishedDataMetadataPersistentQUuid')] = IDS['publishedDataMetadataPersistent' + metadata + 'AUuid']
            replies[path(base, 'isPublishedDataQUuid', 'isPublishedDataYesAUuid', 'publishedDataCatalogueQUuid')] = IDS['publishedDataCatalogue' + catalogue + 'AUuid']
        from check_repository_profiles import PRESERVATION
        for profile in ('review', 'submission'):
            soup = render_grouping(replies, km, profile)
            groups = soup.select('.preservation-shared-policy')
            self.assertEqual(len(choices), len(groups))
            self.assertEqual(replies[data], [node['data-item-id'] for node in soup.select('.dataset-section')])
            for index, (group, (duration, metadata, catalogue)) in enumerate(zip(groups, choices)):
                members = replies[data][index::len(choices)]
                self.assertEqual(members, group['data-member-ids'].split())
                self.assertIn('technically possible' if duration == 'Technical' else 'legal, contractual or regulatory reasons', group.get_text())
                for field, value in [('metadata', metadata), ('catalogue', catalogue)]:
                    self.assertIn(PRESERVATION['en'][field][value], group.get_text())
                self.assertEqual(members, [ref.find_parent(class_='dataset-section')['data-item-id']
                    for ref in soup.select('.preservation-policy-reference a[href="#' + group['id'] + '"]')])

    def test_grouping_preserves_authored_context_papers_and_contact_anchors(self):
        km, replies = grouping_fixture(4)
        data = path('preservingCUuid', 'producedDataQUuid')
        paper = 'https://example.org/same-paper'
        for index, item in enumerate(replies[data], 1):
            base = path(data, item)
            replies[path(base, 'producedDataNameQUuid')] = 'Same dataset name' if index < 3 else ' \n '
            replies[path(base, 'producedDataDescriptionQUuid')] = AUTHORED
            stage = path(base, 'producedDataStageQUuid')
            replies[stage] = IDS['producedDataStagePublishedAUuid' if index < 4 else 'producedDataStageRawAUuid']
            replies[path(stage, 'producedDataStagePublishedAUuid', 'producedDataPaperQUuid')] = paper
            listing = path(base, 'isPublishedDataQUuid', 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
            replies[listing] = ['repo-first', 'repo-gap', 'repo-contact']
            replies[path(listing, 'repo-first', 'publishedDataRepositoryKindQUuid')] = IDS['publishedDataRepositoryNationalAUuid']
            kind = path(listing, 'repo-contact', 'publishedDataRepositoryKindQUuid')
            replies[kind] = IDS['publishedDataRepositoryDomainSpecificAUuid']
            replies[path(kind, 'publishedDataRepositoryDomainSpecificAUuid', 'domainSpecificRepoNameQUuid')] = {
                'value': {'value': {'type': 'PlainType', 'value': 'Repository ' + str(index)}}}
            contact = path(kind, 'publishedDataRepositoryDomainSpecificAUuid', 'domainSpecificRepoContactBeforeQUuid')
            replies[contact] = IDS['domainSpecificRepoContactBeforeOtherAUuid']
            replies[path(contact, 'domainSpecificRepoContactBeforeOtherAUuid', 'domainSpecificRepoContactBeforeOtherQUuid')] = AUTHORED if index < 3 else ''
        for profile in ('review', 'submission'):
            soup = render_grouping(replies, km, profile)
            self.assertEqual(1, len(soup.select('.preservation-shared-policy')))
            self.assertEqual(3, len(soup.select('.paper-reference-value')))
            self.assertEqual([paper] * 3, [node.get_text() for node in soup.select('.paper-reference-value')])
            self.assertFalse(soup.select('.preservation-shared-policy .answer-detail, .preservation-shared-policy .paper-reference, .preservation-shared-policy .repository-destinations'))
            q10 = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2', replies, km=km, output_profile=profile), 'html.parser')
            for index, dataset in enumerate(soup.select('.dataset-section'), 1):
                self.assertEqual('group-' + str(index), dataset['data-item-id'])
                self.assertEqual(str(index), dataset.h5.select_one('.dataset-label')['data-list-index'])
                self.assertEqual(index < 3, 'Same dataset name' in dataset.h5.get_text())
                self.assertEqual(index >= 3 and profile == 'review',
                                 '(no name given)' in dataset.h5.get_text())
                self.assertEqual(AUTHORED, dataset.select_one('[data-fact-id="preservation-dataset-description"]').decode_contents())
                self.assertIn('published results' if index < 4 else 'raw data', dataset.select_one('[data-fact-id="preservation-data-stage"]').get_text())
                self.assertEqual(index < 4, bool(dataset.select('.paper-reference')))
                ids = ['repo-first', 'repo-gap', 'repo-contact'] if profile == 'review' else ['repo-first', 'repo-contact']
                self.assertEqual(ids, [node['data-item-id'] for node in dataset.select('.repository-distribution')])
                self.assertEqual(['Distribution ' + str(i) + ':' for i in ([1, 2, 3] if profile == 'review' else [1, 3])], [node.get_text() for node in dataset.select('.repository-label')])
                target = dataset.select_one('#repository-contact-' + str(index) + '-3')
                self.assertIsNotNone(target)
                self.assertIn('Repository ' + str(index), target.find_parent(class_='repository-distribution').get_text())
                detail = target.select_one('.answer-detail')
                if index < 3: self.assertEqual(AUTHORED, detail.decode_contents())
                else: self.assertIsNone(detail)
                self.assertEqual(int(index >= 3 and profile == 'review'), len(target.select('.data-gap')))
                self.assertEqual(1, len(q10.select('.repository-contact-reference a[href="#repository-contact-' + str(index) + '-3"]')))
            self.assertFalse(soup.select('p p, p div, p ul, p table, ul:empty, li:empty'))

    def test_compiled_bilingual_binding_contract_has_same_paths_and_valid_options(self):
        contract = json.loads((ROOT / 'requirements/preservation-bindings-2.7.0.json').read_text())['knowledge_models']
        en, zh = [contract[l]['selected_questions'] for l in ('en','zh-Hant')]
        self.assertEqual(16, len(en))
        for name, q in en.items():
            self.assertEqual(IDS[name], q['uuid'])
            self.assertEqual(q['path'], zh[name]['path'])
            self.assertEqual(q['type'], zh[name]['type'])
            self.assertFalse(q['static_template_references'])
            self.assertEqual([a['uuid'] for a in q['choices']], [a['uuid'] for a in zh[name]['choices']])
            self.assertEqual(q['multi_choices'] and [a['uuid'] for a in q['multi_choices']], zh[name]['multi_choices'] and [a['uuid'] for a in zh[name]['multi_choices']])
            self.assertIn(q['uuid'], IDS.values())

    def test_free_descriptions_reasons_and_custom_periods_keep_authored_blocks(self):
        replies = plain('preservation-custom')
        fields = ['producedDataDescriptionQUuid', 'notPublishedReasonOtherQUuid', 'archivedAfterPeriodOtherQUuid']
        for name in fields:
            key = next(p for p in replies if p.endswith(IDS[name]))
            replies[key] = AUTHORED
        soup = render(replies)
        for fact in ['preservation-dataset-description', 'nonpublication-reason', 'archive-minimum-period']:
            self.assertEqual(AUTHORED, soup.select_one(f'.answer-detail[data-fact-id="{fact}"]').decode_contents())
        self.assertFalse(soup.select('p p, p div, p ul'))

    def test_publication_reasons_are_attributed_not_recast_as_destruction(self):
        base = plain(); key = next(p for p in base if p.endswith(IDS['notPublishedReasonQUuid']))
        for option in ['Raw','Results','Intermediate','NoReuse','Cost','Lost','Other']:
            replies = dict(base); replies[key] = IDS[f'notPublishedReason{option}AUuid']
            soup = render(replies)
            self.assertEqual('complete', soup.select_one('[data-fact-id="nonpublication-reason"]')['data-status'])
            self.assertNotIn('will be destroyed', soup.get_text())
        for option in [None, 'Other']:
            replies = dict(base)
            for p in list(replies):
                if p.startswith(key): replies.pop(p)
            if option: replies[key] = IDS['notPublishedReasonOtherAUuid']
            soup = render(replies)
            self.assertEqual('missing', soup.select_one('[data-fact-id="nonpublication-reason"]')['data-status'])
            self.assertIn('This dataset will not be published.', soup.get_text())

    def test_data_stage_options_and_paper_parent_do_not_leak_stale_answers(self):
        replies = plain(); key = next(p for p in replies if p.endswith(IDS['producedDataStageQUuid']))
        for option in ['Raw','Intermediate','Unpublishable','Published']:
            replies[key] = IDS[f'producedDataStage{option}AUuid']
            soup = render(replies)
            self.assertEqual(option == 'Published', bool(soup.select('[data-fact-id="preservation-related-paper"]')))
            self.assertEqual(2, len(soup.select('[data-fact-id="preservation-data-stage"]')))
        replies[key] = ''
        self.assertFalse(render(replies).select('[data-fact-id="preservation-related-paper"]'))

    def test_archive_minimum_and_payer_matrix_keeps_partial_answers(self):
        for replies, period, payer in archive_matrix():
            with self.subTest(period=period,payer=payer):
                archive = render(replies).select_one('.post-project-archive')
                duration = archive.select_one('[data-fact-id="archive-minimum-period"]')
                self.assertEqual('complete' if period in ['archivedAfterPeriodFiveAUuid','archivedAfterPeriodTenAUuid','archivedAfterPeriodFifteenAUuid'] else 'missing', duration['data-status'])
                self.assertEqual('complete' if payer else 'missing', archive.select_one('[data-fact-id="archive-payer"]')['data-status'])
                self.assertEqual('complete', archive.select_one('[data-fact-id="archive-extension"]')['data-status'])

    def test_archival_extension_choices_and_missing_details(self):
        replies = plain(); ap = path('preservingCUuid','archivedAfterQUuid','archivedAfterYesAUuid')
        extension = path(ap,'archivedAfterExtendQUuid')
        for choice, state in [(None,'missing'),('archivedAfterExtendNoAUuid','explicit-no'),('archivedAfterExtendYesAUuid','complete')]:
            other = dict(replies); other[extension] = IDS[choice] if choice else ''
            soup = render(other).select_one('.post-project-archive')
            self.assertEqual(state, soup.select_one('[data-fact-id="archive-extension"]')['data-status'])
            self.assertEqual(choice=='archivedAfterExtendYesAUuid', bool(soup.select('[data-fact-id="archive-extension-actual-use"]')))
        for reason in ['Legal','Budget']:
            other = plain('preservation-custom')
            other[path(extension,'archivedAfterExtendNoAUuid','archivedAfterExtendNoReasonQUuid')] = IDS[f'archivedAfterExtendNo{reason}AUuid']
            self.assertEqual('complete',render(other).select_one('[data-fact-id="archive-extension-limit"]')['data-status'])

    def test_multichoice_renewal_basis_does_not_drop_individual_selections(self):
        base = plain(); key = next(p for p in base if p.endswith(IDS['archivedAfterExtendBasisQUuid']))
        names = ['Actual','Predicted','Budget']; facts = ['actual-use','predicted-use','budget']
        for flags in itertools.product([False,True],repeat=3):
            replies = dict(base); replies[key] = [IDS[f'archivedAfterExtendBasis{n}ChoiceUuid'] for n,flag in zip(names,flags) if flag]
            soup = render(replies)
            for fact, flag in zip(facts,flags): self.assertEqual(flag,bool(soup.select(f'[data-fact-id="archive-extension-{fact}"]')))
            self.assertEqual(not any(flags),bool(soup.select('[data-fact-id="archive-extension-basis"][data-status="missing"]')))

    def test_archive_no_and_missing_are_not_global_nonpreservation_claims(self):
        replies = plain(); key = path('preservingCUuid','archivedAfterQUuid')
        replies[key] = IDS['archivedAfterNoAUuid']
        soup = render(replies); archive=soup.select_one('.post-project-archive')
        self.assertEqual('project',archive['data-scope'])
        self.assertEqual('explicit-no',archive.select_one('[data-fact-id="post-project-archive"]')['data-status'])
        self.assertFalse(archive.select('[data-fact-id="archive-payer"], [data-fact-id="archive-minimum-period"]'))
        self.assertIn('Retention period (prepaid): 15 years.',soup.get_text())
        replies[key] = ''
        self.assertFalse(render(replies).select('.post-project-archive'))

    def test_repository_funding_does_not_fall_under_the_cold_storage_heading(self):
        soup=render(plain())
        archive=soup.select_one('.post-project-archive')
        resources=soup.select_one('.preservation-resources')
        self.assertFalse(resources.find_parent(class_='post-project-archive'))
        self.assertIn(archive,list(resources.next_siblings))
        self.assertEqual('Repository costs and publication preparation',resources.find_previous('h4').get_text())
        only_archive=render({path('preservingCUuid','archivedAfterQUuid'):IDS['archivedAfterNoAUuid']})
        self.assertFalse(only_archive.select('.preservation-resources'))
        self.assertEqual(['Project-wide cold storage after the project'],[h.get_text() for h in only_archive.select('h4')])

    def test_negative_migration_choices_remain_visible_and_unknown_is_not_no(self):
        ap = path('preservingCUuid','archivedAfterQUuid','archivedAfterYesAUuid')
        for name, fact in [('Formats','archive-format-migration'),('Media','archive-media-migration')]:
            for choice,state in [(None,'missing'),('No','explicit-no'),('Yes','complete')]:
                replies=plain(); replies[path(ap,f'archivedAfter{name}QUuid')] = IDS[f'archivedAfter{name}{choice}AUuid'] if choice else ''
                self.assertEqual(state,render(replies).select_one(f'[data-fact-id="{fact}"]')['data-status'])

    def test_selection_review_is_not_a_fabricated_policy_and_empty_fallback_survives(self):
        self.assertIn('data-status="missing-output"',render_question(Q11,{}))
        for case in preservation_cases('en'):
            soup=render(plain(case)); review=soup.select_one('[data-fact-id="preservation-selection-review"]')
            self.assertEqual('needs-review',review['data-status'])
            self.assertNotIn('All data will be preserved',soup.get_text())
