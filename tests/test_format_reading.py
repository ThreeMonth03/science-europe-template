import hashlib
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from format_reading_contract import check_roots, compare, expected


class FormatReadingTests(unittest.TestCase):
    def test_exact_whole_question_projection_including_missing_no_and_unknown(self):
        frozen=ROOT/'tests/fixtures/format-0.3.30.en.html.j2'
        self.assertEqual(hashlib.sha256(frozen.read_bytes()).hexdigest(),'9ae958eae76cd2b2523b9e961d4cb58497ed7449c3fc32b0b1e8f42017e56224')
        self.assertEqual(check_roots(ROOT,frozen,'english'),264)

    def test_oracle_rejects_changed_authored_text_gaps_quantities_and_formatting(self):
        before=BeautifulSoup('<div class="format-description"><div class="format-summary"><p>Data format: <strong>Original.csv</strong>.</p><p>It is a standardized format.</p><p>This is a suitable format for long-term archiving.</p><p>We expect 0 files in this format.</p><p>The estimated average file size is <span class="quantity">0.0001 GB</span>.</p></div><p class="data-gap" data-status="missing">Keep gap.</p><div class="answer-detail"><p>We expect 0 files in this format.</p></div></div>','html.parser')
        after,changes=expected(before,'english');self.assertEqual(len(changes),1);compare(before,after,'english')
        for original,replacement in [('Original.csv','original.csv'),('0.0001','0.01'),('missing','complete'),('Keep gap.',''),('suitable for','suitable.. for'),('<strong>','<em>'),('We expect 0 files in this format.','edited answer')]:
            with self.assertRaises(AssertionError):compare(before,BeautifulSoup(str(after).replace(original,replacement),'html.parser'),'english')
