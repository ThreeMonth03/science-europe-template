"""Q2 format facts survive partial answers; authored reasons are not prose fragments."""
import itertools
import unittest
from bs4 import BeautifulSoup
from test_answer_retention import IDS, path
from test_reading_units import AUTHORED, Q2
from test_science_europe_contract import render_question
from test_structure_bindings import BlockProbe

FORMATS = path('creatingCUuid', 'formatsQUuid')
FORMAT = path(FORMATS, 'format-1')
STANDARD = path(FORMAT, 'formatsIsStandardQUuid')
WHY = path(STANDARD, 'formatsIsStandardNoAUuid', 'formatsWhyNonStandardQUuid')
REASON = path(WHY, 'formatsWhyNSAnotherReasonAUuid', 'formatsWhyNSAnotherReasonQUuid')
ARCHIVE = path(FORMAT, 'formatsIsLTSuitableQUuid')
CONVERT = path(ARCHIVE, 'formatsIsLTSuitableNoAUuid', 'formatsConvertLTSuitableQUuid')
VOLUME = path(FORMAT, 'formatsVolumeQUuid')
COUNT = path(VOLUME, 'formatsVolumeFileSizeAUuid', 'formatsVolumeFilesQUuid')
SIZE = path(VOLUME, 'formatsVolumeFileSizeAUuid', 'formatsVolumeFileGBQUuid')
TOTAL = path(VOLUME, 'formatsVolumeTotalAUuid', 'formatsVolumeTotalGBQUuid')


def values():
    # Match DSW's nested runtime IntegrationReply, not just the event payload.
    return {FORMATS: ['format-1'], path(FORMAT, 'formatsNameQUuid'):
            {'value': {'value': {'type': 'PlainType', 'value': 'MyInstrument v1.2 / CSV'}}}}


def volume_cases():
    for count, size in itertools.product([None, '', ' ', '0', '12'], [None, '', ' ', '0', '0.0001']):
        data = values(); data[VOLUME] = IDS['formatsVolumeFileSizeAUuid']
        if count is not None: data[COUNT] = count
        if size is not None: data[SIZE] = size
        yield data, count, size


