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

Q11 = 'src/questions/11-data-preservation.html.j2'
AUTHORED = '<p>Keep Selection-2027-12-31.csv.</p><p>Do not merge this paragraph.</p><ul><li>First.</li><li>Second.</li></ul>'


def plain(case='preservation-complete'):
    return {p: v['value'] for p,v in preservation_cases('en')[case].items()}


def render(replies): return BeautifulSoup(render_question(Q11, replies), 'html.parser')


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
