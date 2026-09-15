import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_q8_word import cases, allowed_changes, word_changes


class Q8WordProbeTests(unittest.TestCase):
    def test_only_label_attribute_can_change(self):
        old = {'t': 'Div', 'c': [['', [], []], [{'t': 'Plain', 'c': [{'t': 'Str', 'c': 'Original.csv'}]}]]}
        new = copy.deepcopy(old); new['c'][0][2] = [['custom-style', 'Pilot List Lead']]
        with self.assertRaises(AssertionError): allowed_changes(old, new)
        new['c'][1][0]['t'] = 'Para'
        self.assertEqual(1, allowed_changes(old, new))
        new['c'][1][0]['c'][0]['c'] = 'changed.csv'
        with self.assertRaises(AssertionError): allowed_changes(old, new)

    def test_removal_and_wrong_styles_fail(self):
        with self.assertRaises(AssertionError): allowed_changes([{'t': 'Plain', 'c': []}], [])
        with self.assertRaises(AssertionError): allowed_changes('Pilot List Lead', 'Pilot Lead')

    def test_matrix_has_bounded_and_rejected_shapes(self):
        rows = cases(); self.assertEqual(26, len(rows))
        self.assertEqual(10, sum(count > 0 for _, _, count in rows))
        self.assertEqual(len(rows), len({name for name, _, _ in rows}))

    def test_docx_oracle_rejects_text_or_unrelated_style_change(self):
        old = [{'text': 'CASE: one', 'style': 'Heading2', 'other_xml': 'heading'},
               {'text': 'Original.csv', 'style': 'Compact', 'other_xml': 'same'}]
        new = copy.deepcopy(old); new[1]['style'] = 'PilotListLead'
        self.assertEqual({'one': 1}, word_changes(old, new))
        new[1]['other_xml'] = 'different numbering'
        with self.assertRaises(AssertionError): word_changes(old, new)
        new = copy.deepcopy(old); new[0]['style'] = 'PilotListLead'
        with self.assertRaises(AssertionError): word_changes(old, new)
