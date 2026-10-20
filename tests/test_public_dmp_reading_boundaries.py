"""Bounded fixes from the public-DMP reading review; no source-specific strings."""
from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from current_support import IDS, PREFIX, environment, path


class PublicDMPReadingBoundaries(unittest.TestCase):
    def render(self, question, replies, **extra):
        return BeautifulSoup(environment(ROOT, True).from_string(
            PREFIX + "{% include 'src/questions/" + question + "' %}").render(
                repliesMap=replies, output_profile='submission', **extra), 'html.parser')

    def test_policy_label_leads_only_its_own_opening_not_the_whole_answer(self):
        listing = path('adminDetailsCUuid', 'policiesProceduresQUuid')
        authored = '<p>' + 'Original long explanation. ' * 20 + '</p><p>Original ending.</p>'
        for name, body, expected in [('Policy', authored, True),
                ('Policy', '<p>Original <strong>emphasis</strong>.</p>', True),
                ('Policy', '<table><tr><td>Original</td></tr></table>', False),
                ('中' * 81, authored, False), ('', authored, False), ('Policy', '', False)]:
            with self.subTest(name=name, body=body[:30]):
                replies = {listing: ['a', 'b'], path(listing, 'a', 'policiesProceduresNameQUuid'): name,
                    path(listing, 'a', 'policiesProceduresDescriptionQUuid'): body,
                    path(listing, 'b', 'policiesProceduresNameQUuid'): 'Next policy'}
                soup = self.render('06-access-security.html.j2', replies)
                item = soup.select_one('.answer > ul > li')
                self.assertEqual(bool(item.select_one(':scope > .answer-lead > p')), expected)
                self.assertFalse(item.select('.short-policy-item'))
                if body:
                    rendered_body = ''.join(str(n) for n in BeautifulSoup(body, 'html.parser').contents)
                    self.assertIn(rendered_body, str(item))
                self.assertNotIn('Next policy', item.get_text())

    def test_empty_metadata_wrapper_does_not_precede_the_first_real_answer(self):
        storage = path('processingCUuid', 'storageConvQUuid')
        soup = self.render('03-docs-metadata.html.j2', {storage: IDS['storageConvExploreAUuid'],
            path(storage, 'storageConvExploreAUuid', 'storageConvObjStoreQUuid'): IDS['storageConvObjStoreYesAUuid']})
        self.assertFalse(soup.select('.metadata-policy'))
        first = soup.select_one('.answer').find(True, recursive=False)
        self.assertEqual((first.name, first.get_text()), ('h4', 'Data storage and file conventions'))
        metadata = path('accessCUuid', 'metadataOpenQUuid')
        soup = self.render('03-docs-metadata.html.j2', {metadata: IDS['metadataOpenNoAUuid']})
        self.assertIn('Metadata will not be available openly.', soup.select_one('.metadata-policy').get_text())

    def test_sharing_hint_extends_only_bounded_plain_records(self):
        template = environment(ROOT, True).from_string(PREFIX + '{{ macros.shortDatasetRecord(body, label, limit=500) }}')
        for body, label, expected in [('<p>' + 'x' * 350 + '</p>', 'Dataset', True),
                ('<p>' + 'x' * 493 + '</p>', 'Dataset', True),
                ('<p>' + 'x' * 494 + '</p>', 'Dataset', False),
                ('<p>' + 'x' * 500 + '</p>', 'Dataset', False),
                ('<p>' + '中' * 493 + '</p>', 'Dataset', True),
                ('<p>' + '中' * 494 + '</p>', 'Dataset', False),
                ('<p>Original</p>', 'x' * 81, False),
                ('<table><tr><td>Original</td></tr></table>', 'Dataset', False),
                ('<p style="height:900px">Original</p>', 'Dataset', False),
                ('<p>Original</p>' * 7, 'Dataset', False)]:
            self.assertEqual(bool(template.render(body=body, label=label)), expected)
        # Other questions retain their original, narrower default.
        default = environment(ROOT, True).from_string(PREFIX + '{{ macros.shortDatasetRecord(body, label) }}')
        self.assertFalse(default.render(body='<p>' + 'x' * 350 + '</p>', label='Dataset'))


if __name__ == '__main__':
    unittest.main()
