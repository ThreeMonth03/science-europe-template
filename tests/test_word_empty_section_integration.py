"""Exact current assets must pass before historical regression projections."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from word_empty_section_contract import project_source, historical, load

class WordSectionIntegrationTests(unittest.TestCase):
    def test_exact_reviewed_overlay_and_prior_view(self):
        previous, metadata = project_source()
        actual = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
        self.assertEqual(metadata, json.loads(historical('template.json')))
        self.assertEqual(metadata['version'], '0.3.49')
        self.assertEqual(actual, load('recipe').overlay(previous))
        self.assertEqual({n for n in actual if actual[n] != previous[n]}, load('recipe').CHANGED)

    def test_rejects_other_source_and_inventory_changes(self):
        actual = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
        metadata = json.loads((ROOT / 'template.json').read_text())
        for name in ['src/word/question-spacing.lua', 'src/word/question-spacing.xml', 'src/layout.css', 'src/word/reference.docx']:
            with self.subTest(name=name), self.assertRaises(AssertionError):
                project_source({**actual, name: actual[name] + b'!'}, metadata)
        for changed in [{**actual, 'src/extra': b''}, {n:v for n,v in actual.items() if n != 'src/word/question-spacing.lua'}]:
            with self.assertRaises(AssertionError): project_source(changed, metadata)

    def test_rejects_identity_and_format_changes(self):
        actual, metadata = project_source()
        current = load('recipe').overlay(actual); metadata['version'] = '0.3.50'
        for mutate in [lambda m:m.update(version='0.3.51'), lambda m:m.update(templateId='prototype'),
                       lambda m:m['formats'][-1]['steps'].pop(), lambda m:m['formats'][0].update(uuid='wrong')]:
            bad = copy.deepcopy(metadata); mutate(bad)
            with self.assertRaises(AssertionError): project_source(current, bad)

if __name__ == '__main__': unittest.main()
