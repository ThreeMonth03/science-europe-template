"""Submission-only prose resources must not reserve empty budget columns.

Authored bodies here are pre-rendered HTML, as in the existing component
adapter. Stock worker/parser and native pagination remain separate QA.
"""
import itertools
from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_answer_mapping import question
from check_project_acronym import fixture as project_fixture, integration
from current_support import IDS, PREFIX, environment, path

QUESTION = 'src/questions/15-required-resources.html.j2'
MODES = {'html': {}, 'pdf': {'pdf_budget_reading': True},
         'word': {'word_budget_reading': True}}
PURPOSES = (
    '<p>Retain source records.</p>',
    '<p>保留來源紀錄。</p><p>保留 v1.2 與 0.csv。</p>',
    '<p>First.</p><ul><li>Outer<ul><li>Nested.</li></ul></li></ul>',
    '<table><thead><tr><th>Record</th><th>Years</th></tr></thead>'
    '<tbody><tr><td>Original</td><td>10</td></tr></tbody></table>',
    '<p><img src="source-figure.png" alt="Original figure"></p>',
)


def fixture(rows):
    km, replies = project_fixture(None, 'Source-based project', 'study')
    children = km['entities']['questions'][IDS['projectsQUuid']]['itemTemplateQuestionUuids']
    children = question(km, children, IDS['costQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
    for field in ('costTitleQUuid', 'costDescriptionQUuid', 'costAmountQUuid'):
        question(km, children, IDS[field], 'ValueQuestion')
    question(km, children, IDS['costCurrencyQUuid'], 'IntegrationQuestion')
    question(km, children, IDS['costAllocationQUuid'], 'MultiChoiceQuestion',
             [IDS['costAllocation' + option + 'AUuid'] for option in
              ('Findability', 'Accessibility', 'Interoperability', 'Reusability')]
             + [IDS['costManagementAUuid']])
    question(km, children, IDS['costCoverQUuid'], 'OptionsQuestion',
             [IDS['costCoverGrantAUuid'], IDS['costCoverOtherAUuid']])
    for option, field in (('Grant', 'costCoverGrantIdQUuid'), ('Other', 'costCoverOtherHowQUuid')):
        question(km, km['entities']['answers'][IDS['costCover' + option + 'AUuid']]['followUpUuids'],
                 IDS[field], 'ValueQuestion')
    replies.update({path('adminDetailsCUuid', 'additionalExpertiseQUuid'): IDS['additionalExpertiseNoAUuid'],
                    path('adminDetailsCUuid', 'additionalHWSWQUuid'): IDS['additionalHWSWNoAUuid'],
                    path('preservingCUuid', 'repoChargesQUuid'): IDS['repoChargesNoAUuid']})
    listing = path('adminDetailsCUuid', 'projectsQUuid', 'study', 'costQUuid')
    replies[listing] = [f'cost-{i}' for i in range(1, len(rows) + 1)]
    for i, row in enumerate(rows, 1):
        item = path(listing, f'cost-{i}')
        for key, binding in [('title', 'costTitleQUuid'), ('purpose', 'costDescriptionQUuid'),
                             ('amount', 'costAmountQUuid')]:
            if key in row: replies[path(item, binding)] = row[key]
        if 'currency' in row: replies[path(item, 'costCurrencyQUuid')] = integration(row['currency'])
        if 'allocation' in row: replies[path(item, 'costAllocationQUuid')] = row['allocation']
        if 'cover' in row:
            cover = path(item, 'costCoverQUuid')
            replies[cover] = IDS.get('costCover' + row['cover'] + 'AUuid', row['cover'])
            for option, field, value_key in [('Grant', 'costCoverGrantIdQUuid', 'grant'),
                                             ('Other', 'costCoverOtherHowQUuid', 'cover_detail')]:
                if value_key in row:
                    replies[path(cover, 'costCover' + option + 'AUuid', field)] = row[value_key]
    return km, replies, listing


class PublicDmpResourceProseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = {escape: environment(ROOT, escape).from_string(
            PREFIX + "{% include '" + QUESTION + "' %}") for escape in (False, True)}

    def render(self, rows, *, profile='submission', mode='html', escape=False):
        km, replies, listing = fixture(rows)
        raw = self.templates[escape].render(km=km, repliesMap=replies,
                                           output_profile=profile, **MODES[mode])
        return raw, BeautifulSoup(raw, 'html.parser'), listing

    def test_prose_only_submission_is_full_width_and_keeps_authored_html(self):
        for escape, mode, purpose in itertools.product((False, True), MODES, PURPOSES):
            with self.subTest(escape=escape, mode=mode, purpose=purpose):
                raw, soup, listing = self.render([{'title': 'Resource A', 'purpose': purpose}],
                                                  escape=escape, mode=mode)
                record, = soup.select('.project-resources > .resource-prose')
                self.assertEqual(record['data-item-id'], path(listing, 'cost-1'))
                self.assertEqual(record.select_one('p > strong').get_text(), 'Resource A')
                self.assertIn(purpose, raw)  # Including pure images, never striptags eligibility.
                self.assertFalse(soup.select('table.resource-table, .resource-budget, .resource-funding'))
                self.assertFalse(soup.select('.data-gap, .data-review'))

    def test_review_keeps_three_columns_and_all_original_missing_hints(self):
        for escape, mode in itertools.product((False, True), MODES):
            raw, soup, _ = self.render([{'title': 'Resource A', 'purpose': PURPOSES[0]}],
                                      profile='review', escape=escape, mode=mode)
            self.assertFalse(soup.select('.resource-prose'))
            table, = soup.select('table.resource-table')
            self.assertEqual(len(table.select('thead th')), 3)
            self.assertEqual(len(table.select('tbody > tr > td')), 3)
            self.assertEqual({n['data-fact-id'] for n in table.select('.data-gap')},
                             {'resource-amount', 'resource-allocation', 'cost-coverage'})
            self.assertIn(PURPOSES[0], raw)

    def test_every_partial_budget_funding_or_allocation_keeps_the_budget_path(self):
        partials = [
            {'amount': '0'}, {'amount': '5000'}, {'currency': 'TWD'},
            {'amount': '0', 'currency': 'TWD'},
            {'cover': 'Grant'}, {'cover': 'Grant', 'grant': 'GRANT-0'},
            {'cover': 'Other'}, {'cover': 'Other', 'cover_detail': '<p>Institutional support.</p>'},
            {'cover': 'Other', 'cover_detail': '<p><img src="funding.png" alt="Funding"></p>'},
            {'allocation': [IDS['costAllocationFindabilityAUuid']]},
            {'allocation': [IDS['costManagementAUuid']]},
            {'allocation': ['unknown-allocation']},  # Conservative original fallback, no invented claim.
        ]
        for escape, mode, partial in itertools.product((False, True), MODES, partials):
            with self.subTest(escape=escape, mode=mode, partial=partial):
                raw, soup, _ = self.render([{'title': 'Resource A', 'purpose': PURPOSES[0], **partial}],
                                          escape=escape, mode=mode)
                self.assertFalse(soup.select('.resource-prose'))
                self.assertTrue(soup.select('table.resource-table'))
                self.assertIn(PURPOSES[0], raw)
                self.assertFalse(soup.select('.data-gap, .data-review'))
                text = soup.get_text(' ', strip=True)
                if 'amount' in partial: self.assertIn(partial['amount'], text)
                if 'currency' in partial: self.assertIn(partial['currency'], text)
                if partial.get('cover') == 'Other' and 'cover_detail' not in partial:
                    self.assertIn('Other funding arrangements are planned.', text)
                if partial.get('allocation') == ['unknown-allocation']:
                    self.assertNotIn('This resource supports', text)

    def test_mixed_records_keep_order_identity_zero_and_neutral_original_ordinal(self):
        rows = [
            {'title': 'First prose', 'purpose': '<p>First source.</p>'},
            {'title': 'Paid', 'purpose': '<p>Paid purpose.</p>', 'amount': '0', 'currency': 'TWD'},
            {'purpose': '<p>Unnamed source.</p>'},
            {'title': 'Currency only', 'purpose': '<p>Currency purpose.</p>', 'currency': 'EUR'},
            {'title': 'Last prose', 'purpose': '<p>Last source.</p>'},
        ]
        for escape, mode in itertools.product((False, True), MODES):
            raw, soup, listing = self.render(rows, escape=escape, mode=mode)
            owner, = soup.select('.project-resources')
            records = owner.select(':scope > .resource-prose, :scope > table.resource-table > tbody > tr')
            self.assertEqual([n['data-item-id'] for n in records],
                             [path(listing, f'cost-{i}') for i in range(1, 6)])
            self.assertEqual(len(soup.select('.resource-prose')), 3)
            self.assertEqual(soup.select('.resource-prose')[1].strong.get_text(), 'Resource 3')
            self.assertIn('0 TWD', soup.get_text(' ', strip=True))
            for row in rows: self.assertEqual(raw.count(row['purpose']), 1)
            self.assertFalse(soup.select('.data-gap, .data-review'))

    def test_blank_scalars_do_not_create_budget_claims_or_empty_columns(self):
        for escape, mode, blank in itertools.product((False, True), MODES, ('', ' \t\n\u3000')):
            raw, soup, _ = self.render([{'title': 'Only prose', 'purpose': PURPOSES[0],
                'amount': blank, 'currency': blank, 'allocation': [], 'cover': 'unknown',
                'cover_detail': '<p>Stale funding must not appear.</p>'}], escape=escape, mode=mode)
            self.assertEqual(len(soup.select('.resource-prose')), 1)
            self.assertFalse(soup.select('table.resource-table'))
            self.assertNotIn('Stale funding', raw)
            self.assertNotIn('Other funding arrangements', raw)

    def test_title_only_is_retained_but_completely_empty_record_is_not_reclassified(self):
        for mode in MODES:
            _, soup, _ = self.render([{'title': 'Named resource'}], mode=mode)
            self.assertEqual(soup.select_one('.resource-prose').strong.get_text(), 'Named resource')
            _, soup, _ = self.render([{}], mode=mode)
            self.assertFalse(soup.select('.resource-prose'))
            self.assertTrue(soup.select('table.resource-table'))

    def test_funded_authored_tables_keep_the_existing_full_width_funding_renderer(self):
        funding = '<table><tr><th>Source</th></tr><tr><td>FUNDER-0</td></tr></table>'
        rows = [{'title': 'Prose', 'purpose': PURPOSES[0]},
                {'title': 'Funded', 'purpose': PURPOSES[0], 'amount': '0',
                 'currency': 'TWD', 'cover': 'Other', 'cover_detail': funding}]
        for mode in ('pdf', 'word'):
            raw, soup, listing = self.render(rows, mode=mode)
            self.assertEqual(len(soup.select('.resource-prose')), 1)
            self.assertEqual(len(soup.select('.' + mode + '-rich-funding-metadata')), 1)
            self.assertIn(funding, raw)
            self.assertEqual(soup.select_one('.' + mode + '-rich-funding-metadata')['data-item-id'],
                             path(listing, 'cost-2'))


if __name__ == '__main__':
    unittest.main()
