"""Fixed choices become prose; missing answers and authored blocks stay distinct."""
import itertools
from copy import deepcopy
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from test_answer_retention import IDS, path
from test_science_europe_contract import render_question

METHODS = [
    ('Calibrating', 'measurement calibration'),
    ('Repetition', 'repeat sampling or measurement'),
    ('Standardized', 'standardized data capture or recording'),
    ('Validation', 'data entry validation'),
    ('PeerReview', 'data peer review'),
    ('Vocabularies', 'use of controlled vocabularies'),
    ('Consistency', 'measurement of samples with known outcomes to monitor consistency'),
]
MEASURED = path('creatingCUuid', 'measuredQUuid')
DATASETS = path(MEASURED, 'measuredYesAUuid', 'measuredDataQUuid')
DATASET = path(DATASETS, 'test-dataset')
QUALITY = path(DATASET, 'measuredDataQualityQUuid')
PREFIX = path(QUALITY, 'measuredDataQualityYesAUuid')
Q1 = 'src/questions/01-how-data.html.j2'
Q4 = 'src/questions/04-quality-control.html.j2'


def replies():
    return {MEASURED: IDS['measuredYesAUuid'], DATASETS: ['test-dataset'],
            path(DATASET, 'measuredDataNameQUuid'): 'Coastal observations',
            QUALITY: IDS['measuredDataQualityYesAUuid']}


