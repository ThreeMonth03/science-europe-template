import unittest
from bs4 import BeautifulSoup

from test_answer_retention import IDS, path
from test_science_europe_contract import render_question
import test_storage_sharing
from test_structure_bindings import BlockProbe


class NarrativePaginationTests(unittest.TestCase):
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
        # A contributor label is emitted once; the length still prevents a
        # keep-together class without duplicating the user's authored name.
        self.assertEqual(1, output.count('Very long institutional group name ' * 30))
        self.assertIn('Data stewardship:', output)
        self.assertIn('DMP implementation:', output)

    def test_short_distribution_is_bounded_but_free_terms_are_not_kept_whole(self):
        from generate_storage_fixtures import storage_cases
        replies = {k: v['value'] for k, v in storage_cases('en')['storage-sharing'].items()}
        output = render_question('src/questions/10-share-restrictions.html.j2', replies)
        self.assertEqual(2, output.count('class="distribution-section"'))
        self.assertEqual(1, output.count('class="distribution-reading-unit short-reading-unit"'))
        self.assertEqual(1, output.count('class="distribution-reading-unit"'))
        self.assertIn('Do not redistribute the preliminary files.', output)
