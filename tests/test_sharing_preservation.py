import itertools
import sys
import unittest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from test_science_europe_contract import ROOT, render_question
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_sharing_fixtures import sharing_cases
from generate_storage_fixtures import storage_cases
from generate_pilot_fixtures import IDS, path

Q10 = 'src/questions/10-share-restrictions.html.j2'
Q11 = 'src/questions/11-data-preservation.html.j2'
AUTHORED = '<p>Keep Access-2027-12-31.csv!</p><p>Second paragraph.</p><ul><li>First.</li><li>Second.</li></ul>'


def matrix_cases():
    base = {p: v['value'] for p, v in storage_cases('en')['storage-sharing'].items()}
    prefix = next(p for p in base if p.endswith(IDS['licenseRestrictConditionsQUuid'])).rsplit('.', 1)[0]
    for access, metadata, has_custom in itertools.product(
        [None, 'licenseRestrictAccessRequestAUuid', 'licenseRestrictAccessCommitteeAUuid', 'licenseRestrictAccessAnotherAUuid'],
        [None, 'licenseRestrictMetadataYesAUuid', 'licenseRestrictMetadataNoAUuid'], [False, True]):
        replies = dict(base)
        ap = path(prefix, 'licenseRestrictAccessQUuid'); mp = path(prefix, 'licenseRestrictMetadataQUuid')
        replies.pop(ap, None); replies.pop(mp, None)
        if access: replies[ap] = IDS[access]
        if metadata: replies[mp] = IDS[metadata]
        if has_custom: replies[path(ap, 'licenseRestrictAccessAnotherAUuid', 'licenseRestrictAccessAnotherQUuid')] = AUTHORED
        yield replies, access, metadata, has_custom


class SharingPreservationTests(unittest.TestCase):
    def test_date_hint_is_scoped_and_does_not_rewrite_free_text(self):
        env = Environment(loader=FileSystemLoader(ROOT), extensions=['jinja2.ext.do'])
        env.filters['markdown'] = lambda v: v
        render = env.from_string("{% import 'src/macros.html.j2' as m %}{{ m.calendarDate(value) }}").render
        for value in ('2027-12-31', '2028-02-29'):
            soup = BeautifulSoup(render(value=value), 'html.parser')
            self.assertEqual(value, soup.select_one('.date-value')['data-iso-date'])
            self.assertEqual(value, soup.get_text())
        for value in ('Access-2027-12-31.csv', '2027-1-1', '2027-12-31 or later', '２０２７-１２-３１', '<b>planned</b>'):
            soup = BeautifulSoup(render(value=value), 'html.parser')
            self.assertFalse(soup.select('.date-value, b'))
            self.assertEqual(value, soup.get_text())

    def test_process_matrix_distinguishes_no_unknown_and_authored_details(self):
        for replies, access, metadata, has_custom in matrix_cases():
            soup = BeautifulSoup(render_question(Q10, replies), 'html.parser')
            proc = soup.select_one('.restriction-process')
            self.assertEqual(access is None, bool(proc.select('[data-fact-id="restriction-access-process"]')))
            selected = access == 'licenseRestrictAccessAnotherAUuid'
            self.assertEqual(selected and not has_custom, bool(proc.select('[data-fact-id="restriction-custom-process"][data-status="missing"]')))
            self.assertEqual(metadata is None, bool(proc.select('[data-fact-id="restriction-metadata-publication"]')))
            self.assertEqual(metadata == 'licenseRestrictMetadataNoAUuid', 'will not be published' in proc.get_text())
            self.assertEqual(selected and has_custom, 'Access-2027-12-31.csv' in proc.get_text())
            detail = proc.select_one('.answer-detail')
            if selected and has_custom: self.assertEqual(AUTHORED, detail.decode_contents())
            self.assertFalse(soup.select('p p, p div, p ul'))

    def test_restricted_summary_contains_date_but_not_free_conditions(self):
        replies = {p: v['value'] for p,v in storage_cases('en')['storage-sharing'].items()}
        soup = BeautifulSoup(render_question(Q10, replies), 'html.parser')
        entry = soup.select_one('.license-entry:not(.joined-policy)')
        self.assertEqual(2, len(entry.select('.license-summary > p')))
        self.assertIn('2027-06-01', entry.select_one('.license-summary').get_text())
        self.assertFalse(entry.select('.license-summary .answer-detail, .joined-policy'))

    def test_preservation_gaps_break_runs_without_hiding_metadata(self):
        replies = {p: v['value'] for p,v in sharing_cases('en')['sharing-missing'].items()}
        soup = BeautifulSoup(render_question(Q11, replies), 'html.parser')
        summary = soup.select_one('.preservation-summary')
        self.assertEqual(2, len(summary.select('.reading-gap')))
        self.assertFalse(summary.select(':scope > p.data-gap'))
        self.assertIn('The metadata will be available even when the data no longer exists.', summary.get_text())

    def test_preservation_cost_free_answer_has_separate_label_and_blocks(self):
        replies = {p: v['value'] for p,v in sharing_cases('en')['sharing-custom'].items()}
        key = next(p for p in replies if p.endswith(IDS['repoChargesHowPayOtherQUuid']))
        replies[key] = AUTHORED
        soup = BeautifulSoup(render_question(Q11, replies), 'html.parser')
        resources = soup.select_one('.preservation-resources')
        self.assertEqual(AUTHORED, resources.select_one('.answer-detail').decode_contents())
        self.assertEqual('Other arrangements for paying repository costs:', resources.select_one('.answer-lead').get_text())
        self.assertFalse(soup.select('p p, p div, p ul'))