class QualityReadingTests(unittest.TestCase):
    def test_all_128_selected_method_combinations_match_in_q1_and_q4(self):
        for selected in itertools.product((False, True), repeat=len(METHODS)):
            values = replies()
            for (name, _), yes in zip(METHODS, selected):
                answer = IDS.get(f'mdQuality{name}{"Yes" if yes else "No"}AUuid')
                if answer: values[path(PREFIX, f'mdQuality{name}QUuid')] = answer
            for profile in ('review', 'submission'):
                summaries = []
                for template in (Q1, Q4):
                    soup = BeautifulSoup(render_question(template, values, output_profile=profile), 'html.parser')
                    summary = soup.select_one('[data-fact-id="quality-methods"]')
                    self.assertIsNotNone(summary)
                    if any(selected):
                        expected = ', '.join(text for (_, text), yes in zip(METHODS, selected) if yes)
                        self.assertEqual(f'Quality control measures for Coastal observations: {expected}.', summary.get_text())
                        self.assertFalse(summary.select('p, ul, li, br'))
                    else:
                        self.assertEqual('missing' if profile == 'review' else 'partial', summary['data-status'])
                    summaries.append(summary.get_text())
                self.assertEqual(*summaries)

    def test_unknown_quality_is_not_explicit_no(self):
        for answer in (None, 'measuredDataQualityNoAUuid'):
            values = replies()
            if answer: values[QUALITY] = IDS[answer]
            else: del values[QUALITY]
            for template in (Q1, Q4):
                root = BeautifulSoup(render_question(template, values), 'html.parser')
                marker = root.select_one('[data-fact-id="quality-control"]')
                self.assertEqual('explicit-no' if answer else 'missing', marker['data-status'])

    def test_missing_dataset_list_is_visible(self):
        soup = BeautifulSoup(render_question(Q4, {MEASURED: IDS['measuredYesAUuid']}), 'html.parser')
        self.assertIsNotNone(soup.select_one('[data-status="missing-output"]'))

    def test_q4_missing_quality_keeps_question_without_name_only_blocks(self):
        values = replies(); del values[QUALITY]
        values[DATASETS].append('second-dataset')
        for profile in ('review', 'submission'):
            soup = BeautifulSoup(render_question(Q4, values, output_profile=profile), 'html.parser')
            self.assertIsNotNone(soup.select_one('#q-quality-control > h3'))
            if profile == 'submission':
                self.assertEqual('', soup.select_one('.answer').get_text(strip=True))
                self.assertFalse(soup.select('.quality-dataset, .quality-context, .data-gap'))
            else:
                self.assertEqual(2, len(soup.select('.quality-dataset [data-status="missing"]')))
            q1 = BeautifulSoup(render_question(Q1, values, output_profile=profile), 'html.parser')
            self.assertIn('Coastal observations', q1.get_text())

    def test_q4_only_answered_quality_keeps_original_dataset_number(self):
        values = replies(); del values[QUALITY]
        values[DATASETS].append('second-dataset')
        second = path(DATASETS, 'second-dataset')
        values[path(second, 'measuredDataQualityQUuid')] = IDS['measuredDataQualityNoAUuid']
        soup = BeautifulSoup(render_question(Q4, values, output_profile='submission'), 'html.parser')
        blocks = soup.select('.quality-dataset')
        self.assertEqual([second], [block['data-item-id'] for block in blocks])
        self.assertEqual('explicit-no', blocks[0].select_one('[data-fact-id="quality-control"]')['data-status'])
        self.assertIn('Instrument dataset 2', blocks[0].get_text())
        self.assertNotIn('Coastal observations', soup.select_one('.answer').get_text())

    def test_other_methods_keep_authored_blocks_and_do_not_claim_no_methods(self):
        values = replies()
        other = path(PREFIX, 'mdQualityOtherQUuid')
        values[other] = IDS['mdQualityOtherYesAUuid']
        authored = '<p>Keep v1.2; do not rewrite!</p><p>Second paragraph。</p><ul><li>Check A.</li><li>Check B</li></ul>'
        values[path(other, 'mdQualityOtherYesAUuid', 'mdQualityOtherWhatQUuid')] = authored
        for template in (Q1, Q4):
            soup = BeautifulSoup(render_question(template, values), 'html.parser')
            detail = soup.select_one('[data-fact-id="quality-other"]')
            self.assertEqual(authored, detail.div.decode_contents())
            self.assertEqual(2, len(detail.select('p')))
            self.assertFalse(detail.find_parent('p'))
            self.assertFalse(soup.select('[data-fact-id="quality-methods"][data-status="missing"]'))
        del values[path(other, 'mdQualityOtherYesAUuid', 'mdQualityOtherWhatQUuid')]
        self.assertIn('data-fact-id="quality-other" data-status="missing"', render_question(Q4, values))

    def test_unnamed_dataset_has_fallback(self):
        values = replies(); del values[path(DATASET, 'measuredDataNameQUuid')]
        self.assertIn('(no name given)', render_question(Q4, values))

    def test_legal_fallback_only_for_empty_output(self):
        template = 'src/questions/08-copyright-ipr.html.j2'
        ownership = path('creatingCUuid', 'ownershipQUuid')
        detail = path(ownership, 'ownershipOtherAUuid', 'ownershipOtherQUuid')
        partial = 'Rights to the collected data are arranged in another way.'
        for values in ({}, {ownership: 'unknown-option'},
                       {ownership: 'unknown-option', detail: '<p>Inactive ownership detail.</p>'}):
            self.assertIn('data-status="missing-output"', render_question(template, values))
            self.assertNotIn(partial, render_question(template, values))
        for profile, value in itertools.product(('review', 'submission'), (None, '', ' \t\n\u3000')):
            values = {ownership: IDS['ownershipOtherAUuid']}
            if value is not None: values[detail] = value
            output = render_question(template, values, output_profile=profile)
            self.assertEqual(1, output.count(partial))
            self.assertNotIn('data-status="missing-output"', output)
        output = render_question(template, {ownership: IDS['ownershipNoOwnerAUuid']})
        self.assertIn('The project data are not protected by copyright and therefore have no copyright owner.', output)
        self.assertNotIn(partial, output)
        output = render_question(template, {ownership: IDS['ownershipPIAUuid']})
        self.assertIn('All data will be owned by the Principal Investigator.', output)
        self.assertNotIn('data-status="missing-output"', output)

    def test_multiple_open_data_reasons_have_one_complete_lead_and_keep_reason_order(self):
        opened = path('accessCUuid', 'openImmediatelyQUuid')
        prefix = path(opened, 'openImmediatelyNoAUuid')
        values = {opened: IDS['openImmediatelyNoAUuid'],
                  path(prefix, 'notOpenLegalReasonsQUuid'): IDS['notOpenLegalReasonsYesAUuid'],
                  path(prefix, 'notOpenBusinessReasonsQUuid'): IDS['notOpenBusinessReasonsPatentsAUuid'],
                  path(prefix, 'notOpenOtherReasonsQUuid'): IDS['notOpenOtherReasonsPapersAUuid']}
        expected = ['legal restrictions', 'patent-related commercial considerations',
                    'papers need to be submitted first']
        for profile in ('review', 'submission'):
            soup = BeautifulSoup(render_question('src/questions/08-copyright-ipr.html.j2', values,
                output_profile=profile), 'html.parser')
            reasons = soup.select_one('.answer-detail > ul')
            self.assertIsNotNone(reasons)
            lead = reasons.find_previous_sibling()
            self.assertIsNotNone(lead)
            self.assertIn('answer-lead', lead.get('class', []))
            self.assertEqual(1, len(lead.find_all('p', recursive=False)))
            self.assertEqual('The data cannot be made fully open for the following reasons:', lead.get_text(' ', strip=True))
            self.assertEqual(expected, [item.get_text(' ', strip=True) for item in reasons.find_all('li', recursive=False)])
            self.assertFalse(soup.select('p p, p div, p ul, p ol'))

        # Few rich reason items can occupy a page; only their owned outer list
        # may flow. Ordinary short lists, authored child lists and other Qs keep
        # the existing rule, as do fixed leads and individual table rows.
        short_selector = 'html body .answer-detail ul:has(> li:last-child:nth-child(-n+3))'
        # The official worker matches this descendant form, but not the
        # multi-level leading-child form :has(> li > ...). Ownership stays direct.
        rich_selector = ('html body #q-copyright-ipr > .answer > .answer-detail > ul:has('
                         'li > div.answer-lead, li > table, li > pre, li > ul, li > ol)')
        css = (Path(__file__).resolve().parents[1] / 'src/layout.css').read_text()
        self.assertEqual(1, css.count(short_selector + ' { break-inside: avoid; }'))
        self.assertEqual(1, css.count(rich_selector + ' { break-inside: auto; }'))
        self.assertLess(css.index(short_selector), css.index(rich_selector))
        self.assertIn('html body .answer-lead { break-after: avoid; }', css)
        self.assertIn('html body tr { break-inside: avoid; }', css)
        native_cases = []
        for rich in ('<table><tr><td>Original value.</td></tr></table>',
                     '<pre><code>Original &lt;value&gt;.</code></pre>',
                     '<ul><li>Original nested bullet.</li></ul>',
                     '<ol><li>Original nested step.</li></ol>',
                     '<p>Short authored explanation.</p>',
                     '<p>' + 'Long authored reason. ' * 100 + '</p>'):
            source = ('<html><body><div id="q-copyright-ipr"><div class="answer">'
                      '<div class="answer-detail"><div class="answer-lead"><p>Reasons:</p></div>'
                      '<ul><li><div class="answer-lead"><p>First reason:</p></div>' + rich +
                      '</li><li>Second reason.</li></ul></div></div></div></body></html>')
            soup = BeautifulSoup(source, 'html.parser')
            native_cases.append((source, 1))
            self.assertEqual([soup.select_one('.answer-detail > ul')], soup.select(rich_selector))
            self.assertFalse(any('answer-lead' in node.get('class', []) for node in soup.select(rich_selector)))
            ordinary_source = source.replace(rich, '<p>Short original explanation.</p>').replace(
                '<div class="answer-lead"><p>First reason:</p></div>', '<p>First fixed reason.</p>')
            for unchanged in (source.replace('id="q-copyright-ipr"', 'id="q-other"'),
                              source.replace('class="answer"', 'class="unowned"'),
                              source.replace('class="answer-detail"', 'class="other-detail"'),
                              source.replace('<div class="answer-detail">', '<div><div class="answer-detail">', 1)
                                    .replace('</div></div></div></body>', '</div></div></div></div></body>'),
                              ordinary_source):
                self.assertFalse(BeautifulSoup(unchanged, 'html.parser').select(rich_selector))
                native_cases.append((unchanged, 0))
            ordinary = BeautifulSoup(ordinary_source, 'html.parser')
            self.assertEqual([ordinary.select_one('.answer-detail > ul')], ordinary.select(short_selector))

        # Use the already pinned worker's selector engine, not only SoupSieve.
        import importlib.util, json, subprocess
        spec = importlib.util.spec_from_file_location('pinned_worker',
            Path(__file__).resolve().parents[1] / 'scripts/probe_budget_word.py')
        worker = importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)
        runner = '''import cssselect2,json,sys
from weasyprint import HTML
p=json.load(sys.stdin)
print(json.dumps([len(list(cssselect2.ElementWrapper.from_html_root(
    HTML(string=source).etree_element).query_all(p['selector']))) for source in p['sources']]))
'''
        counts = json.loads(subprocess.check_output(
            ['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python',
             worker.IMAGE, '-B', '-c', runner],
            input=json.dumps(dict(selector=rich_selector, sources=[s for s, _ in native_cases])).encode(),
            timeout=120))
        self.assertEqual([expected for _, expected in native_cases], counts)

    def test_paper_reason_does_not_change_submission_into_publication(self):
        opened = path('accessCUuid', 'openImmediatelyQUuid')
        values = {opened: IDS['openImmediatelyNoAUuid'],
                  path(opened, 'openImmediatelyNoAUuid', 'notOpenOtherReasonsQUuid'):
                      IDS['notOpenOtherReasonsPapersAUuid']}
        for profile in ('review', 'submission'):
            text = BeautifulSoup(render_question('src/questions/08-copyright-ipr.html.j2', values,
                output_profile=profile), 'html.parser').get_text(' ', strip=True)
            self.assertIn('The data cannot be made fully open because papers need to be submitted first.', text)
            self.assertNotIn('publish a paper', text)

    def test_authorization_lead_precedes_unchanged_authored_blocks(self):
        opened = path('accessCUuid', 'openImmediatelyQUuid')
        legal = path(opened, 'openImmediatelyNoAUuid', 'notOpenLegalReasonsQUuid')
        authentication = path(legal, 'notOpenLegalReasonsYesAUuid', 'legalReasonsAuthenticatedQUuid')
        authorization = path(authentication, 'legalReasonsAuthenticatedYesAUuid', 'legalReasonsAuthorizeQUuid')
        for question in ('08-copyright-ipr', '10-share-restrictions'):
            for kind, fixed_lead in [('Other', 'We will use the following authorization arrangements:'),
                    ('OldCommittee', 'We will make use of an existing data committee:')]:
                for authored in ['', '  ', '<p>Access office.</p>', '<p>Original.</p>' * 50,
                        '<ul><li>Original A.</li><li>Original B.</li></ul>',
                        '<table><tr><td>Original.</td><td>Keep.</td></tr></table>',
                        '<p>First <strong>owned</strong> paragraph.</p><ul><li>Keep this item.</li></ul><p>Last paragraph.</p>']:
                    values = {opened: IDS['openImmediatelyNoAUuid'], legal: IDS['notOpenLegalReasonsYesAUuid'],
                              authentication: IDS['legalReasonsAuthenticatedYesAUuid'],
                              authorization: IDS['legalReasonsAuthorize'+kind+'AUuid'],
                              path(authorization, 'legalReasonsAuthorize'+kind+'AUuid', 'legalReasonsAuthorize'+kind+'QUuid'): authored}
                    for profile in ('review', 'submission'):
                        with self.subTest(question=question, kind=kind, authored=authored, profile=profile):
                            soup = BeautifulSoup(render_question('src/questions/'+question+'.html.j2', values,
                                output_profile=profile), 'html.parser')
                            leads = soup.select('.answer-lead')
                            self.assertEqual(len(leads), int(bool(authored.strip())))
                            self.assertFalse(soup.select('p p, p div, p ul, p ol, p table'))
                            if not authored.strip(): continue
                            lead = leads[0]
                            self.assertEqual([node.name for node in lead.find_all(recursive=False)], ['p'])
                            if question.startswith('08-'):
                                self.assertEqual(fixed_lead, lead.p.get_text())
                                self.assertEqual(lead.parent.get('class'), ['answer-detail'])
                                body = lead.next_siblings
                            else:
                                self.assertIn('We will permit authenticated access to the data.', lead.get_text())
                                body = lead.find_next_sibling('div', class_='authorization-details').contents
                            self.assertEqual(authored, ''.join(str(node) for node in body))

    def test_workspace_access_requires_current_reachable_choice_but_keeps_https(self):
        chapter = IDS['processingCUuid']
        workspace, yes, no = (IDS[n] for n in ('sharedWorkspaceQUuid', 'sharedWorkspaceYesAUuid', 'sharedWorkspaceNoAUuid'))
        access = IDS['sharedAccessControlQUuid']
        choices = {IDS[name]: text for name, text in (
            ('sharedAccessControlMembersRWAUuid', 'All project members, and no one else, have read and write access to the data.'),
            ('sharedAccessControlInstituteRAUuid', 'Everyone at the institute has read access to the data; all project members have read and write access.'),
            ('sharedAccessControlMembersRAUuid', 'Only project members have read access; only designated project members can modify the data.'),
            ('sharedAccessControlMembersRequestAUuid', 'Everyone at the institute can read the data; only project members can request write access.'))}
        km = {'chapterUuids': [chapter], 'entities': {
            'chapters': {chapter: {'questionUuids': [workspace, IDS['risksQUuid']]}},
            'questions': {workspace: {'questionType': 'OptionsQuestion', 'answerUuids': [yes, no]},
                          access: {'questionType': 'OptionsQuestion', 'answerUuids': list(choices)},
                          IDS['risksQUuid']: {'questionType': 'OptionsQuestion', 'answerUuids': [IDS['risksExploreAUuid']]},
                          IDS['risksHttpsQUuid']: {'questionType': 'OptionsQuestion', 'answerUuids': [IDS['risksHttpsYesAUuid']]}},
            'answers': {yes: {'followUpUuids': [access]}, no: {'followUpUuids': []},
                        IDS['risksExploreAUuid']: {'followUpUuids': [IDS['risksHttpsQUuid']]},
                        IDS['risksHttpsYesAUuid']: {'followUpUuids': []},
                        **{choice: {'followUpUuids': []} for choice in choices}}}}
        workspace_path = path(chapter, workspace)
        access_path = path(workspace_path, yes, access)
        sibling = {path(chapter, 'risksQUuid'): IDS['risksExploreAUuid'],
                   path(chapter, 'risksQUuid', 'risksExploreAUuid', 'risksHttpsQUuid'): IDS['risksHttpsYesAUuid']}
        for parent in (yes, no, None, '', 'unknown'):
            for choice in (*choices, 'unknown'):
                values = dict(sibling, **{access_path: choice})
                if parent is not None: values[workspace_path] = parent
                for schema in ({}, {'km': km}):
                    for profile in ('review', 'submission'):
                        with self.subTest(parent=parent, choice=choice, schema=bool(schema), profile=profile):
                            soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', values,
                                output_profile=profile, **schema), 'html.parser')
                            text = soup.get_text(' ', strip=True)
                            active = parent == yes and choice in choices
                            self.assertEqual(active, 'Access to data during research' in text)
                            for fact in choices.values(): self.assertEqual(active and fact == choices.get(choice), fact in text)
                            self.assertIn('All project web services are accessible through HTTPS.', text)
        values = dict(sibling, **{workspace_path: yes, access_path: next(iter(choices))})
        for mutation in ('removed-question', 'removed-followup', 'wrong-type', 'removed-choice', 'dangling-answer'):
            altered = deepcopy(km)
            if mutation == 'removed-question': del altered['entities']['questions'][access]
            elif mutation == 'removed-followup': altered['entities']['answers'][yes]['followUpUuids'] = []
            elif mutation == 'wrong-type': altered['entities']['questions'][access]['questionType'] = 'ValueQuestion'
            elif mutation == 'removed-choice': altered['entities']['questions'][access]['answerUuids'] = []
            else: del altered['entities']['answers'][values[access_path]]
            for profile in ('review', 'submission'):
                text = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', values,
                    output_profile=profile, km=altered), 'html.parser').get_text(' ', strip=True)
                self.assertNotIn('Access to data during research', text, mutation)
                self.assertIn('All project web services are accessible through HTTPS.', text, mutation)

    def test_unnamed_roles_keep_facts_and_a_specific_name_gap(self):
        parent = path('adminDetailsCUuid', 'contributorsQUuid')
        template = 'src/questions/14-dm-responsible.html.j2'
        for name, roles in [('', ['contributorRoleDataStewardAUuid']), ('Named team', ['contributorRoleContactPersonAUuid'])]:
            values = {parent: ['person'], path(parent, 'person', 'contributorNameQUuid'): name,
                      path(parent, 'person', 'contributorRoleQUuid'): [IDS[r] for r in roles]}
            output = render_question(template, values)
            if name:
                self.assertIn('data-status="missing-output"', output)
                self.assertNotIn('class="responsibility-summary"', output)
            else:
                self.assertIn('Contributor 1', output)
                self.assertIn('Contributor 1 is responsible for managing data', output)
                self.assertIn('data-fact-id="responsible-person-name" data-status="missing"', output)
                self.assertNotIn('data-status="missing-output"', output)

    def test_responsibility_sentences_keep_actors_roles_and_original_indices(self):
        from current_support import PREFIX as wrapper, ROOT, environment
        duties = [
            ('DataCurator', 'reviewing, enhancing, cleaning or standardizing metadata and associated data submitted to a data centre or repository for storage, use and maintenance.'),
            ('DataCollector', 'finding, gathering and collecting data.'),
            ('DataManager', 'maintaining the completed resource.'),
            ('DataSteward', 'managing data and supporting its effective use, including data processing, policies, guidelines and availability.'),
            ('Distributor', 'producing and disseminating electronic or print copies of the resource.'),
            ('DataProtector', 'addressing personal-data protection and data-protection policies.'),
            ('CreatorOfDMP', 'implementing the data management plan and ensuring that it is reviewed and revised.'),
        ]
        roles = [IDS['contributorRole' + role + 'AUuid'] for role, _ in duties]
        parent = path('adminDetailsCUuid', 'contributorsQUuid')
        source = wrapper + "{% include 'src/questions/14-dm-responsible.html.j2' %}"
        contact = IDS['contributorRoleContactPersonAUuid']
        for escaping, profile in itertools.product((False, True), ('review', 'submission')):
            render = environment(ROOT, escape=escaping).from_string(source).render
            for selected in [[role] for role in roles] + [roles]:
                with self.subTest(escaping=escaping, profile=profile, roles=selected):
                    values = {parent: ['actor'], path(parent, 'actor', 'contributorNameQUuid'): '<A&B>',
                              path(parent, 'actor', 'contributorRoleQUuid'): selected}
                    output = render(repliesMap=values, output_profile=profile)
                    soup = BeautifulSoup(output, 'html.parser')
                    summaries = soup.select('.responsibility-summary')
                    self.assertEqual(1, len(summaries))
                    expected = ' '.join('<A&B> is responsible for ' + duty
                                        for role, (_, duty) in zip(roles, duties) if role in selected)
                    self.assertEqual(expected, summaries[0].get_text())
                    self.assertEqual(selected, summaries[0]['data-role-uuids'].split())
                    self.assertEqual(len(selected), output.count('&lt;A&amp;B&gt;'))
                    self.assertFalse(summaries[0].find_all())
                    self.assertFalse(soup.select('.responsible-person, .data-gap'))

            for missing_name in (None, '', ' \t\n\u3000'):
                people = [('contact', 'No assignment', [contact]),
                          ('same-a', 'Same team', [roles[1]]),
                          ('unnamed', missing_name, [roles[3]]),
                          ('same-b', 'Same team', [roles[6]]),
                          ('unknown', 'Unknown actor', ['future-role']),
                          ('mixed', 'Mixed actor', [roles[2], contact, 'future-role'])]
                values = {parent: [item for item, _, _ in people]}
                for item, name, selected in people:
                    if name is not None: values[path(parent, item, 'contributorNameQUuid')] = name
                    values[path(parent, item, 'contributorRoleQUuid')] = selected
                with self.subTest(escaping=escaping, profile=profile, missing_name=missing_name):
                    soup = BeautifulSoup(render(repliesMap=values, output_profile=profile), 'html.parser')
                    blocks = soup.select('.person-responsibilities')
                    self.assertEqual(['same-a', 'unnamed', 'same-b', 'mixed'],
                                     [block['data-contributor-id'] for block in blocks])
                    self.assertEqual(['2', '3', '4', '6'],
                                     [block['data-contributor-index'] for block in blocks])
                    for block, actor, role in zip(blocks, ['Same team', 'Contributor 3', 'Same team', 'Mixed actor'],
                                                  [roles[1], roles[3], roles[6], roles[2]]):
                        summary = block.select_one('.responsibility-summary')
                        duty = dict(zip(roles, [text for _, text in duties]))[role]
                        self.assertEqual(actor + ' is responsible for ' + duty, summary.get_text())
                        self.assertEqual([role], summary['data-role-uuids'].split())
                    gaps = soup.select('[data-fact-id="responsible-person-name"]')
                    self.assertEqual(int(profile == 'review'), len(gaps))
                    if gaps:
                        self.assertEqual('unnamed', gaps[0].parent['data-contributor-id'])
                        self.assertEqual('missing', gaps[0]['data-status'])
                    self.assertNotIn('No assignment', soup.get_text())
                    self.assertNotIn('Unknown actor', soup.get_text())
                    self.assertFalse(soup.select('[data-status="missing-output"]'))
