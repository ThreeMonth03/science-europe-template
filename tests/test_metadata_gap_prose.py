import hashlib
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from metadata_gap_prose_contract import check_roots, project, restore, compare, joined, old_nodes
from metadata_gap_panel_contract import historical_css
from probe_metadata_gap_prose import check_word, NS


class MetadataGapProseTests(unittest.TestCase):
    def test_word_oracle_rejects_text_style_and_authored_changes(self):
        from xml.etree import ElementTree as E
        from metadata_gap_prose_contract import OLD
        def para(text):
            root = E.Element('{' + NS['w'] + '}p')
            properties = E.SubElement(root, '{' + NS['w'] + '}pPr')
            E.SubElement(properties, '{' + NS['w'] + '}pStyle', {'{' + NS['w'] + '}val': 'BodyText'})
            run = E.SubElement(root, '{' + NS['w'] + '}r')
            E.SubElement(run, '{' + NS['w'] + '}t').text = text
            return E.tostring(root, encoding='unicode')
        for language in ('english', 'chinese'):
            before = list(map(para, ['Original.csv', *OLD[language], 'End.']))
            after = list(map(para, ['Original.csv', joined(language).get_text(), 'End.']))
            self.assertEqual(check_word(before, after, language), 1)
            self.assertEqual(check_word(before[:2] + before[3:], before[:2] + before[3:], language), 0)
            for i, old, new in [(0, 'Original.csv', 'original.csv'), (1, 'BodyText', 'Compact'),
                                (1, joined(language).get_text(), 'Wrong.'), (2, 'End.', 'End')]:
                changed = after.copy(); changed[i] = changed[i].replace(old, new)
                with self.assertRaises(AssertionError):
                    check_word(before, changed, language)
            with self.assertRaises(AssertionError):
                check_word(before, after[:-1], language)

    def test_full_q3_missing_unknown_no_and_authored_content(self):
        result = check_roots(ROOT, ROOT / 'tests/fixtures/metadata-0.3.36.en.html.j2', 'english')
        self.assertEqual(result['comparisons'], 1726)
        self.assertGreater(result['joined'], 0)

    def test_projection_rejects_fact_loss_negation_and_authored_mutations(self):
        for language in ('english', 'chinese'):
            before = BeautifulSoup('<div id="q-docs-metadata"><div class="answer"><div class="metadata-policy"><div class="reading-gap">'
                + ''.join(map(str, old_nodes(language))) + '</div><div class="answer-detail">Original.csv</div></div></div></div>', 'html.parser')
            after = project(before, language)
            compare(before, after, language)
            self.assertEqual(str(restore(after, language)), str(before))
            for old, new in [('metadata-harvestable', 'other'), ('missing', 'explicit-no'), ('Original.csv', 'original.csv'),
                             ('</span>', '!</span>'), ('metadata-publication-gap', 'data-gap')]:
                with self.assertRaises(AssertionError):
                    compare(before, BeautifulSoup(str(after).replace(old, new), 'html.parser'), language)

    def test_no_new_layout_patch_is_needed(self):
        css = (ROOT / 'src/layout.css').read_text()
        self.assertNotIn('BEGIN metadata gap panel:', css)
        self.assertNotIn('metadata-publication-gap', css)
        # Exact retired-panel reconstruction stays available for historic gates.
        self.assertIn('BEGIN metadata gap panel:', historical_css(css))
