import hashlib
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from metadata_followup_contract import check_roots, expected, compare, PARENT, DICTIONARY, ACCESS, REASON, IDS


class MetadataFollowupTests(unittest.TestCase):
    def test_whole_question_with_parent_guards_no_missing_unknown_and_capacity(self):
        frozen = ROOT/'tests/fixtures/metadata-0.3.32.en.html.j2'
        self.assertEqual(hashlib.sha256(frozen.read_bytes()).hexdigest(), '47cc7a83c6dca520b730b314f794fd607a18811a167b5b511095f3b2b9c27b4c')
        self.assertEqual(check_roots(ROOT, frozen, 'english'), 1726)

    def test_oracle_rejects_wrong_state_lost_text_and_authored_mutation(self):
        before = BeautifulSoup('<div id="q-docs-metadata"><div class="answer"><div class="dataset-policy metadata-policy"><p>Metadata will not be available openly.</p><div class="answer-detail" data-fact-id="metadata-access-explanation"><p>Original.csv</p></div></div><div class="storage-conventions-policy"><p>Keep 0 GB.</p></div></div></div>', 'html.parser')
        data = {PARENT: IDS['metadataExploreAUuid'], DICTIONARY: IDS['metadataDictionaryNoAUuid'], ACCESS: IDS['metadataOpenNoAUuid'], REASON: 'Original.csv'}
        after = expected(before, data, 'english'); compare(before, after, data, 'english')
        for old, new in [('Original.csv', 'original.csv'), ('explicit-no', 'complete'), ('will not create', 'will create'), ('0 GB', '1 GB'), ('dictionary.', 'dictionary..')]:
            with self.assertRaises(AssertionError): compare(before, BeautifulSoup(str(after).replace(old, new), 'html.parser'), data, 'english')
