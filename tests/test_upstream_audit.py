"""Current upstream risk metadata and Git change-list interpretation."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_upstream import changed_paths, classify, local_paths


class UpstreamAuditTests(unittest.TestCase):
    def test_recorded_base_and_risk_groups_remain_explicit(self):
        config = json.loads((ROOT / '.upstream/base.json').read_text())
        self.assertEqual(config['repository'], 'https://github.com/ds-wizard/science-europe-template.git')
        self.assertRegex(config['baselineCommit'], r'^[0-9a-f]{40}$')
        self.assertTrue(config['baselineRef'].startswith('upstream/'))
        for path in ('template.json', 'src/uuids.j2'):
            self.assertEqual(classify(path, config['riskGroups'])[1], 'critical')
        self.assertEqual(classify('src/word/pilot.lua', config['riskGroups']), ('word-layout', 'high'))
        self.assertEqual(classify('unclassified.txt', config['riskGroups']), ('other', 'low'))

    def test_changed_paths_keep_status_and_rename_destination(self):
        with patch('audit_upstream.git', return_value='M\tsrc/uuids.j2\nR100\told.txt\tnew.txt\nD\tdeleted.txt') as command:
            self.assertEqual(changed_paths('base', 'target'), [('M', 'src/uuids.j2'), ('R100', 'new.txt'), ('D', 'deleted.txt')])
            command.assert_called_once_with('diff', '--name-status', 'base..target', '--')

    def test_local_paths_ignore_empty_lines_and_deduplicate(self):
        with patch('audit_upstream.git', return_value='src/layout.css\n\nsrc/layout.css\nsrc/word/pilot.lua') as command:
            self.assertEqual(local_paths('base'), {'src/layout.css', 'src/word/pilot.lua'})
            command.assert_called_once_with('diff', '--name-only', 'base', '--')
