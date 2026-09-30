import itertools
import unittest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from test_science_europe_contract import ROOT, render_question
from test_format_volume import values, FORMATS, Q2
from generate_storage_fixtures import storage_cases
from current_support import IDS, environment, path, PREFIX


class ReadingPolishTests(unittest.TestCase):
    def test_metadata_standard_sentences_keep_selected_names_and_parent_guards(self):
        parent = path('creatingCUuid', 'metadataQUuid')
        standards = path(parent, 'metadataExploreAUuid', 'metadataStandardsQUuid')
        prefix = path(standards, 'metadataStandardsExploreAUuid')
        options = [('DC', 'Dublin Core'), ('DataCite', 'DataCite'),
                   ('DDI', 'DDI (Data Documentation Initiative)')]
        render = environment(ROOT, escape=True).from_string(
            PREFIX + "{% include 'src/questions/03-docs-metadata.html.j2' %}").render
        for selected, profile in itertools.product(itertools.product([False, True], repeat=3), ['review', 'submission']):
            replies = {parent: IDS['metadataExploreAUuid'], standards: IDS['metadataStandardsExploreAUuid']}
            for (key, _), enabled in zip(options, selected):
                if enabled:
                    replies[path(prefix, 'metadataStandards' + key + 'QUuid')] = IDS['metadataStandards' + key + 'YesAUuid']
            names = [label for (_, label), enabled in zip(options, selected) if enabled]
            expected = ''
            if names:
                joined = names[0] if len(names) == 1 else ' and '.join(names) if len(names) == 2 else ', '.join(names[:-1]) + ', and ' + names[-1]
                expected = 'We will document the data using the ' + joined + (' metadata standard.' if len(names) == 1 else ' metadata standards.')
            soup = BeautifulSoup(render(repliesMap=replies, output_profile=profile), 'html.parser')
            paragraphs = [p.get_text() for p in soup.select('.metadata-policy p') if 'document the data using' in p.get_text()]
            self.assertEqual([expected] if expected else [], paragraphs)
            for guard in [parent, standards]:
                inactive = dict(replies, **{guard: 'unknown'})
                self.assertNotIn('document the data using', render(repliesMap=inactive, output_profile=profile))

    def test_repository_cost_prose_preserves_payer_and_independent_preparation_budget(self):
        charges = path('preservingCUuid', 'repoChargesQUuid')
        payer = path(charges, 'repoChargesYesAUuid', 'repoChargesHowPayQUuid')
        preparation = path('preservingCUuid', 'budgetTimeEffortQUuid')
        sentences = {
            'Budgeted': 'The project budget includes the repository service fees.',
            'Department': 'A participating department will cover the repository service fees.',
            'Institute': 'A participating institute will cover the repository service fees.',
        }
        free = 'The repositories we use do not charge for their services.'
        funded = 'We have allocated funds for the time and effort needed to prepare the data for publication.'
        authored = 'Keep v1.2: 0 TWD; department A does not pay.'
        render = environment(ROOT, escape=True).from_string(
            PREFIX + "{% include 'src/questions/11-data-preservation.html.j2' %}").render
        for charge, payment, budget, profile in itertools.product([None, 'No', 'Yes', 'unknown'], [None, *sentences, 'Other', 'unknown'], [None, 'No', 'Yes'], ['review', 'submission']):
            replies = {path(payer, 'repoChargesHowPayOtherAUuid', 'repoChargesHowPayOtherQUuid'): authored}
            for key, value, stem in [(charges, charge, 'repoCharges'), (payer, payment, 'repoChargesHowPay'), (preparation, budget, 'budgetTimeEffort')]:
                if value is not None: replies[key] = IDS.get(stem + value + 'AUuid', value)
            text = BeautifulSoup(render(repliesMap=replies, output_profile=profile), 'html.parser').get_text(' ', strip=True)
            for option, sentence in sentences.items():
                self.assertEqual(charge == 'Yes' and payment == option, sentence in text)
            self.assertEqual(charge == 'No', free in text)
            self.assertEqual(budget == 'Yes', funded in text)
            self.assertEqual(charge == 'Yes' and payment == 'Other', authored in text)

    def test_fixed_english_prose_uses_complete_natural_sentences(self):
        source = '\n'.join((ROOT/path).read_text() for path in [
            'src/questions/05-store-backup.html.j2',
            'src/questions/06-access-security.html.j2',
            'src/questions/07-personal-data.html.j2',
            'src/questions/08-copyright-ipr.html.j2',
            'src/questions/09-ethical-issues.html.j2',
        ])
        for phrase in [
            'There is no shared workspace used',
            'secure HTTP (https://...)',
            'We pseudonymize inside the project',
            'We will use following policies',
            "based on subject's consent",
            'in order to fulfil contract',
            'We will be working with the philosophy',
            'restrictions are falling away',
            'We will have not decided yet',
            're-users',
        ]:
            self.assertNotIn(phrase, source)
        for phrase in [
            'The project will not use a shared workspace to work with data.',
            'All project web services are accessible through HTTPS.',
            'We will use the following policies and procedures:',
            'with the consent of the data subjects.',
            'We will manage our data according to the principle',
            'Data will be released as soon as the restrictions no longer apply.',
        ]:
            self.assertIn(phrase, source)
        for phrase in [
            'data loss and data disclosure',
            'data loss and data tampering',
            'data disclosure and data tampering',
            'data loss, data disclosure, and data tampering',
        ]:
            self.assertIn(phrase, source)
        self.assertNotIn("join(' and ')", source)
        self.assertEqual(4, source.count('risk_list('))
        self.assertEqual(1, source.count('macro risk_list'))

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
