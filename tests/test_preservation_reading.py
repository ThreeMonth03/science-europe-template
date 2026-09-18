import copy
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from preservation_reading_contract import source_delta, prior_reference, old_reference, expected_ast, W, STYLE
from probe_preservation_reading import reference, cases


class PreservationReadingTests(unittest.TestCase):
    def test_exact_source_delta_leaves_all_existing_jinja_and_lua_unchanged(self):
        self.assertEqual(source_delta()['version'], '0.3.39')

    def test_one_new_style_and_no_existing_reference_change(self):
        before, after = old_reference(ROOT, 'en'), reference(ROOT)
        prior_reference(before, after)
        for mutation in ('old-font', 'new-keep', 'new-base', 'other-part', 'duplicate'):
            with self.subTest(mutation=mutation), zipfile.ZipFile(io.BytesIO(after)) as archive:
                parts = {n: archive.read(n) for n in archive.namelist()}
            tree = E.fromstring(parts['word/styles.xml'])
            new = next(s for s in tree if s.get(W+'styleId') == STYLE)
            if mutation == 'old-font': tree[0].set('unexpected', 'true')
            elif mutation == 'new-keep': new.find(W+'pPr/'+W+'keepNext').set(W+'val', '1')
            elif mutation == 'new-base': new.find(W+'basedOn').set(W+'val', 'Heading5')
            elif mutation == 'duplicate': tree.append(copy.deepcopy(new))
            else: parts['docProps/core.xml'] += b' '
            parts['word/styles.xml'] = E.tostring(tree)
            data = io.BytesIO()
            with zipfile.ZipFile(data, 'w') as target:
                for name, value in parts.items(): target.writestr(name, value)
            with self.assertRaises(AssertionError): prior_reference(before, data.getvalue())

    def test_named_boundary_and_fallback_matrix(self):
        rows = cases(); names = [r[0] for r in rows]
        self.assertEqual(len(names), len(set(names)))
        by_name = {n: ids for n, _, ids in rows}
        for name in ('name-boundary', 'cjk-name-boundary', 'summary-360', 'cjk-summary-180'):
            self.assertEqual(by_name[name], ['one'])
        for name in ('name-too-long', 'summary-361', 'authored', 'gap', 'table', 'image', 'unknown-heading'):
            self.assertEqual(by_name[name], [])
        self.assertEqual(by_name['mixed-second-only'], ['two'])
        self.assertEqual(by_name['same-labels'], ['one', 'two'])

    def test_ast_projection_preserves_anchors_and_every_other_node(self):
        name = [{'t': 'Str', 'c': 'Original.csv'}]; summary = [{'t': 'Str', 'c': '0'}]
        policy = {'t': 'Div', 'c': [['', ['preservation-summary', 'dataset-policy'], []], [{'t': 'Para', 'c': summary}]]}
        header = {'t': 'Header', 'c': [5, ['original.csv', [], []], name]}
        data = {'t': 'Div', 'c': [['', ['dataset-section'], [['item-id', 'one']]], [header, policy]]}
        answer = {'t': 'Div', 'c': [['', ['answer'], []], [data, {'t': 'Para', 'c': [{'t': 'Str', 'c': 'Untouched.'}]}]]}
        source = {'t': 'Div', 'c': [['q-data-preservation', [], []], [answer]]}
        result = expected_ast(source, ['one'])
        self.assertEqual(expected_ast(source, []), source)
        self.assertEqual(result['c'][1][0]['c'][1][1], answer['c'][1][1])
        joined = result['c'][1][0]['c'][1][0]['c'][1][0]['c'][1][0]['c'][1][0]['c']
        self.assertEqual(joined, [{'t': 'Strong', 'c': [{'t': 'Span', 'c': [['original.csv', [], []], name]}]}, {'t': 'LineBreak'}]+summary)
        self.assertEqual(len(source['c'][1][0]['c'][1][0]['c'][1]), 2)
        with self.assertRaises(AssertionError): expected_ast(source, ['missing'])


if __name__ == '__main__': unittest.main()
