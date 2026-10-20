"""Keep optional re-use prose meaningful and name-only format inventories compact."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_access_reading import reuse_replies, reuse_schema
from current_support import IDS, PREFIX, environment, path

Q2 = "{% include 'src/questions/02-what-data.html.j2' %}"
Q13 = "{% include 'src/questions/13-persistent-identifier.html.j2' %}"
FORMATS = path('creatingCUuid', 'formatsQUuid')
NAMES = ('WAV', 'MP3', 'DOCX', 'PDF', 'TXT', 'NVP')


def name_reply(name, raw=None):
    value = dict(type='PlainType', value=name)
    if raw is not None:
        value.update(type='IntegrationType', raw=raw)
    return {'value': {'type': 'IntegrationReply', 'value': value}}


def format_replies(names=NAMES):
    replies = {FORMATS: [f'format-{i}' for i in range(len(names))]}
    replies.update({path(FORMATS, item, 'formatsNameQUuid'): name_reply(name)
                    for item, name in zip(replies[FORMATS], names)})
    return replies


class PublicDmpPartialListsTests(unittest.TestCase):
    def render(self, source, replies, profile='submission', escape=False, km=None):
        context = {} if km is None else {'km': km}
        soup = BeautifulSoup(environment(ROOT, escape).from_string(PREFIX + source).render(
            repliesMap=replies, output_profile=profile, **context), 'html.parser')
        self.assertFalse(soup.select('p p, p div, p ul, p table, ul:empty, li:empty'))
        if profile == 'submission':
            self.assertFalse(soup.select('.data-gap, .data-review, .empty-value'))
        return soup

    def test_name_only_reuse_is_not_an_answer_but_original_name_and_question_remain(self):
        for escape in (False, True):
            for option in ('', 'unknown'):
                with self.subTest(escape=escape, option=option):
                    replies, _ = reuse_replies(option, 'Existing dataset', '<p>Inactive use.</p>')
                    soup = self.render(Q2 + Q13, replies, escape=escape, km=reuse_schema())
                    self.assertIsNone(soup.select_one('.measured-data-reuse'))
                    self.assertIn('Existing dataset', soup.select_one('#q-what-data').get_text())
                    self.assertIsNotNone(soup.select_one('#q-persistent-identifier > h3'))
                    self.assertNotIn('Inactive use.', soup.get_text())
                    for profile in ('review', 'unknown'):
                        review = self.render(Q13, replies, profile, escape, reuse_schema())
                        self.assertEqual('Existing dataset', review.select_one('.reuse-summary strong').get_text())

    def test_known_reuse_and_authored_uses_remain_without_a_name(self):
        authored = '<p>Keep an independent use.</p><ul><li>Keep the list.</li></ul><table><tr><td>Keep the table.</td></tr></table>'
        for escape in (False, True):
            for option in ('Us', 'SameField', 'OtherField'):
                with self.subTest(escape=escape, option=option):
                    replies, listing = reuse_replies(option, None, authored)
                    replies[listing] = ['blank-first', 'name-only', 'measured-a']
                    replies[path(listing, 'name-only', 'measuredDataNameQUuid')] = 'Not a reuse answer'
                    soup = self.render(Q13, replies, escape=escape, km=reuse_schema())
                    rows = soup.select('.measured-data-reuse > ul > li')
                    self.assertEqual(['measured-a'], [row['data-item-id'] for row in rows])
                    self.assertIsNotNone(rows[0].select_one('.dataset-label[data-list-index="3"]'))
                    self.assertIsNotNone(rows[0].select_one('[data-fact-id="measured-data-reuse"]'))
                    body = rows[0].select_one('[data-fact-id="measured-data-reuse-uses"]')
                    self.assertEqual(option == 'OtherField', bool(body))
                    if body:
                        self.assertEqual(authored, body.decode_contents())

    def test_wholly_name_only_submission_is_one_inventory_with_original_identity(self):
        for escape in (False, True):
            for names in (NAMES, ('Same name', 'Same name'), ('中文格式', 'Other format')):
                with self.subTest(escape=escape, names=names):
                    replies = format_replies(names)
                    soup = self.render(Q2, replies, escape=escape)
                    listing = soup.select_one('.format-name-list')
                    self.assertIsNotNone(listing)
                    self.assertEqual(list(names), [n.get_text() for n in listing.select('strong[data-item-id]')])
                    self.assertEqual(replies[FORMATS], [n['data-item-id'] for n in listing.select('strong')])
                    self.assertEqual(1, len(soup.select('.data-formats > p')))
                    self.assertFalse(soup.select('.format-description'))
                    self.assertIsNotNone(soup.select_one('#q-what-data > h3'))
                    self.assertNotIn('suitable for sharing', soup.get_text())

    def test_compact_inventory_keeps_integration_links(self):
        replies = format_replies(('FAIR format', 'Plain format'))
        replies[path(FORMATS, 'format-0', 'formatsNameQUuid')] = name_reply(
            '', raw={'name': 'FAIR format', 'doi': '10.1234/example'})
        for escape in (False, True):
            soup = self.render(Q2, replies, escape=escape)
            link = soup.select_one('.format-name-list strong[data-item-id="format-0"] a')
            self.assertEqual('FAIR format', link.get_text())
            self.assertEqual('https://doi.org/10.1234/example', link['href'])

    def test_review_keeps_each_name_and_its_original_missing_field_prompts(self):
        for escape in (False, True):
            for profile in ('review', 'unknown'):
                with self.subTest(escape=escape, profile=profile):
                    soup = self.render(Q2, format_replies(), profile, escape)
                    self.assertIsNone(soup.select_one('.format-name-list'))
                    records = soup.select('.format-description')
                    self.assertEqual(6, len(records))
                    for record, name in zip(records, NAMES):
                        self.assertIn(name, record.get_text())
                        self.assertIsNotNone(record.select_one('.data-gap [data-fact-id="format-standard"]'))
                        self.assertIsNotNone(record.select_one('.data-gap [data-fact-id="format-archiving"]'))
                        self.assertIsNotNone(record.select_one('.data-gap [data-fact-id="format-volume"]'))

    def test_partial_details_unknown_choices_and_missing_names_are_not_merged(self):
        first = path(FORMATS, 'format-0')
        volume = path(first, 'formatsVolumeQUuid')
        cases = [
            (path(first, 'formatsIsStandardQUuid'), IDS['formatsIsStandardYesAUuid'], 'standard format'),
            (path(first, 'formatsIsLTSuitableQUuid'), IDS['formatsIsLTSuitableNoAUuid'], 'not suitable for both'),
            (volume, IDS['formatsVolumeTotalAUuid'], None),
            (volume, 'unsupported-volume-option', None),
            (path(first, 'formatsIsStandardQUuid'), 'unsupported-standard-option', None),
            (path(first, 'formatsIsLTSuitableQUuid'), 'unsupported-suitability-option', None),
            (path(first, 'formatsNameQUuid'), name_reply(' \t\n\u3000'), 'Data format 1.'),
        ]
        for escape in (False, True):
            for key, value, expected in cases:
                with self.subTest(escape=escape, key=key, value=value):
                    replies = format_replies()
                    replies[key] = deepcopy(value)
                    if key == volume and value == IDS['formatsVolumeTotalAUuid']:
                        replies[path(volume, 'formatsVolumeTotalAUuid', 'formatsVolumeTotalGBQUuid')] = '0.25'
                        expected = '0.25\u00a0GB'
                    soup = self.render(Q2, replies, escape=escape)
                    self.assertIsNone(soup.select_one('.format-name-list'))
                    self.assertEqual(replies[FORMATS], [n['data-item-id'] for n in soup.select('.format-description')])
                    if expected:
                        self.assertIn(expected, soup.select_one('.format-description').get_text())
                    for name in NAMES[1:]:
                        self.assertIn(name, soup.get_text())

    def test_single_and_empty_format_inventories_keep_existing_behavior(self):
        for escape in (False, True):
            single = self.render(Q2, format_replies(('Only format',)), escape=escape)
            self.assertIsNone(single.select_one('.format-name-list'))
            self.assertEqual(1, len(single.select('.format-description')))
            empty = self.render(Q2, {FORMATS: []}, escape=escape)
            self.assertIsNotNone(empty.select_one('#q-what-data > h3'))
            self.assertIsNone(empty.select_one('.data-formats'))
            review = self.render(Q2, {FORMATS: []}, 'review', escape)
            self.assertIsNotNone(review.select_one('[data-requirement-id="SE-1b"][data-status="missing-output"]'))

    def test_authored_reason_and_partial_file_count_keep_their_own_records(self):
        authored = '<p>Keep the reason.</p><ul><li>Keep a constraint.</li></ul><table><tr><td>Keep a value.</td></tr></table>'
        replies = format_replies()
        standard = path(FORMATS, 'format-0', 'formatsIsStandardQUuid')
        reason = path(standard, 'formatsIsStandardNoAUuid', 'formatsWhyNonStandardQUuid')
        volume = path(FORMATS, 'format-1', 'formatsVolumeQUuid')
        replies.update({standard: IDS['formatsIsStandardNoAUuid'],
            reason: IDS['formatsWhyNSAnotherReasonAUuid'],
            path(reason, 'formatsWhyNSAnotherReasonAUuid', 'formatsWhyNSAnotherReasonQUuid'): authored,
            volume: IDS['formatsVolumeFileSizeAUuid'],
            path(volume, 'formatsVolumeFileSizeAUuid', 'formatsVolumeFilesQUuid'): '0'})
        for escape in (False, True):
            soup = self.render(Q2, replies, escape=escape)
            self.assertIsNone(soup.select_one('.format-name-list'))
            first = soup.select_one('.format-description[data-item-id="format-0"]')
            self.assertEqual(authored, first.select_one('.reading-detail').decode_contents())
            second = soup.select_one('.format-description[data-item-id="format-1"]')
            self.assertIn('number of files or study subjects is 0.', second.get_text())
            self.assertNotIn('average data volume', second.get_text())
            review = self.render(Q2, replies, 'review', escape)
            self.assertIsNotNone(review.select_one('[data-item-id="format-1"] .data-gap [data-fact-id="format-file-size"]'))


if __name__ == '__main__':
    unittest.main()
