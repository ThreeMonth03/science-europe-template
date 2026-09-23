import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/full-km-followups')]
from full_km_followups_contract import project_source, CONTRACT, prior_css, identifier_css
from followup_recipe import baseline_sources, overlay
from followup_probe import check


class FullKmFollowupIntegrationTests(unittest.TestCase):
    def test_css_projection_removes_only_exact_owned_bytes(self):
        delta = identifier_css()
        self.assertEqual(prior_css('before' + delta + 'after'), 'beforeafter')
        self.assertEqual(prior_css('old-css'), 'old-css')
        with self.assertRaises(AssertionError): prior_css(delta + delta)
        with self.assertRaises(AssertionError): prior_css(delta.replace('inline', 'block'))

    def test_actual_sources_match_reviewed_prototype_and_keep_old_gate(self):
        from submission_flow_contract import project_source as before_flow
        current, current_metadata = before_flow()
        self.assertEqual(current, overlay(baseline_sources()))
        prior, metadata = project_source(current, current_metadata)
        self.assertEqual(metadata['version'], '0.3.45')
        from submission_reading_contract import project_source as older
        self.assertEqual(older(prior, metadata)[1]['version'], '0.3.44')
        self.assertGreater(len(check(ROOT, current, prior)), 240)

    def test_all_current_bytes_inventory_and_metadata_are_checked_before_projection(self):
        current = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
        metadata = json.loads((ROOT / 'template.json').read_text())
        for name in current:
            with self.subTest(name=name), self.assertRaises(AssertionError):
                project_source({**current, name: current[name] + b'!'}, metadata)
        for name in CONTRACT['added']:
            with self.assertRaises(AssertionError): project_source({n: v for n, v in current.items() if n != name}, metadata)
        with self.assertRaises(AssertionError): project_source({**current, 'src/extra.j2': b''}, metadata)
        for field in ['version', 'format', 'uuid', 'compatibility']:
            bad = copy.deepcopy(metadata)
            if field == 'version': bad['version'] = '0.3.49'
            elif field == 'format': bad['formats'][0]['name'] += '!'
            elif field == 'uuid': bad['formats'][0]['uuid'] = 'wrong'
            else: bad['allowedPackages'][0]['minVersion'] = '0.0.0'
            with self.assertRaises(AssertionError): project_source(current, bad)


if __name__ == '__main__': unittest.main()