class FormatVolumeTests(unittest.TestCase):
    def render(self, data):
        html = render_question(Q2, data)
        probe = BlockProbe(); probe.feed(html)
        self.assertEqual([], probe.errors); self.assertEqual([], probe.stack)
        return BeautifulSoup(html, 'html.parser').select_one('.format-description')

    def test_each_quantity_survives_missing_sibling_including_zero(self):
        for data, count, size in volume_cases():
            with self.subTest(count=count, size=size):
                soup = self.render(data)
                self.assertEqual(not bool((count or '').strip()), bool(soup.select('[data-fact-id="format-file-count"]')))
                self.assertEqual(not bool((size or '').strip()), bool(soup.select('[data-fact-id="format-file-size"]')))
                if (count or '').strip(): self.assertIn(f'We expect {count} files', soup.get_text())
                if (size or '').strip():
                    prefix = 'average size of' if (count or '').strip() else 'average file size is'
                    self.assertIn(f'{prefix} {size} GB.', soup.get_text().replace('\xa0', ' '))
                self.assertFalse(soup.select('.format-summary .data-gap, .format-summary ul, .format-summary br'))

    def test_total_and_small_are_distinct_from_unknown(self):
        for total in ('120', '0', None, '', ' '):
            data = values(); data[VOLUME] = IDS['formatsVolumeTotalAUuid']
            if total is not None: data[TOTAL] = total
            soup = self.render(data)
            self.assertEqual(not bool((total or '').strip()), bool(soup.select('[data-fact-id="format-total-volume"]')))
            if (total or '').strip(): self.assertIn(f'estimated data volume is {total} GB.', soup.get_text().replace('\xa0', ' '))
        data[VOLUME] = IDS['formatsVolumeSmallAUuid']
        self.assertIn('small volume of data', self.render(data).get_text())
        del data[VOLUME]
        self.assertTrue(self.render(data).select('[data-fact-id="format-volume"]'))

    def test_nonstandard_and_unsuitable_no_answers_do_not_disappear(self):
        for why, convert in itertools.product([None, 'formatsWhyNSThereIsNoStandardAUuid', 'formatsWhyNSItIsOptimizedAUuid', 'formatsWhyNSAnotherReasonAUuid'], [None, 'formatsConvertLTSuitableYesAUuid', 'formatsConvertLTSuitableNoAUuid']):
            data = values(); data[STANDARD] = IDS['formatsIsStandardNoAUuid']; data[ARCHIVE] = IDS['formatsIsLTSuitableNoAUuid']
            if why: data[WHY] = IDS[why]
            if convert: data[CONVERT] = IDS[convert]
            soup = self.render(data); text = soup.get_text(' ', strip=True)
            self.assertIn('not using a standardized format', text)
            self.assertIn('not', text); self.assertIn('suitable', text)
            self.assertEqual(why in (None, 'formatsWhyNSAnotherReasonAUuid'), bool(soup.select('[data-fact-id="nonstandard-reason"][data-status="missing"]')))
            self.assertEqual(convert is None, bool(soup.select('[data-fact-id="format-conversion"]')))
            self.assertEqual(convert == 'formatsConvertLTSuitableNoAUuid', 'do not plan to convert' in text)

    def test_free_reason_keeps_blocks_case_and_terminal_punctuation(self):
        data = values(); data[STANDARD] = IDS['formatsIsStandardNoAUuid']; data[WHY] = IDS['formatsWhyNSAnotherReasonAUuid']
        for answer in (AUTHORED, '<p>JSON, CSV and MyInstrument v1.2!</p>', '<p>Do not add a full stop</p>'):
            data[REASON] = answer; soup = self.render(data)
            detail = soup.select_one('[data-fact-id="nonstandard-reason"][data-status="complete"]')
            detail.select_one('.answer-lead').decompose()
            self.assertEqual(answer, detail.decode_contents().strip())
            self.assertNotIn(answer, soup.select_one('.format-summary').decode_contents())

    def test_unknown_is_not_no_and_gaps_form_one_separate_paragraph(self):
        soup = self.render({FORMATS: ['format-1']})
        self.assertIn('Unnamed data format 1.', soup.get_text())
        self.assertNotIn('not suitable', soup.get_text())
        self.assertNotIn('not using', soup.get_text())
        self.assertEqual(1, len(soup.select('p.data-gap')))
        self.assertEqual(4, len(soup.select('p.data-gap > span[data-status="missing"]')))

    def test_no_numeric_coercion_or_rounded_zero_total(self):
        for count, size in [('2', '0.0001'), ('2.5', 'invalid'), ('1e3', '0.5')]:
            data = values(); data[VOLUME] = IDS['formatsVolumeFileSizeAUuid']; data[COUNT] = count; data[SIZE] = size
            text = self.render(data).get_text().replace('\xa0', ' ')
            self.assertIn(f'We expect {count} files', text); self.assertIn(f'average size of {size} GB.', text)
            self.assertNotIn('GB in total', text)

    def test_inactive_followups_do_not_leak_into_other_choices(self):
        data = values(); data.update({STANDARD: IDS['formatsIsStandardYesAUuid'], WHY: IDS['formatsWhyNSAnotherReasonAUuid'], REASON: AUTHORED,
            ARCHIVE: IDS['formatsIsLTSuitableYesAUuid'], CONVERT: IDS['formatsConvertLTSuitableNoAUuid'], VOLUME: IDS['formatsVolumeSmallAUuid'], COUNT: '999', SIZE: '888', TOTAL: '777'})
        text = self.render(data).get_text()
        for stale in ('999', '888', '777', 'Keep v1.2', 'do not plan to convert'):
            self.assertNotIn(stale, text)
