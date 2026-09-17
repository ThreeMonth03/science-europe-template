import hashlib
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from storage_gap_contract import check_roots, compare, expected, WORDS, PARENT, SPACE, AMOUNT, IDS
from metadata_followup_contract import expected as metadata_projection


class StorageGapTests(unittest.TestCase):
    def test_whole_q3_missing_zero_unknown_stale_and_authored_text(self):
        frozen = ROOT/'tests/fixtures/storage-0.3.31.en.html.j2'
        self.assertEqual(hashlib.sha256(frozen.read_bytes()).hexdigest(), '0f929ac601ffb00aa6d8a7352fa4edcb2fd1ab0ed2d4a3daa3b07190bac7dded')
        self.assertEqual(check_roots(ROOT, frozen, 'english', following_projection=metadata_projection), 866)

    def test_oracle_rejects_lost_answers_changed_gap_and_wrong_quantity(self):
        data = {PARENT: IDS['storageConvExploreAUuid'], SPACE: IDS['storageSpaceSpecifyAUuid']}
        before = BeautifulSoup('<div class="storage-conventions-policy"><div class="answer-detail"><p>Original.csv</p></div></div>', 'html.parser')
        after = expected(before, data, 'english')
        compare(before, after, data, 'english')
        for old, new in [('Original.csv', 'original.csv'), ('missing', 'complete'), ('storage-capacity', 'wrong'), ('(GB).', '.'), ('reading-gap', 'dataset-policy')]:
            with self.assertRaises(AssertionError):
                compare(before, BeautifulSoup(str(after).replace(old, new), 'html.parser'), data, 'english')
        data[AMOUNT] = '0'
        before = BeautifulSoup('<div class="storage-conventions-policy"><p>'+''.join([WORDS['english']['old'][0], '0', WORDS['english']['old'][1]])+'</p></div>', 'html.parser')
        after = expected(before, data, 'english')
        with self.assertRaises(AssertionError):
            compare(before, BeautifulSoup(str(after).replace('0 gigabytes', '1 gigabytes'), 'html.parser'), data, 'english')
