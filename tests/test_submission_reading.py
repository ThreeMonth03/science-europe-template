import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from submission_reading_contract import CONTRACT, project_source


class SubmissionReadingTests(unittest.TestCase):
    def test_exact_five_jinja_and_two_shared_word_files(self):
        prior, metadata = project_source()
        self.assertEqual(metadata['version'], '0.3.44')
        self.assertEqual(len(CONTRACT['changed']), 5)
        self.assertEqual(set(CONTRACT['added']), {'src/word/short-tables.lua', 'src/word/short-tables.xml'})
        self.assertTrue(all(n.endswith('.j2') for n in CONTRACT['changed']))
        self.assertEqual(set(prior), set(CONTRACT['before']))

    def test_no_unreviewed_source_asset_or_metadata_can_be_projected(self):
        current = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
        metadata = json.loads((ROOT / 'template.json').read_text())
        for name in CONTRACT['changed'] + CONTRACT['added'] + ['src/layout.css', 'src/word/pilot.lua']:
            with self.subTest(name=name), self.assertRaises(AssertionError):
                project_source({**current, name: current[name] + b'!'}, metadata)
        for name in CONTRACT['added']:
            with self.assertRaises(AssertionError): project_source({n: b for n, b in current.items() if n != name}, metadata)
        with self.assertRaises(AssertionError): project_source({**current, 'src/extra.xml': b''}, metadata)
        for mutation in ['version', 'format', 'uuid', 'rewrite']:
            bad = copy.deepcopy(metadata)
            if mutation == 'version': bad['version'] = '0.3.46'
            elif mutation == 'format': bad['formats'][0]['name'] += '!'
            elif mutation == 'uuid': bad['formats'][0]['uuid'] = 'wrong'
            else:
                fmt = next(f for f in bad['formats'] if f['name'].startswith('Word'))
                fmt['steps'][-1]['options']['rewrite:word/document.xml'] = 'render:unknown.xml'
            with self.assertRaises(AssertionError): project_source(current, bad)

    def test_old_source_contract_still_rejects_mutation_after_projection(self):
        from submission_preview_contract import project_source as project_previous
        prior, metadata = project_source()
        result, old = project_previous(prior, metadata)
        self.assertEqual(old['version'], '0.3.43')
        self.assertEqual(set(result), set(prior))
        prior['src/macros.html.j2'] += b'!'
        with self.assertRaises(AssertionError): project_previous(prior, metadata)


if __name__ == '__main__': unittest.main()
