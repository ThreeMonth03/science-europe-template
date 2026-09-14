import unittest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from test_science_europe_contract import ROOT, render_question
from test_format_volume import values, FORMATS, Q2
from generate_storage_fixtures import storage_cases


class ReadingPolishTests(unittest.TestCase):
    def test_missing_fields_have_one_lead_and_one_terminal_period(self):
        soup = BeautifulSoup(render_question(Q2, {FORMATS: ['format-1']}), 'html.parser')
        gap = soup.select_one('.format-description p.data-gap')
        self.assertEqual(1, gap.get_text().count('Information still needed:'))
        self.assertEqual(4, len(gap.select('[data-status="missing"]')))
        self.assertEqual(1, gap.get_text().count('.'))
        self.assertEqual(3, gap.get_text().count(', '))

    def test_quantity_keeps_short_units_but_not_long_text_unbreakable(self):
        env = Environment(loader=FileSystemLoader(ROOT), extensions=['jinja2.ext.do'])
        env.filters['markdown'] = lambda v: v
        render = env.from_string("{% import 'src/macros.html.j2' as m %}{{ m.quantity(value, 'GB') }}").render
        for value in ('0', '0.0001', '120'):
            soup = BeautifulSoup(render(value=value), 'html.parser')
            self.assertEqual(value + '\xa0GB', soup.select_one('.quantity').get_text())
        self.assertNotIn('class="quantity"', render(value='Long free answer ' * 10))

    def test_only_simple_repository_and_standard_licence_are_joinable(self):
        for case in ('storage-sharing', 'storage-sharing-partial'):
            replies = {k: v['value'] for k,v in storage_cases('en')[case].items()}
            soup = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2', replies), 'html.parser')
            self.assertEqual(1, len(soup.select('.license-entry.joined-policy')))
            self.assertEqual(2 if case == 'storage-sharing' else 1, len(soup.select('.repository-arrangement.joined-policy')))
            self.assertFalse(soup.select('.joined-policy .answer-detail, .joined-policy .data-gap'))
            self.assertFalse(soup.select('.distribution-reading-unit > p.data-gap'))
            self.assertIsNotNone(soup.select_one('.license-entry:not(.joined-policy) .answer-detail'))
