import sys
import hashlib
import io
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/full-km-followups'))
from followup_recipe import baseline_sources, overlay, INSERTIONS, IDENTIFIER_CSS
from followup_probe import check, verify_public_bindings
import prepare_knowledge_models


class FullKmFollowupPrototypeTests(unittest.TestCase):
    def test_public_bundle_download_and_cache_are_checksum_verified(self):
        content = b'public test bundle'
        bundles = {'test.km': hashlib.sha256(content).hexdigest()}
        with tempfile.TemporaryDirectory() as directory, patch.object(prepare_knowledge_models, 'BUNDLES', bundles), \
                patch.object(prepare_knowledge_models, 'urlopen') as request:
            root = Path(directory)
            request.return_value = io.BytesIO(b'wrong download')
            with self.assertRaises(ValueError): prepare_knowledge_models.prepare(root)
            self.assertFalse(list(root.iterdir()))
            request.return_value = io.BytesIO(content)
            prepare_knowledge_models.prepare(root)
            self.assertEqual((root / 'test.km').read_bytes(), content)
            request.reset_mock()
            prepare_knowledge_models.prepare(root)
            request.assert_not_called()
            (root / 'test.km').write_bytes(b'corrupt cache')
            with self.assertRaises(ValueError): prepare_knowledge_models.prepare(root)
            request.assert_not_called()
            self.assertEqual((root / 'test.km').read_bytes(), b'corrupt cache')

    def test_public_english_and_chinese_km_parent_chains(self):
        for name in ['root-2.7.0.km', 'root-zh-hant-2.7.0.km']:
            with self.subTest(name=name): verify_public_bindings(ROOT / 'fixtures/knowledge-models' / name)

    def test_profiles_authored_retention_parents_and_filtered_questions(self):
        previous = baseline_sources()
        self.assertGreater(len(check(ROOT, overlay(previous), previous)), 200)

    def test_overlay_changes_three_questions_and_one_owned_css_rule(self):
        previous = baseline_sources(); current = overlay(previous)
        self.assertEqual(set(current) - set(previous), {'src/full-km-followups.j2', *INSERTIONS.values()})
        self.assertEqual({n for n in previous if current[n] != previous[n]}, {*INSERTIONS, 'src/layout.css'})
        self.assertEqual(current['src/layout.css'], previous['src/layout.css'] + IDENTIFIER_CSS)
        from submission_flow_contract import project_source
        actual, _ = project_source()
        self.assertEqual(actual, current, 'Integrated source must match the approved prototype exactly')
        for name in ['src/layout.css', *INSERTIONS]:
            with self.assertRaises(AssertionError): overlay({**previous, name: previous[name] + b'!'})
        with self.assertRaises(AssertionError): overlay({**previous, 'src/unreviewed.j2': b''})


if __name__ == '__main__': unittest.main()
