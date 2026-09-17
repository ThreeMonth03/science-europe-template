import copy
from pathlib import Path
import sys
import unittest
from lxml import etree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from q5_word_join_contract import W, NEW, REMOVE, prior_lua, check_word
from storage_context_contract import without_reviewed_context


def paragraph(text, style='PilotLead'):
    p = ET.Element(W + 'p', nsmap={'w': W[1:-1]})
    props = ET.SubElement(p, W + 'pPr')
    ET.SubElement(props, W + 'pStyle').set(W + 'val', style)
    r = ET.SubElement(p, W + 'r'); ET.SubElement(r, W + 't').text = text
    return p


def pair():
    old = [paragraph('5. Storage?', 'Heading3'), paragraph('0 GB; Original.csv。'), paragraph('Limitations:'),
           paragraph('Location unknown.', 'PilotListLead'), paragraph('Schedule unknown.', 'Compact'), paragraph('6. Security?', 'Heading3')]
    new = copy.deepcopy(old)
    run = ET.SubElement(new[1], W + 'r'); ET.SubElement(run, W + 'br')
    new[1].append(copy.deepcopy(new[2][1])); new.pop(2)
    return old, new


class Q5WordJoinTests(unittest.TestCase):
    def test_exact_source_delta_composes_with_original_hash_gate(self):
        source = (ROOT / 'src/word/pilot.lua').read_text()
        restored = prior_lua(source)
        self.assertNotIn('-- BEGIN joined Q5', restored)
        self.assertEqual(without_reviewed_context(source, 'lua'), without_reviewed_context(restored, 'lua'))
        for value in (source.replace(NEW, ''), source + NEW, source.replace(REMOVE, ''),
                      source.replace('joined:insert(pandoc.LineBreak())', 'joined:insert(pandoc.Space())')):
            with self.assertRaises(AssertionError): prior_lua(value)
        with self.assertRaises(AssertionError): without_reviewed_context(source.replace('units > 900', 'units > 901'), 'lua')

    def test_one_exact_join_preserves_punctuation_styles_and_other_questions(self):
        old, new = pair()
        self.assertEqual(check_word(old, new, True), 1)
        for index in range(len(new)):
            changed = copy.deepcopy(new); changed[index].find('.//' + W + 't').text += '!'
            with self.assertRaises(AssertionError): check_word(old, changed, True)
        for index in range(len(new)):
            changed = copy.deepcopy(new)
            changed[index].find(W + 'pPr/' + W + 'pStyle').set(W + 'val', 'Other')
            with self.assertRaises(AssertionError): check_word(old, changed, True)

    def test_missing_extra_or_page_breaks_and_inline_format_changes_fail(self):
        old, new = pair()
        for kind in ('missing', 'extra', 'page', 'bold'):
            changed = copy.deepcopy(new)
            if kind == 'missing': changed[1].remove(changed[1][2])
            elif kind == 'extra': ET.SubElement(changed[1][2], W + 'br')
            elif kind == 'page': changed[1].find('.//' + W + 'br').set(W + 'type', 'page')
            else: ET.SubElement(ET.SubElement(changed[1][1], W + 'rPr'), W + 'b')
            with self.assertRaises(AssertionError): check_word(old, changed, True)

    def test_fallback_and_ambiguous_pairs_cannot_join(self):
        old, new = pair()
        self.assertEqual(check_word(old, old, False), 0)
        with self.assertRaises(AssertionError): check_word(old, new, False)
        with self.assertRaises(AssertionError): check_word(old + old, new + new, True)
        broken = copy.deepcopy(old); ET.SubElement(broken[1][1], W + 'br')
        with self.assertRaises(AssertionError): check_word(broken, new, True)


if __name__ == '__main__': unittest.main()
