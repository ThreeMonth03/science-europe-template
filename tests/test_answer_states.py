"""Missing answers must not become claims; repository choices have local scope."""
import itertools
import sys
import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_pilot_fixtures import IDS, path

Q5 = 'src/questions/05-store-backup.html.j2'
Q11 = 'src/questions/11-data-preservation.html.j2'
LEAD = 'The fields mapped by this template are insufficient to establish the following operational details:'
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


def support_replies(choices=(None,), repository='Special', publication='Yes'):
    data = path('preservingCUuid', 'producedDataQUuid')
    pub = path(data, 'dataset-a', 'isPublishedDataQUuid')
    dist = path(pub, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
    replies = {data: ['dataset-a'], dist: [f'distro-{i}' for i in range(len(choices))]}
    if publication: replies[pub] = IDS[f'isPublishedData{publication}AUuid']
    for i, choice in enumerate(choices):
        kind = path(dist, f'distro-{i}', 'publishedDataRepositoryKindQUuid')
        if repository: replies[kind] = IDS[f'publishedDataRepository{repository}AUuid']
        prefix = path(kind, 'publishedDataRepositorySpecialAUuid')
        if choice is not None:
            replies[path(prefix, 'specialRepoLongTermSupportQUuid')] = IDS.get(f'specialRepoLongTermSupport{choice}AUuid', choice)
        replies[path(prefix, 'specialRepoServiceLevelQUuid')] = IDS['specialRepoServiceLevelAdvancedAUuid']
    return replies


class AnswerStateTests(unittest.TestCase):
    def test_q5_neutral_mapping_limit_does_not_imply_supplied_answers(self):
        for replies in storage_matrix():
            with self.subTest(replies=replies):
                soup = BeautifulSoup(render_question(Q5, replies), 'html.parser')
                self.assertEqual(LEAD, soup.select_one('.storage-detail-limits > p').get_text())
                self.assertEqual(['unmapped', 'unmapped'], [n['data-status'] for n in soup.select('.storage-detail-limits [data-fact-id]')])
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
