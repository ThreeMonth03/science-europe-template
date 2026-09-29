"""Fail closed before offering historical views of the Q3 integration."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from q3_policy_prose_contract import project_source, load, historical

class Q3IntegrationTests(unittest.TestCase):
    def test_exact_frozen_overlay_and_prior_view(self):
        before, metadata=project_source()
        candidate={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
        from current_repairs_contract import project_source as project_candidate
        current, _ = project_candidate(candidate, json.loads((ROOT/'template.json').read_text()))
        self.assertEqual(current,load('recipe').overlay(before))
        self.assertEqual(metadata,json.loads(historical('template.json')))
        self.assertEqual(metadata['version'],'0.3.50')
        self.assertEqual(set(current)-set(before),{'src/metadata-prose.html.j2'})
        self.assertEqual({n for n in before if before[n]!=current[n]},{'src/questions/03-docs-metadata.html.j2'})

    def test_rejects_unreviewed_source_inventory_and_assets(self):
        current={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
        for name in ['src/metadata-prose.html.j2','src/questions/03-docs-metadata.html.j2','src/layout.css',
                     'src/word/reference.docx','src/word/question-spacing.xml']:
            with self.subTest(name=name),self.assertRaises(AssertionError):project_source({**current,name:current[name]+b'!'})
            with self.subTest(missing=name),self.assertRaises(AssertionError):project_source({n:v for n,v in current.items() if n!=name})
        with self.assertRaises(AssertionError):project_source({**current,'src/unknown':b''})

    def test_rejects_metadata_and_format_drift(self):
        metadata=json.loads((ROOT/'template.json').read_text())
        for mutate in [lambda m:m.update(version='0.3.52'),lambda m:m.update(templateId='prototype'),
                       lambda m:m['formats'][-1]['steps'].pop(),lambda m:m['formats'][0].update(uuid='wrong')]:
            bad=copy.deepcopy(metadata);mutate(bad)
            with self.assertRaises(AssertionError):project_source(metadata=bad)

if __name__=='__main__':unittest.main()
