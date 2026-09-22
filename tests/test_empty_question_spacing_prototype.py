import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('empty_question_' + name, ROOT / 'experiments/empty-question-spacing' / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class EmptyQuestionSpacingTests(unittest.TestCase):
    def test_exact_markers_preserve_all_content_and_review(self):
        recipe = load('recipe'); reuse = recipe.load_reuse()
        before = reuse.overlay(reuse.baseline_sources())
        rows = load('probe').check(ROOT, before, recipe.overlay(before))
        self.assertGreater(len(rows), 100)

    def test_unrelated_source_drift_rejected(self):
        recipe = load('recipe'); reuse = recipe.load_reuse()
        before = reuse.overlay(reuse.baseline_sources()); before['src/layout.css'] += b'\n'
        with self.assertRaises(AssertionError): recipe.overlay(before)


if __name__ == '__main__': unittest.main()
