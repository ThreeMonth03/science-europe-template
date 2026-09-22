"""The immutable prototype remains reproducible through the verified old view."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('reuse_summary_' + name, ROOT / 'experiments/reuse-summary' / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class ReuseSummaryPrototypeTests(unittest.TestCase):
    def test_exact_overlay_and_branch_matrix(self):
        recipe = load('recipe'); before = recipe.baseline_sources()
        from submission_flow_contract import project_source
        current, _ = project_source()
        self.assertEqual(before, current)
        rows = load('probe').check(ROOT, recipe.overlay(before))
        self.assertEqual(1600, sum(row['case'] == 'choices' for row in rows))
        self.assertGreater(len(rows), 1800)

    def test_unrelated_source_drift_rejected(self):
        recipe = load('recipe'); before = recipe.baseline_sources()
        before['src/layout.css'] += b'\n/* unexpected */\n'
        with self.assertRaises(AssertionError): recipe.overlay(before)


if __name__ == '__main__': unittest.main()
