"""Only visible content should introduce derived submission subsections."""
from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_project_acronym import LISTING, fixture, funding_fixture, integration
from current_support import IDS, PREFIX, WRAPPER, environment, path


class DerivedSubmissionHeadingsTests(unittest.TestCase):
    def render(self, source, replies, profile='submission', km=None, escape=False):
        env = environment(ROOT, escape)
        env.filters['datetime_format'] = lambda value, fmt: '2026-10-02'
        return BeautifulSoup(env.from_string(PREFIX + source).render(
            repliesMap=replies, output_profile=profile, km=km or {},
            dc={'project': {'name': 'Document name', 'versions': []},
                'document': {'created_at': ''}},
            ctx={'phaseUuid': None, 'project': {'versionUuid': None}}), 'html.parser')

    def provenance(self, choice='provenanceOtherAUuid', detail=None):
        parent = path('creatingCUuid', 'metadataQUuid')
        question = path(parent, 'metadataExploreAUuid', 'provenanceQUuid')
        replies = {parent: IDS['metadataExploreAUuid'], question: IDS[choice]}
        if detail is not None:
            replies[path(question, 'provenanceOtherAUuid', 'provenanceOtherQUuid')] = detail
        return replies

    def test_blank_other_provenance_hides_only_submission_subheading(self):
        source = "{% include 'src/questions/01-how-data.html.j2' %}"
        for detail in (None, '', ' \t\n\u3000'):
            for escape in (False, True):
                with self.subTest(detail=detail, escape=escape):
                    replies = self.provenance(detail=detail)
                    submission = self.render(source, replies, escape=escape)
                    self.assertIsNotNone(submission.select_one('#q-how-data > h3'))
                    self.assertNotIn('Provenance', submission.get_text())
                    self.assertFalse(submission.select('.data-gap'))
                    for profile in ('review', 'unknown'):
                        review = self.render(source, replies, profile, escape=escape)
                        self.assertIn('Provenance', review.get_text())
                        self.assertIsNotNone(review.select_one('[data-fact-id="provenance-detail"]'))

    def test_known_provenance_keeps_fixed_fact_and_heading(self):
        for choice in ('provenanceLabNotebooksAUuid', 'provenanceELabNotebookAUuid',
                       'provenanceSystemAUuid'):
            with self.subTest(choice=choice):
                soup = self.render("{% include 'src/questions/01-how-data.html.j2' %}",
                    self.provenance(choice))
                self.assertIn('Provenance', soup.get_text())
                self.assertIsNotNone(soup.select_one('[data-fact-id="provenance"][data-status="complete"]'))

    def test_provenance_media_and_tables_are_not_empty_text(self):
        for content in ('<img src="chart.png" alt="">', '<IMG SRC="chart.png" ALT="">',
                        '<table><tr><td></td></tr></table>'):
            for escape in (False, True):
                with self.subTest(content=content, escape=escape):
                    soup = self.render("{% include 'src/questions/01-how-data.html.j2' %}",
                        self.provenance(detail=content), escape=escape)
                    self.assertIn('Provenance', soup.get_text())
                    self.assertIsNotNone(soup.select_one('img, table'))

    def test_empty_overview_disappears_but_named_cover_is_preserved(self):
        source = "{% include 'src/frontmatter.html.j2' %}{% include 'src/projects.html.j2' %}"
        for name in ('Named project', None, ' \t\n\u3000'):
            for escape in (False, True):
                with self.subTest(name=name, escape=escape):
                    km, replies = fixture(None, name)
                    soup = self.render(source, replies, km=km, escape=escape)
                    self.assertEqual('Named project' if name == 'Named project' else 'Data Management Plan',
                        soup.h1.get_text())
                    self.assertIsNone(soup.select_one('#dmp-projects'))
                    review = self.render(source, replies, 'review', km, escape)
                    self.assertIsNotNone(review.select_one('#dmp-projects > h2'))
                    self.assertIn('Funding information has not been provided.', review.get_text())

    def test_filled_unnamed_project_retains_original_ordinal_and_all_fields(self):
        km, replies = fixture(None, None, 'second')
        replies[LISTING] = ['empty-first', 'second', 'third']
        replies[path(LISTING, 'second', 'projectNumberQUuid')] = '0'
        replies[path(LISTING, 'third', 'projectNameQUuid')] = 'Third project'
        for escape in (False, True):
            soup = self.render("{% include 'src/projects.html.j2' %}", replies, km=km, escape=escape)
            self.assertEqual(['second', 'third'], [p['data-item-id'] for p in soup.select('.project')])
            self.assertEqual('Project 2', soup.select_one('[data-item-id="second"] > h3').get_text())
            self.assertEqual('0', soup.select_one('[data-fact-id="project-number"] td').get_text())
            self.assertEqual('Third project', soup.select_one('[data-item-id="third"] > h3').get_text())
            self.assertIsNotNone(soup.select_one('#dmp-projects > h2'))

    def test_funding_only_project_is_meaningful(self):
        for values in (dict(name=integration('Funding body')), dict(grant='0'), dict(status='Granted')):
            km, replies, _ = funding_fixture(**values)
            replies.pop(path(LISTING, 'project-a', 'projectNameQUuid'), None)
            soup = self.render("{% include 'src/projects.html.j2' %}", replies, km=km)
            self.assertEqual('Project 1', soup.select_one('.project > h3').get_text())
            self.assertIsNotNone(soup.select_one('[data-fact-id="project-funding"] li'))

    def test_abstract_media_tables_and_authored_prose_are_preserved(self):
        for content in ('<img src="chart.png" alt="">', '<IMG SRC="chart.png" ALT="">',
                        '<table><tr><td></td></tr></table>', '<p>Keep <em>authored text</em>.</p>'):
            for escape in (False, True):
                with self.subTest(content=content, escape=escape):
                    km, replies = fixture(None, None)
                    replies[path(LISTING, 'project-a', 'projectAbstractQUuid')] = content
                    soup = self.render("{% include 'src/projects.html.j2' %}", replies, km=km, escape=escape)
                    self.assertEqual('Project 1', soup.select_one('.project > h3').get_text())
                    self.assertIsNotNone(soup.select_one('.abstract img, .abstract table, .abstract em'))

    def test_all_original_questions_survive_empty_derived_sections(self):
        km, replies = fixture(None, 'Named project')
        replies.update(self.provenance(detail=' \t\n\u3000'))
        soup = self.render(WRAPPER[len(PREFIX):], replies, km=km)
        self.assertEqual(15, len(soup.select('.question > h3')))
        self.assertEqual(6, len(soup.select('.dmp-section')))
        self.assertIsNone(soup.select_one('#dmp-projects'))
        self.assertFalse(soup.select('.data-gap, .data-review, .empty-value'))


if __name__ == '__main__':
    unittest.main()
