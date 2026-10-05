"""Missing, negative and unreachable replies must remain distinguishable."""
import sys
import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
from test_personal_data_gaps import UUIDS, case, QUESTION
from test_answer_retention import path
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

    def test_known_privacy_restriction_survives_blank_access_procedure(self):
        opened = path('accessCUuid', 'openImmediatelyQUuid')
        legal = path(opened, 'openImmediatelyNoAUuid', 'notOpenLegalReasonsQUuid')
        privacy = path(legal, 'notOpenLegalReasonsYesAUuid', 'notOpenLegalReasonsPrivacyQUuid')
        procedure = path(privacy, 'notOpenLegalReasonsPrivacyYesAUuid', 'notOpenLegalReasonsPrivacyAccessQUuid')
        values = {opened: UUIDS['openImmediatelyNoAUuid'], legal: UUIDS['notOpenLegalReasonsYesAUuid'],
                  privacy: UUIDS['notOpenLegalReasonsPrivacyYesAUuid']}
        known = 'Privacy restrictions prevent some project data from being made openly available.'
        for blank in (None, '', ' \t\n\u3000'):
            current = dict(values)
            if blank is not None: current[procedure] = blank
            for profile in ('review', 'submission'):
                with self.subTest(blank=blank, profile=profile):
                    soup = BeautifulSoup(render_question(QUESTION, current, output_profile=profile), 'html.parser')
                    fact = soup.select_one('[data-fact-id="personal-data-privacy-restriction"][data-status="complete"]')
                    self.assertIsNotNone(fact)
                    self.assertEqual(known, fact.get_text(' ', strip=True))
                    self.assertFalse(soup.select('h4'))
                    if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review, .empty-value'))
        values[procedure] = 'Request permission from the data custodian.'
        self.assertIn(values[procedure], self.output(values).get_text())
        for parent, inactive in ((opened, UUIDS['openImmediatelyYesAUuid']),
                                 (legal, UUIDS['notOpenLegalReasonsNoAUuid']),
                                 (privacy, '')):
            current = dict(values); current[parent] = inactive
            for profile in ('review', 'submission'):
                soup = BeautifulSoup(render_question(QUESTION, current, output_profile=profile), 'html.parser')
                self.assertFalse(soup.select('[data-fact-id="personal-data-privacy-restriction"]'))
                self.assertNotIn(values[procedure], soup.get_text())

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

    def test_empty_safeguards_keep_original_question_without_submission_subheading(self):
        for blank in (None, '', ' \t\n\u3000'):
            values = replies('personal-followups-empty')
            for field in ('identifiability', 'additional', 'transfer'):
                if blank is not None:
                    values[PATHS[field]] = blank if field == 'additional' else ''
            for profile in ('review', 'submission'):
                with self.subTest(blank=blank, profile=profile):
                    soup = BeautifulSoup(render_question(QUESTION, values, output_profile=profile), 'html.parser')
                    self.assertTrue(soup.select_one('#q-personal-data > h3').get_text().startswith('7. '))
                    heading = soup.find('h4', string='Technical and procedural measures')
                    if profile == 'submission':
                        self.assertIsNone(heading)
                        self.assertFalse(soup.select('.data-gap, .data-review, .empty-value'))
                    else:
                        self.assertIsNotNone(heading)
                        self.assertEqual(4, len(soup.select('[data-status="missing"]')))

    def test_single_safeguard_fact_keeps_subheading_and_known_answer(self):
        facts = [('identifiability', 'cpersGdprSafeguardsIdentifAnonymAUuid', 'The stored data are irrevocably anonymized.'),
                 ('identifiability', 'cpersGdprSafeguardsIdentifPseudoAUuid', 'The stored data are pseudonymized.'),
                 ('identifiability', 'cpersGdprSafeguardsIdentifIdentifiableAUuid', 'The stored data are identifiable.'),
                 ('transfer', 'cpersGdprSafeguardsTransferNoAUuid', 'We do not plan to transfer data outside the EU/EEA.'),
                 ('transfer', 'cpersGdprSafeguardsTransferYesAUuid', 'We plan to transfer data outside the EU/EEA.')]
        for field, choice, expected in facts:
            values = replies('personal-followups-empty')
            values[PATHS[field]] = UUIDS[choice]
            if choice.endswith('NoAUuid'):
                values[PATHS['measures']] = 'STALE-MEASURES'
            for profile in ('review', 'submission'):
                with self.subTest(choice=choice, profile=profile):
                    soup = BeautifulSoup(render_question(QUESTION, values, output_profile=profile), 'html.parser')
                    self.assertIsNotNone(soup.find('h4', string='Technical and procedural measures'))
                    self.assertIn(expected, soup.get_text())
                    self.assertNotIn('STALE-', soup.get_text())

    def test_media_and_authored_safeguards_survive_unknown_siblings_not_inactive_parents(self):
        for body, tags in [('<p>Original.</p><ul><li>Keep order.</li></ul>', ['p', 'ul']),
                           ('<IMG src="https://example.org/measures.png">', ['img']),
                           ('<table><tr><td></td></tr></table>', ['table'])]:
            values = replies('personal-followups-empty')
            values[PATHS['additional']] = body
            values[PATHS['identifiability']] = values[PATHS['transfer']] = 'UNKNOWN-CHOICE'
            for profile in ('review', 'submission'):
                with self.subTest(body=body, profile=profile):
                    soup = BeautifulSoup(render_question(QUESTION, values, output_profile=profile), 'html.parser')
                    self.assertIsNotNone(soup.find('h4', string='Technical and procedural measures'))
                    detail = soup.select_one('[data-fact-id="personal-data-additional-safeguards"][data-status="complete"]')
                    self.assertEqual(tags, [n.name for n in detail.find_all(recursive=False)])
                    for parent in ('parent', 'gdpr', 'safeguards'):
                        inactive = dict(values)
                        inactive[PATHS[parent]] = ''
                        hidden = BeautifulSoup(render_question(QUESTION, inactive, output_profile=profile), 'html.parser')
                        self.assertIsNone(hidden.select_one('[data-fact-id="personal-data-additional-safeguards"]'))
                        self.assertIsNone(hidden.find('h4', string='Technical and procedural measures'))

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
        expected = {
            'Contract': 'because the processing is necessary to perform a contract.',
            'Legit': 'because the processing is necessary for legitimate interests.',
            'Vital': 'because the processing is necessary to protect vital interests.',
            'Legal': 'because the processing is necessary to comply with a legal obligation.',
        }
        ethical_endings = {'Contract': 'performance of a contract.', 'Legit': 'legitimate interests.',
                           'Vital': 'protection of vital interests.',
                           'Legal': 'compliance with a legal obligation.'}
        for choice, ending in expected.items():
            values = replies('personal-transfer-complete')
            values[PATHS['other']] = UUIDS['cpersGdprLegalBasisOtherWhich'+choice+'AUuid']
            self.assertIn(ending, self.output(values).get_text())
            ethical = self.output(values, Q9)
            details = ethical.select('.answer-detail')
            self.assertEqual(1, len(details))
            self.assertIn('Alternative legal basis for collecting personal data', details[0].get_text())
            self.assertIn(ethical_endings[choice], details[0].get_text())
            self.assertNotIn('has not been specified', details[0].get_text())
            # A different, unanswered dataset legitimately retains its prompt.
            self.assertTrue(ethical.select('.ethical-datasets .data-gap'))
        del values[PATHS['other']]
        missing = self.output(values, Q9).select_one('.answer-detail')
        self.assertIn('has not been specified; see Question 7.', missing.get_text())

    def test_explore_and_public_interest_do_not_add_unsupported_claims(self):
        text = self.output(case(), Q9).get_text(' ', strip=True)
        self.assertNotIn('We explored', text)
        self.assertNotIn('more important than the privacy', text)
        self.assertIn('The stated legal basis for collecting and processing personal data is a task carried out in the public interest.', text)

    def test_consent_basis_and_ethics_prose_are_complete_sentences(self):
        values = case()
        values[PATHS['legal']] = UUIDS['cpersGdprLegalBasisAskAUuid']
        consent_prefix = '.'.join([
            PATHS['legal'], UUIDS['cpersGdprLegalBasisAskAUuid']])
        values[consent_prefix+'.'+UUIDS['cpersConsentQUuid']] = UUIDS['cpersConsentUseAnonAUuid']
        values[consent_prefix+'.'+UUIDS['cpersReusersQUuid']] = UUIDS['cpersReusersYesAUuid']
        procedure = consent_prefix+'.'+UUIDS['cpersDescribeProcedureQUuid']
        values[procedure] = 'Document consent before collection.'
        q7 = self.output(values).get_text(' ', strip=True)
        self.assertIn('with the consent of the data subjects.', q7)
        q9 = self.output(values, Q9).get_text(' ', strip=True)
        self.assertIn("We will obtain consent for this project's use of the data and for anonymization.", q9)
        self.assertIn('We will then anonymize the data for subsequent reuse.', q9)
        self.assertIn('The consent form will be available to people who reuse the data.', q9)
        self.assertIn('The procedure for obtaining consent from data subjects is as follows:', q9)
        self.assertNotIn('; We', q9)
        self.assertNotIn('re-users', q9)

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
