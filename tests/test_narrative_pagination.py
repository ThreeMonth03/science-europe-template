import unittest
from bs4 import BeautifulSoup

from test_answer_retention import IDS, path
from test_science_europe_contract import render_question
import test_storage_sharing
from test_structure_bindings import BlockProbe


class NarrativePaginationTests(unittest.TestCase):
    def test_restricted_custom_process_keeps_only_its_fixed_nonempty_lead(self):
        datasets = path('preservingCUuid', 'producedDataQUuid')
        published = path(datasets, 'd1', 'isPublishedDataQUuid')
        distributions = path(published, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
        licences = path(distributions, 'r1', 'publishedDataLicensesQUuid')
        licence = path(licences, 'l1', 'publishedDataLicenseQUuid')
        restricted = path(licence, 'publishedDataLicenseRestrictAUuid')
        access = path(restricted, 'licenseRestrictAccessQUuid')
        detail = path(access, 'licenseRestrictAccessAnotherAUuid', 'licenseRestrictAccessAnotherQUuid')
        base = {datasets: ['d1'], published: IDS['isPublishedDataYesAUuid'],
                distributions: ['r1'], licences: ['l1'], licence: IDS['publishedDataLicenseRestrictAUuid'],
                access: IDS['licenseRestrictAccessAnotherAUuid'],
                path(restricted, 'licenseRestrictMetadataQUuid'): IDS['licenseRestrictMetadataYesAUuid']}
        rich = '<p>Original opening.</p><table><tr><td>Original cell.</td></tr></table><p>Original ending.</p>'
        for profile in ('review', 'submission'):
            for value in (rich, '0', 'false', None, '', ' \t\n\u3000'):
                with self.subTest(profile=profile, value=value):
                    replies = dict(base)
                    if value is not None: replies[detail] = value
                    output = render_question('src/questions/10-share-restrictions.html.j2', replies,
                                             output_profile=profile)
                    soup = BeautifulSoup(output, 'html.parser')
                    process = soup.select_one('.restriction-process')
                    lead = process.find('div', recursive=False)
                    self.assertEqual('Access requests will follow a specialized process.', lead.p.get_text())
                    filled = value is not None and bool(value.strip())
                    self.assertEqual(['answer-lead'] if filled else None, lead.get('class'))
                    self.assertEqual([lead.p], lead.find_all(recursive=False))
                    authored = process.select_one('[data-fact-id="restriction-custom-process"][data-status="complete"]')
                    if filled:
                        self.assertEqual(authored, lead.find_next_sibling())
                        self.assertEqual(value, authored.decode_contents())
                        self.assertFalse(authored.select('.answer-lead'))
                    else:
                        self.assertIsNone(authored)
                        self.assertEqual(profile == 'review', bool(process.select_one('.data-gap')))
                    self.assertFalse({'answer-lead', 'short-reading-unit'} & set(process.get('class', [])))
                    self.assertEqual('The conditions will be published as part of open metadata.',
                                     process.find_all('p', recursive=False)[-1].get_text())
                    probe = BlockProbe(); probe.feed(output)
                    self.assertEqual([], probe.errors)

    def test_folder_item_leads_attach_only_to_their_own_nonempty_details(self):
        storage = path('processingCUuid', 'storageConvQUuid')
        filesystem = path(storage, 'storageConvExploreAUuid', 'storageConvFSysQUuid')
        prefix = path(filesystem, 'storageConvFSysYesAUuid')
        owners = [('Subj', 'folder for each sample/subject'),
                  ('Analysis', '(sub)folder for each (repeated) analysis'),
                  ('WorkflowStep', '(sub)folder for each step in the analysis workflow')]
        base = {storage: IDS['storageConvExploreAUuid'], filesystem: IDS['storageConvFSysYesAUuid']}
        for name, _ in owners:
            base[path(prefix, 'scFSys' + name + 'FoldersQUuid')] = IDS['scFSys' + name + 'FoldersYesAUuid']
        for profile in ('submission', 'review'):
            for value in ('rich', None, '', ' \t\n\u3000', '0', 'false', 'only-Subj', 'only-Analysis', 'only-WorkflowStep'):
                with self.subTest(profile=profile, value=value):
                    values, bodies = dict(base), []
                    for name, _ in owners:
                        body = ('<p>' + name + ' opening.</p><ul><li>' + name + ' original item.</li></ul>'
                                if value in ('rich', 'only-' + name) else None if str(value).startswith('only-') else value)
                        bodies.append(body)
                        if body is not None:
                            values[path(prefix, 'scFSys' + name + 'FoldersQUuid',
                                        'scFSys' + name + 'FoldersYesAUuid',
                                        'scFSys' + name + 'FoldersConvsQUuid')] = body
                    output = render_question('src/questions/03-docs-metadata.html.j2', values, output_profile=profile)
                    soup = BeautifulSoup(output, 'html.parser')
                    policy = soup.select_one('.storage-conventions-policy')
                    listing = policy.find('ul', recursive=False)
                    self.assertEqual(3, len(listing.find_all('li', recursive=False)))
                    for node in (soup.select_one('.answer'), policy, listing):
                        self.assertFalse({'answer-lead', 'short-reading-unit'} & set(node.get('class', [])))
                    for item, (_, phrase), body in zip(listing.find_all('li', recursive=False), owners, bodies):
                        label = item.find('div', recursive=False)
                        self.assertEqual('There will be a ' + phrase + '.', ' '.join(label.get_text().split()))
                        self.assertEqual(phrase, label.strong.get_text())
                        self.assertEqual('margin:0', label.p.get('style'))
                        self.assertFalse(label.select('ul, ol, table, pre, div'))
                        filled = body is not None and bool(body.strip())
                        self.assertEqual(['answer-lead'] if filled else None, label.get('class'))
                        detail = label.find_next_sibling()
                        if filled:
                            self.assertEqual(['answer-detail'], detail.get('class'))
                            lead = detail.find('div', recursive=False)
                            self.assertEqual(['answer-lead'], lead.get('class'))
                            self.assertEqual('Each of those will use the following conventions:', lead.p.get_text())
                            self.assertEqual(1, detail.decode_contents().count(body))
                        else:
                            self.assertIsNone(detail)
                    probe = BlockProbe(); probe.feed(output)
                    self.assertEqual([], probe.errors)

    def test_custom_pseudonymization_keeps_fixed_lead_outside_authored_blocks(self):
        # These body tests supply HTML through the registered test adapter;
        # they do not exercise the Markdown parser or native Word layout.
        risks = path('processingCUuid', 'risksQUuid')
        personal = path(risks, 'risksExploreAUuid', 'risksPersonalDataQUuid')
        method = path(personal, 'risksPersonalDataPseudoAUuid', 'risksPseudonymizationQUuid')
        detail = path(method, 'risksPseudonymizationAnotherAUuid', 'risksPseudonymizationAnotherQUuid')
        authored = '<p>Custodian opening.</p><ul><li>Original key-handling item.</li></ul>'
        base = {risks: IDS['risksExploreAUuid'], personal: IDS['risksPersonalDataPseudoAUuid'],
                method: IDS['risksPseudonymizationAnotherAUuid']}
        for profile in ('submission', 'review'):
            for value in (authored, None, '', ' \t\n\u3000'):
                with self.subTest(profile=profile, value=value):
                    values = dict(base)
                    if value is not None: values[detail] = value
                    output = render_question('src/questions/06-access-security.html.j2', values,
                                             output_profile=profile)
                    soup = BeautifulSoup(output, 'html.parser')
                    block = soup.select_one('#q-access-security > .answer > .answer-detail')
                    self.assertIsNotNone(block)
                    lead = block.find('div', recursive=False)
                    self.assertIn('All personal data will be processed in pseudonymized form only.', lead.get_text())
                    self.assertIn('form only. We use', ' '.join(lead.get_text().split()))
                    if value == authored:
                        self.assertEqual(['answer-lead'], lead.get('class'))
                        self.assertTrue(lead.get_text().strip().endswith('We use a specific pseudonymization method:'))
                        self.assertEqual('Custodian opening.', lead.find_next_sibling().get_text())
                        self.assertEqual('Original key-handling item.', lead.find_next_sibling().find_next_sibling().li.get_text())
                        self.assertEqual(1, output.count(authored))
                    else:
                        self.assertFalse(block.select('.answer-lead, ul, table, pre'))
                        self.assertTrue(lead.get_text().strip().endswith('We use a specific pseudonymization method.'))
                        self.assertNotIn(':', lead.get_text())
                    probe = BlockProbe(); probe.feed(output)
                    self.assertEqual([], probe.errors)
            for state in ('missing-risk-parent', 'not-personal', 'different-method'):
                with self.subTest(profile=profile, stale=state):
                    values = {**base, detail: authored}
                    if state == 'missing-risk-parent': del values[risks]
                    elif state == 'not-personal': values[personal] = IDS['risksPersonalDataNotUsingAUuid']
                    else: values[method] = IDS['risksPseudonymizationInsideAUuid']
                    output = render_question('src/questions/06-access-security.html.j2', values,
                                             output_profile=profile)
                    self.assertNotIn('Custodian opening.', output)
                    self.assertNotIn('Original key-handling item.', output)
                    self.assertNotIn('We use a specific pseudonymization method', output)

    def test_custom_opening_reasons_keep_single_and_multiple_bodies_owned(self):
        opened = path('accessCUuid', 'openImmediatelyQUuid')
        closed = path(opened, 'openImmediatelyNoAUuid')
        legal = path(closed, 'notOpenLegalReasonsQUuid')
        reasons = [('Business', 'commercial considerations unrelated to patents'),
                   ('Other', 'reasons other than publishing a paper')]
        bodies = {name: '<p>' + name + ' opening.</p><ul><li>' + name + ' original item.</li></ul>'
                  for name, _ in reasons}
        for selected in (('Business',), ('Other',), ('Business', 'Other')):
            for profile in ('submission', 'review'):
                for filled in (True, False):
                    with self.subTest(selected=selected, profile=profile, filled=filled):
                        values = {opened: IDS['openImmediatelyNoAUuid'], legal: IDS['notOpenLegalReasonsNoAUuid']}
                        for name in selected:
                            choice = path(closed, 'notOpen' + name + 'ReasonsQUuid')
                            values[choice] = IDS['notOpen' + name + 'ReasonsOtherAUuid']
                            values[path(choice, 'notOpen' + name + 'ReasonsOtherAUuid',
                                        'notOpen' + name + 'ReasonsOtherQUuid')] = bodies[name] if filled else ' \t\n\u3000'
                        output = render_question('src/questions/08-copyright-ipr.html.j2', values,
                                                 output_profile=profile)
                        soup = BeautifulSoup(output, 'html.parser')
                        root = soup.select_one('#q-copyright-ipr > .answer > .answer-detail')
                        self.assertIsNotNone(root)
                        records = root.find('ul', recursive=False).find_all('li', recursive=False) if len(selected) > 1 else [root]
                        self.assertEqual(len(selected), len(records))
                        for name, record in zip(selected, records):
                            phrase = dict(reasons)[name]
                            lead = record.find('div', recursive=False)
                            self.assertIsNotNone(lead)
                            self.assertIn(phrase, lead.p.get_text())
                            if filled:
                                self.assertEqual(['answer-lead'], lead.get('class'))
                                self.assertTrue(lead.p.get_text().endswith(':'))
                                self.assertEqual(name + ' opening.', lead.find_next_sibling().get_text())
                                self.assertEqual(name + ' original item.', lead.find_next_sibling().find_next_sibling().li.get_text())
                                self.assertEqual(1, output.count(bodies[name]))
                            else:
                                self.assertIsNone(lead.get('class'))
                                self.assertNotIn(':', lead.p.get_text())
                                if len(selected) == 1:
                                    self.assertEqual('The data cannot be made fully open because of ' + phrase + '.', lead.p.get_text())
                                self.assertNotIn(name + ' opening.', output)
                        probe = BlockProbe(); probe.feed(output)
                        self.assertEqual([], probe.errors)

    def test_reuse_permission_lead_and_detail_follow_their_own_dataset_label(self):
        parent = path('reusingCUuid', 'preexistingQUuid')
        permission = 'It is available under specific restrictions, which we will follow in our project'
        for profile in ('submission', 'review'):
            for named in (True, False):
                for value in ('rich', None, ' \t\n\u3000'):
                    with self.subTest(profile=profile, named=named, value=value):
                        values = {parent: IDS['preexistingYesAUuid']}
                        for kind in ('ref', 'nref'):
                            listing = path(parent, 'preexistingYesAUuid', kind + 'DataQUuid')
                            values[listing] = ['unused', 'record']
                            values[path(listing, 'unused', kind + 'DataUseQUuid')] = IDS[kind + 'DataUseNoAUuid']
                            used = path(listing, 'record', kind + 'DataUseQUuid')
                            values[used] = IDS[kind + 'DataUseYesAUuid']
                            choice = path(used, kind + 'DataUseYesAUuid', kind + 'DataConditionsQUuid')
                            values[choice] = IDS[kind + 'DataConditionsOtherAUuid']
                            if named: values[path(listing, 'record', kind + 'DataNameQUuid')] = kind + ' original name'
                            if value is not None:
                                values[path(choice, kind + 'DataConditionsOtherAUuid', kind + 'DataConditionsOtherQUuid')] = (
                                    '<p>' + kind + ' terms.</p><ul><li>' + kind + ' original condition.</li></ul>' if value == 'rich' else value)
                        output = render_question('src/questions/08-copyright-ipr.html.j2', values,
                                                 output_profile=profile)
                        soup = BeautifulSoup(output, 'html.parser')
                        lead = next(node for node in soup.select('div.answer-lead')
                                    if node.get_text() == 'The following conditions apply to the reference and non-reference datasets that we reuse:')
                        records = lead.find_next_sibling().find_all('li', recursive=False)
                        self.assertEqual(2, len(records))
                        for kind, record in zip(('ref', 'nref'), records):
                            label = record.find('div', recursive=False)
                            if named: self.assertEqual(kind + ' original name', label.get_text())
                            elif profile == 'submission':
                                neutral = label.select_one('.dataset-label')
                                self.assertEqual('reference' if kind == 'ref' else 'non-reference', neutral['data-list-kind'])
                                self.assertEqual('2', neutral['data-list-index'])
                            else: self.assertEqual('(no name given)', label.get_text())
                            fixed = label.find_next_sibling()
                            self.assertEqual('p', fixed.name)
                            self.assertEqual(permission + (':' if value == 'rich' else '.'), fixed.get_text())
                            detail = fixed.find_next_sibling()
                            if value == 'rich':
                                self.assertEqual(['answer-lead'], fixed.get('class'))
                                self.assertEqual(['answer-detail'], detail.get('class'))
                                self.assertEqual(kind + ' terms.', detail.p.get_text())
                                self.assertEqual(kind + ' original condition.', detail.li.get_text())
                                self.assertNotIn(('nref' if kind == 'ref' else 'ref') + ' terms.',
                                                 [node.get_text() for node in detail.find_all('p', recursive=False)])
                            else:
                                self.assertIsNone(fixed.get('class'))
                                self.assertIsNone(detail)
                        probe = BlockProbe(); probe.feed(output)
                        self.assertEqual([], probe.errors)

    def test_each_consent_detail_has_its_own_fixed_lead_without_flattening_answers(self):
        parent = path('creatingCUuid', 'collectPersonalQUuid')
        gdpr = path(parent, 'collectPersonalYesAUuid', 'cpersGdprQUuid')
        legal = path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprLegalBasisQUuid')
        consent = path(legal, 'cpersGdprLegalBasisAskAUuid')
        values = {parent: IDS['collectPersonalYesAUuid'], gdpr: IDS['cpersGdprExploreAUuid'],
                  legal: IDS['cpersGdprLegalBasisAskAUuid']}
        fields = [(path(consent, 'cpersExplainInformedQUuid'), 'Informed'),
                  (path(consent, 'cpersDescribeProcedureQUuid'), 'Procedure'),
                  (path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprPurposeQUuid'), 'Purpose')]
        for key, name in fields:
            values[key] = '<p>' + name + ' opening.</p><ul><li>' + name + ' original item.</li></ul>'
        for profile in ('submission', 'review'):
            output = render_question('src/questions/09-ethical-issues.html.j2', values, output_profile=profile)
            soup = BeautifulSoup(output, 'html.parser')
            leads = soup.select('.answer-detail > div.answer-lead')
            self.assertEqual(3, len(leads))
            for lead, (_, name) in zip(leads, fields):
                body = lead.find_next_sibling()
                self.assertEqual('div', body.name)
                self.assertEqual(name + ' opening.', body.p.get_text())
                self.assertEqual(name + ' original item.', body.li.get_text())
                self.assertEqual(1, output.count(values[next(k for k, v in fields if v == name)]))
            probe = BlockProbe(); probe.feed(output)
            self.assertEqual([], probe.errors)

    def test_qualified_reference_label_keeps_only_its_own_relation(self):
        data = path('preservingCUuid', 'producedDataQUuid')
        published = path(data, 'data', 'isPublishedDataQUuid')
        refs = path(published, 'isPublishedDataYesAUuid', 'publishedQReferencesQUuid')
        items = path(refs, 'publishedQReferencesYesAUuid', 'publishedQReferencesItemQUuid')
        values = {data: ['data'], published: IDS['isPublishedDataYesAUuid'],
                  refs: IDS['publishedQReferencesYesAUuid'], items: ['with-body', 'name-only'],
                  path(items, 'with-body', 'publishedQReferenceIdQUuid'): 'Original.csv',
                  path(items, 'with-body', 'publishedQReferenceRelQUuid'): 'Original relation. Keep item.',
                  path(items, 'name-only', 'publishedQReferenceIdQUuid'): 'Name-only.csv'}
        soup = BeautifulSoup(render_question('src/questions/10-share-restrictions.html.j2', values,
            output_profile='submission'), 'html.parser')
        lead = next(d for d in soup.select('div.answer-lead') if d.get_text() == 'References to other datasets:')
        records = lead.find_next_sibling().find_all('li', recursive=False)
        self.assertEqual('Original.csv', records[0].select_one('.answer-lead').get_text())
        self.assertEqual('Original relation. Keep item.', records[0].select_one('.answer-detail').get_text())
        self.assertFalse(records[1].select('.answer-lead'))
        self.assertEqual('Name-only.csv', records[1].get_text(strip=True))

    def test_archive_only_does_not_answer_security(self):
        replies = test_storage_sharing.StorageSharingTests().storage_replies()
        output = render_question('src/questions/06-access-security.html.j2', replies)
        self.assertIn('data-status="missing-output"', output)
        self.assertIn('href="#q-store-backup"', output)
        self.assertNotIn('will be archiving', output)
        self.assertNotIn('infrequently backed up', output)
        probe = BlockProbe(); probe.feed(output)
        self.assertEqual([], probe.errors)

    def test_security_content_and_reference_are_independent(self):
        replies = test_storage_sharing.StorageSharingTests().storage_replies()
        replies[path('processingCUuid', 'risksQUuid')] = IDS['risksExploreAUuid']
        replies[path('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksHttpsQUuid')] = IDS['risksHttpsYesAUuid']
        output = render_question('src/questions/06-access-security.html.j2', replies)
        self.assertIn('All project web services are accessible through HTTPS', output)
        self.assertNotIn('data-status="missing-output"', output)
        self.assertIn('href="#q-store-backup"', output)

    def test_empty_security_does_not_promise_archival_details(self):
        output = render_question('src/questions/06-access-security.html.j2', {})
        self.assertIn('data-status="missing-output"', output)
        self.assertNotIn('href="#q-store-backup"', output)

    def test_archive_branch_matrix_remains_in_q5_only(self):
        for frequency in ('archivedDuringReFrequentBackupsYesAUuid', 'archivedDuringReFrequentBackupsNoAUuid', None):
            for recovery in ('archivedDuringRelyYesAUuid', 'archivedDuringRelyNoAUuid', None):
                replies = test_storage_sharing.StorageSharingTests().storage_replies()
                root = path('preservingCUuid', 'archivedDuringQUuid', 'archivedDuringYesAUuid', 'archivedDuringReQUuid', 'archivedDuringReYesAUuid')
                key = path(root, 'archivedDuringReFrequentBackupsQUuid')
                if frequency: replies[key] = IDS[frequency]
                else: del replies[key]
                if recovery: replies[path(root, 'archivedDuringRelyQUuid')] = IDS[recovery]
                q5 = render_question('src/questions/05-store-backup.html.j2', replies)
                q6 = render_question('src/questions/06-access-security.html.j2', replies)
                self.assertEqual(bool(recovery), 'data-fact-id="archive-human-error-recovery"' in q5)
                self.assertEqual(bool(frequency), 'data-fact-id="archive-frequent-backup-need"' in q5)
                self.assertIn('data-status="missing-output"', q6)
                for output in (q5, q6):
                    probe = BlockProbe(); probe.feed(output)
                    self.assertEqual([], probe.errors)

    def test_storage_gaps_are_outside_joined_paragraph_runs(self):
        output = render_question('src/questions/05-store-backup.html.j2', {})
        self.assertEqual(2, output.count('<div class="reading-gap"><p class="data-gap"'))
        self.assertIn('data-fact-id="backup-arrangement" data-status="missing"', output)

    def test_archive_only_submission_omits_empty_workspace_policy_but_keeps_archive_facts(self):
        values = test_storage_sharing.StorageSharingTests().storage_replies()
        submission = BeautifulSoup(render_question('src/questions/05-store-backup.html.j2', values,
            output_profile='submission'), 'html.parser')
        self.assertFalse(submission.select('.workspace-policy, .data-gap, .reading-gap'))
        self.assertEqual('Archival during the project', submission.select_one('h4').get_text())
        for fact, text in (('during-project-archive', 'Data will be archived in cold storage during the project.'),
                           ('archive-medium', 'The archive will be stored on tape.'),
                           ('archive-remote-location', 'The archive will be stored at a remote location.')):
            self.assertEqual(text, submission.select_one('[data-fact-id="'+fact+'"]').get_text())
        review = BeautifulSoup(render_question('src/questions/05-store-backup.html.j2', values,
            output_profile='review'), 'html.parser')
        self.assertIsNotNone(review.select_one('.workspace-policy [data-fact-id="working-storage-arrangement"][data-status="missing"]'))

    def test_security_policy_lead_remains_attached_to_its_owned_list(self):
        policies = path('adminDetailsCUuid', 'policiesProceduresQUuid')
        values = {policies: ['policy'], path(policies, 'policy', 'policiesProceduresNameQUuid'): 'Access policy'}
        soup = BeautifulSoup(render_question('src/questions/06-access-security.html.j2', values,
            output_profile='submission'), 'html.parser')
        lead = soup.select_one('.answer > div.answer-lead')
        self.assertEqual('We will use the following policies and procedures:', lead.get_text())
        self.assertEqual('ul', lead.find_next_sibling().name)
        self.assertEqual('Access policy', lead.find_next_sibling().get_text(' ', strip=True))

    def test_long_restrictions_stay_in_a_separate_answer_block(self):
        from generate_storage_fixtures import storage_cases
        replies = {k: v['value'] for k, v in storage_cases('en')['storage-sharing'].items()}
        key = next(k for k in replies if k.endswith(IDS['licenseRestrictConditionsQUuid']))
        text = '<p>First supplied paragraph.</p><ul><li>Supplied item.</li></ul><p>Last supplied paragraph.</p>'
        replies[key] = text
        output = render_question('src/questions/10-share-restrictions.html.j2', replies)
        self.assertIn('<div class="answer-detail">' + text + '</div>', output)
        probe = BlockProbe(); probe.feed(output)
        self.assertEqual([], probe.errors)
        del replies[key]
        output = render_question('src/questions/10-share-restrictions.html.j2', replies)
        self.assertIn('data-fact-id="distribution-restriction-terms" data-status="missing"', output)
        self.assertIn('2027-06-01', output)

    def test_only_short_responsibilities_get_keep_together_class(self):
        root = path('adminDetailsCUuid', 'contributorsQUuid')
        replies = {root: ['person'], path(root, 'person', 'contributorNameQUuid'): 'A. Example',
                   path(root, 'person', 'contributorRoleQUuid'): [IDS['contributorRoleDataStewardAUuid'], IDS['contributorRoleCreatorOfDMPAUuid']]}
        output = render_question('src/questions/14-dm-responsible.html.j2', replies)
        self.assertIn('short-reading-unit', output)
        replies[path(root, 'person', 'contributorNameQUuid')] = 'Very long institutional group name ' * 30
        output = render_question('src/questions/14-dm-responsible.html.j2', replies)
        self.assertNotIn('short-reading-unit', output)
        # Each complete responsibility sentence names its actor. The full
        # text, including repeated long names, determines keep-together.
        self.assertEqual(2, output.count('Very long institutional group name ' * 30))
        self.assertIn('is responsible for managing data', output)
        self.assertIn('is responsible for implementing the data management plan', output)

    def test_short_distribution_is_bounded_but_free_terms_are_not_kept_whole(self):
        from generate_storage_fixtures import storage_cases
        replies = {k: v['value'] for k, v in storage_cases('en')['storage-sharing'].items()}
        output = render_question('src/questions/10-share-restrictions.html.j2', replies)
        self.assertEqual(2, output.count('class="distribution-section"'))
        self.assertEqual(1, output.count('class="distribution-reading-unit short-reading-unit"'))
        self.assertEqual(1, output.count('class="distribution-reading-unit"'))
        self.assertIn('Do not redistribute the preliminary files.', output)
