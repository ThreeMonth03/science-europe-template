"""Small counterexamples: related unanswered questions must not erase facts."""

import re
import unittest
from pathlib import Path

from test_science_europe_contract import render_question


ROOT = Path(__file__).resolve().parents[1]
IDS = dict(re.findall(r'set\s+(\w+)\s*=\s*"([0-9a-f-]{36})"', (ROOT / 'src/uuids.j2').read_text()))


def path(*parts):
    return '.'.join(IDS.get(part, part) for part in parts)


class AnswerRetentionTests(unittest.TestCase):
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
                    self.assertIn('There are no tools needed', output)
                else:
                    self.assertNotIn('There are no tools needed', output)
                    self.assertIn('data-status="missing"', output)

    def test_unknown_publication_is_not_no_published_data(self):
        datasets = path('preservingCUuid', 'producedDataQUuid')
        output = render_question('src/questions/12-access-data.html.j2', {datasets: ['dataset-1']})
        self.assertNotIn('There are no published data', output)
        self.assertIn('data-status="missing"', output)


if __name__ == '__main__':
    unittest.main()
