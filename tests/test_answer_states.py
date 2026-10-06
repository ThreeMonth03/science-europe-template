"""Missing answers must not become claims; repository choices have local scope."""
import itertools
from copy import deepcopy
import sys
import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_pilot_fixtures import IDS, path
from current_support import support_replies

Q5 = 'src/questions/05-store-backup.html.j2'
Q11 = 'src/questions/11-data-preservation.html.j2'
LEAD = 'The fields mapped by this template are insufficient to establish the following operational details:'
SUPPORT = {
    'complete': 'We will be able to support this repository for a sufficiently long time.',
    'explicit-no': 'We will not be able to support this repository for a sufficiently long time.',
    'missing': 'Whether we will be able to support this repository for a sufficiently long time has not been specified.',
}


def storage_matrix():
    workspace = path('processingCUuid', 'sharedWorkspaceQUuid')
    archive = path('preservingCUuid', 'archivedDuringQUuid')
    for work, arch in itertools.product([None, 'Yes', 'No'], repeat=2):
        replies = {}
        if work: replies[workspace] = IDS[f'sharedWorkspace{work}AUuid']
        if arch: replies[archive] = IDS[f'archivedDuring{arch}AUuid']
        yield replies


class AnswerStateTests(unittest.TestCase):
    def test_instrument_acquisition_survives_missing_or_empty_dataset_list(self):
        measured = path('creatingCUuid', 'measuredQUuid')
        datasets = path(measured, 'measuredYesAUuid', 'measuredDataQUuid')
        fact = 'We will acquire data using measurement equipment.'
        for choice, listing, profile in itertools.product(('Yes', 'No', None, 'unknown'), (None, []), ('review', 'submission')):
            replies = {path(datasets, 'removed-item', 'measuredDataNameQUuid'): 'Stale instrument dataset'}
            if choice is not None: replies[measured] = IDS.get('measured'+choice+'AUuid', choice)
            if listing is not None: replies[datasets] = listing
            with self.subTest(choice=choice, listing=listing, profile=profile):
                soup = BeautifulSoup(render_question('src/questions/01-how-data.html.j2', replies,
                    output_profile=profile), 'html.parser')
                text = soup.get_text(' ', strip=True)
                self.assertEqual(choice == 'Yes', fact in text)
                self.assertNotIn('Stale instrument dataset', text)
                if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))

    def test_carrying_data_survives_missing_security_details_without_inference(self):
        risk = path('processingCUuid', 'risksQUuid')
        prefix = path(risk, 'risksExploreAUuid')
        carry = path(prefix, 'risksCarryHomeQUuid')
        enc = path(carry, 'risksCarryHomeYesAUuid', 'risksCarryHomeEncQUuid')
        password = path(carry, 'risksCarryHomeYesAUuid', 'risksCarryHomePassQUuid')
        for encryption, protection, profile in itertools.product(('Yes', 'No', None, 'unknown'),
                ('Yes', 'No', None, 'unknown'), ('review', 'submission')):
            replies = {risk: IDS['risksExploreAUuid'], carry: IDS['risksCarryHomeYesAUuid'],
                path(prefix, 'risksHttpsQUuid'): IDS['risksHttpsYesAUuid']}
            if encryption is not None: replies[enc] = IDS.get('risksCarryHomeEnc'+encryption+'AUuid', encryption)
            if protection is not None: replies[password] = IDS.get('risksCarryHomePass'+protection+'AUuid', protection)
            with self.subTest(encryption=encryption, protection=protection, profile=profile):
                soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', replies,
                    output_profile=profile), 'html.parser')
                text = soup.get_text(' ', strip=True)
                verb = 'can' if encryption == 'Yes' or protection == 'Yes' else 'will'
                self.assertIn('Project members '+verb+' carry data with them', text)
                self.assertEqual(encryption == 'Yes', 'on encrypted data carriers' in text)
                self.assertEqual(encryption == 'No', 'Not all data carriers are encrypted.' in text)
                self.assertEqual(protection == 'Yes', 'password-protected laptops' in text)
                self.assertIn('All project web services are accessible through HTTPS.', text)
                if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))

    def test_risk_parent_gates_all_risk_facts_but_not_workspace_access(self):
        risk = path('processingCUuid', 'risksQUuid')
        prefix = path(risk, 'risksExploreAUuid')
        choices = {'risksStoreLabQUuid': 'risksStoreLabNoAUuid',
                   'risksCarryHomeQUuid': 'risksCarryHomeNoAUuid',
                   'risksHttpsQUuid': 'risksHttpsYesAUuid',
                   'risksInstructedQUuid': 'risksInstructedYesAUuid',
                   'risksInfoLossQUuid': 'risksInfoLossSmallAUuid',
                   'risksPersonalDataQUuid': 'risksPersonalDataNotUsingAUuid'}
        workspace = path('processingCUuid', 'sharedWorkspaceQUuid')
        values = {path(prefix, q): IDS[a] for q, a in choices.items()}
        values.update({workspace: IDS['sharedWorkspaceYesAUuid'],
            path(workspace, 'sharedWorkspaceYesAUuid', 'sharedAccessControlQUuid'): IDS['sharedAccessControlMembersRWAUuid']})
        facts = ('will not store data or software', 'will not carry data with them',
                 'accessible through HTTPS', 'have been instructed',
                 'The potential impact of data loss is small', 'We are not using any personal information.')
        for parent, profile in itertools.product((IDS['risksExploreAUuid'], None, '', 'unknown'), ('review', 'submission')):
            replies = dict(values)
            if parent is not None: replies[risk] = parent
            with self.subTest(parent=parent, profile=profile):
                soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', replies,
                    output_profile=profile), 'html.parser')
                text = soup.get_text(' ', strip=True)
                for fact in facts: self.assertEqual(parent == IDS['risksExploreAUuid'], fact in text, fact)
                self.assertIn('All project members have read and write access to the data.', text)
                self.assertFalse(soup.select('p p, p div, p ul'))

    def test_negative_followups_preserve_exact_no_and_active_yes_only(self):
        cases = [
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksInfoLossQUuid'),
             'risksInfoLossSmallAUuid', 'risksInfoLossNoAUuid',
             '4c5d329b-6e18-4f4e-92a9-f0298adf38fe',
             'The potential impact of data loss is small.',
             'We have not considered the possible impact on the project or organization of data loss.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksInfoLeakQUuid'),
             'risksInfoLeakSmallAUuid', 'risksInfoLeakNoAUuid',
             '04dd5577-367f-4c34-b90c-4bc25d80c819',
             'The potential impact of data disclosure is small.',
             'We have not considered the possible impact on the project or organization of data disclosure.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksInfoVandalismQUuid'),
             'risksInfoVandalismSmallAUuid', 'risksInfoVandalismNoAUuid',
             'b4dbc287-8eed-4799-800e-5ce0ede13cd8',
             'The potential impact of data tampering is small.',
             'We have not considered the possible impact on the project or organization of data tampering.'),
            ('src/questions/10-share-restrictions.html.j2',
             ('accessCUuid', 'openImmediatelyQUuid', 'openImmediatelyNoAUuid',
              'notOpenLegalReasonsQUuid', 'notOpenLegalReasonsYesAUuid', 'legalReasonsAuthenticatedQUuid'),
             'legalReasonsAuthenticatedYesAUuid', 'legalReasonsAuthenticatedNoAUuid',
             'da8b25a9-8865-4ce8-a2ba-d592c42daa4c',
             'We will permit authenticated access to the data.',
             'We will not permit authenticated access to the data.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksStoreLabQUuid'),
             'risksStoreLabYesAUuid', 'risksStoreLabNoAUuid',
             '17172079-ddce-40a7-b93a-f86dc6611452',
             'Project members store data or software on computers in the lab or external hard drives connected to those computers.',
             'Project members will not store data or software on computers in the lab or external hard drives connected to those computers.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksInstructedQUuid'),
             'risksInstructedYesAUuid', 'risksInstructedNoAUuid',
             'd802675e-f76b-4714-87ee-1b328da826ab',
             'Project members have been instructed about both generic and specific risks to the project.',
             'Project members have not received instruction covering both generic and project-specific risks.'),
            ('src/questions/11-data-preservation.html.j2',
             ('preservingCUuid', 'budgetTimeEffortQUuid'),
             'budgetTimeEffortYesAUuid', 'budgetTimeEffortNoAUuid',
             'f765ae2f-7d22-478c-bd53-1a388c4dbcc9',
             'We have allocated funds for the time and effort needed to prepare the data for publication.',
             'We have not budgeted for the time and effort needed to prepare the data for publication.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksCarryHomeQUuid',
              'risksCarryHomeYesAUuid', 'risksCarryHomePassQUuid'),
             'risksCarryHomePassYesAUuid', 'risksCarryHomePassNoAUuid',
             'f2d273c1-8e6e-4656-93ba-6b78d7d6785f',
             'Project members can carry data with them on password-protected laptops.',
             'Not all laptop accounts are password-protected.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksHttpsQUuid'),
             'risksHttpsYesAUuid', 'risksHttpsNoAUuid',
             '2b934f9d-d849-4e22-8e0c-65dbf7b9dbeb',
             'All project web services are accessible through HTTPS.',
             'Not all project web services are accessible through HTTPS.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksCertificationsQUuid'),
             'risksCertificationsYesAUuid', 'risksCertificationsNoAUuid',
             '9acf74b1-e045-477d-be96-695692bb22c3',
             'All data centres that store project data hold appropriate certifications.',
             'Not all data centres that store project data hold appropriate certifications.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksCarryHomeQUuid',
              'risksCarryHomeYesAUuid', 'risksCarryHomeEncQUuid'),
             'risksCarryHomeEncYesAUuid', 'risksCarryHomeEncNoAUuid',
             '546d6e41-80ea-417b-b0e3-a1d9d75a3794',
             'Project members can carry data with them on encrypted data carriers.',
             'Not all data carriers are encrypted.'),
            ('src/questions/03-docs-metadata.html.j2',
             ('processingCUuid', 'storageConvQUuid', 'storageConvExploreAUuid',
              'storageConvFSysQUuid', 'storageConvFSysYesAUuid', 'scDocumentVersioningQUuid'),
             'scDocumentVersioningYesAUuid', 'scDocumentVersioningNoAUuid',
             'd23c7fe6-4b85-4a84-9253-0322f9a94756',
             'We document how we manage file versioning for files and folders.',
             'We have not documented how we manage file versioning for files and folders.'),
            ('src/questions/01-how-data.html.j2',
             ('reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid',
              'dataCompReadQUuid', 'dataCompReadYesAUuid', 'dataCompReadOthersQUuid'),
             'dataCompReadOthersYesAUuid', 'dataCompReadOthersNoAUuid',
             '60bb3161-0877-4b2c-8b32-9932ae63cb27',
             'We will provide others with standardized, machine-readable metadata.',
             'We will not provide others with standardized, machine-readable metadata.'),
        ]
        for template, names, yes, no, exact_no, yes_text, no_text in cases:
            with self.subTest(question=names[-1], stage='bindings'):
                self.assertEqual(exact_no, IDS.get(no), 'The exact No option must have a source binding')
                self.assertIn(yes, IDS, 'The exact Yes option must have a source binding')
            if yes not in IDS or no not in IDS:
                continue
            parts = [IDS[name] for name in names]
            leaf = path(*parts)
            ancestors = {path(*parts[:index]): parts[index]
                         for index in range(2, len(parts), 2)}
            inactive_answers = {
                'openImmediatelyQUuid': 'openImmediatelyYesAUuid',
                'notOpenLegalReasonsQUuid': 'notOpenLegalReasonsNoAUuid',
                'risksCarryHomeQUuid': 'risksCarryHomeNoAUuid',
                'storageConvFSysQUuid': 'storageConvFSysNoAUuid',
                'preexistingQUuid': 'preexistingNoAUuid',
                'dataCompReadQUuid': 'dataCompReadNoAUuid',
            }
            explicit_no_parents = {path(*parts[:index + 1]): IDS[inactive_answers[names[index]]]
                                   for index in range(1, len(parts) - 1, 2)
                                   if names[index] in inactive_answers}
            km = {'chapterUuids': [parts[0]], 'entities': {
                'chapters': {parts[0]: {'questionUuids': [parts[1]]}},
                'questions': {}, 'answers': {}}}
            for index in range(1, len(parts), 2):
                answers = [parts[index + 1]] if index + 1 < len(parts) else [IDS[yes], IDS[no]]
                km['entities']['questions'][parts[index]] = {
                    'questionType': 'OptionsQuestion', 'answerUuids': answers}
                for answer in answers:
                    km['entities']['answers'][answer] = {
                        'followUpUuids': [parts[index + 2]] if index + 2 < len(parts) else []}
            for schema in ({}, {'km': km}):
                for profile, choice in itertools.product(('review', 'submission'), (yes, no, None, '', 'unknown')):
                    values = dict(ancestors)
                    if choice is not None: values[leaf] = IDS.get(choice, choice)
                    with self.subTest(question=names[-1], choice=choice, profile=profile, schema=bool(schema)):
                        soup = BeautifulSoup(render_question(template, values, output_profile=profile, **schema), 'html.parser')
                        text = soup.get_text(' ', strip=True)
                        self.assertEqual(choice == yes, yes_text in text)
                        self.assertEqual(choice == no, no_text in text)
                        self.assertFalse(soup.select('p p, p div, p ul'))
                # Retained Yes/No replies behind inactive ancestors are not current facts.
                for ancestor, choice in itertools.product(ancestors, (yes, no)):
                    parents = (None, '', 'unknown')
                    if ancestor in explicit_no_parents: parents += (explicit_no_parents[ancestor],)
                    for parent in parents:
                        values = dict(ancestors, **{leaf: IDS[choice]})
                        if parent is None: del values[ancestor]
                        else: values[ancestor] = parent
                        text = BeautifulSoup(render_question(template, values, output_profile='submission', **schema), 'html.parser').get_text(' ', strip=True)
                        self.assertNotIn(yes_text, text)
                        self.assertNotIn(no_text, text)
            # A compiled KM cannot authorize a removed question, answer, follow-up or wrong type.
            for mutation, choice in itertools.product(
                    ('removed-question', 'removed-choice', 'dangling-answer', 'removed-followup', 'wrong-type'), (yes, no)):
                altered = deepcopy(km)
                selected = IDS[choice]
                if mutation == 'removed-question': del altered['entities']['questions'][parts[-1]]
                elif mutation == 'removed-choice': altered['entities']['questions'][parts[-1]]['answerUuids'] = [IDS[no if choice == yes else yes]]
                elif mutation == 'dangling-answer': del altered['entities']['answers'][selected]
                elif mutation == 'removed-followup':
                    if len(parts) == 2: altered['entities']['chapters'][parts[0]]['questionUuids'] = []
                    else: altered['entities']['answers'][parts[-2]]['followUpUuids'] = []
                else: altered['entities']['questions'][parts[-1]]['questionType'] = 'ValueQuestion'
                for profile in ('review', 'submission'):
                    text = BeautifulSoup(render_question(template, dict(ancestors, **{leaf: selected}),
                        output_profile=profile, km=altered), 'html.parser').get_text(' ', strip=True)
                    self.assertNotIn(yes_text if choice == yes else no_text, text, mutation)

        # Eventual openness says nothing about whether an agreement is needed.
        for profile in ('review', 'submission'):
            open_path = path('accessCUuid', 'openImmediatelyQUuid')
            collab = path('creatingCUuid', 'collabQUuid')
            replies = {open_path: IDS['openImmediatelyYesAUuid'], collab: IDS['collabYesAUuid'],
                       path(collab, 'collabYesAUuid', 'collabAgreeQUuid'): IDS['collabAgreeYesAUuid']}
            text = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2',
                                 replies, output_profile=profile), 'html.parser').get_text(' ', strip=True)
            self.assertNotIn('No data sharing agreement will be required.', text)
            self.assertIn('A collaboration agreement is in place to specify who can access which project data.', text)

        # Newly mapped authored follow-ups are independent of siblings, but
        # only current answers behind the exact selected parents are visible.
        from check_sentence_layout import partial_fixture
        fields = [
            ('src/questions/11-data-preservation.html.j2',
             'preservingCUuid budgetTimeEffortQUuid budgetTimeEffortYesAUuid budgetTimeEffortAmountQUuid',
             '2a0cf686-63ed-44b6-ae74-38ddd39ac741', 'preparation-budget-amount'),
            ('src/questions/12-access-data.html.j2',
             'preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid isPublishedDataYesAUuid '
             'publishedSpecSwUseQUuid publishedSpecSwUseNoAUuid publishedSpecSwUseNoReasonQUuid',
             '14f7a766-c28e-400e-8426-53f7b4e5b90b', 'software-not-required-reason'),
        ]
        authored = '<p>Keep <strong>v1.2.csv</strong>: 0 TWD; do not rewrite .,</p><ul><li>Reason A.</li></ul>'
        for template, chain, exact_uuid, fact in fields:
            names = chain.split()
            self.assertEqual(exact_uuid, IDS.get(names[-1]))
            if names[-1] not in IDS: continue
            km, base, leaf = partial_fixture(chain)
            for schema, profile, value in itertools.product(({}, {'km': km}), ('review', 'submission'),
                                                           (None, '', ' \t\n\u3000', '0', authored)):
                replies = dict(base)
                if value is not None: replies[leaf] = value
                soup = BeautifulSoup(render_question(template, replies, output_profile=profile, **schema), 'html.parser')
                detail = soup.select_one('[data-fact-id="'+fact+'"]')
                filled = bool((value or '').strip())
                self.assertEqual(filled, bool(detail), (chain, value))
                if detail: self.assertEqual(value, detail.decode_contents())
                self.assertFalse(soup.select('p p, p div, p ul'))
                if profile == 'submission': self.assertFalse(soup.select('.data-gap,.data-review'))
            if fact == 'software-not-required-reason':
                # Equal/missing names cannot merge two datasets' explanations.
                listing = path('preservingCUuid', 'producedDataQUuid')
                other_pub = path(listing, 'OTHER', 'isPublishedDataQUuid')
                other_sw = path(other_pub, 'isPublishedDataYesAUuid', 'publishedSpecSwUseQUuid')
                other_reason = path(other_sw, 'publishedSpecSwUseNoAUuid', 'publishedSpecSwUseNoReasonQUuid')
                replies = dict(base, **{listing: ['ITEM', 'OTHER'], leaf: authored,
                    other_pub: IDS['isPublishedDataYesAUuid'], other_sw: IDS['publishedSpecSwUseNoAUuid'],
                    other_reason: '<p>Only the second dataset uses standard tools.</p>'})
                for profile in ('review', 'submission'):
                    soup = BeautifulSoup(render_question(template, replies, output_profile=profile, km=km), 'html.parser')
                    first = soup.select_one('.dataset-section[data-item-id="ITEM"]')
                    second = soup.select_one('.dataset-section[data-item-id="OTHER"]')
                    self.assertEqual(authored, first.select_one('[data-fact-id="'+fact+'"]').decode_contents())
                    self.assertNotIn('Only the second dataset', first.get_text())
                    self.assertIn('Only the second dataset', second.get_text())
                    self.assertNotIn('v1.2.csv', second.get_text())
                    deleted = dict(replies, **{listing: ['OTHER']})
                    output = render_question(template, deleted, output_profile=profile, km=km)
                    self.assertNotIn('v1.2.csv', output)
                    self.assertIn('Only the second dataset', output)
            for ancestor in base:
                for selected in (None, '', 'unknown', []):
                    replies = dict(base, **{leaf: authored})
                    if selected is None: del replies[ancestor]
                    else: replies[ancestor] = selected
                    soup = BeautifulSoup(render_question(template, replies, output_profile='submission', km=km), 'html.parser')
                    self.assertFalse(soup.select('[data-fact-id="'+fact+'"]'), (chain, ancestor, selected))
            for mutation in ('removed-question', 'removed-followup', 'wrong-type'):
                altered = deepcopy(km)
                if mutation == 'removed-question': del altered['entities']['questions'][exact_uuid]
                elif mutation == 'removed-followup': altered['entities']['answers'][IDS[names[-2]]]['followUpUuids'] = []
                else: altered['entities']['questions'][exact_uuid]['questionType'] = 'OptionsQuestion'
                soup = BeautifulSoup(render_question(template, dict(base, **{leaf: authored}),
                                                    output_profile='submission', km=altered), 'html.parser')
                self.assertFalse(soup.select('[data-fact-id="'+fact+'"]'), (chain, mutation))

    def test_negative_limitations_share_prose_without_losing_positive_siblings(self):
        risk = path('processingCUuid', 'risksQUuid')
        risk_prefix = path(risk, 'risksExploreAUuid')
        carry = path(risk_prefix, 'risksCarryHomeQUuid')
        values = {risk: IDS['risksExploreAUuid'], carry: IDS['risksCarryHomeYesAUuid'],
                  path(carry, 'risksCarryHomeYesAUuid', 'risksCarryHomeEncQUuid'): IDS['risksCarryHomeEncNoAUuid'],
                  path(carry, 'risksCarryHomeYesAUuid', 'risksCarryHomePassQUuid'): IDS['risksCarryHomePassYesAUuid'],
                  path(risk_prefix, 'risksCertificationsQUuid'): IDS['risksCertificationsNoAUuid'],
                  path(risk_prefix, 'risksHttpsQUuid'): IDS['risksHttpsYesAUuid']}
        expected = ('Project members can carry data with them on password-protected laptops. '
                    'Not all data carriers are encrypted. '
                    'Not all data centres that store project data hold appropriate certifications. '
                    'All project web services are accessible through HTTPS.')
        preexisting = path('reusingCUuid', 'preexistingQUuid')
        convert = path(preexisting, 'preexistingYesAUuid', 'dataCompReadQUuid')
        reuse = {preexisting: IDS['preexistingYesAUuid'], convert: IDS['dataCompReadYesAUuid'],
                 path(convert, 'dataCompReadYesAUuid', 'dataCompReadItselfQUuid'): IDS['dataCompReadItselfYesAUuid'],
                 path(convert, 'dataCompReadYesAUuid', 'dataCompReadOthersQUuid'): IDS['dataCompReadOthersNoAUuid']}
        for profile in ('review', 'submission'):
            soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', values,
                output_profile=profile), 'html.parser')
            self.assertEqual(expected, ' '.join(soup.select_one('.answer > p').get_text(' ', strip=True).split()))
            soup = BeautifulSoup(render_question('src/questions/01-how-data.html.j2', reuse,
                output_profile=profile), 'html.parser')
            sentence = soup.find('p', string=lambda text: text and 'We will not provide others' in text)
            self.assertIsNotNone(sentence)
            self.assertEqual('Before reuse, we will need to convert the data into a machine-readable form and '
                'will make this version available to others through a standard repository. '
                'We will not provide others with standardized, machine-readable metadata.',
                ' '.join(sentence.get_text(' ', strip=True).split()))

    def test_q5_neutral_mapping_limit_does_not_imply_supplied_answers(self):
        for replies in storage_matrix():
            with self.subTest(replies=replies):
                soup = BeautifulSoup(render_question(Q5, replies), 'html.parser')
                self.assertEqual(LEAD, soup.select_one('.storage-detail-limits > p').get_text())
                self.assertEqual(['unmapped', 'unmapped'], [n['data-status'] for n in soup.select('.storage-detail-limits [data-fact-id]')])
                self.assertNotIn('The mapped answers describe', soup.get_text())

    def test_stale_archive_children_do_not_establish_storage_details(self):
        replies = {path('preservingCUuid', 'archivedDuringQUuid', 'archivedDuringYesAUuid', 'archiveRemoteQUuid'): IDS['archiveRemoteYesAUuid']}
        for parent in (None, 'No'):
            if parent: replies[path('preservingCUuid', 'archivedDuringQUuid')] = IDS['archivedDuringNoAUuid']
            soup = BeautifulSoup(render_question(Q5, replies), 'html.parser')
            self.assertEqual('unmapped', soup.select_one('[data-fact-id="storage-location"]')['data-status'])
            self.assertNotIn('The archive will be stored at a remote location.', soup.get_text())

    def test_support_yes_no_missing_and_unrecognized_are_distinct(self):
        for choice, state in [('Yes', 'complete'), ('No', 'explicit-no'), (None, 'missing'), ('', 'missing'), ('unknown', 'missing')]:
            soup = BeautifulSoup(render_question(Q11, support_replies((choice,))), 'html.parser')
            node = soup.select_one('[data-fact-id="repository-long-term-support"]')
            self.assertEqual(state, node['data-status'])
            self.assertEqual(SUPPORT[state], node.get_text())
            self.assertEqual('distro-0', node.find_parent(attrs={'data-item-id': True})['data-item-id'])
            self.assertIn('The repository will provide an advanced processing service.', node.parent.get_text())
            self.assertFalse(soup.select('p p, p div, p ul'))

    def test_support_does_not_leak_from_inactive_publication_or_repository(self):
        for publication, repository, choice in itertools.product([None, 'No', 'Yes'], [None, 'National', 'Special'], ['Yes', 'No', None]):
            soup = BeautifulSoup(render_question(Q11, support_replies((choice,), repository, publication)), 'html.parser')
            self.assertEqual(publication == 'Yes' and repository == 'Special', bool(soup.select('[data-fact-id="repository-long-term-support"]')))

    def test_each_distribution_keeps_its_own_support_state(self):
        soup = BeautifulSoup(render_question(Q11, support_replies(('Yes', 'No', None))), 'html.parser')
        self.assertEqual([('distro-0', 'complete'), ('distro-1', 'explicit-no'), ('distro-2', 'missing')],
                         [(n.find_parent(attrs={'data-item-id': True})['data-item-id'], n['data-status']) for n in soup.select('[data-fact-id="repository-long-term-support"]')])
        self.assertEqual(3, soup.get_text().count('The repository will provide an advanced processing service.'))
