"""Fixed choices become prose; missing answers and authored blocks stay distinct."""
import itertools
from copy import deepcopy
import unittest
from bs4 import BeautifulSoup
from test_answer_retention import IDS, path
from test_science_europe_contract import render_question

METHODS = [
    ('Calibrating', 'measurement calibration'),
    ('Repetition', 'repeat sampling or measurement'),
    ('Standardized', 'standardized data capture and recording'),
    ('Validation', 'data entry validation'),
    ('PeerReview', 'data peer review'),
    ('Vocabularies', 'use of controlled vocabularies'),
    ('Consistency', 'measurement of samples with known outcomes to monitor consistency'),
]
MEASURED = path('creatingCUuid', 'measuredQUuid')
DATASETS = path(MEASURED, 'measuredYesAUuid', 'measuredDataQUuid')
DATASET = path(DATASETS, 'test-dataset')
QUALITY = path(DATASET, 'measuredDataQualityQUuid')
PREFIX = path(QUALITY, 'measuredDataQualityYesAUuid')
Q1 = 'src/questions/01-how-data.html.j2'
Q4 = 'src/questions/04-quality-control.html.j2'


def replies():
    return {MEASURED: IDS['measuredYesAUuid'], DATASETS: ['test-dataset'],
            path(DATASET, 'measuredDataNameQUuid'): 'Coastal observations',
            QUALITY: IDS['measuredDataQualityYesAUuid']}


