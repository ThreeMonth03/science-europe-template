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
    def test_negative_followups_preserve_exact_no_and_active_yes_only(self):
        cases = [
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
            self.assertEqual(exact_no, IDS[no])
            parts = [IDS[name] for name in names]
            leaf = path(*parts)
            ancestors = {path(*parts[:index]): parts[index]
                         for index in range(2, len(parts), 2)}
            inactive_answers = {
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
            for mutation in ('removed-question', 'removed-choice', 'dangling-answer', 'removed-followup', 'wrong-type'):
                altered = deepcopy(km)
                if mutation == 'removed-question': del altered['entities']['questions'][parts[-1]]
                elif mutation == 'removed-choice': altered['entities']['questions'][parts[-1]]['answerUuids'] = [IDS[yes]]
                elif mutation == 'dangling-answer': del altered['entities']['answers'][IDS[no]]
                elif mutation == 'removed-followup': altered['entities']['answers'][parts[-2]]['followUpUuids'] = []
                else: altered['entities']['questions'][parts[-1]]['questionType'] = 'ValueQuestion'
                for profile in ('review', 'submission'):
                    text = BeautifulSoup(render_question(template, dict(ancestors, **{leaf: IDS[no]}),
                        output_profile=profile, km=altered), 'html.parser').get_text(' ', strip=True)
                    self.assertNotIn(no_text, text, mutation)

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
