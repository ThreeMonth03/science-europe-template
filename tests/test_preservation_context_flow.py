import sys
import unittest
from test_preservation_coverage import AUTHORED, plain, render
from test_science_europe_contract import ROOT
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_pilot_fixtures import IDS, path


def runs(policy):
    result, pending = [], []
    for child in policy.find_all(recursive=False):
        if child.name == 'p':
            pending.append(child)
        else:
            if pending: result.append(pending)
            pending = []
    if pending: result.append(pending)
    return result


class PreservationContextFlowTests(unittest.TestCase):
    def test_context_and_arrangements_share_one_direct_owned_run(self):
        for case in ('preservation-complete', 'preservation-partial',
                     'preservation-custom', 'preservation-no-cold'):
            soup = render(plain(case))
            for dataset in soup.select('.dataset-section'):
                policy = dataset.select_one('.preservation-summary.dataset-policy')
                self.assertEqual([policy], dataset.select('.dataset-policy'))
                stage = dataset.select_one('[data-fact-id="preservation-data-stage"]')
                self.assertIs(stage.parent, policy)
                run = next(r for r in runs(policy) if stage in r)
                self.assertTrue(any('This dataset will' in p.get_text() for p in run))
            paper = soup.select_one('[data-fact-id="preservation-related-paper"]')
            self.assertIs(paper.parent, soup.select_one('.preservation-summary'))

    def test_authored_blocks_remain_byte_identical_and_interrupt_runs(self):
        replies = plain('preservation-custom')
        for name in ('producedDataDescriptionQUuid', 'notPublishedReasonOtherQUuid'):
            replies[next(p for p in replies if p.endswith(IDS[name]))] = AUTHORED
        soup = render(replies)
        for fact in ('preservation-dataset-description', 'nonpublication-reason'):
            node = soup.select_one(f'.answer-detail[data-fact-id="{fact}"]')
            self.assertEqual(AUTHORED, node.decode_contents())
            self.assertIsNone(node.find_parent('p'))
            self.assertIs(node.parent, node.find_parent(class_='preservation-summary'))
        self.assertFalse(soup.select('p p, p div, p ul, .dataset-policy .dataset-policy'))

    def test_missing_publication_breaks_stage_from_retention_without_inference(self):
        replies = plain()
        publication = next(p for p in replies if p.endswith(IDS['isPublishedDataQUuid']))
        replies[publication] = ''
        dataset = render(replies).select_one('.dataset-section')
        policy = dataset.select_one('.preservation-summary')
        gap = policy.select_one('[data-fact-id="preservation-publication-decision"]')
        self.assertEqual('missing', gap['data-status'])
        self.assertIn('reading-gap', gap.parent['class'])
        self.assertFalse(dataset.select('.repository-destinations'))
        stage_run = next(r for r in runs(policy) if any(p.get('data-fact-id') == 'preservation-data-stage' for p in r))
        self.assertFalse(any('will be published' in p.get_text() or 'Retention period' in p.get_text() for p in stage_run))
        self.assertIn('The metadata will be available', policy.get_text())

    def test_absent_context_does_not_suppress_arrangements_or_inject_empty_paragraph(self):
        replies = plain()
        for key in list(replies):
            if key.endswith(IDS['producedDataDescriptionQUuid']) or IDS['producedDataStageQUuid'] in key:
                replies.pop(key)
        soup = render(replies)
        self.assertFalse(soup.select('[data-fact-id="preservation-data-stage"], [data-fact-id="preservation-related-paper"]'))
        for policy in soup.select('.preservation-summary'):
            self.assertIn('This dataset will', policy.get_text())
            self.assertTrue(all(p.get_text(strip=True) for p in policy.find_all('p', recursive=False)))

    def test_project_archive_and_repository_contacts_stay_outside_dataset_policy(self):
        soup = render(plain())
        for selector in ('.post-project-archive', '.repository-destinations', '.preservation-resources'):
            for node in soup.select(selector):
                self.assertIsNone(node.find_parent(class_='preservation-summary'))
        empty = render({})
        self.assertTrue(empty.select('[data-status="missing-output"]'))
        self.assertFalse(empty.select('.preservation-summary'))
