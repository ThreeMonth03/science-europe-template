"""Exact current assets must pass before historical regression projections."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from word_empty_section_contract import project_source, historical, load

class WordSectionIntegrationTests(unittest.TestCase):
    def test_engine_mount_is_readable_without_exposing_private_temp_root(self):
        import probe_word_empty_sections as probe
        def check_mount(baseline, candidate, output):
            self.assertEqual(baseline.name, 'baseline')
            self.assertEqual(baseline.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(baseline.stat().st_mode & 0o005, 0o005)
            self.assertEqual((baseline / 'src/public.xml').read_bytes(), b'public fixture')
            self.assertEqual(candidate.name, 'candidate')
            self.assertEqual(candidate.parent, baseline.parent)
            self.assertEqual(candidate.stat().st_mode & 0o005, 0o005)
            self.assertEqual((candidate / 'src/after.xml').read_bytes(), b'historical overlay')
            return {'rows': [None] * 121}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(probe, 'project_source', return_value=({'src/public.xml': b'public fixture'}, {})), \
                patch.object(probe, 'load', return_value=SimpleNamespace(run=check_mount,
                    overlay=lambda before: {**before, 'src/after.xml': b'historical overlay'})):
            output = Path(directory) / 'result.json'
            probe.main(output)
            self.assertTrue(json.loads(output.read_text())['historical_scope'])

    def test_exact_reviewed_overlay_and_prior_view(self):
        previous, metadata = project_source()
        from q3_policy_prose_contract import project_source as before_q3
        actual, _ = before_q3()
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
