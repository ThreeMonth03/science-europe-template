"""Production 0.3.49 must be the exact reviewed Q1 overlay, never a loose patch."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from reuse_preparation_contract import project_source, historical, load


class PreparationIntegrationTests(unittest.TestCase):
    def test_exact_prior_view_and_prototype_recipe(self):
        before, metadata = project_source()
        self.assertEqual(metadata, json.loads(historical('template.json')))
        self.assertEqual(metadata['version'], '0.3.48')
        actual = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
        self.assertEqual(actual, load('recipe').overlay(before))
        self.assertEqual({n for n in before if before[n] != actual[n]}, {'src/questions/01-how-data.html.j2'})

    def test_rejects_wrong_identity_steps_and_missing_inventory(self):
        actual = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
        metadata = json.loads((ROOT / 'template.json').read_text())
        for mutation in [lambda m: m.update(version='999.0.0'), lambda m: m.update(templateId='prototype'),
                         lambda m: m['formats'][-1]['steps'].pop(), lambda m: m['formats'][0].update(uuid='wrong')]:
            bad = copy.deepcopy(metadata); mutation(bad)
            with self.assertRaises(AssertionError): project_source(actual, bad)
        for name in ['src/questions/01-how-data.html.j2', 'src/layout.css', 'src/word/reference.docx']:
            with self.subTest(name=name), self.assertRaises(AssertionError):
                project_source({**actual, name: actual[name] + b'!'}, metadata)
        with self.assertRaises(AssertionError): project_source({**actual, 'src/extra': b''}, metadata)


if __name__ == '__main__': unittest.main()
