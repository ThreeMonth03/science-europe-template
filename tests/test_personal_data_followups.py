"""Missing, negative and unreachable replies must remain distinguishable."""
import sys
import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
from test_personal_data_gaps import UUIDS, case, QUESTION
sys.path.insert(0, str(ROOT/'scripts'))
from generate_personal_data_fixtures import personal_data_cases, personal_paths

Q9 = 'src/questions/09-ethical-issues.html.j2'
PATHS = personal_paths()


def replies(name, locale='en'):
    return {p: ({'value': {'value': v['value']}} if v['type'] == 'IntegrationReply' else v['value'])
            for p, v in personal_data_cases(locale)[name].items()}


class PersonalDataFollowupTests(unittest.TestCase):
    def output(self, values, question=QUESTION):
        soup = BeautifulSoup(render_question(question, values), 'html.parser')
        self.assertFalse(soup.select('p p, p div, p ul, p ol, p table'))
        return soup

    def facts(self, values):
        return {p['data-fact-id'] for p in self.output(values).select('[data-fact-id][data-status="missing"]')}

    def test_opened_followups_are_not_completed_answers(self):
        values = replies('personal-followups-empty')
        self.assertEqual({'personal-data-other-legal-basis', 'personal-data-identifiability',
                          'personal-data-additional-safeguards', 'personal-data-transfer'}, self.facts(values))
        text = self.output(values).get_text(' ', strip=True)
        self.assertNotIn('We are collecting and processing personal data', text)
        ethical = self.output(values, Q9).get_text(' ', strip=True)
        self.assertIn('has not been specified; see Question 7.', ethical)
        self.assertNotIn('consent-based:', ethical)
        self.assertNotIn('not subject to ethical legislation', ethical)

    def test_transfer_yes_keeps_intent_when_measures_missing(self):
        values = replies('personal-transfer-missing')
        self.assertEqual({'personal-data-legal-basis', 'personal-data-transfer-measures'}, self.facts(values))
        self.assertIn('We plan to transfer data outside the EU/EEA.', self.output(values).get_text())
        values[PATHS['measures']] = ' \n\t '
        self.assertIn('personal-data-transfer-measures', self.facts(values))

    def test_negative_transfer_is_not_missing_and_ignores_stale_child(self):
        values = replies('personal-transfer-no')
        self.assertEqual(set(), self.facts(values))
        values[PATHS['measures']] = 'STALE-TRANSFER-MEASURES'
        text = self.output(values).get_text()
        self.assertIn('We do not plan to transfer data outside the EU/EEA.', text)
        self.assertNotIn('STALE-', text)

    def test_missing_transfer_ignores_stale_child(self):
        values = replies('personal-followups-empty')
        values[PATHS['measures']] = 'STALE-TRANSFER-MEASURES'
        self.assertIn('personal-data-transfer', self.facts(values))
        self.assertNotIn('STALE-', self.output(values).get_text())

    def test_block_answers_are_siblings_of_leads_not_nested_paragraphs(self):
        values = replies('personal-transfer-complete')
        for field in ['additional', 'measures']:
            values[PATHS[field]] = '<p>First <strong>original</strong> paragraph.</p><p>Second.</p><ul><li>Keep order.</li></ul>'
        soup = self.output(values)
        self.assertEqual(set(), self.facts(values))
        for fact in ['personal-data-additional-safeguards', 'personal-data-transfer-measures']:
            detail = soup.select_one('[data-fact-id="'+fact+'"]')
            self.assertEqual(['p', 'p', 'ul'], [n.name for n in detail.find_all(recursive=False)])
            self.assertEqual('answer-lead', detail.find_previous_sibling()['class'][0])

    def test_all_other_legal_bases_still_form_complete_sentences(self):
        expected = {'Contract': 'in order to fulfil contract.', 'Legit': 'based on legitimate interest.',
                    'Vital': 'based on vital interest.', 'Legal': 'based on legal requirement.'}
        for choice, ending in expected.items():
            values = replies('personal-transfer-complete')
            values[PATHS['other']] = UUIDS['cpersGdprLegalBasisOtherWhich'+choice+'AUuid']
            self.assertIn(ending, self.output(values).get_text())
            self.assertNotIn('has not been specified', self.output(values, Q9).get_text())

    def test_explore_and_public_interest_do_not_add_unsupported_claims(self):
        text = self.output(case(), Q9).get_text(' ', strip=True)
        self.assertNotIn('We explored', text)
        self.assertNotIn('more important than the privacy', text)
        self.assertIn('The stated legal basis for collecting and processing personal data is public interest.', text)

    def test_inactive_parent_hides_followups_even_if_children_are_stale(self):
        for value in [UUIDS['collectPersonalNoAUuid'], '']:
            values = replies('personal-transfer-complete'); values[PATHS['parent']] = value
            soup = self.output(values)
            self.assertFalse(soup.select('[data-fact-id^="personal-data-"]'))
            self.assertNotIn('Audit-2027.csv', soup.get_text())

    def test_selected_safeguards_does_not_mask_missing_legal_basis(self):
        values = replies('personal-transfer-complete')
        del values[PATHS['legal']]
        self.assertEqual({'personal-data-legal-basis'}, self.facts(values))

    def test_blank_additional_safeguards_is_not_a_completed_empty_block(self):
        values = replies('personal-transfer-complete'); values[PATHS['additional']] = ' \n\t '
        self.assertEqual({'personal-data-additional-safeguards'}, self.facts(values))
