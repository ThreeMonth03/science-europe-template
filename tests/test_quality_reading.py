"""Fixed choices become prose; missing answers and authored blocks stay distinct."""
import itertools
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
            self.assertEqual(authored, detail.decode_contents())
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

    def test_unnamed_or_unmapped_roles_do_not_suppress_responsibility_gap(self):
        parent = path('adminDetailsCUuid', 'contributorsQUuid')
        template = 'src/questions/14-dm-responsible.html.j2'
        for name, roles in [('', ['contributorRoleDataStewardAUuid']), ('Named team', ['contributorRoleContactPersonAUuid'])]:
            values = {parent: ['person'], path(parent, 'person', 'contributorNameQUuid'): name,
                      path(parent, 'person', 'contributorRoleQUuid'): [IDS[r] for r in roles]}
            self.assertIn('data-status="missing-output"', render_question(template, values))
