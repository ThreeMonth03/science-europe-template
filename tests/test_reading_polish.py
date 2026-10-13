import itertools
from copy import deepcopy
import unittest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, Undefined
from test_science_europe_contract import ROOT, render_question
from test_format_volume import values, FORMATS, Q2
from generate_storage_fixtures import storage_cases
from current_support import IDS, environment, path, PREFIX
from check_answer_mapping import chapter, question, schema
from check_project_acronym import fixture as project_fixture


class ReadingPolishTests(unittest.TestCase):
    def test_known_other_arrangements_survive_only_missing_active_details(self):
        from check_sentence_layout import partial_fixture
        cases = [
            ('01-how-data', 'creatingCUuid metadataQUuid metadataExploreAUuid provenanceQUuid '
             'provenanceOtherAUuid provenanceOtherQUuid', 'provenance', 'provenance-detail',
             'We use other arrangements to document data provenance.'),
            ('02-what-data', 'creatingCUuid measuredQUuid measuredYesAUuid measuredDataQUuid ITEM '
             'measuredDataWhoQUuid measuredDataWhoExternalAUuid mdExternalOwnershipQUuid '
             'mdExternalOwnershipOtherAUuid mdExternalOwnershipOtherQUuid', 'external-ownership', 'external-ownership',
             'Other arrangements have been made for ownership of this dataset.'),
            ('11-data-preservation', 'preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid '
             'isPublishedDataYesAUuid publishedDistrosQUuid ITEM publishedDataRepositoryKindQUuid '
             'publishedDataRepositoryDomainSpecificAUuid domainSpecificRepoContactBeforeQUuid '
             'domainSpecificRepoContactBeforeOtherAUuid domainSpecificRepoContactBeforeOtherQUuid',
             'repository-contact-arrangements', 'repository-contact-arrangements',
             'Other arrangements have been made for contacting the repository.'),
        ]
        authored = '<p>Original arrangement <strong>remains</strong>.</p><ul><li>Keep the owner-specific detail.</li></ul>'
        for name, chain, fact, gap, sentence in cases:
            km, base, detail = partial_fixture(chain)
            leaf = detail.rsplit('.', 2)[0]
            qid, choice = leaf.split('.')[-1], base[leaf]
            template = 'src/questions/' + name + '.html.j2'
            for context, profile, value in itertools.product(({}, {'km': km}), ('review', 'submission'),
                    (None, '', ' \t\n\u3000', authored)):
                values = dict(base)
                if value is not None: values[detail] = value
                output = render_question(template, values, output_profile=profile, **context)
                soup = BeautifulSoup(output, 'html.parser')
                blank = not (value or '').strip()
                with self.subTest(name=name, profile=profile, value=value, schema=bool(context)):
                    self.assertEqual(int(blank), output.count(sentence))
                    self.assertEqual(not blank, authored in output)
                    self.assertEqual(blank and profile == 'review', bool(soup.select(
                        '.data-gap[data-fact-id="' + gap + '"]')))
                    if blank:
                        self.assertEqual(sentence, soup.select_one(
                            '[data-fact-id="' + fact + '"][data-status="complete"]').get_text())
                    if profile == 'submission': self.assertFalse(soup.select('.data-gap,.data-review'))
                    if name == '01-how-data': self.assertIn('Provenance', [h.get_text() for h in soup.select('h4')])
                    if name == '11-data-preservation': self.assertIsNotNone(soup.select_one('#repository-contact-1-1'))
            for profile, control in itertools.product(('review', 'submission'),
                    ('missing', 'unknown', 'removed-question', 'wrong-type', 'removed-choice', 'dangling-choice')):
                altered, values = deepcopy(km), {**base, detail: authored}
                if control == 'missing': del values[leaf]
                elif control == 'unknown': values[leaf] = 'unknown-option'
                elif control == 'removed-question': del altered['entities']['questions'][qid]
                elif control == 'wrong-type': altered['entities']['questions'][qid]['questionType'] = 'ValueQuestion'
                elif control == 'removed-choice': altered['entities']['questions'][qid]['answerUuids'] = []
                else: del altered['entities']['answers'][choice]
                # Only the new fallback is guarded here; existing filled branches
                # are deliberately outside this repair's source-change scope.
                values.pop(detail) if control not in ('missing', 'unknown') else None
                output = render_question(template, values, km=altered, output_profile=profile)
                self.assertNotIn(sentence, output, (name, control))
                if control in ('missing', 'unknown'): self.assertNotIn(authored, output)
            for ancestor in base.keys() - {leaf}:
                inactive = {**base, detail: authored}
                inactive.pop(ancestor)
                output = render_question(template, inactive, km=km, output_profile='submission')
                self.assertNotIn(sentence, output, (name, ancestor))
                self.assertNotIn(authored, output, (name, ancestor))
            typed_env = environment(ROOT)
            fallback = typed_env.filters['reply_str_value']
            typed_env.filters['reply_str_value'] = lambda reply: str(reply['value']['value']) if isinstance(reply, dict) else fallback(reply)
            typed_render = typed_env.from_string(PREFIX + "{% include '" + template + "' %}").render
            for reply_type in ('AnswerReply', 'StringReply', 'ItemListReply'):
                values = {**base, leaf: {'value': {'type': reply_type, 'value': choice}}}
                self.assertEqual(reply_type == 'AnswerReply', sentence in typed_render(
                    repliesMap=values, km=km, output_profile='submission'), (name, reply_type))
            if name != '01-how-data':
                listing = next(key for key, value in base.items() if isinstance(value, list))
                multiple = {**base, listing: ['ITEM', 'ITEM2']}
                for key, value in base.items():
                    if key.startswith(listing + '.ITEM.'):
                        multiple[key.replace(listing + '.ITEM.', listing + '.ITEM2.', 1)] = value
                multiple[detail.replace(listing + '.ITEM.', listing + '.ITEM2.', 1)] = authored
                soup = BeautifulSoup(render_question(template, multiple, km=km, output_profile='submission'), 'html.parser')
                selector = '.collection-dataset' if name == '02-what-data' else '.dataset-section'
                owners = soup.select(selector)
                self.assertEqual(['ITEM', 'ITEM2'], [node['data-item-id'] for node in owners])
                self.assertIn(sentence, owners[0].get_text())
                self.assertNotIn('owner-specific detail', owners[0].get_text())
                self.assertNotIn(sentence, owners[1].get_text())
                self.assertIn(authored, str(owners[1]))
                if name == '11-data-preservation':
                    self.assertIsNotNone(owners[0].select_one('#repository-contact-1-1'))
                    self.assertIsNotNone(owners[1].select_one('#repository-contact-2-1'))

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

        # The real KM places capture and both paper followups inside each list item.
        capture = '4e84a44f-e66b-42f5-bb42-7e6c4bd3b79b'
        digital, paper = '407560bc-705a-4885-85d6-4f61fe58eeed', '374974a6-2c51-4508-aa93-9ef8f1ef65fd'
        entry = '32f5bc5c-6bc6-4df0-849f-1619951c5b98'
        team, member, other = ('9d51aae1-ca1b-4267-b0df-d43dc85f5bc6',
                              '9660950a-41d7-4c3b-a6fd-97e58c8fa412', '82ef3ee8-461e-4f5b-a66a-2d4aaccbe68b')
        detail = 'f0e57014-79ad-4f2d-becd-e00f50ed1770'
        available = 'a205f751-cbb6-4f58-a692-2ba450e1e133'
        not_yet, yes = '1c6da256-72d5-45b1-842e-c1458e6d2e21', '83d23b9f-4b91-4444-8e38-f1c7982e41aa'
        question(km, fields, capture, 'OptionsQuestion', [digital, paper])
        followups = km['entities']['answers'][paper]['followUpUuids']
        question(km, followups, entry, 'OptionsQuestion', [team, member, other])
        question(km, followups, available, 'OptionsQuestion', [not_yet, yes])
        question(km, km['entities']['answers'][other]['followUpUuids'], detail, 'ValueQuestion')['valueType'] = 'TextQuestionValueType'
        for qid in (IDS['neqDataSetsNameQUuid'], IDS['neqDataSetsDescQUuid']):
            km['entities']['questions'][qid]['valueType'] = 'TextQuestionValueType'
        base = path(listing, 'dataset-a')
        capture_path = path(base, capture)
        entry_path, available_path = path(capture_path, paper, entry), path(capture_path, paper, available)
        detail_path = path(entry_path, other, detail)
        capture_facts = {digital: 'All data in this dataset will be captured immediately in digital form.',
                         paper: 'Data in this dataset will first be captured on paper.'}
        entry_facts = {team: 'A specialized team will perform the data entry.',
                       member: 'A member of the project team will perform the data entry.',
                       other: 'Other arrangements have been made for data entry.'}
        available_facts = {yes: 'We have arranged for someone to make this dataset available in digital form.',
                           not_yet: 'We have not yet arranged for someone to make this dataset available in digital form.'}
        lead = 'Other data-entry arrangements:'
        authored = '<p>Keep the original entry arrangement.</p><ul><li>Double entry, not scanning.</li></ul><table><tr><td>Original check</td></tr></table>'
        description = '<p>Original dataset description.</p><ul><li>Retain original paper records.</li></ul>'
        fixed_facts = list(capture_facts.values()) + list(entry_facts.values()) + list(available_facts.values())
        scenarios = [(digital, other, not_yet, authored), (paper, None, None, authored),
                     (paper, team, yes, authored), (paper, member, not_yet, authored),
                     (paper, None, yes, authored), (paper, 'unknown', 'unknown', authored),
                     (None, other, yes, authored), ('unknown', other, yes, authored)]
        scenarios += [(paper, other, yes, value) for value in (None, '', ' \t\n\u3000', authored)]
        for (capture_choice, entry_choice, available_choice, value), profile in itertools.product(scenarios, ('review', 'submission')):
            replies = {parent: IDS['neqDataYesAUuid'], listing: ['dataset-a'],
                       path(base, 'neqDataSetsNameQUuid'): 'Survey <2026> & logs',
                       path(base, 'neqDataSetsDescQUuid'): description}
            for key, answer in ((capture_path, capture_choice), (entry_path, entry_choice),
                                (available_path, available_choice), (detail_path, value)):
                if answer is not None: replies[key] = answer
            output = render_question(Q2, replies, km=km, output_profile=profile)
            expected = [capture_facts[capture_choice]] if capture_choice in capture_facts else []
            if capture_choice == paper:
                if entry_choice in entry_facts and (entry_choice != other or not (value or '').strip()):
                    expected.append(entry_facts[entry_choice])
                if available_choice in available_facts: expected.append(available_facts[available_choice])
            for sentence in fixed_facts: self.assertEqual(sentence in expected, sentence in output, (capture_choice, entry_choice, sentence))
            has_detail = capture_choice == paper and entry_choice == other and bool((value or '').strip())
            self.assertEqual(has_detail, authored in output)
            self.assertEqual(has_detail, lead in output)
            self.assertIn(description, output)
            soup = BeautifulSoup(output, 'html.parser')
            owned = soup.select_one('li[data-item-id="dataset-a"]')
            self.assertIsNotNone(owned)
            self.assertEqual('Survey <2026> & logs', owned.select_one('.item-label').get_text())
            self.assertFalse(owned.select('survey, p p'))
            if expected:
                self.assertIn(' '.join(expected), [p.get_text(' ', strip=True) for p in owned.select('p')])
            if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))

        values = {parent: IDS['neqDataYesAUuid'], listing: ['dataset-a'], capture_path: paper,
                  entry_path: other, available_path: yes, detail_path: authored,
                  path(base, 'neqDataSetsDescQUuid'): description}
        for qid, choice, absent in ((capture, paper, [capture_facts[paper], lead, authored, available_facts[yes]]),
                                   (entry, other, [lead, authored]), (available, yes, [available_facts[yes]])):
            for mutation, profile in itertools.product(('removed', 'type', 'detached', 'choice', 'dangling'), ('review', 'submission')):
                altered = deepcopy(km)
                if mutation == 'removed': del altered['entities']['questions'][qid]
                elif mutation == 'type': altered['entities']['questions'][qid]['questionType'] = 'ValueQuestion'
                elif mutation == 'detached':
                    container = altered['entities']['questions'][IDS['neqDataSetsQUuid']]['itemTemplateQuestionUuids'] if qid == capture else altered['entities']['answers'][paper]['followUpUuids']
                    container.remove(qid)
                elif mutation == 'choice': altered['entities']['questions'][qid]['answerUuids'].remove(choice)
                else: del altered['entities']['answers'][choice]
                output = render_question(Q2, values, km=altered, output_profile=profile)
                for sentence in absent: self.assertNotIn(sentence, output, (qid, mutation, sentence))
                self.assertIn(description, output)
                if qid != capture: self.assertIn(capture_facts[paper], output)
                if qid == entry: self.assertIn(available_facts[yes], output)
                if qid == available: self.assertIn(authored, output)
        for mutation in ('removed', 'type', 'value-type'):
            altered = deepcopy(km)
            if mutation == 'removed': del altered['entities']['questions'][detail]
            elif mutation == 'type': altered['entities']['questions'][detail]['questionType'] = 'OptionsQuestion'
            else: altered['entities']['questions'][detail]['valueType'] = 'NumberQuestionValueType'
            output = render_question(Q2, values, km=altered, output_profile='submission')
            self.assertNotIn(authored, output)
            self.assertIn(entry_facts[other], output)
            self.assertIn(available_facts[yes], output)
        for key, invalid in ((parent, None), (parent, '514befe5-76b0-4e4e-bdf5-2bc164e38d7f'),
                             (parent, 'unknown'), (listing, None), (listing, []), (listing, ['different-item'])):
            inactive = dict(values)
            if invalid is None: inactive.pop(key)
            else: inactive[key] = invalid
            output = render_question(Q2, inactive, km=km, output_profile='submission')
            for sentence in fixed_facts + [authored, description]: self.assertNotIn(sentence, output)
        typed_env = environment(ROOT, escape=True)
        typed_env.filters['reply_str_value'] = lambda reply: '' if isinstance(reply, Undefined) or reply is None else (
            str(reply['value']['value']) if isinstance(reply, dict) and isinstance(reply.get('value'), dict)
            else str(reply['value']) if isinstance(reply, dict) and 'value' in reply else str(reply))
        typed_render = typed_env.from_string(PREFIX + "{% include 'src/questions/02-what-data.html.j2' %}").render
        for key, choice, absent in ((parent, IDS['neqDataYesAUuid'], fixed_facts + [authored, description]),
                                   (capture_path, paper, [capture_facts[paper], lead, authored, available_facts[yes]]),
                                   (entry_path, other, [lead, authored]),
                                   (available_path, yes, [available_facts[yes]])):
            invalid = dict(values, **{key: {'value': {'type': 'StringReply', 'value': choice}}})
            output = typed_render(repliesMap=invalid, km=km, output_profile='submission')
            for sentence in absent: self.assertNotIn(sentence, output, (key, 'wrong-reply-type'))
        invalid = dict(values, **{detail_path: {'value': {'type': 'AnswerReply', 'value': authored}}})
        output = typed_render(repliesMap=invalid, km=km, output_profile='submission')
        self.assertNotIn(authored, output)
        self.assertIn(entry_facts[other], output)
        typed = dict(values)
        for key in (parent, capture_path, entry_path, available_path):
            typed[key] = {'value': {'type': 'AnswerReply', 'value': values[key]}}
        typed[detail_path] = {'value': {'type': 'StringReply', 'value': authored}}
        output = typed_render(repliesMap=typed, km=km, output_profile='submission')
        for sentence in (capture_facts[paper], available_facts[yes], authored): self.assertIn(sentence, output)
        # A second nameless record keeps its current ordinal and its own paper facts.
        multiple = dict(values, **{capture_path: digital, listing: ['dataset-a', 'dataset-b']})
        second = path(listing, 'dataset-b')
        multiple.update({path(second, 'neqDataSetsNameQUuid'): ' \u3000', path(second, capture): paper,
                         path(second, capture, paper, entry): member,
                         path(second, capture, paper, available): not_yet})
        soup = BeautifulSoup(render_question(Q2, multiple, km=km, output_profile='submission'), 'html.parser')
        owned = soup.select('li[data-item-id]')
        self.assertEqual(['dataset-a', 'dataset-b'], [li['data-item-id'] for li in owned])
        self.assertIn(capture_facts[digital], owned[0].get_text())
        self.assertNotIn(entry_facts[member], owned[0].get_text())
        self.assertIn('Non-equipment dataset 2', owned[1].get_text())
        for sentence in (capture_facts[paper], entry_facts[member], available_facts[not_yet]):
            self.assertIn(sentence, owned[1].get_text())
        self.assertNotIn(description, str(owned[1]))

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
