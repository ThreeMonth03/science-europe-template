"""Missing answers must not become claims; repository choices have local scope."""
import itertools
from copy import deepcopy
import sys
import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
sys.path.insert(0, str(ROOT / 'scripts'))
from current_support import IDS, path
from current_support import support_replies

Q5 = 'src/questions/05-store-backup.html.j2'
Q11 = 'src/questions/11-data-preservation.html.j2'
LEAD = 'Please check these details; the answers used in this section do not establish them:'
SUPPORT = {
    'complete': 'We will be able to support this repository for a sufficiently long time.',
    'explicit-no': 'We will not be able to support this repository for a sufficiently long time.',
    'missing': 'Whether we will be able to support this repository for a sufficiently long time has not been specified.',
}


def storage_matrix():
    workspace = path('processingCUuid', 'sharedWorkspaceQUuid')
    archive = path('preservingCUuid', 'archivedDuringQUuid')
    for work, arch in itertools.product([None, 'Yes', 'No'], repeat=2):
        replies = {}
        if work: replies[workspace] = IDS[f'sharedWorkspace{work}AUuid']
        if arch: replies[archive] = IDS[f'archivedDuring{arch}AUuid']
        yield replies


class AnswerStateTests(unittest.TestCase):
    def test_consent_scope_replaces_only_the_generic_lead_and_preserves_authored_followups(self):
        from check_sentence_layout import partial_fixture
        from current_support import PREFIX, environment
        template_path = 'src/questions/09-ethical-issues.html.j2'
        chain = ('creatingCUuid collectPersonalQUuid collectPersonalYesAUuid cpersGdprQUuid '
                 'cpersGdprExploreAUuid cpersGdprLegalBasisQUuid cpersGdprLegalBasisAskAUuid cpersConsentQUuid')
        km, base, leaf = partial_fixture(chain)
        ancestors = tuple(base)
        scopes = {
            'Use': "We will obtain consent for this project's specific use of the data.",
            'Reuse': "We will obtain consent for this project's use and for subsequent reuse of the data.",
            'UseAnon': "We will obtain consent for this project's use of the data and for anonymization. We will then anonymize the data for subsequent reuse.",
            'Anon': 'We will obtain consent to anonymize the data. We will anonymize the data before any further processing.',
        }
        choices = {name: IDS['cpersConsent' + name + 'AUuid'] for name in scopes}
        km['entities']['questions'][IDS['cpersConsentQUuid']].update(
            questionType='OptionsQuestion', answerUuids=list(choices.values()))
        km['entities']['answers'].update({choice: {'followUpUuids': []} for choice in choices.values()})
        parent = leaf.rsplit('.', 1)[0]
        authored = '<p>Keep Consent-v1.2.csv; A&amp;B.</p><p>Separate paragraph.</p><ul><li>Original item.</li></ul><table><tr><td>Original cell.</td></tr></table>'
        for question in ('cpersExplainInformedQUuid', 'cpersDescribeProcedureQUuid'):
            base[path(parent, question)] = authored
        base[path('creatingCUuid', 'collectPersonalQUuid', 'collectPersonalYesAUuid',
                  'cpersGdprQUuid', 'cpersGdprExploreAUuid', 'cpersGdprPurposeQUuid')] = authored
        generic = 'We ask the data subjects for their consent.'
        for escape in (False, True):
            env = environment(ROOT, escape)
            flat_value = env.filters['reply_str_value']
            # Decode real typed envelopes; the template must reject wrong reply types.
            env.filters['reply_str_value'] = lambda r: r['value'].get('value', '') if isinstance(r, dict) and isinstance(r.get('value'), dict) else flat_value(r)
            template = env.from_string(PREFIX + "{% include '" + template_path + "' %}")
            def render(values, profile, schema):
                raw = template.render(repliesMap=values, output_profile=profile, **schema)
                self.assertEqual(raw.count(authored), 3)
                soup = BeautifulSoup(raw, 'html.parser')
                self.assertFalse(soup.select('p p,p div,p ul,p table'))
                if profile == 'submission': self.assertFalse(soup.select('.data-gap,.data-review'))
                return ' '.join(soup.get_text(' ', strip=True).split())
            for schema, profile, choice in itertools.product(({}, {'km': km}), ('review', 'submission'),
                    (*scopes, None, '', 'unknown', 'typed', 'wrong-reply-type')):
                values = dict(base)
                if choice is not None: values[leaf] = choices.get(choice, choice)
                if choice in ('typed', 'wrong-reply-type'):
                    values[leaf] = {'value': {'type': 'AnswerReply' if choice == 'typed' else 'StringReply', 'value': choices['Use']}}
                text = render(values, profile, schema)
                expected = 'Use' if choice == 'typed' else choice if choice in scopes else None
                self.assertEqual(text.count(generic), int(expected is None), (escape, profile, choice, bool(schema)))
                for name, phrase in scopes.items(): self.assertEqual(phrase in text, name == expected)
            for profile, mutation in itertools.product(('review', 'submission'),
                    ('removed-question', 'removed-choice', 'dangling-answer', 'removed-followup', 'wrong-question-type')):
                altered = deepcopy(km)
                node = altered['entities']['questions'][IDS['cpersConsentQUuid']]
                if mutation == 'removed-question': del altered['entities']['questions'][IDS['cpersConsentQUuid']]
                elif mutation == 'removed-choice': node['answerUuids'].remove(choices['Use'])
                elif mutation == 'dangling-answer': del altered['entities']['answers'][choices['Use']]
                elif mutation == 'removed-followup': altered['entities']['answers'][IDS['cpersGdprLegalBasisAskAUuid']]['followUpUuids'].clear()
                else: node['questionType'] = 'ValueQuestion'
                text = render({**base, leaf: choices['Use']}, profile, {'km': altered})
                self.assertEqual(text.count(generic), 1, mutation)
                self.assertFalse(any(phrase in text for phrase in scopes.values()), mutation)
            for ancestor in ancestors:
                values = {**base, leaf: choices['Use']}; values.pop(ancestor)
                raw = template.render(repliesMap=values, output_profile='submission', km=km)
                self.assertNotIn(generic, raw)
                self.assertFalse(any(phrase in raw for phrase in scopes.values()))

    def test_reused_negative_facts_and_openness_are_active_answers_not_missing_values(self):
        from check_sentence_layout import partial_fixture
        cases = [
            ('src/questions/01-how-data.html.j2',
             'reusingCUuid preexistingQUuid preexistingYesAUuid refDataQUuid ITEM '
             'refDataUseQUuid refDataUseYesAUuid refDataVersionedQUuid',
             'refDataVersionedYesAUuid', 'refDataVersionedNoAUuid', 'dataset-versioning',
             'This reference dataset is not versioned.'),
            ('src/questions/01-how-data.html.j2',
             'reusingCUuid preexistingQUuid preexistingYesAUuid nrefDataQUuid ITEM '
             'nrefDataUseQUuid nrefDataUseYesAUuid nrefDataPersonalQUuid',
             'nrefDataPersonalYesAUuid', 'nrefDataPersonalNoAUuid', 'reuse-personal-data',
             'This dataset does not contain personal data.'),
            ('src/questions/08-copyright-ipr.html.j2',
             'accessCUuid asOpenAsPossibleQUuid',
             'asOpenAsPossibleYesAUuid', 'asOpenAsPossibleNoAUuid', 'openness-principle',
             'We will not manage our data according to the principle of being as open as possible.'),
        ]
        for template, chain, yes, no, fact, sentence in cases:
            km, base, leaf = partial_fixture(chain)
            question = IDS[chain.split()[-1]]
            km['entities']['questions'][question].update(
                questionType='OptionsQuestion', answerUuids=[IDS[yes], IDS[no]])
            km['entities']['answers'].update({IDS[yes]: {'followUpUuids': []},
                                             IDS[no]: {'followUpUuids': []}})
            for schema, profile, choice in itertools.product(({}, {'km': km}),
                    ('review', 'submission'), (IDS[no], IDS[yes], None, '', 'unknown')):
                values = dict(base)
                if choice is not None: values[leaf] = choice
                with self.subTest(fact=fact, profile=profile, choice=choice, schema=bool(schema)):
                    soup = BeautifulSoup(render_question(template, values, output_profile=profile, **schema), 'html.parser')
                    node = soup.select_one('[data-fact-id="'+fact+'"]')
                    status = ('explicit-no' if choice == IDS[no] else 'complete'
                              if fact == 'dataset-versioning' and choice == IDS[yes] else None)
                    self.assertEqual(status is not None, bool(node))
                    if node:
                        self.assertEqual(status, node['data-status'])
                        self.assertEqual(sentence if status == 'explicit-no' else
                                         'This reference dataset is versioned.', node.get_text(' ', strip=True))
                    if profile == 'submission': self.assertFalse(soup.select('.data-gap,.data-review'))
            for profile, mutation in itertools.product(('review', 'submission'),
                    ('removed-question', 'removed-choice', 'dangling-answer', 'wrong-type', 'wrong-reply-type')):
                altered = deepcopy(km)
                values = {**base, leaf: IDS[no]}
                if mutation == 'removed-question': del altered['entities']['questions'][question]
                elif mutation == 'removed-choice': altered['entities']['questions'][question]['answerUuids'] = [IDS[yes]]
                elif mutation == 'dangling-answer': del altered['entities']['answers'][IDS[no]]
                elif mutation == 'wrong-type': altered['entities']['questions'][question]['questionType'] = 'ValueQuestion'
                else: values[leaf] = {'value': {'type': 'StringReply', 'value': IDS[no]}}
                soup = BeautifulSoup(render_question(template, values, output_profile=profile, km=altered), 'html.parser')
                self.assertFalse(soup.select('[data-fact-id="'+fact+'"]'), (fact, mutation))
            for ancestor in base:
                values = {**base, leaf: IDS[no]}
                values.pop(ancestor)
                soup = BeautifulSoup(render_question(template, values, output_profile='submission', km=km), 'html.parser')
                self.assertFalse(soup.select('[data-fact-id="'+fact+'"]'), (fact, ancestor))

    def test_reference_versioning_yes_survives_only_missing_detail_siblings(self):
        from check_sentence_layout import partial_fixture
        from check_answer_mapping import question
        from current_support import PREFIX, environment
        chain = ('reusingCUuid preexistingQUuid preexistingYesAUuid refDataQUuid ITEM '
                 'refDataUseQUuid refDataUseYesAUuid refDataVersionedQUuid')
        km, base, leaf = partial_fixture(chain)
        yes, no = IDS['refDataVersionedYesAUuid'], IDS['refDataVersionedNoAUuid']
        km['entities']['questions'][IDS['refDataVersionedQUuid']].update(
            questionType='OptionsQuestion', answerUuids=[yes, no])
        km['entities']['answers'].update({yes: {'followUpUuids': []}, no: {'followUpUuids': []}})
        children = km['entities']['answers'][yes]['followUpUuids']
        question(km, children, IDS['refDataVersionedWhichQUuid'], 'ValueQuestion')
        policies = [IDS['refDataVersionedChange'+name+'AUuid'] for name in ('Stay', 'New', 'All')]
        policy_texts = ['the current version will continue to be used.',
                        'it will be used for new analyses.',
                        'all analyses will be repeated using it.']
        question(km, children, IDS['refDataVersionedChangeQUuid'], 'OptionsQuestion', policies)
        which = path(leaf, 'refDataVersionedYesAUuid', 'refDataVersionedWhichQUuid')
        policy = path(leaf, 'refDataVersionedYesAUuid', 'refDataVersionedChangeQUuid')
        env = environment(ROOT)
        old_str, old_items = env.filters['reply_str_value'], env.filters['reply_items']
        # This local adapter decodes typed envelopes; the production type guard,
        # not a fixture's dict representation, must reject a wrong reply type.
        env.filters['reply_str_value'] = lambda r: r['value'].get('value', '') if isinstance(r, dict) and isinstance(r.get('value'), dict) else old_str(r)
        env.filters['reply_items'] = lambda r: r['value'].get('value', []) if isinstance(r, dict) and isinstance(r.get('value'), dict) else old_items(r)
        template = env.from_string(PREFIX + "{% include 'src/questions/01-how-data.html.j2' %}")
        render = lambda values, profile, schema: BeautifulSoup(template.render(
            repliesMap=values, output_profile=profile, **schema), 'html.parser')
        details = [(None, None), ('', None), (' \t\n\u3000', 'unknown'),
                   ('Version-082', None), (None, policies[0]), (None, policies[1]),
                   (None, policies[2]), ('Version-082', policies[0])]
        for schema, profile, (version, change) in itertools.product(({}, {'km': km}),
                ('review', 'submission'), details):
            values = {**base, leaf: yes}
            values[which], values[policy] = version, change
            soup = render(values, profile, schema)
            fact = soup.select('[data-fact-id="dataset-versioning"][data-status="complete"]')
            expected = not (version or '').strip() and change not in policies
            self.assertEqual(int(expected), len(fact), (profile, version, change, bool(schema)))
            if fact: self.assertEqual('This reference dataset is versioned.', fact[0].get_text(strip=True))
            self.assertEqual(version == 'Version-082', 'Version-082' in soup.get_text())
            for selected, text in zip(policies, policy_texts):
                self.assertEqual(change == selected, text in soup.get_text())
            if profile == 'submission': self.assertFalse(soup.select('.data-gap,.data-review'))
            else:
                self.assertEqual(not (version or '').strip(), bool(soup.select('[data-fact-id="dataset-version"][data-status="missing"]')))
                self.assertEqual(change not in policies, bool(soup.select('[data-fact-id="dataset-version-policy"][data-status="missing"]')))
        typed = {key: {'value': {'type': 'ItemListReply' if isinstance(value, list) else 'AnswerReply', 'value': value}}
                 for key, value in {**base, leaf: yes}.items()}
        for profile in ('review', 'submission'):
            self.assertEqual(1, len(render(typed, profile, {'km': km}).select('[data-fact-id="dataset-versioning"][data-status="complete"]')))
            for mutation in ('missing', 'empty', 'unknown', 'wrong-reply-type',
                             'removed-question', 'removed-choice', 'dangling-answer', 'wrong-question-type'):
                altered, values = deepcopy(km), deepcopy(typed)
                if mutation == 'missing': values.pop(leaf)
                elif mutation in ('empty', 'unknown'): values[leaf]['value']['value'] = '' if mutation == 'empty' else 'unknown'
                elif mutation == 'wrong-reply-type': values[leaf]['value']['type'] = 'StringReply'
                elif mutation == 'removed-question': del altered['entities']['questions'][IDS['refDataVersionedQUuid']]
                elif mutation == 'removed-choice': altered['entities']['questions'][IDS['refDataVersionedQUuid']]['answerUuids'] = [no]
                elif mutation == 'dangling-answer': del altered['entities']['answers'][yes]
                else: altered['entities']['questions'][IDS['refDataVersionedQUuid']]['questionType'] = 'ValueQuestion'
                self.assertFalse(render(values, profile, {'km': altered}).select('[data-fact-id="dataset-versioning"]'), mutation)
            for ancestor in base:
                values = deepcopy(typed); values.pop(ancestor)
                self.assertFalse(render(values, profile, {'km': km}).select('[data-fact-id="dataset-versioning"]'), ancestor)

    def test_instrument_acquisition_survives_missing_or_empty_dataset_list(self):
        measured = path('creatingCUuid', 'measuredQUuid')
        datasets = path(measured, 'measuredYesAUuid', 'measuredDataQUuid')
        fact = 'We will acquire data using measurement equipment.'
        for choice, listing, profile in itertools.product(('Yes', 'No', None, 'unknown'), (None, []), ('review', 'submission')):
            replies = {path(datasets, 'removed-item', 'measuredDataNameQUuid'): 'Stale instrument dataset'}
            if choice is not None: replies[measured] = IDS.get('measured'+choice+'AUuid', choice)
            if listing is not None: replies[datasets] = listing
            with self.subTest(choice=choice, listing=listing, profile=profile):
                soup = BeautifulSoup(render_question('src/questions/01-how-data.html.j2', replies,
                    output_profile=profile), 'html.parser')
                text = soup.get_text(' ', strip=True)
                self.assertEqual(choice == 'Yes', fact in text)
                self.assertNotIn('Stale instrument dataset', text)
                if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))

    def test_carrying_data_survives_missing_security_details_without_inference(self):
        risk = path('processingCUuid', 'risksQUuid')
        prefix = path(risk, 'risksExploreAUuid')
        carry = path(prefix, 'risksCarryHomeQUuid')
        enc = path(carry, 'risksCarryHomeYesAUuid', 'risksCarryHomeEncQUuid')
        password = path(carry, 'risksCarryHomeYesAUuid', 'risksCarryHomePassQUuid')
        for carrying, encryption, protection, profile in itertools.product(
                ('Yes', 'No', None, 'unknown'), ('Yes', 'No', None, 'unknown'),
                ('Yes', 'No', None, 'unknown'), ('review', 'submission')):
            replies = {risk: IDS['risksExploreAUuid'],
                path(prefix, 'risksHttpsQUuid'): IDS['risksHttpsYesAUuid']}
            if carrying is not None: replies[carry] = IDS.get('risksCarryHome'+carrying+'AUuid', carrying)
            if encryption is not None: replies[enc] = IDS.get('risksCarryHomeEnc'+encryption+'AUuid', encryption)
            if protection is not None: replies[password] = IDS.get('risksCarryHomePass'+protection+'AUuid', protection)
            with self.subTest(carrying=carrying, encryption=encryption, protection=protection, profile=profile):
                soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', replies,
                    output_profile=profile), 'html.parser')
                text = soup.get_text(' ', strip=True)
                self.assertEqual(carrying == 'Yes', 'Project members carry data with them' in text)
                self.assertEqual(carrying == 'No', 'Project members do not carry data with them' in text)
                self.assertEqual(carrying == 'Yes' and encryption == 'Yes', 'All data carriers are encrypted.' in text)
                self.assertEqual(carrying == 'Yes' and encryption == 'No', 'Not all data carriers are encrypted.' in text)
                self.assertEqual(carrying == 'Yes' and protection == 'Yes', 'Accounts on laptops are password-protected.' in text)
                self.assertEqual(carrying == 'Yes' and protection == 'No', 'Not all laptop accounts are password-protected.' in text)
                self.assertNotIn('can carry data', text)
                self.assertNotIn('will carry data', text)
                self.assertNotIn('will not carry data', text)
                self.assertIn('All project web services are accessible through HTTPS.', text)
                if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))
        for storing, profile in itertools.product(('Yes', 'No'), ('review', 'submission')):
            replies = {risk: IDS['risksExploreAUuid'], carry: IDS['risksCarryHomeYesAUuid'],
                       path(prefix, 'risksStoreLabQUuid'): IDS['risksStoreLab'+storing+'AUuid']}
            soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', replies,
                                 output_profile=profile), 'html.parser')
            expected = ('Project members '+('store' if storing == 'Yes' else 'do not store')+
                ' data or software on computers in the lab or external hard drives connected to those computers. '
                'Project members carry data with them (e.g. on laptops, USB sticks, or other external media).')
            self.assertEqual(expected, ' '.join(soup.select_one('.answer > p').get_text(' ', strip=True).split()))

    def test_risk_parent_gates_all_risk_facts_but_not_workspace_access(self):
        risk = path('processingCUuid', 'risksQUuid')
        prefix = path(risk, 'risksExploreAUuid')
        choices = {'risksStoreLabQUuid': 'risksStoreLabNoAUuid',
                   'risksCarryHomeQUuid': 'risksCarryHomeNoAUuid',
                   'risksHttpsQUuid': 'risksHttpsYesAUuid',
                   'risksInstructedQUuid': 'risksInstructedYesAUuid',
                   'risksInfoLossQUuid': 'risksInfoLossSmallAUuid',
                   'risksPersonalDataQUuid': 'risksPersonalDataNotUsingAUuid'}
        workspace = path('processingCUuid', 'sharedWorkspaceQUuid')
        values = {path(prefix, q): IDS[a] for q, a in choices.items()}
        values.update({workspace: IDS['sharedWorkspaceYesAUuid'],
            path(workspace, 'sharedWorkspaceYesAUuid', 'sharedAccessControlQUuid'): IDS['sharedAccessControlMembersRWAUuid']})
        facts = ('do not store data or software', 'do not carry data with them',
                 'accessible through HTTPS', 'have been instructed',
                 'The potential impact of data loss is small', 'We are not using any personal information.')
        for parent, profile in itertools.product((IDS['risksExploreAUuid'], None, '', 'unknown'), ('review', 'submission')):
            replies = dict(values)
            if parent is not None: replies[risk] = parent
            with self.subTest(parent=parent, profile=profile):
                soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', replies,
                    output_profile=profile), 'html.parser')
                text = soup.get_text(' ', strip=True)
                for fact in facts: self.assertEqual(parent == IDS['risksExploreAUuid'], fact in text, fact)
                self.assertIn('All project members, and no one else, have read and write access to the data.', text)
                self.assertFalse(soup.select('p p, p div, p ul'))

    def test_independent_party_custodian_requires_active_typed_text_without_hiding_access(self):
        from check_sentence_layout import partial_fixture
        from check_answer_mapping import question
        from current_support import PREFIX, environment
        chain = ('processingCUuid risksQUuid risksExploreAUuid risksPersonalDataQUuid '
                 'risksPersonalDataPseudoAUuid risksPseudonymizationQUuid '
                 'risksPseudonymizationPartyAUuid risksPseudonymizationPartyQUuid')
        km, base, leaf = partial_fixture(chain)
        self.assertEqual('5d51a103-ec07-4c20-b269-f2f59f26d2cd', IDS['risksPseudonymizationPartyQUuid'])
        km['entities']['questions'][IDS['risksPseudonymizationPartyQUuid']]['valueType'] = 'TextQuestionValueType'
        # These alternate real choices make the retained Party child inactive.
        for q, a in [('risksPersonalDataQUuid', 'risksPersonalDataNotUsingAUuid'),
                     ('risksPseudonymizationQUuid', 'risksPseudonymizationInsideAUuid')]:
            km['entities']['questions'][IDS[q]]['answerUuids'].append(IDS[a])
            km['entities']['answers'][IDS[a]] = {'followUpUuids': []}
        question(km, km['entities']['chapters'][IDS['processingCUuid']]['questionUuids'],
                 IDS['sharedWorkspaceQUuid'], 'OptionsQuestion', [IDS['sharedWorkspaceYesAUuid']])
        question(km, km['entities']['answers'][IDS['sharedWorkspaceYesAUuid']]['followUpUuids'],
                 IDS['sharedAccessControlQUuid'], 'OptionsQuestion', [IDS['sharedAccessControlMembersRWAUuid']])
        workspace = path('processingCUuid', 'sharedWorkspaceQUuid')
        base.update({workspace: IDS['sharedWorkspaceYesAUuid'],
            path(workspace, 'sharedWorkspaceYesAUuid', 'sharedAccessControlQUuid'): IDS['sharedAccessControlMembersRWAUuid']})
        env = environment(ROOT)
        old_str = env.filters['reply_str_value']
        env.filters['reply_str_value'] = lambda r: r['value'].get('value', '') if isinstance(r, dict) and isinstance(r.get('value'), dict) else old_str(r)
        template = env.from_string(PREFIX + "{% include 'src/questions/06-access-security.html.j2' %}")
        render = lambda values, profile, schema: BeautifulSoup(template.render(
            repliesMap=values, output_profile=profile, **schema), 'html.parser')
        typed = lambda values: {key: {'value': {'type': 'StringReply' if key == leaf else 'AnswerReply',
                                               'value': value}} for key, value in values.items()}
        authored = '<p>University <strong>linkage unit</strong>, version 0.</p><ul><li>Keep the original conditions.</li></ul>'
        generic = 'Pseudonymization is performed by an independent party to enable data linkage.'
        exclusive = 'All project members, and no one else, have read and write access to the data.'
        for profile, schema, value in itertools.product(('review', 'submission'), ({}, {'km': km}),
                                                       (None, '', ' \t\n\u3000', '0', authored)):
            values = dict(base)
            if value is not None: values[leaf] = value
            soup = render(typed(values) if schema else values, profile, schema)
            detail = soup.select_one('[data-fact-id="pseudonymization-key-custodian"]')
            self.assertEqual(bool(value and value.strip()), bool(detail), (profile, bool(schema), value))
            self.assertEqual(1, soup.get_text(' ', strip=True).count(generic))
            self.assertIn(exclusive, soup.get_text(' ', strip=True))
            if detail:
                self.assertEqual('complete', detail['data-status'])
                self.assertIn('answer-detail', detail['class'])
                lead = detail.find('div', recursive=False)
                self.assertEqual(['answer-lead'], lead['class'])
                self.assertEqual('Independent party that keeps the pseudonymization keys:', lead.p.get_text())
                self.assertEqual(value, ''.join(str(node) for node in lead.next_siblings).strip())
            if profile == 'submission': self.assertFalse(soup.select('.data-gap,.data-review'))
            self.assertFalse(soup.select('p p, p div, p ul'))
        active = typed({**base, leaf: authored})
        risk = path('processingCUuid', 'risksQUuid')
        personal = path(risk, 'risksExploreAUuid', 'risksPersonalDataQUuid')
        pseudo = path(personal, 'risksPersonalDataPseudoAUuid', 'risksPseudonymizationQUuid')
        mutations = [('missing-main', pseudo), ('unknown-main', pseudo),
                     ('alternate-personal', personal), ('alternate-pseudonymization', pseudo),
                     *[('missing-ancestor', p) for p in (risk, personal)],
                     *[('wrong-ancestor-reply', p) for p in (risk, personal, pseudo)],
                     ('wrong-leaf-reply', leaf), ('wrong-leaf-value', leaf),
                     ('wrong-value-type', leaf), ('wrong-question-type', leaf),
                     ('removed-question', leaf), ('removed-followup', pseudo),
                     ('removed-choice', pseudo), ('dangling-choice', pseudo)]
        for profile, (mutation, target) in itertools.product(('review', 'submission'), mutations):
            values, altered = deepcopy(active), deepcopy(km)
            if mutation in ('missing-main', 'missing-ancestor'): values.pop(target)
            elif mutation == 'unknown-main': values[target]['value']['value'] = 'unknown'
            elif mutation == 'alternate-personal': values[target]['value']['value'] = IDS['risksPersonalDataNotUsingAUuid']
            elif mutation == 'alternate-pseudonymization': values[target]['value']['value'] = IDS['risksPseudonymizationInsideAUuid']
            elif mutation in ('wrong-ancestor-reply', 'wrong-leaf-reply'):
                values[target]['value']['type'] = 'StringReply' if target != leaf else 'AnswerReply'
            elif mutation == 'wrong-leaf-value': values[leaf]['value']['value'] = 0
            elif mutation == 'wrong-value-type': altered['entities']['questions'][IDS['risksPseudonymizationPartyQUuid']]['valueType'] = 'StringQuestionValueType'
            elif mutation == 'wrong-question-type': altered['entities']['questions'][IDS['risksPseudonymizationPartyQUuid']]['questionType'] = 'OptionsQuestion'
            elif mutation == 'removed-question': del altered['entities']['questions'][IDS['risksPseudonymizationPartyQUuid']]
            elif mutation == 'removed-followup': altered['entities']['answers'][IDS['risksPseudonymizationPartyAUuid']]['followUpUuids'] = []
            elif mutation == 'removed-choice': altered['entities']['questions'][IDS['risksPseudonymizationQUuid']]['answerUuids'].remove(IDS['risksPseudonymizationPartyAUuid'])
            else: del altered['entities']['answers'][IDS['risksPseudonymizationPartyAUuid']]
            soup = render(values, profile, {'km': altered})
            self.assertFalse(soup.select('[data-fact-id="pseudonymization-key-custodian"]'), (profile, mutation, target))
            self.assertNotIn('linkage unit', soup.get_text(), (profile, mutation, target))
            self.assertIn(exclusive, soup.get_text(' ', strip=True), (profile, mutation))

    def test_negative_followups_preserve_exact_no_and_active_yes_only(self):
        cases = [
            ('src/questions/01-how-data.html.j2',
             ('reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid', 'dataHarmoQUuid'),
             'dataHarmoYesAUuid', 'dataHarmoNoAUuid',
             '51b686f1-8a57-4d55-a1a5-30d77d074ada',
             'Before reuse, we need to harmonize existing data from different sources',
             'We do not need to harmonize existing data from different sources before reuse.'),
            ('src/questions/01-how-data.html.j2',
             ('reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid', 'dataCompReadQUuid'),
             'dataCompReadYesAUuid', 'dataCompReadNoAUuid',
             'd613ee29-a81b-44aa-83b5-2bf21ba43d22',
             'Before reuse, we will need to convert the data into a machine-readable form.',
             'We will not use existing data that needs to be converted into a machine-readable form before reuse.'),
            ('src/questions/09-ethical-issues.html.j2',
             ('creatingCUuid', 'collectPersonalQUuid', 'collectPersonalYesAUuid',
              'cpersGdprQUuid', 'cpersGdprExploreAUuid', 'cpersGdprNeedDpiaQUuid'),
             'cpersGdprNeedDpiaYesAUuid', 'cpersGdprNeedDpiaNoAUuid',
             'd0741ff3-370b-44e7-860d-00b1f01e6254',
             'According to the questionnaire, a data protection impact assessment (DPIA) is required.',
             'According to the questionnaire, a data protection impact assessment (DPIA) is not required.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksInfoLossQUuid'),
             'risksInfoLossSmallAUuid', 'risksInfoLossNoAUuid',
             '4c5d329b-6e18-4f4e-92a9-f0298adf38fe',
             'The potential impact of data loss is small.',
             'We have not considered the possible impact on the project or organization of data loss.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksInfoLeakQUuid'),
             'risksInfoLeakSmallAUuid', 'risksInfoLeakNoAUuid',
             '04dd5577-367f-4c34-b90c-4bc25d80c819',
             'The potential impact of data disclosure is small.',
             'We have not considered the possible impact on the project or organization of data disclosure.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksInfoVandalismQUuid'),
             'risksInfoVandalismSmallAUuid', 'risksInfoVandalismNoAUuid',
             'b4dbc287-8eed-4799-800e-5ce0ede13cd8',
             'The potential impact of data tampering is small.',
             'We have not considered the possible impact on the project or organization of data tampering.'),
            ('src/questions/10-share-restrictions.html.j2',
             ('accessCUuid', 'openImmediatelyQUuid', 'openImmediatelyNoAUuid',
              'notOpenLegalReasonsQUuid', 'notOpenLegalReasonsYesAUuid', 'legalReasonsAuthenticatedQUuid'),
             'legalReasonsAuthenticatedYesAUuid', 'legalReasonsAuthenticatedNoAUuid',
             'da8b25a9-8865-4ce8-a2ba-d592c42daa4c',
             'We will permit authenticated access to the data.',
             'We will not permit authenticated access to the data.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksStoreLabQUuid'),
             'risksStoreLabYesAUuid', 'risksStoreLabNoAUuid',
             '17172079-ddce-40a7-b93a-f86dc6611452',
             'Project members store data or software on computers in the lab or external hard drives connected to those computers.',
             'Project members do not store data or software on computers in the lab or external hard drives connected to those computers.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksInstructedQUuid'),
             'risksInstructedYesAUuid', 'risksInstructedNoAUuid',
             'd802675e-f76b-4714-87ee-1b328da826ab',
             'Project members have been instructed about both generic and specific risks to the project.',
             'Project members have not received instruction covering both generic and project-specific risks.'),
            ('src/questions/11-data-preservation.html.j2',
             ('preservingCUuid', 'budgetTimeEffortQUuid'),
             'budgetTimeEffortYesAUuid', 'budgetTimeEffortNoAUuid',
             'f765ae2f-7d22-478c-bd53-1a388c4dbcc9',
             'We have allocated funds for the time and effort needed to prepare the data for publication.',
             'We have not budgeted for the time and effort needed to prepare the data for publication.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksCarryHomeQUuid',
              'risksCarryHomeYesAUuid', 'risksCarryHomePassQUuid'),
             'risksCarryHomePassYesAUuid', 'risksCarryHomePassNoAUuid',
             'f2d273c1-8e6e-4656-93ba-6b78d7d6785f',
             'Accounts on laptops are password-protected.',
             'Not all laptop accounts are password-protected.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksHttpsQUuid'),
             'risksHttpsYesAUuid', 'risksHttpsNoAUuid',
             '2b934f9d-d849-4e22-8e0c-65dbf7b9dbeb',
             'All project web services are accessible through HTTPS.',
             'Not all project web services are accessible through HTTPS.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksCertificationsQUuid'),
             'risksCertificationsYesAUuid', 'risksCertificationsNoAUuid',
             '9acf74b1-e045-477d-be96-695692bb22c3',
             'All data centres that store project data hold appropriate certifications.',
             'Not all data centres that store project data hold appropriate certifications.'),
            ('src/questions/06-access-security.html.j2',
             ('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksCarryHomeQUuid',
              'risksCarryHomeYesAUuid', 'risksCarryHomeEncQUuid'),
             'risksCarryHomeEncYesAUuid', 'risksCarryHomeEncNoAUuid',
             '546d6e41-80ea-417b-b0e3-a1d9d75a3794',
             'All data carriers are encrypted.',
             'Not all data carriers are encrypted.'),
            ('src/questions/03-docs-metadata.html.j2',
             ('processingCUuid', 'storageConvQUuid', 'storageConvExploreAUuid',
              'storageConvFSysQUuid', 'storageConvFSysYesAUuid', 'scDocumentVersioningQUuid'),
             'scDocumentVersioningYesAUuid', 'scDocumentVersioningNoAUuid',
             'd23c7fe6-4b85-4a84-9253-0322f9a94756',
             'We document how we manage file versioning for files and folders.',
             'We have not documented how we manage file versioning for files and folders.'),
            ('src/questions/01-how-data.html.j2',
             ('reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid',
              'dataCompReadQUuid', 'dataCompReadYesAUuid', 'dataCompReadOthersQUuid'),
             'dataCompReadOthersYesAUuid', 'dataCompReadOthersNoAUuid',
             '60bb3161-0877-4b2c-8b32-9932ae63cb27',
             'We will provide others with standardized, machine-readable metadata.',
             'We will not provide others with standardized, machine-readable metadata.'),
        ]
        for template, names, yes, no, exact_no, yes_text, no_text in cases:
            with self.subTest(question=names[-1], stage='bindings'):
                self.assertEqual(exact_no, IDS.get(no), 'The exact No option must have a source binding')
                self.assertIn(yes, IDS, 'The exact Yes option must have a source binding')
            if yes not in IDS or no not in IDS:
                continue
            parts = [IDS[name] for name in names]
            leaf = path(*parts)
            ancestors = {path(*parts[:index]): parts[index]
                         for index in range(2, len(parts), 2)}
            inactive_answers = {
                'collectPersonalQUuid': 'collectPersonalNoAUuid',
                'openImmediatelyQUuid': 'openImmediatelyYesAUuid',
                'notOpenLegalReasonsQUuid': 'notOpenLegalReasonsNoAUuid',
                'risksCarryHomeQUuid': 'risksCarryHomeNoAUuid',
                'storageConvFSysQUuid': 'storageConvFSysNoAUuid',
                'preexistingQUuid': 'preexistingNoAUuid',
                'dataCompReadQUuid': 'dataCompReadNoAUuid',
            }
            explicit_no_parents = {path(*parts[:index + 1]): IDS[inactive_answers[names[index]]]
                                   for index in range(1, len(parts) - 1, 2)
                                   if names[index] in inactive_answers}
            km = {'chapterUuids': [parts[0]], 'entities': {
                'chapters': {parts[0]: {'questionUuids': [parts[1]]}},
                'questions': {}, 'answers': {}}}
            for index in range(1, len(parts), 2):
                answers = [parts[index + 1]] if index + 1 < len(parts) else [IDS[yes], IDS[no]]
                km['entities']['questions'][parts[index]] = {
                    'questionType': 'OptionsQuestion', 'answerUuids': answers}
                for answer in answers:
                    km['entities']['answers'][answer] = {
                        'followUpUuids': [parts[index + 2]] if index + 2 < len(parts) else []}
            for schema in ({}, {'km': km}):
                for profile, choice in itertools.product(('review', 'submission'), (yes, no, None, '', 'unknown')):
                    values = dict(ancestors)
                    if choice is not None: values[leaf] = IDS.get(choice, choice)
                    with self.subTest(question=names[-1], choice=choice, profile=profile, schema=bool(schema)):
                        soup = BeautifulSoup(render_question(template, values, output_profile=profile, **schema), 'html.parser')
                        text = soup.get_text(' ', strip=True)
                        self.assertEqual(choice == yes, yes_text in text)
                        self.assertEqual(choice == no, no_text in text)
                        self.assertFalse(soup.select('p p, p div, p ul'))
                # Retained Yes/No replies behind inactive ancestors are not current facts.
                for ancestor, choice in itertools.product(ancestors, (yes, no)):
                    parents = (None, '', 'unknown')
                    if ancestor in explicit_no_parents: parents += (explicit_no_parents[ancestor],)
                    for parent in parents:
                        values = dict(ancestors, **{leaf: IDS[choice]})
                        if parent is None: del values[ancestor]
                        else: values[ancestor] = parent
                        text = BeautifulSoup(render_question(template, values, output_profile='submission', **schema), 'html.parser').get_text(' ', strip=True)
                        self.assertNotIn(yes_text, text)
                        self.assertNotIn(no_text, text)
            # A compiled KM cannot authorize a removed question, answer, follow-up or wrong type.
            for mutation, choice in itertools.product(
                    ('removed-question', 'removed-choice', 'dangling-answer', 'removed-followup', 'wrong-type'), (yes, no)):
                altered = deepcopy(km)
                selected = IDS[choice]
                if mutation == 'removed-question': del altered['entities']['questions'][parts[-1]]
                elif mutation == 'removed-choice': altered['entities']['questions'][parts[-1]]['answerUuids'] = [IDS[no if choice == yes else yes]]
                elif mutation == 'dangling-answer': del altered['entities']['answers'][selected]
                elif mutation == 'removed-followup':
                    if len(parts) == 2: altered['entities']['chapters'][parts[0]]['questionUuids'] = []
                    else: altered['entities']['answers'][parts[-2]]['followUpUuids'] = []
                else: altered['entities']['questions'][parts[-1]]['questionType'] = 'ValueQuestion'
                for profile in ('review', 'submission'):
                    text = BeautifulSoup(render_question(template, dict(ancestors, **{leaf: selected}),
                        output_profile=profile, km=altered), 'html.parser').get_text(' ', strip=True)
                    self.assertNotIn(yes_text if choice == yes else no_text, text, mutation)

        # Eventual openness says nothing about whether an agreement is needed.
        for profile in ('review', 'submission'):
            open_path = path('accessCUuid', 'openImmediatelyQUuid')
            collab = path('creatingCUuid', 'collabQUuid')
            replies = {open_path: IDS['openImmediatelyYesAUuid'], collab: IDS['collabYesAUuid'],
                       path(collab, 'collabYesAUuid', 'collabAgreeQUuid'): IDS['collabAgreeYesAUuid']}
            text = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2',
                                 replies, output_profile=profile), 'html.parser').get_text(' ', strip=True)
            self.assertNotIn('No data sharing agreement will be required.', text)
            self.assertIn('A collaboration agreement is in place to specify who can access which project data.', text)

        # Newly mapped authored follow-ups are independent of siblings, but
        # only current answers behind the exact selected parents are visible.
        from check_sentence_layout import partial_fixture
        fields = [
            ('src/questions/11-data-preservation.html.j2',
             'preservingCUuid budgetTimeEffortQUuid budgetTimeEffortYesAUuid budgetTimeEffortAmountQUuid',
             '2a0cf686-63ed-44b6-ae74-38ddd39ac741', 'preparation-budget-amount'),
            ('src/questions/12-access-data.html.j2',
             'preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid isPublishedDataYesAUuid '
             'publishedSpecSwUseQUuid publishedSpecSwUseNoAUuid publishedSpecSwUseNoReasonQUuid',
             '14f7a766-c28e-400e-8426-53f7b4e5b90b', 'software-not-required-reason'),
        ]
        authored = '<p>Keep <strong>v1.2.csv</strong>: 0 TWD; do not rewrite .,</p><ul><li>Reason A.</li></ul>'
        for template, chain, exact_uuid, fact in fields:
            names = chain.split()
            self.assertEqual(exact_uuid, IDS.get(names[-1]))
            if names[-1] not in IDS: continue
            km, base, leaf = partial_fixture(chain)
            for schema, profile, value in itertools.product(({}, {'km': km}), ('review', 'submission'),
                                                           (None, '', ' \t\n\u3000', '0', authored)):
                replies = dict(base)
                if value is not None: replies[leaf] = value
                soup = BeautifulSoup(render_question(template, replies, output_profile=profile, **schema), 'html.parser')
                detail = soup.select_one('[data-fact-id="'+fact+'"]')
                filled = bool((value or '').strip())
                self.assertEqual(filled, bool(detail), (chain, value))
                if detail: self.assertEqual(value, detail.decode_contents())
                self.assertFalse(soup.select('p p, p div, p ul'))
                if profile == 'submission': self.assertFalse(soup.select('.data-gap,.data-review'))
            if fact == 'software-not-required-reason':
                # Equal/missing names cannot merge two datasets' explanations.
                listing = path('preservingCUuid', 'producedDataQUuid')
                other_pub = path(listing, 'OTHER', 'isPublishedDataQUuid')
                other_sw = path(other_pub, 'isPublishedDataYesAUuid', 'publishedSpecSwUseQUuid')
                other_reason = path(other_sw, 'publishedSpecSwUseNoAUuid', 'publishedSpecSwUseNoReasonQUuid')
                replies = dict(base, **{listing: ['ITEM', 'OTHER'], leaf: authored,
                    other_pub: IDS['isPublishedDataYesAUuid'], other_sw: IDS['publishedSpecSwUseNoAUuid'],
                    other_reason: '<p>Only the second dataset uses standard tools.</p>'})
                for profile in ('review', 'submission'):
                    soup = BeautifulSoup(render_question(template, replies, output_profile=profile, km=km), 'html.parser')
                    first = soup.select_one('.dataset-section[data-item-id="ITEM"]')
                    second = soup.select_one('.dataset-section[data-item-id="OTHER"]')
                    self.assertEqual(authored, first.select_one('[data-fact-id="'+fact+'"]').decode_contents())
                    self.assertNotIn('Only the second dataset', first.get_text())
                    self.assertIn('Only the second dataset', second.get_text())
                    self.assertNotIn('v1.2.csv', second.get_text())
                    deleted = dict(replies, **{listing: ['OTHER']})
                    output = render_question(template, deleted, output_profile=profile, km=km)
                    self.assertNotIn('v1.2.csv', output)
                    self.assertIn('Only the second dataset', output)
            for ancestor in base:
                for selected in (None, '', 'unknown', []):
                    replies = dict(base, **{leaf: authored})
                    if selected is None: del replies[ancestor]
                    else: replies[ancestor] = selected
                    soup = BeautifulSoup(render_question(template, replies, output_profile='submission', km=km), 'html.parser')
                    self.assertFalse(soup.select('[data-fact-id="'+fact+'"]'), (chain, ancestor, selected))
            for mutation in ('removed-question', 'removed-followup', 'wrong-type'):
                altered = deepcopy(km)
                if mutation == 'removed-question': del altered['entities']['questions'][exact_uuid]
                elif mutation == 'removed-followup': altered['entities']['answers'][IDS[names[-2]]]['followUpUuids'] = []
                else: altered['entities']['questions'][exact_uuid]['questionType'] = 'OptionsQuestion'
                soup = BeautifulSoup(render_question(template, dict(base, **{leaf: authored}),
                                                    output_profile='submission', km=altered), 'html.parser')
                self.assertFalse(soup.select('[data-fact-id="'+fact+'"]'), (chain, mutation))

    def test_negative_limitations_share_prose_without_losing_positive_siblings(self):
        risk = path('processingCUuid', 'risksQUuid')
        risk_prefix = path(risk, 'risksExploreAUuid')
        carry = path(risk_prefix, 'risksCarryHomeQUuid')
        values = {risk: IDS['risksExploreAUuid'], carry: IDS['risksCarryHomeYesAUuid'],
                  path(carry, 'risksCarryHomeYesAUuid', 'risksCarryHomeEncQUuid'): IDS['risksCarryHomeEncNoAUuid'],
                  path(carry, 'risksCarryHomeYesAUuid', 'risksCarryHomePassQUuid'): IDS['risksCarryHomePassYesAUuid'],
                  path(risk_prefix, 'risksCertificationsQUuid'): IDS['risksCertificationsNoAUuid'],
                  path(risk_prefix, 'risksHttpsQUuid'): IDS['risksHttpsYesAUuid']}
        expected = ('Project members carry data with them (e.g. on laptops, USB sticks, or other external media). '
                    'Not all data carriers are encrypted. '
                    'Accounts on laptops are password-protected. '
                    'Not all data centres that store project data hold appropriate certifications. '
                    'All project web services are accessible through HTTPS.')
        preexisting = path('reusingCUuid', 'preexistingQUuid')
        convert = path(preexisting, 'preexistingYesAUuid', 'dataCompReadQUuid')
        reuse = {preexisting: IDS['preexistingYesAUuid'], convert: IDS['dataCompReadYesAUuid'],
                 path(convert, 'dataCompReadYesAUuid', 'dataCompReadItselfQUuid'): IDS['dataCompReadItselfYesAUuid'],
                 path(convert, 'dataCompReadYesAUuid', 'dataCompReadOthersQUuid'): IDS['dataCompReadOthersNoAUuid']}
        for profile in ('review', 'submission'):
            soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', values,
                output_profile=profile), 'html.parser')
            self.assertEqual(expected, ' '.join(soup.select_one('.answer > p').get_text(' ', strip=True).split()))
            soup = BeautifulSoup(render_question('src/questions/01-how-data.html.j2', reuse,
                output_profile=profile), 'html.parser')
            sentence = soup.find('p', string=lambda text: text and 'We will not provide others' in text)
            self.assertIsNotNone(sentence)
            self.assertEqual('Before reuse, we will need to convert the data into a machine-readable form and '
                'will make this version available to others through a standard repository. '
                'We will not provide others with standardized, machine-readable metadata.',
                ' '.join(sentence.get_text(' ', strip=True).split()))

    def test_q5_neutral_mapping_limit_does_not_imply_supplied_answers(self):
        for replies in storage_matrix():
            for profile in ('review', 'submission'):
                with self.subTest(replies=replies, profile=profile):
                    soup = BeautifulSoup(render_question(Q5, replies, output_profile=profile), 'html.parser')
                    if profile == 'submission':
                        self.assertFalse(soup.select('.storage-detail-limits'))
                        self.assertNotIn(LEAD, soup.get_text())
                        continue
                    self.assertEqual(LEAD, soup.select_one('.storage-detail-limits > p').get_text())
                    self.assertEqual(['unmapped', 'unmapped'], [n['data-status'] for n in soup.select('.storage-detail-limits [data-fact-id]')])
                    self.assertEqual(['Exact working-storage and backup locations.',
                        'The actual backup schedule. A need for frequent backups does not specify a schedule.'],
                        [n.get_text() for n in soup.select('.storage-detail-limits li')])
                    self.assertNotIn('The mapped answers describe', soup.get_text())

    def test_stale_archive_children_do_not_establish_storage_details(self):
        replies = {path('preservingCUuid', 'archivedDuringQUuid', 'archivedDuringYesAUuid', 'archiveRemoteQUuid'): IDS['archiveRemoteYesAUuid']}
        for parent in (None, 'No'):
            if parent: replies[path('preservingCUuid', 'archivedDuringQUuid')] = IDS['archivedDuringNoAUuid']
            soup = BeautifulSoup(render_question(Q5, replies), 'html.parser')
            self.assertEqual('unmapped', soup.select_one('[data-fact-id="storage-location"]')['data-status'])
            self.assertNotIn('The archive will be stored at a remote location.', soup.get_text())

    def test_support_yes_no_missing_and_unrecognized_are_distinct(self):
        for choice, state in [('Yes', 'complete'), ('No', 'explicit-no'), (None, 'missing'), ('', 'missing'), ('unknown', 'missing')]:
            soup = BeautifulSoup(render_question(Q11, support_replies((choice,))), 'html.parser')
            node = soup.select_one('[data-fact-id="repository-long-term-support"]')
            self.assertEqual(state, node['data-status'])
            self.assertEqual(SUPPORT[state], node.get_text())
            self.assertEqual('distro-0', node.find_parent(attrs={'data-item-id': True})['data-item-id'])
            self.assertIn('The repository will provide an advanced processing service.', node.parent.get_text())
            self.assertFalse(soup.select('p p, p div, p ul'))

    def test_support_does_not_leak_from_inactive_publication_or_repository(self):
        for publication, repository, choice in itertools.product([None, 'No', 'Yes'], [None, 'National', 'Special'], ['Yes', 'No', None]):
            soup = BeautifulSoup(render_question(Q11, support_replies((choice,), repository, publication)), 'html.parser')
            self.assertEqual(publication == 'Yes' and repository == 'Special', bool(soup.select('[data-fact-id="repository-long-term-support"]')))

    def test_each_distribution_keeps_its_own_support_state(self):
        soup = BeautifulSoup(render_question(Q11, support_replies(('Yes', 'No', None))), 'html.parser')
        self.assertEqual([('distro-0', 'complete'), ('distro-1', 'explicit-no'), ('distro-2', 'missing')],
                         [(n.find_parent(attrs={'data-item-id': True})['data-item-id'], n['data-status']) for n in soup.select('[data-fact-id="repository-long-term-support"]')])
        self.assertEqual(3, soup.get_text().count('The repository will provide an advanced processing service.'))
