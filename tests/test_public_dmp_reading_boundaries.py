"""Bounded fixes from the public-DMP reading review; no source-specific strings."""
from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from current_support import IDS, PREFIX, environment, path


def quality_fixture(fixed=True):
    measured = path('creatingCUuid', 'measuredQUuid')
    listing = path(measured, 'measuredYesAUuid', 'measuredDataQUuid')
    item = path(listing, 'dataset-1')
    control = path(item, 'measuredDataQualityQUuid')
    methods = path(control, 'measuredDataQualityYesAUuid')
    other = path(methods, 'mdQualityOtherQUuid')
    replies = {measured: IDS['measuredYesAUuid'], listing: ['dataset-1'],
        path(item, 'measuredDataNameQUuid'): 'Dataset A', control: IDS['measuredDataQualityYesAUuid'],
        other: IDS['mdQualityOtherYesAUuid']}
    if fixed:
        replies[path(methods, 'mdQualityCalibratingQUuid')] = IDS['mdQualityCalibratingYesAUuid']
    return replies, listing, item, path(other, 'mdQualityOtherYesAUuid', 'mdQualityOtherWhatQUuid')


class PublicDMPReadingBoundaries(unittest.TestCase):
    def render(self, question, replies, **extra):
        return BeautifulSoup(environment(ROOT, True).from_string(
            PREFIX + "{% include 'src/questions/" + question + "' %}").render(
                repliesMap=replies, output_profile='submission', **extra), 'html.parser')

    def test_policy_label_leads_only_its_own_opening_not_the_whole_answer(self):
        listing = path('adminDetailsCUuid', 'policiesProceduresQUuid')
        authored = '<p>' + 'Original long explanation. ' * 20 + '</p><p>Original ending.</p>'
        for name, body, expected in [('Policy', authored, True),
                ('Policy', '<p>Original <strong>emphasis</strong>.</p>', True),
                ('Policy', '<table><tr><td>Original</td></tr></table>', False),
                ('中' * 81, authored, False), ('', authored, False), ('Policy', '', False)]:
            with self.subTest(name=name, body=body[:30]):
                replies = {listing: ['a', 'b'], path(listing, 'a', 'policiesProceduresNameQUuid'): name,
                    path(listing, 'a', 'policiesProceduresDescriptionQUuid'): body,
                    path(listing, 'b', 'policiesProceduresNameQUuid'): 'Next policy'}
                soup = self.render('06-access-security.html.j2', replies)
                item = soup.select_one('.answer > ul > li')
                self.assertEqual(bool(item.select_one(':scope > .answer-lead > p')), expected)
                self.assertFalse(item.select('.short-policy-item'))
                if body:
                    rendered_body = ''.join(str(n) for n in BeautifulSoup(body, 'html.parser').contents)
                    self.assertIn(rendered_body, str(item))
                self.assertNotIn('Next policy', item.get_text())

    def test_empty_metadata_wrapper_does_not_precede_the_first_real_answer(self):
        storage = path('processingCUuid', 'storageConvQUuid')
        soup = self.render('03-docs-metadata.html.j2', {storage: IDS['storageConvExploreAUuid'],
            path(storage, 'storageConvExploreAUuid', 'storageConvObjStoreQUuid'): IDS['storageConvObjStoreYesAUuid']})
        self.assertFalse(soup.select('.metadata-policy'))
        first = soup.select_one('.answer').find(True, recursive=False)
        self.assertEqual((first.name, first.get_text()), ('h4', 'Data storage and file conventions'))
        metadata = path('accessCUuid', 'metadataOpenQUuid')
        soup = self.render('03-docs-metadata.html.j2', {metadata: IDS['metadataOpenNoAUuid']})
        self.assertIn('Metadata will not be available openly.', soup.select_one('.metadata-policy').get_text())

    def test_sharing_hint_extends_only_bounded_plain_records(self):
        template = environment(ROOT, True).from_string(PREFIX + '{{ macros.shortDatasetRecord(body, label, limit=500) }}')
        for body, label, expected in [('<p>' + 'x' * 350 + '</p>', 'Dataset', True),
                ('<p>' + 'x' * 493 + '</p>', 'Dataset', True),
                ('<p>' + 'x' * 494 + '</p>', 'Dataset', False),
                ('<p>' + 'x' * 500 + '</p>', 'Dataset', False),
                ('<p>' + '中' * 493 + '</p>', 'Dataset', True),
                ('<p>' + '中' * 494 + '</p>', 'Dataset', False),
                ('<p>Original</p>', 'x' * 81, False),
                ('<table><tr><td>Original</td></tr></table>', 'Dataset', False),
                ('<p style="height:900px">Original</p>', 'Dataset', False),
                ('<p>Original</p>' * 7, 'Dataset', False)]:
            self.assertEqual(bool(template.render(body=body, label=label)), expected)
        # Other questions retain their original, narrower default.
        default = environment(ROOT, True).from_string(PREFIX + '{{ macros.shortDatasetRecord(body, label) }}')
        self.assertFalse(default.render(body='<p>' + 'x' * 350 + '</p>', label='Dataset'))

    def test_full_quality_detail_occurs_only_in_q4_submission_but_review_is_unchanged(self):
        authored = '<p>Keep <em>Original.csv</em> &amp; every condition.</p><ul><li>Keep this constraint.</li></ul><table><tr><td>Keep the record.</td></tr></table>'
        replies, _, _, detail = quality_fixture()
        replies[detail] = authored
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX +
                "{% include 'src/questions/01-how-data.html.j2' %}{% include 'src/questions/04-quality-control.html.j2' %}")
            for profile in ('submission', 'review', 'unknown'):
                with self.subTest(escape=escape, profile=profile):
                    rendered = template.render(repliesMap=replies, output_profile=profile)
                    soup = BeautifulSoup(rendered, 'html.parser')
                    q1, q4 = soup.select_one('#q-how-data'), soup.select_one('#q-quality-control')
                    self.assertEqual(1 if profile == 'submission' else 2, rendered.count(authored))
                    self.assertEqual(authored, q4.select_one('[data-fact-id="quality-other"] .reading-detail').decode_contents())
                    self.assertEqual(profile != 'submission', bool(q1.select_one('.answer-detail[data-fact-id="quality-other"]')))
                    for question in (q1, q4):
                        self.assertIn('measurement calibration', question.get_text())
                    if profile == 'submission':
                        self.assertFalse(q1.select('.data-gap, .data-review'))

    def test_other_only_quality_keeps_known_yes_overview_and_complete_detail_in_q4(self):
        replies, _, _, detail = quality_fixture(fixed=False)
        authored = '<p>Keep the only specified method.</p><ol><li>Keep its condition.</li></ol>'
        replies[detail] = authored
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX +
                "{% include 'src/questions/01-how-data.html.j2' %}{% include 'src/questions/04-quality-control.html.j2' %}")
            rendered = template.render(repliesMap=replies, output_profile='submission')
            soup = BeautifulSoup(rendered, 'html.parser')
            q1, q4 = soup.select_one('#q-how-data'), soup.select_one('#q-quality-control')
            self.assertEqual('Quality control is planned for Dataset A.', q1.select_one('.quality-summary').get_text())
            self.assertNotIn('only specified method', q1.get_text())
            self.assertNotIn('No quality control', soup.get_text())
            self.assertEqual(1, rendered.count(authored))
            self.assertEqual(authored, q4.select_one('[data-fact-id="quality-other"] .reading-detail').decode_contents())

    def test_quality_overview_preserves_instruments_and_original_missing_name_ordinals(self):
        replies, listing, item, detail = quality_fixture()
        replies.pop(path(item, 'measuredDataNameQUuid'))
        replies[listing] = ['blank-first', 'dataset-1', 'dataset-2']
        replies[detail] = '<p>Keep the second dataset quality detail.</p>'
        replies[path(listing, 'dataset-2', 'measuredDataQualityQUuid')] = IDS['measuredDataQualityNoAUuid']
        instruments = path(item, 'measuredDataInstrQUuid')
        instrument_detail = '<p>Keep detector setup.</p><ul><li>Keep instrument settings.</li></ul>'
        replies.update({instruments: ['detector'],
            path(instruments, 'detector', 'measuredDataInstrNameQUuid'): 'Detector A',
            path(instruments, 'detector', 'measuredDataInstrDescQUuid'): instrument_detail})
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX +
                "{% include 'src/questions/01-how-data.html.j2' %}{% include 'src/questions/04-quality-control.html.j2' %}")
            soup = BeautifulSoup(template.render(repliesMap=replies, output_profile='submission'), 'html.parser')
            q1, q4 = soup.select_one('#q-how-data'), soup.select_one('#q-quality-control')
            self.assertIn('Detector A', q1.select_one('.single-instrument').get_text())
            self.assertEqual(instrument_detail, q1.select_one('.single-instrument .answer-detail').decode_contents())
            self.assertIsNotNone(q1.select_one('h5 .dataset-label[data-list-index="2"]'))
            self.assertIsNotNone(q4.select_one('[data-item-id="' + item + '"] .dataset-label[data-list-index="2"]'))
            self.assertIsNotNone(q4.select_one('[data-status="explicit-no"] .dataset-label[data-list-index="3"]'))
            self.assertFalse(q1.select('.answer-detail[data-fact-id="quality-other"]'))


if __name__ == '__main__':
    unittest.main()
