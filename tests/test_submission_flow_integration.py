import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from submission_flow_contract import CONTRACT, project_source, prior_css, spacing_css

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class SubmissionFlowIntegrationTests(unittest.TestCase):
    def test_actual_sources_equal_the_sealed_prototype_and_old_view_is_exact(self):
        from empty_section_spacing_contract import project_source as before_sections
        source, _ = before_sections()
        spacing = load('experiments/empty-question-spacing/recipe.py', 'flow_recipe')
        reuse = spacing.load_reuse(); before, metadata = project_source()
        self.assertEqual(metadata['version'], '0.3.46')
        self.assertEqual(source, spacing.overlay(reuse.overlay(before)))
        from full_km_followups_contract import project_source as older
        self.assertEqual(older(before, metadata)[1]['version'], '0.3.45')
        q1 = load('experiments/reuse-summary/probe.py', 'flow_q1_probe')
        compact = load('experiments/empty-question-spacing/probe.py', 'flow_spacing_probe')
        self.assertEqual(len(q1.check(ROOT, source)), 1844)
        self.assertEqual(len(compact.check(ROOT, reuse.overlay(before), source)), 480)

    def test_every_source_asset_helper_and_metadata_change_is_rejected(self):
        source = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
        metadata = json.loads((ROOT/'template.json').read_text())
        for name in source:
            with self.subTest(name=name), self.assertRaises(AssertionError): project_source({**source, name: source[name]+b'!'}, metadata)
            with self.assertRaises(AssertionError): project_source({n:v for n,v in source.items() if n != name}, metadata)
        with self.assertRaises(AssertionError): project_source({**source,'src/unreviewed.xml':b''}, metadata)
        for mutation in [lambda m:m.update(version='999.0.0'), lambda m:m.update(templateId='wrong'),
            lambda m:m['formats'][0].update(uuid='wrong'), lambda m:m['formats'][-1]['steps'].pop(),
            lambda m:m['allowedPackages'].clear()]:
            bad=copy.deepcopy(metadata); mutation(bad)
            with self.assertRaises(AssertionError): project_source(source,bad)

    def test_css_projection_rejects_partial_duplicate_or_changed_rules(self):
        delta=spacing_css(); self.assertEqual(prior_css('x'+delta+'y'),'xy')
        self.assertEqual(prior_css('old-css'),'old-css')
        for css in [delta+delta,delta.replace('auto','avoid'),delta.split('*/')[0]]:
            with self.assertRaises(AssertionError): prior_css(css)

if __name__ == '__main__': unittest.main()
