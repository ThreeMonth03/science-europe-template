import copy,json
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from empty_section_spacing_contract import project_source,prior_css,css,load

class EmptySectionIntegrationTests(unittest.TestCase):
    def test_actual_sources_reproduce_prototype_and_old_view(self):
        before,metadata=project_source();self.assertEqual(metadata['version'],'0.3.47')
        from reuse_preparation_contract import project_source as before_preparation
        actual,_=before_preparation()
        self.assertEqual(len(load('probe').check(ROOT,before,actual)),396)
        from submission_flow_contract import project_source as older
        self.assertEqual(older(before,metadata)[1]['version'],'0.3.46')

    def test_rejects_every_source_asset_inventory_and_metadata_drift(self):
        sources={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
        metadata=json.loads((ROOT/'template.json').read_text())
        for name in sources:
            with self.subTest(name=name),self.assertRaises(AssertionError):project_source({**sources,name:sources[name]+b'!'},metadata)
            with self.assertRaises(AssertionError):project_source({n:v for n,v in sources.items() if n!=name},metadata)
        with self.assertRaises(AssertionError):project_source({**sources,'src/extra':b''},metadata)
        for mutate in [lambda m:m.update(version='999.0.0'),lambda m:m.update(templateId='wrong'),
            lambda m:m['formats'][0].update(uuid='wrong'),lambda m:m['formats'][-1]['steps'].pop(),lambda m:m['allowedPackages'].clear()]:
            bad=copy.deepcopy(metadata);mutate(bad)
            with self.assertRaises(AssertionError):project_source(sources,bad)

    def test_only_exact_css_block_can_be_projected_without_losing_surroundings(self):
        delta=css().decode();self.assertEqual(prior_css('prior'+delta),'prior')
        self.assertEqual(prior_css('prior'),'prior')
        self.assertEqual(prior_css('prior'+delta+'unreviewed suffix'),'priorunreviewed suffix')
        for bad in [delta+delta,delta.replace('.8em','.9em'),delta.split('*/')[0]]:
            with self.assertRaises(AssertionError):prior_css(bad)

if __name__=='__main__':unittest.main()
