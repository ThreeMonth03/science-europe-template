import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from probe_identifier_spacing import baseline,old_lua,CSS_BEGIN,CSS_END,word_delta,without_reviewed_archive_panels
from probe_archive_gap_panels import split_css


class IdentifierSpacingTests(unittest.TestCase):
    def test_only_scoped_additions_to_frozen_0327(self):
        sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
        self.assertEqual('7136b5e64ac731b736ed3dd400e7e69994e89448c54bb2b6e35ccbc189275fa7',
                         sha(old_lua((ROOT/'src/word/pilot.lua').read_text())))
        self.assertEqual('2647f94a302062d334ca663350f1484c31ffba1dd247a8f4c58344cb66467159',
                         sha(baseline(without_reviewed_archive_panels((ROOT/'src/layout.css').read_text()),CSS_BEGIN,CSS_END)))

    def test_later_block_is_exactly_reviewed_not_a_free_hash_exception(self):
        source=(ROOT/'src/layout.css').read_text();before,block=split_css(source)
        self.assertEqual(without_reviewed_archive_panels(source),before)
        self.assertEqual(without_reviewed_archive_panels(before),before)
        for changed in [source.replace('.2em','.3em'),source+block,source.replace('/* END archive gap pairs */','')]:
            with self.assertRaises(AssertionError):without_reviewed_archive_panels(changed)

    def test_control_oracle_rejects_any_change(self):
        old={'ast':{'blocks':[]},'word_blocks':[]}
        changed=copy.deepcopy(old);changed['ast']['blocks']=['lost']
        with self.assertRaises(AssertionError):word_delta(old,changed,'','',False)

    def test_missing_markers_fail_closed(self):
        with self.assertRaises(AssertionError):baseline('unmarked',CSS_BEGIN,CSS_END)
        with self.assertRaises(AssertionError):old_lua('unmarked')


if __name__=='__main__':unittest.main()
