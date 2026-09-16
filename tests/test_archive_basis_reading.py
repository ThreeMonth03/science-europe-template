import hashlib
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from archive_basis_contract import check_roots, compare, expected


class ArchiveBasisReadingTests(unittest.TestCase):
    def test_all_subsets_unsupported_and_parent_guards_preserve_the_rest_of_q11(self):
        baseline = ROOT/'tests/fixtures/archive-0.3.28.en.html.j2'
        self.assertEqual(hashlib.sha256(baseline.read_bytes()).hexdigest(), 'db6519fc4abb4b4cb99006f2d745ecdc053e1d9d2a59bdefe2ba76892b29ac8c')
        self.assertEqual(check_roots(ROOT,baseline,'english'),274)

    def test_exact_oracle_rejects_missing_facts_punctuation_and_authored_edits(self):
        before = BeautifulSoup('<div class="post-project-archive"><div class="dataset-policy"><div class="answer-lead"><p>The extension decision will take the following into account:</p></div><ul><li data-fact-id="archive-extension-budget" data-status="complete">Available budget.</li></ul><div class="answer-detail"><p>Keep MyFile.csv.</p></div></div></div>', 'html.parser')
        after,count = expected(before,'english')
        self.assertEqual(count,1); self.assertEqual(compare(before,after,'english'),1)
        for original,replacement in [('archive-extension-budget','different-fact'),('complete','missing'),('available budget','invented claim'),('MyFile.csv','myfile.csv'),('budget.</p>','budget..</p>')]:
            # The punctuation mutation is inside the closing span, not an authored paragraph.
            if original == 'budget.</p>': original,replacement = '</span>.</p>','</span>..</p>'
            changed = str(after).replace(original,replacement)
            self.assertNotEqual(str(after),changed)
            with self.assertRaises(AssertionError): compare(before,BeautifulSoup(changed,'html.parser'),'english')
