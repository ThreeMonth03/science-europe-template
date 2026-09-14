import copy
import sys
import unittest
from test_preservation_coverage import plain, render
from test_science_europe_contract import ROOT
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_pilot_fixtures import IDS, path
from generate_paper_fixtures import LONG_URL, PLAIN_CITATION, paper_case


def paper_replies(value):
    replies = plain()
    key = next(p for p in replies if p.endswith(IDS['producedDataPaperQUuid']))
    if value is None: replies.pop(key)
    else: replies[key] = value
    return replies, key


class PaperReferenceTests(unittest.TestCase):
    def test_reference_follows_policy_and_keeps_exact_link_value(self):
        for value in [LONG_URL, 'https://example.org/paper.', 'http://example.org/x?x=1&y=2#end']:
            soup = render(paper_replies(value)[0])
            node = soup.select_one('.paper-reference')
            self.assertEqual(value, node.select_one('.paper-reference-value').get_text())
            self.assertEqual(value, node.a['href'])
            self.assertEqual('Related paper: ' + value, node.get_text())
            self.assertEqual('complete', node['data-status'])
            self.assertIn('preservation-summary', node.find_previous_sibling()['class'])
            self.assertIsNone(node.find_parent(class_='dataset-policy'))
            self.assertEqual(1, len(node.select('p')))

    def test_plain_citations_are_escaped_not_parsed_or_repaired(self):
        values = [PLAIN_CITATION, 'doi:10.1234/Case.', '<script>alert(1)</script>',
                  'https://example.org/paper followed by a title', ' https://example.org/paper',
                  'https://', 'https:///path', 'https://example.org/"quoted"',
                  'https://user@example.org/x', 'https://example.org/\\path',
                  'javascript:alert(1)', 'data:text/html,<b>Title</b>', '//example.org/x']
        for value in values:
            node = render(paper_replies(value)[0]).select_one('.paper-reference')
            self.assertEqual(value, node.select_one('.paper-reference-value').get_text())
            self.assertFalse(node.select('a, script, b, review'))

    def test_missing_or_blank_paper_does_not_hide_stage_or_policy(self):
        for value in [None, '', ' \n\t ']:
            soup = render(paper_replies(value)[0])
            self.assertFalse(soup.select('.paper-reference'))
            self.assertTrue(soup.select('[data-fact-id="preservation-data-stage"]'))
            self.assertIn('This dataset will be published.', soup.get_text())

    def test_stale_paper_is_gated_by_stage_not_publication(self):
        replies, key = paper_replies('Keep-this-reference.csv')
        stage = key.rsplit('.', 2)[0]
        for choice in ['', IDS['producedDataStageRawAUuid'], 'future-stage']:
            other = dict(replies); other[stage] = choice
            self.assertNotIn('Keep-this-reference.csv', render(other).get_text())
        prefix = stage.rsplit('.', 1)[0]
        replies[path(prefix, 'isPublishedDataQUuid')] = IDS['isPublishedDataNoAUuid']
        self.assertEqual('Keep-this-reference.csv', render(replies).select_one('.paper-reference-value').get_text())

    def test_duplicate_names_and_blank_next_item_do_not_move_or_leak_values(self):
        replies = {p: v['value'] for p, v in paper_case('en').items()}
        datasets = render(replies).select('.dataset-section')
        self.assertEqual(3, len(datasets))
        self.assertEqual(1, len({n.h5.get_text() for n in datasets}))
        self.assertEqual([LONG_URL, PLAIN_CITATION], [n.select_one('.paper-reference-value').get_text() for n in datasets[:2]])
        self.assertFalse(datasets[2].select('.paper-reference'))
        # A second field with the same value is independent, not deduplicated.
        keys = [p for p in replies if p.endswith(IDS['producedDataPaperQUuid'])]
        for key in keys[:2]: replies[key] = 'Same-reference.csv'
        self.assertEqual(2, render(replies).get_text().count('Same-reference.csv'))
