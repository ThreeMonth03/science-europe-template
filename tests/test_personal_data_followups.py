"""Missing, negative and unreachable replies must remain distinguishable."""
import sys
import unittest
from copy import deepcopy
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

    def test_q9_dpia_and_ethical_consent_keep_only_reachable_typed_facts(self):
        from check_sentence_layout import partial_fixture
        from check_answer_mapping import question
        from current_support import PREFIX, environment
        chain = ('creatingCUuid collectPersonalQUuid collectPersonalYesAUuid '
                 'cpersGdprQUuid cpersGdprExploreAUuid cpersGdprNeedDpiaQUuid '
                 'cpersGdprNeedDpiaYesAUuid cpersGdprPerformedDpiaQUuid')
        km, base, performed = partial_fixture(chain)
        need = path('creatingCUuid', 'collectPersonalQUuid', 'collectPersonalYesAUuid',
                    'cpersGdprQUuid', 'cpersGdprExploreAUuid', 'cpersGdprNeedDpiaQUuid')
        need_no = UUIDS['cpersGdprNeedDpiaNoAUuid']
        km['entities']['questions'][UUIDS['cpersGdprNeedDpiaQUuid']]['answerUuids'].append(need_no)
        km['entities']['answers'][need_no] = {'followUpUuids': []}
        py, pn = [UUIDS['cpersGdprPerformedDpia'+state+'AUuid'] for state in ('Yes', 'No')]
        pq = km['entities']['questions'][UUIDS['cpersGdprPerformedDpiaQUuid']]
        pq.update(questionType='OptionsQuestion', answerUuids=[py, pn])
        km['entities']['answers'].update({py: {'followUpUuids': []}, pn: {'followUpUuids': []}})
        children = km['entities']['answers'][py]['followUpUuids']
        listing = path(performed, 'cpersGdprPerformedDpiaYesAUuid', 'cpersGdprDpiaListQUuid')
        listed = question(km, children, UUIDS['cpersGdprDpiaListQUuid'], 'ListQuestion')
        for field in ('Dataset', 'Description'):
            question(km, listed['itemTemplateQuestionUuids'], UUIDS['cpersGdprDpia'+field+'QUuid'],
                     'ValueQuestion')['valueType'] = 'TextQuestionValueType'
        reasons = path(performed, 'cpersGdprPerformedDpiaYesAUuid', 'cpersGdprDpiaReasonsQUuid')
        choices = [UUIDS['cpersGdprDpia'+name+'ChoiceUuid'] for name in
                   ('Vulnerable', 'Sensitive', 'LargeScale', 'Automated', 'Evaluation',
                    'Monitoring', 'Matching', 'Innovative', 'Rights')]
        question(km, children, UUIDS['cpersGdprDpiaReasonsQUuid'], 'MultiChoiceQuestion')['choiceUuids'] = choices
        km['entities']['choices'] = {choice: {'label': 'KM-EN-LABEL-MUST-NOT-LEAK'} for choice in choices}
        chapter = km['entities']['chapters'][UUIDS['creatingCUuid']]['questionUuids']
        ey, en = [UUIDS['ethLeg'+state+'AUuid'] for state in ('Yes', 'No')]
        hy, hn = [UUIDS['ethLegHuman'+state+'AUuid'] for state in ('Yes', 'No')]
        iy, ino = [UUIDS['ethLegInformedCollected'+state+'AUuid'] for state in ('Yes', 'No')]
        question(km, chapter, UUIDS['ethLegQUuid'], 'OptionsQuestion', [ey, en])
        question(km, km['entities']['answers'][ey]['followUpUuids'], UUIDS['ethLegHumanQUuid'], 'OptionsQuestion', [hy, hn])
        question(km, km['entities']['answers'][hy]['followUpUuids'], UUIDS['ethLegInformedCollectedQUuid'], 'OptionsQuestion', [iy, ino])
        ethical = path('creatingCUuid', 'ethLegQUuid')
        human = path(ethical, 'ethLegYesAUuid', 'ethLegHumanQUuid')
        informed = path(human, 'ethLegHumanYesAUuid', 'ethLegInformedCollectedQUuid')
        base.update({ethical: ey, human: hy})
        env = environment(ROOT)
        old_str, old_items = env.filters['reply_str_value'], env.filters['reply_items']
        env.filters['reply_str_value'] = lambda r: str(r['value'].get('value', '')) if isinstance(r, dict) and isinstance(r.get('value'), dict) else old_str(r)
        env.filters['reply_items'] = lambda r: r['value'].get('value', []) if isinstance(r, dict) and isinstance(r.get('value'), dict) and isinstance(r['value'].get('value'), list) else old_items(r)
        template = env.from_string(PREFIX + "{% include 'src/questions/09-ethical-issues.html.j2' %}")
        source = (ROOT/Q9).read_text()
        noun_capture = '{%- set dpiaDatasetLabel %}{{ pgettext("questions/09-ethical-issues", "Dataset") }}{% endset -%}'
        prior_boundary = source.replace(noun_capture + "\n{%- set dpiaDatasetKind = 'dpia' -%}\n", '').replace(
            '{{ dpiaDatasetLabel }} {{ macros.datasetLabel(dpiaDatasetKind, record.index) }}',
            "Dataset {{ macros.datasetLabel('dpia', record.index) }}")
        prior_template = env.from_string(PREFIX + prior_boundary)
        # The noun is translator-owned; its surrounding strong/ordinal shell is
        # not. Keep EN units independent of the optional external Tool package.
        self.assertEqual(1, source.count(noun_capture))
        self.assertIn('<strong>{{ dpiaDatasetLabel }} {{ macros.datasetLabel(dpiaDatasetKind, record.index) }}</strong>', source)
        # An explicit one-key translator exercises the noun boundary without
        # source rewriting or depending on the downstream authoritative PO.
        import gettext
        class NounTranslation(gettext.NullTranslations):
            def pgettext(self, context, message):
                return '資料集' if (context, message) == ('questions/09-ethical-issues', 'Dataset') else message
        translated_env = environment(ROOT)
        translated_env.filters.update(env.filters)
        translated_env.install_gettext_translations(NounTranslation(), newstyle=True)
        translated = translated_env.from_string(PREFIX + source)
        render = lambda values, profile, schema: BeautifulSoup(template.render(repliesMap=values,
            output_profile=profile, **schema), 'html.parser')
        typed = lambda value, kind='AnswerReply': {'value': {'type': kind, 'value': value}}
        expected = [('dpia-performed', performed, py, pn,
                     'Data protection impact assessments (DPIAs) have been performed for the personal data.',
                     'Data protection impact assessments (DPIAs) have not been performed for the personal data.'),
                    ('ethical-informed-consent-collected', informed, iy, ino,
                     'Informed consent has been collected from the research subjects.',
                     'Informed consent has not been collected from the research subjects.')]
        for profile in ('review', 'submission'):
            for schema in ({}, {'km': km}):
                for fact, leaf, yes, no, positive, negative in expected:
                    for selected in (yes, no, None, '', 'unknown'):
                        values = dict(base)
                        if selected is not None: values[leaf] = selected
                        soup = render(values, profile, schema)
                        nodes = soup.select('[data-fact-id="'+fact+'"]')
                        self.assertEqual(int(selected in (yes, no)), len(nodes), (profile, fact, selected))
                        if nodes:
                            self.assertEqual('complete' if selected == yes else 'explicit-no', nodes[0]['data-status'])
                            self.assertEqual(positive if selected == yes else negative, nodes[0].get_text(' ', strip=True))
                        if profile == 'submission': self.assertFalse(soup.select('.data-gap,.data-review,.empty-value'))
            values = {key: typed(value) for key, value in {**base, performed: py, informed: ino}.items()}
            values.update({listing: typed(['empty', 'no-name', 'name-only'], 'ItemListReply'),
                path(listing, 'no-name', 'cpersGdprDpiaDescriptionQUuid'): typed('<p>0</p><table><tr><td>DPIA-ORIGINAL</td></tr></table>', 'StringReply'),
                path(listing, 'name-only', 'cpersGdprDpiaDatasetQUuid'): typed('<p>NAME-ONLY &amp; original</p>', 'StringReply'),
                reasons: typed(choices + ['unknown'], 'MultiChoiceReply')})
            soup = render(values, profile, {'km': km})
            self.assertEqual(prior_template.render(repliesMap=values, output_profile=profile, km=km),
                             template.render(repliesMap=values, output_profile=profile, km=km))
            self.assertIn('According to the questionnaire, a data protection impact assessment (DPIA) is required.', soup.get_text())
            records = soup.select('.dpia-record')
            self.assertEqual(['no-name', 'name-only'], [n['data-item-id'] for n in records])
            self.assertEqual(['2', '3'], [n.select_one('.dataset-label')['data-list-index'] for n in records])
            self.assertIn('0', records[0].get_text()); self.assertEqual('DPIA-ORIGINAL', records[0].table.get_text())
            self.assertIsNone(records[1].select_one('[data-fact-id="dpia-description"]'))
            self.assertEqual(choices, [n['data-choice-id'] for n in soup.select('.dpia-reasons li')])
            self.assertNotIn('KM-EN-LABEL-MUST-NOT-LEAK', str(soup))
            self.assertFalse(soup.select('p p,p div,p ul,p table'))
            localized = BeautifulSoup(translated.render(repliesMap=values, output_profile=profile, km=km), 'html.parser')
            leads = localized.select('.dpia-record > .answer-lead > p > strong')
            self.assertEqual(2, len(leads))
            self.assertTrue(all(lead.get_text(strip=True).startswith('資料集') for lead in leads))
            self.assertEqual(['2', '3'], [lead.span['data-list-index'] for lead in leads])
            for parent, inactive in ((need, need_no), (performed, pn),
                    (path('creatingCUuid', 'collectPersonalQUuid'), UUIDS['collectPersonalNoAUuid']),
                    (path('creatingCUuid', 'collectPersonalQUuid', 'collectPersonalYesAUuid', 'cpersGdprQUuid'), '')):
                altered = deepcopy(values); altered[parent] = typed(inactive)
                hidden = render(altered, profile, {'km': km})
                self.assertFalse(hidden.select('.dpia-record,.dpia-reasons'))
                self.assertNotIn('DPIA-ORIGINAL', hidden.get_text())
            for parent, inactive in ((ethical, en), (human, hn), (ethical, ''), (human, 'unknown')):
                altered = deepcopy(values); altered[parent] = typed(inactive)
                self.assertFalse(render(altered, profile, {'km': km}).select('[data-fact-id="ethical-informed-consent-collected"]'))
            for fact, leaf, yes, no, _, _ in expected:
                for mutation in ('wrong-reply', 'wrong-ancestor-reply', 'missing-ancestor', 'removed-question',
                                 'wrong-question-type', 'removed-answer', 'dangling-answer'):
                    altered, schema = deepcopy(values), deepcopy(km)
                    qid = leaf.rsplit('.', 1)[-1]
                    if mutation == 'wrong-reply': altered[leaf] = typed(no, 'StringReply')
                    elif mutation == 'wrong-ancestor-reply': altered[need if leaf == performed else human]['value']['type'] = 'StringReply'
                    elif mutation == 'missing-ancestor': altered.pop(need if leaf == performed else human)
                    elif mutation == 'removed-question': del schema['entities']['questions'][qid]
                    elif mutation == 'wrong-question-type': schema['entities']['questions'][qid]['questionType'] = 'ValueQuestion'
                    elif mutation == 'removed-answer': schema['entities']['questions'][qid]['answerUuids'] = []
                    else: del schema['entities']['answers'][yes if leaf == performed else no]
                    self.assertFalse(render(altered, profile, {'km': schema}).select('[data-fact-id="'+fact+'"]'), (fact, mutation))
            for mutation in ('removed-item', 'wrong-list-reply', 'wrong-text-reply', 'wrong-text-value', 'removed-field', 'wrong-field-type'):
                altered, schema = deepcopy(values), deepcopy(km)
                detail = path(listing, 'no-name', 'cpersGdprDpiaDescriptionQUuid')
                qid = UUIDS['cpersGdprDpiaDescriptionQUuid']
                if mutation == 'removed-item': altered[listing]['value']['value'] = ['name-only']
                elif mutation == 'wrong-list-reply': altered[listing]['value']['type'] = 'MultiChoiceReply'
                elif mutation == 'wrong-text-reply': altered[detail]['value']['type'] = 'AnswerReply'
                elif mutation == 'wrong-text-value': altered[detail]['value']['value'] = ['INVALID-TEXT']
                elif mutation == 'removed-field': del schema['entities']['questions'][qid]
                else: schema['entities']['questions'][qid]['valueType'] = 'IntegerQuestionValueType'
                self.assertNotIn('DPIA-ORIGINAL', render(altered, profile, {'km': schema}).get_text(), mutation)
            for mutation in ('wrong-reply', 'removed-choice', 'dangling-choice', 'wrong-question-type'):
                altered, schema = deepcopy(values), deepcopy(km)
                if mutation == 'wrong-reply': altered[reasons]['value']['type'] = 'ItemListReply'
                elif mutation == 'removed-choice': schema['entities']['questions'][UUIDS['cpersGdprDpiaReasonsQUuid']]['choiceUuids'] = choices[1:]
                elif mutation == 'dangling-choice': del schema['entities']['choices'][choices[0]]
                else: schema['entities']['questions'][UUIDS['cpersGdprDpiaReasonsQUuid']]['questionType'] = 'ListQuestion'
                actual = [n['data-choice-id'] for n in render(altered, profile, {'km': schema}).select('.dpia-reasons li')]
                self.assertEqual([] if mutation in ('wrong-reply', 'wrong-question-type') else choices[1:], actual, mutation)
