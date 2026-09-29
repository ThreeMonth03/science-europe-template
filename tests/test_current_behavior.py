"""Discovered by make check; the same registry is used for bilingual CI."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from check_current import SUITES, run_suite
from current_repairs_contract import project_source, source_tree


class CurrentBehaviorTests(unittest.TestCase):
    pass


class CurrentRepairContractTests(unittest.TestCase):
    def test_exact_candidate_projects_and_any_source_drift_fails(self):
        import json
        current = source_tree()
        metadata = json.loads((ROOT / 'template.json').read_text())
        before, prior_metadata = project_source(current, metadata)
        self.assertEqual('0.3.51', prior_metadata['version'])
        self.assertNotIn('src/active-answer.j2', before)

        changed = dict(current)
        changed['src/questions/13-persistent-identifier.html.j2'] += b'\n'
        with self.assertRaises(AssertionError):
            project_source(changed, metadata)

        added = dict(current)
        added['src/unreviewed.j2'] = b''
        with self.assertRaises(AssertionError):
            project_source(added, metadata)

        changed_metadata = dict(metadata, version='0.3.52')
        with self.assertRaises(AssertionError):
            project_source(current, changed_metadata)


def test_suite(name):
    def test(self):
        run_suite(name, ROOT, 'en')
    return test


for name in SUITES:
    setattr(CurrentBehaviorTests, 'test_' + name, test_suite(name))


if __name__ == '__main__': unittest.main()
