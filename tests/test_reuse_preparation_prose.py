"""A wording experiment must neither edit production nor change answer states."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('preparation_' + name, ROOT / 'experiments/reuse-preparation-prose' / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class PreparationProseTests(unittest.TestCase):
    def test_exact_scope_and_answer_matrix(self):
        recipe = load('recipe'); before = recipe.baseline_sources()
        from reuse_preparation_contract import project_source
        self.assertEqual(before, project_source()[0])
        actual = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
        self.assertEqual(recipe.overlay(before), actual)
        rows = load('probe').check(ROOT, before, actual)
        self.assertEqual(396, sum(r['case'].startswith('fixture-') for r in rows))
        self.assertGreater(len(rows), 8000)

    def test_rejects_source_drift(self):
        recipe = load('recipe'); before = recipe.baseline_sources()
        before['src/layout.css'] += b'/* drift */'
        with self.assertRaises(AssertionError): recipe.overlay(before)

    def test_missing_does_not_mean_no_and_negative_is_explicit(self):
        probe = load('probe')
        rows = list(probe.cases())
        missing = next(c for c in rows if c['convert'] == 'dataCompReadYesAUuid' and c['version'] is None and c['metadata'] is None)
        self.assertEqual(probe.expected(missing), [probe.C + '.'])
        negative = {**missing, 'version': 'dataCompReadItselfNoAUuid'}
        self.assertIn('will not make', probe.expected(negative)[0])


if __name__ == '__main__': unittest.main()
