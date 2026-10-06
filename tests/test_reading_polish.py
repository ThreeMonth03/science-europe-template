import itertools
from copy import deepcopy
import unittest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from test_science_europe_contract import ROOT, render_question
from test_format_volume import values, FORMATS, Q2
from generate_storage_fixtures import storage_cases
from current_support import IDS, environment, path, PREFIX
from check_answer_mapping import chapter, question, schema
from check_project_acronym import fixture as project_fixture


class ReadingPolishTests(unittest.TestCase):
    def test_metadata_standard_sentences_keep_selected_names_and_parent_guards(self):
        parent = path('creatingCUuid', 'metadataQUuid')
        standards = path(parent, 'metadataExploreAUuid', 'metadataStandardsQUuid')
        prefix = path(standards, 'metadataStandardsExploreAUuid')
        options = [('DC', 'Dublin Core'), ('DataCite', 'DataCite'),
                   ('DDI', 'DDI (Data Documentation Initiative)')]
        render = environment(ROOT, escape=True).from_string(
            PREFIX + "{% include 'src/questions/03-docs-metadata.html.j2' %}").render
        for selected, profile in itertools.product(itertools.product([False, True], repeat=3), ['review', 'submission']):
            replies = {parent: IDS['metadataExploreAUuid'], standards: IDS['metadataStandardsExploreAUuid']}
            for (key, _), enabled in zip(options, selected):
                if enabled:
                    replies[path(prefix, 'metadataStandards' + key + 'QUuid')] = IDS['metadataStandards' + key + 'YesAUuid']
            names = [label for (_, label), enabled in zip(options, selected) if enabled]
            expected = ''
            if names:
                joined = names[0] if len(names) == 1 else ' and '.join(names) if len(names) == 2 else ', '.join(names[:-1]) + ', and ' + names[-1]
                expected = 'We will document the data using the ' + joined + (' metadata standard.' if len(names) == 1 else ' metadata standards.')
            soup = BeautifulSoup(render(repliesMap=replies, output_profile=profile), 'html.parser')
            paragraphs = [p.get_text() for p in soup.select('.metadata-policy p') if 'document the data using' in p.get_text()]
            self.assertEqual([expected] if expected else [], paragraphs)
            for guard in [parent, standards]:
                inactive = dict(replies, **{guard: 'unknown'})
                self.assertNotIn('document the data using', render(repliesMap=inactive, output_profile=profile))

        keywords = path(prefix, 'metadataStandardsKeywordsQUuid')
        fact = 'We will include keywords or relevant ontology references to optimize the possibility for discovery and potential reuse.'
        km = schema()
        question(km, chapter(km, IDS['creatingCUuid']), IDS['metadataQUuid'], 'OptionsQuestion', [IDS['metadataExploreAUuid']])
        question(km, km['entities']['answers'][IDS['metadataExploreAUuid']]['followUpUuids'],
                 IDS['metadataStandardsQUuid'], 'OptionsQuestion', [IDS['metadataStandardsExploreAUuid']])
        question(km, km['entities']['answers'][IDS['metadataStandardsExploreAUuid']]['followUpUuids'],
                 IDS['metadataStandardsKeywordsQUuid'], 'OptionsQuestion',
                 [IDS['metadataStandardsKeywordsYesAUuid'], 'ca706a0f-ef35-4ee6-ba48-c73a4c33dafe'])
        for choice, profile in itertools.product((None, 'unknown', IDS['metadataStandardsKeywordsYesAUuid'],
                'ca706a0f-ef35-4ee6-ba48-c73a4c33dafe'), ('review', 'submission')):
            replies = {parent: IDS['metadataExploreAUuid'], standards: IDS['metadataStandardsExploreAUuid']}
            if choice is not None: replies[keywords] = choice
            output = render(km=km, repliesMap=replies, output_profile=profile)
            self.assertEqual(choice == IDS['metadataStandardsKeywordsYesAUuid'], fact in output)
            self.assertNotIn('keywords and relevant ontology references', output)
            for guard in (parent, standards):
                inactive = {key: value for key, value in replies.items() if key != guard}
                self.assertNotIn(fact, render(km=km, repliesMap=inactive, output_profile=profile))
        replies[keywords] = IDS['metadataStandardsKeywordsYesAUuid']
        for mutation in ('removed', 'type', 'choice', 'dangling'):
            altered = deepcopy(km)
            if mutation == 'removed': del altered['entities']['questions'][IDS['metadataStandardsKeywordsQUuid']]
            elif mutation == 'type': altered['entities']['questions'][IDS['metadataStandardsKeywordsQUuid']]['questionType'] = 'ValueQuestion'
            elif mutation == 'choice': altered['entities']['questions'][IDS['metadataStandardsKeywordsQUuid']]['answerUuids'] = []
            else: del altered['entities']['answers'][IDS['metadataStandardsKeywordsYesAUuid']]
            self.assertNotIn(fact, render(km=altered, repliesMap=replies, output_profile='submission'))

    def test_repository_cost_prose_preserves_payer_and_independent_preparation_budget(self):
        charges = path('preservingCUuid', 'repoChargesQUuid')
        payer = path(charges, 'repoChargesYesAUuid', 'repoChargesHowPayQUuid')
        preparation = path('preservingCUuid', 'budgetTimeEffortQUuid')
        sentences = {
            'Budgeted': 'The project budget includes the repository service fees.',
            'Department': 'A participating department will cover the repository service fees.',
            'Institute': 'A participating institute will cover the repository service fees.',
        }
        free = 'The repositories we use do not charge for their services.'
        funded = 'We have allocated funds for the time and effort needed to prepare the data for publication.'
        unfunded = 'We have not budgeted for the time and effort needed to prepare the data for publication.'
        self.assertEqual('f765ae2f-7d22-478c-bd53-1a388c4dbcc9', IDS.get('budgetTimeEffortNoAUuid'))
        authored = 'Keep v1.2: 0 TWD; department A does not pay.'
        render = environment(ROOT, escape=True).from_string(
            PREFIX + "{% include 'src/questions/11-data-preservation.html.j2' %}").render
        for charge, payment, budget, profile in itertools.product([None, 'No', 'Yes', 'unknown'], [None, *sentences, 'Other', 'unknown'], [None, 'No', 'Yes'], ['review', 'submission']):
            replies = {path(payer, 'repoChargesHowPayOtherAUuid', 'repoChargesHowPayOtherQUuid'): authored}
            for key, value, stem in [(charges, charge, 'repoCharges'), (payer, payment, 'repoChargesHowPay'), (preparation, budget, 'budgetTimeEffort')]:
                if value is not None: replies[key] = IDS.get(stem + value + 'AUuid', value)
            text = BeautifulSoup(render(repliesMap=replies, output_profile=profile), 'html.parser').get_text(' ', strip=True)
            for option, sentence in sentences.items():
                self.assertEqual(charge == 'Yes' and payment == option, sentence in text)
            self.assertEqual(charge == 'No', free in text)
            self.assertEqual(budget == 'Yes', funded in text)
            self.assertEqual(budget == 'No', unfunded in text)
            self.assertEqual(charge == 'Yes' and payment == 'Other', authored in text)

        km, replies = project_fixture()
        children = km['entities']['questions'][IDS['projectsQUuid']]['itemTemplateQuestionUuids']
        children = question(km, children, IDS['costQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
        question(km, children, IDS['costTitleQUuid'], 'ValueQuestion')
        question(km, children, IDS['costCoverQUuid'], 'OptionsQuestion', [IDS['costCoverGrantAUuid'], IDS['costCoverOtherAUuid']])
        question(km, km['entities']['answers'][IDS['costCoverOtherAUuid']]['followUpUuids'], IDS['costCoverOtherHowQUuid'], 'ValueQuestion')
        listing = path('adminDetailsCUuid', 'projectsQUuid', 'project-a', 'costQUuid')
        coverage = path(listing, 'resource-a', 'costCoverQUuid')
        detail = path(coverage, 'costCoverOtherAUuid', 'costCoverOtherHowQUuid')
        replies.update({listing: ['resource-a'], path(listing, 'resource-a', 'costTitleQUuid'): 'Archival storage'})
        fact = 'Other funding arrangements are planned.'
        authored = '<p>Keep 0 TWD.</p><ul><li>Department A does not pay.</li></ul><table><tr><td>Original funding</td></tr></table>'
        for choice, value, profile in itertools.product((None, 'unknown', IDS['costCoverGrantAUuid'], IDS['costCoverOtherAUuid']),
                (None, '', ' \t\n\u3000', authored), ('review', 'submission')):
            values = dict(replies)
            if choice is not None: values[coverage] = choice
            if value is not None: values[detail] = value
            output = render_question('src/questions/15-required-resources.html.j2', values, km=km, output_profile=profile)
            soup = BeautifulSoup(output, 'html.parser')
            self.assertEqual(choice == IDS['costCoverOtherAUuid'] and not (value or '').strip(), fact in output)
            self.assertEqual(choice == IDS['costCoverOtherAUuid'] and value == authored, authored in output)
            self.assertEqual(choice == IDS['costCoverGrantAUuid'], 'This cost will be covered by a funding grant.' in output)
            self.assertIn('Archival storage', output)
            if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))
        for mutation in ('removed', 'type', 'choice', 'dangling', 'project', 'resource'):
            altered, values = deepcopy(km), dict(replies, **{coverage: IDS['costCoverOtherAUuid']})
            if mutation == 'removed': del altered['entities']['questions'][IDS['costCoverQUuid']]
            elif mutation == 'type': altered['entities']['questions'][IDS['costCoverQUuid']]['questionType'] = 'ValueQuestion'
            elif mutation == 'choice': altered['entities']['questions'][IDS['costCoverQUuid']]['answerUuids'] = []
            elif mutation == 'dangling': del altered['entities']['answers'][IDS['costCoverOtherAUuid']]
            elif mutation == 'project': values[path('adminDetailsCUuid', 'projectsQUuid')] = []
            else: values[listing] = []
            self.assertNotIn(fact, render_question('src/questions/15-required-resources.html.j2', values, km=altered, output_profile='submission'))

    def test_fixed_english_prose_uses_complete_natural_sentences(self):
        source = '\n'.join((ROOT/path).read_text() for path in [
            'src/questions/05-store-backup.html.j2',
            'src/questions/06-access-security.html.j2',
            'src/questions/07-personal-data.html.j2',
            'src/questions/08-copyright-ipr.html.j2',
            'src/questions/09-ethical-issues.html.j2',
        ])
        for phrase in [
            'There is no shared workspace used',
            'secure HTTP (https://...)',
            'We pseudonymize inside the project',
            'We will use following policies',
            "based on subject's consent",
            'in order to fulfil contract',
            'We will be working with the philosophy',
            'restrictions are falling away',
            'We will have not decided yet',
            're-users',
        ]:
            self.assertNotIn(phrase, source)
        for phrase in [
            'The project will not use a shared workspace to work with data.',
            'All project web services are accessible through HTTPS.',
            'We will use the following policies and procedures:',
            'with the consent of the data subjects.',
            'We will manage our data according to the principle',
            'Data will be released as soon as the restrictions no longer apply.',
        ]:
            self.assertIn(phrase, source)
        for phrase in [
            'data loss and data disclosure',
            'data loss and data tampering',
            'data disclosure and data tampering',
            'data loss, data disclosure, and data tampering',
        ]:
            self.assertIn(phrase, source)
        self.assertNotIn("join(' and ')", source)
        self.assertEqual(5, source.count('risk_list('))
        self.assertEqual(1, source.count('macro risk_list'))
        self.assertEqual(1, source.count('We have not considered the possible impact on the project or organization of '))

        ownership = path('creatingCUuid', 'ownershipQUuid')
        detail = path(ownership, 'ownershipOtherAUuid', 'ownershipOtherQUuid')
        fact = 'Rights to the collected data are arranged in another way.'
        authored = '<p>Keep the original ownership arrangement.</p><ul><li>Do not invent a rightsholder.</li></ul>'
        km = schema()
        question(km, chapter(km, IDS['creatingCUuid']), IDS['ownershipQUuid'], 'OptionsQuestion', [IDS['ownershipOtherAUuid'], IDS['ownershipPIAUuid']])
        question(km, km['entities']['answers'][IDS['ownershipOtherAUuid']]['followUpUuids'], IDS['ownershipOtherQUuid'], 'ValueQuestion')
        for choice, value, profile in itertools.product((None, 'unknown', IDS['ownershipPIAUuid'], IDS['ownershipOtherAUuid']),
                (None, '', ' \t\n\u3000', authored), ('review', 'submission')):
            replies = {}
            if choice is not None: replies[ownership] = choice
            if value is not None: replies[detail] = value
            output = render_question('src/questions/08-copyright-ipr.html.j2', replies, km=km, output_profile=profile)
            self.assertEqual(choice == IDS['ownershipOtherAUuid'] and not (value or '').strip(), fact in output)
            self.assertEqual(choice == IDS['ownershipOtherAUuid'] and value == authored, authored in output)
            if profile == 'submission': self.assertFalse(BeautifulSoup(output, 'html.parser').select('.data-gap, .data-review'))
        replies = {ownership: IDS['ownershipOtherAUuid']}
        for mutation in ('removed', 'type', 'choice', 'dangling'):
            altered = deepcopy(km)
            if mutation == 'removed': del altered['entities']['questions'][IDS['ownershipQUuid']]
            elif mutation == 'type': altered['entities']['questions'][IDS['ownershipQUuid']]['questionType'] = 'ValueQuestion'
            elif mutation == 'choice': altered['entities']['questions'][IDS['ownershipQUuid']]['answerUuids'] = []
            else: del altered['entities']['answers'][IDS['ownershipOtherAUuid']]
            self.assertNotIn(fact, render_question('src/questions/08-copyright-ipr.html.j2', replies, km=altered, output_profile='submission'))

    def test_missing_fields_have_one_lead_and_one_terminal_period(self):
        soup = BeautifulSoup(render_question(Q2, {FORMATS: ['format-1']}), 'html.parser')
        gap = soup.select_one('.format-description p.data-gap')
        self.assertEqual(1, gap.get_text().count('Information still needed:'))
        self.assertEqual(4, len(gap.select('[data-status="missing"]')))
        self.assertEqual(1, gap.get_text().count('.'))
        self.assertEqual(3, gap.get_text().count(', '))

        parent = path('creatingCUuid', 'neqDataQUuid')
        listing = path(parent, 'neqDataYesAUuid', 'neqDataSetsQUuid')
        kind = path(parent, 'neqDataYesAUuid', 'neqDataQuestQUuid')
        fact = 'The project includes data capture that does not use measurement equipment.'
        km = schema()
        question(km, chapter(km, IDS['creatingCUuid']), IDS['neqDataQUuid'], 'OptionsQuestion',
                 [IDS['neqDataYesAUuid'], '514befe5-76b0-4e4e-bdf5-2bc164e38d7f'])
        children = km['entities']['answers'][IDS['neqDataYesAUuid']]['followUpUuids']
        question(km, children, IDS['neqDataQuestQUuid'], 'OptionsQuestion', [IDS['neqDataQuestYesAUuid']])
        fields = question(km, children, IDS['neqDataSetsQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
        question(km, fields, IDS['neqDataSetsNameQUuid'], 'ValueQuestion')
        question(km, fields, IDS['neqDataSetsDescQUuid'], 'ValueQuestion')
        for choice, items, profile in itertools.product((None, 'unknown', '514befe5-76b0-4e4e-bdf5-2bc164e38d7f', IDS['neqDataYesAUuid']),
                (None, []), ('review', 'submission')):
            replies = {path(listing, 'removed-item', 'neqDataSetsNameQUuid'): 'Stale non-equipment data'}
            if choice is not None: replies[parent] = choice
            if items is not None: replies[listing] = items
            output = render_question(Q2, replies, km=km, output_profile=profile)
            self.assertEqual(choice == IDS['neqDataYesAUuid'], fact in output)
            self.assertNotIn('Stale non-equipment data', output)
            if profile == 'submission': self.assertFalse(BeautifulSoup(output, 'html.parser').select('.data-gap, .data-review'))
        for replies in ({parent: IDS['neqDataYesAUuid'], kind: IDS['neqDataQuestYesAUuid']},
                {parent: IDS['neqDataYesAUuid'], listing: ['dataset-a'], path(listing, 'dataset-a', 'neqDataSetsDescQUuid'): 'Original dataset description.'}):
            output = render_question(Q2, replies, km=km, output_profile='submission')
            self.assertNotIn(fact, output)
            self.assertIn('questionnaires' if kind in replies else 'Original dataset description.', output)
        for mutation in ('removed', 'type', 'choice', 'dangling'):
            altered = deepcopy(km)
            if mutation == 'removed': del altered['entities']['questions'][IDS['neqDataQUuid']]
            elif mutation == 'type': altered['entities']['questions'][IDS['neqDataQUuid']]['questionType'] = 'ValueQuestion'
            elif mutation == 'choice': altered['entities']['questions'][IDS['neqDataQUuid']]['answerUuids'] = []
            else: del altered['entities']['answers'][IDS['neqDataYesAUuid']]
            self.assertNotIn(fact, render_question(Q2, {parent: IDS['neqDataYesAUuid']}, km=altered, output_profile='submission'))

    def test_quantity_keeps_short_units_but_not_long_text_unbreakable(self):
        env = Environment(loader=FileSystemLoader(ROOT), extensions=['jinja2.ext.do'])
        env.filters['markdown'] = lambda v: v
        render = env.from_string("{% import 'src/macros.html.j2' as m %}{{ m.quantity(value, 'GB') }}").render
        for value in ('0', '0.0001', '120'):
            soup = BeautifulSoup(render(value=value), 'html.parser')
            self.assertEqual(value + '\xa0GB', soup.select_one('.quantity').get_text())
        self.assertNotIn('class="quantity"', render(value='Long free answer ' * 10))

    def test_only_simple_repository_and_standard_licence_are_joinable(self):
        for case in ('storage-sharing', 'storage-sharing-partial'):
            replies = {k: v['value'] for k,v in storage_cases('en')[case].items()}
            soup = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2', replies), 'html.parser')
            self.assertEqual(1, len(soup.select('.license-entry.joined-policy')))
            self.assertEqual(2 if case == 'storage-sharing' else 1, len(soup.select('.repository-arrangement.joined-policy')))
            self.assertFalse(soup.select('.joined-policy .answer-detail, .joined-policy .data-gap'))
            self.assertFalse(soup.select('.distribution-reading-unit > p.data-gap'))
            self.assertIsNotNone(soup.select_one('.license-entry:not(.joined-policy) .answer-detail'))
