import unittest
from test_answer_retention import IDS, path
from test_science_europe_contract import render_question
from test_structure_bindings import BlockProbe


class StorageSharingTests(unittest.TestCase):
    def storage_replies(self):
        archive = path('preservingCUuid', 'archivedDuringQUuid')
        root = path(archive, 'archivedDuringYesAUuid')
        change = path(root, 'archivedDuringReQUuid')
        return {archive: IDS['archivedDuringYesAUuid'],
                path(root, 'archiveRemoteQUuid'): IDS['archiveRemoteYesAUuid'],
                path(root, 'archiveMediumQUuid'): IDS['archiveMediumTapeAUuid'],
                change: IDS['archivedDuringReYesAUuid'],
                path(change, 'archivedDuringReYesAUuid', 'archivedDuringReFrequentBackupsQUuid'): IDS['archivedDuringReFrequentBackupsYesAUuid']}

    def test_archive_facts_do_not_require_a_shared_workspace_answer(self):
        output = render_question('src/questions/05-store-backup.html.j2', self.storage_replies())
        for value in ('The archive will be stored on tape.', 'The archive will be stored at a remote location.', 'Frequent backups are required because the archived data changes frequently.'):
            self.assertIn(value, output)
        self.assertNotIn('daily', output.lower())
        self.assertIn('data-fact-id="backup-frequency" data-status="partial"', output)

    def test_missing_archive_detail_does_not_erase_medium(self):
        replies = self.storage_replies()
        for key in list(replies):
            if key.endswith(IDS['archiveRemoteQUuid']) or key.endswith(IDS['archivedDuringReFrequentBackupsQUuid']): del replies[key]
        output = render_question('src/questions/05-store-backup.html.j2', replies)
        self.assertIn('The archive will be stored on tape.', output)
        self.assertNotIn('The archive will be stored at a remote location.', output)
        self.assertIn('data-fact-id="backup-frequency" data-status="unmapped"', output)

    def test_no_frequent_backups_does_not_mean_no_backups(self):
        replies = self.storage_replies()
        for key in replies:
            if key.endswith(IDS['archivedDuringReFrequentBackupsQUuid']): replies[key] = IDS['archivedDuringReFrequentBackupsNoAUuid']
        output = render_question('src/questions/05-store-backup.html.j2', replies)
        self.assertIn('Frequent backups are not required because the archived data changes infrequently.', output)
        self.assertNotIn('No backups are required', output)

    def test_q10_license_is_retained_without_repository_or_access(self):
        datasets = path('preservingCUuid', 'producedDataQUuid')
        pub = path(datasets, 'd1', 'isPublishedDataQUuid')
        dist = path(pub, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
        licences = path(dist, 'r1', 'publishedDataLicensesQUuid')
        replies = {datasets: ['d1'], pub: IDS['isPublishedDataYesAUuid'], dist: ['r1'], licences: ['l1'],
                   path(licences, 'l1', 'publishedDataLicenseStartQUuid'): '2027-12-31',
                   path(licences, 'l1', 'publishedDataLicenseQUuid'): IDS['publishedDataLicenseCCBYAUuid']}
        output = render_question('src/questions/10-share-restrictions.html.j2', replies)
        self.assertIn('2027-12-31', output)
        self.assertIn('CC-BY', output)
        self.assertIn('data-fact-id="distribution-access" data-status="missing"', output)
        probe = BlockProbe(); probe.feed(output)
        self.assertEqual([], probe.errors)

    def test_template_owned_sharing_lists_are_shallow(self):
        from generate_retention_fixtures import retention_cases
        replies = {key: value['value'] for key, value in retention_cases('en')['structured'].items()}
        for q in ('10-share-restrictions', '11-data-preservation', '12-access-data', '13-persistent-identifier'):
            output = render_question(f'src/questions/{q}.html.j2', replies)
            self.assertIn('class="dataset-section"', output, q)
            probe = BlockProbe(); probe.feed(output)
            self.assertEqual([], probe.errors, q)
            class DepthProbe(BlockProbe):
                depth = 0
                def handle_starttag(self, tag, attrs):
                    super().handle_starttag(tag, attrs)
                    self.depth = max(self.depth, sum(t in ('ul', 'ol') for t in self.stack))
            depth = DepthProbe(); depth.feed(output)
            self.assertLessEqual(depth.depth, 1, q)

    def test_independent_distribution_terms_survive_partial_answers(self):
        from generate_storage_fixtures import storage_cases
        replies = {key: value['value'] for key, value in storage_cases('en')['storage-sharing-partial'].items()}
        output = render_question('src/questions/10-share-restrictions.html.j2', replies)
        for value in ('2027-12-31', '2027-06-01', 'Do not redistribute the preliminary files.', 'https://example.org/coast/review-terms'):
            self.assertIn(value, output)
        self.assertEqual(2, output.count('class="distribution-section"'))
        probe = BlockProbe(); probe.feed(output)
        self.assertEqual([], probe.errors)

    def test_pid_yes_survives_missing_assigner(self):
        datasets = path('preservingCUuid', 'producedDataQUuid')
        pub = path(datasets, 'd1', 'isPublishedDataQUuid')
        dist = path(pub, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
        replies = {datasets: ['d1'], pub: IDS['isPublishedDataYesAUuid'], dist: ['r1'],
                   path(dist, 'r1', 'publishedDataIdentifierQUuid'): IDS['publishedDataIdentifierYesAUuid']}
        self.assertIn('Persistent identifiers will be assigned.', render_question('src/questions/13-persistent-identifier.html.j2', replies))


if __name__ == '__main__': unittest.main()