class QualityReadingTests(unittest.TestCase):
    def test_all_128_selected_method_combinations_match_in_q1_and_q4(self):
        for selected in itertools.product((False, True), repeat=len(METHODS)):
            values = replies()
            for (name, _), yes in zip(METHODS, selected):
                answer = IDS.get(f'mdQuality{name}{"Yes" if yes else "No"}AUuid')
                if answer: values[path(PREFIX, f'mdQuality{name}QUuid')] = answer
            summaries = []
            for template in (Q1, Q4):
                soup = BeautifulSoup(render_question(template, values), 'html.parser')
                summary = soup.select_one('[data-fact-id="quality-methods"]')
                self.assertIsNotNone(summary)
                if any(selected):
                    expected = ', '.join(text for (_, text), yes in zip(METHODS, selected) if yes)
                    self.assertEqual(f'Quality control measures for Coastal observations: {expected}.', summary.get_text())
                    self.assertFalse(summary.select('p, ul, li, br'))
                else:
                    self.assertEqual('missing', summary['data-status'])
                summaries.append(summary.get_text())
            self.assertEqual(*summaries)

    def test_unknown_quality_is_not_explicit_no(self):
        for answer in (None, 'measuredDataQualityNoAUuid'):
            values = replies()
            if answer: values[QUALITY] = IDS[answer]
            else: del values[QUALITY]
            for template in (Q1, Q4):
                root = BeautifulSoup(render_question(template, values), 'html.parser')
                marker = root.select_one('[data-fact-id="quality-control"]')
                self.assertEqual('explicit-no' if answer else 'missing', marker['data-status'])

    def test_missing_dataset_list_is_visible(self):
        soup = BeautifulSoup(render_question(Q4, {MEASURED: IDS['measuredYesAUuid']}), 'html.parser')
        self.assertIsNotNone(soup.select_one('[data-status="missing-output"]'))

    def test_other_methods_keep_authored_blocks_and_do_not_claim_no_methods(self):
        values = replies()
        other = path(PREFIX, 'mdQualityOtherQUuid')
        values[other] = IDS['mdQualityOtherYesAUuid']
        authored = '<p>Keep v1.2; do not rewrite!</p><p>Second paragraph。</p><ul><li>Check A.</li><li>Check B</li></ul>'
        values[path(other, 'mdQualityOtherYesAUuid', 'mdQualityOtherWhatQUuid')] = authored
        for template in (Q1, Q4):
            soup = BeautifulSoup(render_question(template, values), 'html.parser')
            detail = soup.select_one('[data-fact-id="quality-other"]')
            self.assertEqual(authored, detail.div.decode_contents())
            self.assertEqual(2, len(detail.select('p')))
            self.assertFalse(detail.find_parent('p'))
            self.assertFalse(soup.select('[data-fact-id="quality-methods"][data-status="missing"]'))
        del values[path(other, 'mdQualityOtherYesAUuid', 'mdQualityOtherWhatQUuid')]
        self.assertIn('data-fact-id="quality-other" data-status="missing"', render_question(Q4, values))

    def test_unnamed_dataset_has_fallback(self):
        values = replies(); del values[path(DATASET, 'measuredDataNameQUuid')]
        self.assertIn('(no name given)', render_question(Q4, values))

    def test_legal_fallback_only_for_empty_output(self):
        template = 'src/questions/08-copyright-ipr.html.j2'
        for values in ({}, {path('creatingCUuid', 'ownershipQUuid'): IDS['ownershipOtherAUuid']}):
            self.assertIn('data-status="missing-output"', render_question(template, values))
        output = render_question(template, {path('creatingCUuid', 'ownershipQUuid'): IDS['ownershipPIAUuid']})
        self.assertIn('All data will be owned by the Principal Investigator.', output)
        self.assertNotIn('data-status="missing-output"', output)

    def test_multiple_open_data_reasons_have_one_complete_lead_and_keep_reason_order(self):
        opened = path('accessCUuid', 'openImmediatelyQUuid')
        prefix = path(opened, 'openImmediatelyNoAUuid')
        values = {opened: IDS['openImmediatelyNoAUuid'],
                  path(prefix, 'notOpenLegalReasonsQUuid'): IDS['notOpenLegalReasonsYesAUuid'],
                  path(prefix, 'notOpenBusinessReasonsQUuid'): IDS['notOpenBusinessReasonsPatentsAUuid'],
                  path(prefix, 'notOpenOtherReasonsQUuid'): IDS['notOpenOtherReasonsPapersAUuid']}
        expected = ['legal restrictions', 'patent-related commercial considerations',
                    'papers need to be submitted first']
        for profile in ('review', 'submission'):
            soup = BeautifulSoup(render_question('src/questions/08-copyright-ipr.html.j2', values,
                output_profile=profile), 'html.parser')
            reasons = soup.select_one('.answer-detail > ul')
            self.assertIsNotNone(reasons)
            lead = reasons.find_previous_sibling()
            self.assertIsNotNone(lead)
            self.assertIn('answer-lead', lead.get('class', []))
            self.assertEqual(1, len(lead.find_all('p', recursive=False)))
            self.assertEqual('The data cannot be made fully open for the following reasons:', lead.get_text(' ', strip=True))
            self.assertEqual(expected, [item.get_text(' ', strip=True) for item in reasons.find_all('li', recursive=False)])
            self.assertFalse(soup.select('p p, p div, p ul, p ol'))

    def test_paper_reason_does_not_change_submission_into_publication(self):
        opened = path('accessCUuid', 'openImmediatelyQUuid')
        values = {opened: IDS['openImmediatelyNoAUuid'],
                  path(opened, 'openImmediatelyNoAUuid', 'notOpenOtherReasonsQUuid'):
                      IDS['notOpenOtherReasonsPapersAUuid']}
        for profile in ('review', 'submission'):
            text = BeautifulSoup(render_question('src/questions/08-copyright-ipr.html.j2', values,
                output_profile=profile), 'html.parser').get_text(' ', strip=True)
            self.assertIn('The data cannot be made fully open because papers need to be submitted first.', text)
            self.assertNotIn('publish a paper', text)

    def test_authorization_lead_precedes_unchanged_authored_blocks(self):
        opened = path('accessCUuid', 'openImmediatelyQUuid')
        legal = path(opened, 'openImmediatelyNoAUuid', 'notOpenLegalReasonsQUuid')
        authentication = path(legal, 'notOpenLegalReasonsYesAUuid', 'legalReasonsAuthenticatedQUuid')
        authorization = path(authentication, 'legalReasonsAuthenticatedYesAUuid', 'legalReasonsAuthorizeQUuid')
        authored = '<p>First <strong>owned</strong> paragraph.</p><ul><li>Keep this item.</li></ul><p>Last paragraph.</p>'
        values = {opened: IDS['openImmediatelyNoAUuid'], legal: IDS['notOpenLegalReasonsYesAUuid'],
                  authentication: IDS['legalReasonsAuthenticatedYesAUuid'],
                  authorization: IDS['legalReasonsAuthorizeOtherAUuid'],
                  path(authorization, 'legalReasonsAuthorizeOtherAUuid', 'legalReasonsAuthorizeOtherQUuid'): authored}
        for profile in ('review', 'submission'):
            soup = BeautifulSoup(render_question('src/questions/08-copyright-ipr.html.j2', values,
                output_profile=profile), 'html.parser')
            heading = soup.select_one('[data-fact-id="authorization-arrangements"]')
            detail = heading.find_next_sibling('div')
            lead = detail.find('div', recursive=False)
            self.assertEqual(['answer-lead'], lead.get('class'))
            self.assertEqual('We will use the following authorization arrangements:', lead.p.get_text())
            self.assertEqual(authored, ''.join(str(node) for node in lead.next_siblings))
            self.assertFalse(soup.select('p p, p div, p ul, p ol'))

    def test_workspace_access_requires_current_reachable_choice_but_keeps_https(self):
        chapter = IDS['processingCUuid']
        workspace, yes, no = (IDS[n] for n in ('sharedWorkspaceQUuid', 'sharedWorkspaceYesAUuid', 'sharedWorkspaceNoAUuid'))
        access = IDS['sharedAccessControlQUuid']
        choices = {IDS[name]: text for name, text in (
            ('sharedAccessControlMembersRWAUuid', 'All project members have read and write access to the data.'),
            ('sharedAccessControlInstituteRAUuid', 'Everyone at the institute has read access to the data; all project members have read and write access.'),
            ('sharedAccessControlMembersRAUuid', 'Only project members have read access; only designated project members can modify the data.'),
            ('sharedAccessControlMembersRequestAUuid', 'Everyone at the institute can read the data; only project members can request write access.'))}
        km = {'chapterUuids': [chapter], 'entities': {
            'chapters': {chapter: {'questionUuids': [workspace, IDS['risksQUuid']]}},
            'questions': {workspace: {'questionType': 'OptionsQuestion', 'answerUuids': [yes, no]},
                          access: {'questionType': 'OptionsQuestion', 'answerUuids': list(choices)},
                          IDS['risksQUuid']: {'questionType': 'OptionsQuestion', 'answerUuids': [IDS['risksExploreAUuid']]},
                          IDS['risksHttpsQUuid']: {'questionType': 'OptionsQuestion', 'answerUuids': [IDS['risksHttpsYesAUuid']]}},
            'answers': {yes: {'followUpUuids': [access]}, no: {'followUpUuids': []},
                        IDS['risksExploreAUuid']: {'followUpUuids': [IDS['risksHttpsQUuid']]},
                        IDS['risksHttpsYesAUuid']: {'followUpUuids': []},
                        **{choice: {'followUpUuids': []} for choice in choices}}}}
        workspace_path = path(chapter, workspace)
        access_path = path(workspace_path, yes, access)
        sibling = {path(chapter, 'risksQUuid'): IDS['risksExploreAUuid'],
                   path(chapter, 'risksQUuid', 'risksExploreAUuid', 'risksHttpsQUuid'): IDS['risksHttpsYesAUuid']}
        for parent in (yes, no, None, '', 'unknown'):
            for choice in (*choices, 'unknown'):
                values = dict(sibling, **{access_path: choice})
                if parent is not None: values[workspace_path] = parent
                for schema in ({}, {'km': km}):
                    for profile in ('review', 'submission'):
                        with self.subTest(parent=parent, choice=choice, schema=bool(schema), profile=profile):
                            soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', values,
                                output_profile=profile, **schema), 'html.parser')
                            text = soup.get_text(' ', strip=True)
                            active = parent == yes and choice in choices
                            self.assertEqual(active, 'Access to data during research' in text)
                            for fact in choices.values(): self.assertEqual(active and fact == choices.get(choice), fact in text)
                            self.assertIn('All project web services are accessible through HTTPS.', text)
        values = dict(sibling, **{workspace_path: yes, access_path: next(iter(choices))})
        for mutation in ('removed-question', 'removed-followup', 'wrong-type', 'removed-choice', 'dangling-answer'):
            altered = deepcopy(km)
            if mutation == 'removed-question': del altered['entities']['questions'][access]
            elif mutation == 'removed-followup': altered['entities']['answers'][yes]['followUpUuids'] = []
            elif mutation == 'wrong-type': altered['entities']['questions'][access]['questionType'] = 'ValueQuestion'
            elif mutation == 'removed-choice': altered['entities']['questions'][access]['answerUuids'] = []
            else: del altered['entities']['answers'][values[access_path]]
            for profile in ('review', 'submission'):
                text = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', values,
                    output_profile=profile, km=altered), 'html.parser').get_text(' ', strip=True)
                self.assertNotIn('Access to data during research', text, mutation)
                self.assertIn('All project web services are accessible through HTTPS.', text, mutation)

    def test_unnamed_roles_keep_facts_and_a_specific_name_gap(self):
        parent = path('adminDetailsCUuid', 'contributorsQUuid')
        template = 'src/questions/14-dm-responsible.html.j2'
        for name, roles in [('', ['contributorRoleDataStewardAUuid']), ('Named team', ['contributorRoleContactPersonAUuid'])]:
            values = {parent: ['person'], path(parent, 'person', 'contributorNameQUuid'): name,
                      path(parent, 'person', 'contributorRoleQUuid'): [IDS[r] for r in roles]}
            output = render_question(template, values)
            if name:
                self.assertIn('data-status="missing-output"', output)
                self.assertNotIn('class="responsibility-summary"', output)
            else:
                self.assertIn('Contributor 1', output)
                self.assertIn('Data stewardship:', output)
                self.assertIn('data-fact-id="responsible-person-name" data-status="missing"', output)
                self.assertNotIn('data-status="missing-output"', output)
