import unittest

from test_answer_retention import IDS, path
from test_science_europe_contract import render_question
import test_storage_sharing
from test_structure_bindings import BlockProbe


class NarrativePaginationTests(unittest.TestCase):
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
        replies[path('processingCUuid', 'risksQUuid', 'risksExploreAUuid', 'risksHttpsQUuid')] = IDS['risksHttpsYesAUuid']
        output = render_question('src/questions/06-access-security.html.j2', replies)
        self.assertIn('All project web services are accessible via secure HTTP', output)
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
        self.assertEqual(2, output.count('Very long institutional group name ' * 30))
