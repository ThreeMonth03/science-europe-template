"""Small counterexamples: related unanswered questions must not erase facts."""

import copy
import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from test_science_europe_contract import render_question


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from current_support import IDS, path


class AnswerRetentionTests(unittest.TestCase):
    def nonreference_access_fixture(self):
        from check_answer_mapping import owner_fixture, question
        km, replies, (parent, listing, use, _) = owner_fixture('nref')
        km['entities']['questions'][IDS['preexistingQUuid']]['answerUuids'].append(IDS['preexistingNoAUuid'])
        km['entities']['answers'][IDS['preexistingNoAUuid']] = {'followUpUuids': []}
        followups = km['entities']['answers'][IDS['nrefDataUseYesAUuid']]['followUpUuids']
        question(km, followups, IDS['nrefDataOwnersQUuid'], 'OptionsQuestion',
                 [IDS['nrefDataOwners'+state+'AUuid'] for state in ('Yes', 'No', 'We')])
        question(km, km['entities']['answers'][IDS['nrefDataOwnersNoAUuid']]['followUpUuids'],
                 IDS['nrefDataOwnersNoReqQUuid'], 'OptionsQuestion',
                 [IDS['nrefDataOwnersNoReqYesAUuid'], IDS['nrefDataOwnersNoReqNoAUuid']])
        question(km, followups, IDS['nrefDataAccessQUuid'], 'OptionsQuestion',
                 [IDS['nrefDataAccess'+state+'AUuid'] for state in ('HaveCopy', 'WillDownload', 'WillOnline')])
        owners = path(use, 'nrefDataUseYesAUuid', 'nrefDataOwnersQUuid')
        request = path(owners, 'nrefDataOwnersNoAUuid', 'nrefDataOwnersNoReqQUuid')
        access = path(use, 'nrefDataUseYesAUuid', 'nrefDataAccessQUuid')
        replies.update({owners: IDS['nrefDataOwnersNoAUuid'], request: IDS['nrefDataOwnersNoReqNoAUuid'],
                        access: IDS['nrefDataAccessWillDownloadAUuid']})
        return km, replies, (parent, listing, use, owners, request, access)

    def test_nonreference_access_facts_stay_in_one_owned_paragraph(self):
        km, base, (_, listing, _, owners, request, access) = self.nonreference_access_fixture()
        for owner, req, method, expected in (
            ('No', 'No', 'WillDownload', 'The rights holder will not collaborate with us on this research. No application for data access is required. We will download or obtain a copy of this dataset.'),
            ('No', 'Yes', 'WillOnline', 'The rights holder will not collaborate with us on this research. We need to apply for access to this dataset. We will use this dataset online.'),
            ('Yes', 'Yes', 'HaveCopy', 'The rights holder will collaborate with us on this research. We already have a copy of this dataset.'),
            ('We', 'No', 'HaveCopy', 'We are the rights holder of this dataset. We already have a copy of this dataset.'),
        ):
            for profile in ('review', 'submission'):
                with self.subTest(owner=owner, request=req, method=method, profile=profile):
                    replies = {**base, owners: IDS['nrefDataOwners'+owner+'AUuid'],
                               request: IDS['nrefDataOwnersNoReq'+req+'AUuid'], access: IDS['nrefDataAccess'+method+'AUuid']}
                    soup = BeautifulSoup(render_question('src/questions/01-how-data.html.j2', replies,
                        km=km, output_profile=profile), 'html.parser')
                    facts = soup.select('[data-fact-id="reuse-access-arrangements"]')
                    self.assertEqual(1, len(facts))
                    self.assertEqual('p', facts[0].name)
                    self.assertEqual(expected, facts[0].get_text())
                    self.assertEqual('dataset-1', facts[0].find_parent('li')['data-item-id'])
                    self.assertFalse(facts[0].select('.data-gap, .data-review'))
        replies = {**base, listing: ['dataset-2', 'dataset-1']}
        prefix = path(listing, 'dataset-1')
        replies.update({key.replace(prefix, path(listing, 'dataset-2'), 1): value
                        for key, value in base.items() if key.startswith(prefix+'.')})
        replies[access.replace(prefix, path(listing, 'dataset-2'), 1)] = IDS['nrefDataAccessWillOnlineAUuid']
        soup = BeautifulSoup(render_question('src/questions/01-how-data.html.j2', replies,
            km=km, output_profile='submission'), 'html.parser')
        facts = soup.select('[data-fact-id="reuse-access-arrangements"]')
        self.assertEqual(['dataset-2', 'dataset-1'], [f.find_parent('li')['data-item-id'] for f in facts])
        self.assertIn('We will use this dataset online.', facts[0].get_text())
        self.assertNotIn('download', facts[0].get_text())
        self.assertIn('We will download or obtain a copy', facts[1].get_text())

    def test_nonreference_access_unknown_or_inactive_fields_do_not_invent_facts(self):
        km, base, (parent, listing, use, owners, request, access) = self.nonreference_access_fixture()
        for state in ('missing', 'unknown', 'no-reuse', 'no-existing', 'deleted-item', 'filtered-access',
                      'unknown-owner', 'missing-request', 'unknown-request', 'removed-owner-answer'):
            with self.subTest(state=state):
                current, replies = copy.deepcopy(km), dict(base)
                if state == 'missing':
                    replies.pop(owners); replies.pop(access)
                if state == 'unknown':
                    replies[owners] = replies[access] = 'obsolete-option'
                if state == 'no-reuse': replies[use] = IDS['nrefDataUseNoAUuid']
                if state == 'no-existing': replies[parent] = IDS['preexistingNoAUuid']
                if state == 'deleted-item': replies[listing] = []
                if state == 'filtered-access':
                    current['entities']['answers'][IDS['nrefDataUseYesAUuid']]['followUpUuids'].remove(IDS['nrefDataAccessQUuid'])
                if state == 'unknown-owner': replies[owners] = 'obsolete-option'
                if state == 'missing-request': replies.pop(request)
                if state == 'unknown-request': replies[request] = 'obsolete-option'
                if state == 'removed-owner-answer':
                    current['entities']['questions'][IDS['nrefDataOwnersQUuid']]['answerUuids'].remove(IDS['nrefDataOwnersNoAUuid'])
                for profile in ('review', 'submission'):
                    soup = BeautifulSoup(render_question('src/questions/01-how-data.html.j2', replies,
                        km=current, output_profile=profile), 'html.parser')
                    facts = soup.select('[data-fact-id="reuse-access-arrangements"]')
                    if state == 'filtered-access':
                        self.assertEqual('The rights holder will not collaborate with us on this research. No application for data access is required.', facts[0].get_text())
                    elif state in ('unknown-owner', 'removed-owner-answer'):
                        self.assertEqual('We will download or obtain a copy of this dataset.', facts[0].get_text())
                    elif state in ('missing-request', 'unknown-request'):
                        self.assertEqual('The rights holder will not collaborate with us on this research. We will download or obtain a copy of this dataset.', facts[0].get_text())
                    else:
                        self.assertEqual([], facts)

    def test_file_naming_answer_keeps_case_sensitive_names(self):
        parent = path('processingCUuid', 'storageConvQUuid')
        filesystem = path(parent, 'storageConvExploreAUuid', 'storageConvFSysQUuid')
        answer = 'Name files station_YYYYMMDD.csv; record corrections in CHANGELOG.md.'
        replies = {parent: IDS['storageConvExploreAUuid'], filesystem: IDS['storageConvFSysYesAUuid'],
                   path(filesystem, 'storageConvFSysYesAUuid', 'scFSysAppointmentsQUuid'): answer}
        output = render_question('src/questions/03-docs-metadata.html.j2', replies)
        self.assertIn(answer, output)

    def test_storage_amount_survives_unanswered_storage_technology(self):
        parent = path('processingCUuid', 'storageConvQUuid')
        space = path(parent, 'storageConvExploreAUuid', 'storageSpaceQUuid')
        for amount in ('2048', '0'):
            with self.subTest(amount=amount):
                replies = {
                    parent: IDS['storageConvExploreAUuid'],
                    space: IDS['storageSpaceSpecifyAUuid'],
                    path(space, 'storageSpaceSpecifyAUuid', 'storageSpaceSpecifyQUuid'): amount,
                }
                output = render_question('src/questions/03-docs-metadata.html.j2', replies)
                self.assertIn(f'{amount} gigabytes', output)
                self.assertNotIn('data-status="missing-output"', output)

    def test_metadata_access_instructions_yes_no_unknown_are_distinct(self):
        parent = path('accessCUuid', 'metadataOpenQUuid')
        question = path(parent, 'metadataOpenYesAUuid', 'metadataOpenInstrQUuid')
        for answer, expected, forbidden in (
            ('metadataOpenInstrYesAUuid', 'including instructions', 'without instructions'),
            ('metadataOpenInstrNoAUuid', 'without instructions', 'including instructions'),
            (None, 'Metadata will be openly available.', 'instructions how'),
        ):
            with self.subTest(answer=answer):
                replies = {parent: IDS['metadataOpenYesAUuid']}
                if answer:
                    replies[question] = IDS[answer]
                output = render_question('src/questions/03-docs-metadata.html.j2', replies)
                self.assertIn(expected, output)
                self.assertNotIn(forbidden, output)

    def test_software_unknown_is_not_no_tools_required(self):
        datasets = path('preservingCUuid', 'producedDataQUuid')
        publication = path(datasets, 'dataset-1', 'isPublishedDataQUuid')
        software = path(publication, 'isPublishedDataYesAUuid', 'publishedSpecSwUseQUuid')
        for answer in (None, 'publishedSpecSwUseYesAUuid', 'publishedSpecSwUseNoAUuid'):
            with self.subTest(answer=answer):
                replies = {datasets: ['dataset-1'], publication: IDS['isPublishedDataYesAUuid']}
                if answer:
                    replies[software] = IDS[answer]
                output = render_question('src/questions/12-access-data.html.j2', replies)
                if answer == 'publishedSpecSwUseNoAUuid':
                    self.assertIn('No specific software is required', output)
                else:
                    self.assertNotIn('No specific software is required', output)
                    self.assertIn('data-status="missing"', output)

    def test_unknown_publication_is_not_no_published_data(self):
        datasets = path('preservingCUuid', 'producedDataQUuid')
        output = render_question('src/questions/12-access-data.html.j2', {datasets: ['dataset-1']})
        self.assertNotIn('There are no published data', output)
        self.assertIn('data-status="missing"', output)


if __name__ == '__main__':
    unittest.main()
