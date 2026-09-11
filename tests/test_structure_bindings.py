"""Regression probes for structural and KM-binding defects, not legal assessment."""

import sys
import unittest
from html.parser import HTMLParser

from jinja2 import Environment, nodes
from test_answer_retention import ROOT, IDS, path
from test_science_europe_contract import render_question

sys.path.insert(0, str(ROOT / 'scripts'))
from generate_retention_fixtures import retention_cases


class BlockProbe(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if 'p' in self.stack and tag in ('p', 'ul', 'ol', 'div', 'table'):
            self.errors.append(f'{tag} inside p')
        if self.stack and self.stack[-1] in ('ul', 'ol') and tag != 'li':
            self.errors.append(f'{tag} directly inside list')
        if tag not in ('br', 'hr', 'img', 'meta', 'link', 'input', 'col', 'wbr'):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]
        else:
            self.errors.append(f'unmatched closing {tag}')


class StructureBindingTests(unittest.TestCase):
    def test_legacy_duration_is_flagged_without_inventing_a_unit(self):
        cases = retention_cases('en')
        for case in ('representative', 'structured'):
            replies = {key: value['value'] for key, value in cases[case].items()}
            output = render_question('src/questions/11-data-preservation.html.j2', replies)
            if case == 'representative':
                self.assertIn('Please specify a time unit', output)
                self.assertIn('Please check how the prepaid', output)
                self.assertNotIn('10 years', output)
            else:
                self.assertIn('10 years', output)
                self.assertIn('We have budgeted for the costs', output)
                self.assertNotIn('needs-review', output)

    def test_explicit_no_ethical_approval_is_retained(self):
        projects = path('adminDetailsCUuid', 'projectsQUuid')
        replies = {projects: ['p1'], path(projects, 'p1', 'projEthicalApprovalQUuid'): IDS['projEthicalApprovalNoAUuid']}
        output = render_question('src/questions/09-ethical-issues.html.j2', replies)
        self.assertIn('According to the questionnaire, this project does not require ethical approval.', output)
        self.assertNotIn('This project requires ethical approval.', output)

    def test_question_bindings_are_defined(self):
        env = Environment(extensions=['jinja2.ext.do'])
        for file in sorted((ROOT / 'src/questions').glob('*.html.j2')):
            for node in env.parse(file.read_text()).find_all(nodes.Getattr):
                if isinstance(node.node, nodes.Name) and node.node.name == 'uuids':
                    self.assertTrue(node.attr in IDS, f'{file.name}: {node.attr}')

    def test_representative_target_blocks_are_valid(self):
        replies = {key: value['value'] for key, value in retention_cases('en')['representative'].items()}
        for question in ('08-copyright-ipr', '09-ethical-issues', '11-data-preservation', '13-persistent-identifier'):
            with self.subTest(question=question):
                probe = BlockProbe()
                probe.feed(render_question(f'src/questions/{question}.html.j2', replies))
                self.assertEqual([], probe.errors)
                self.assertEqual([], probe.stack)

    def test_repository_costs_survive_absent_dataset_list(self):
        replies = {path('preservingCUuid', 'repoChargesQUuid'): IDS['repoChargesNoAUuid']}
        output = render_question('src/questions/11-data-preservation.html.j2', replies)
        self.assertIn('None of the used repositories charge', output)

    def test_contract_legal_basis_binding_is_not_misspelled(self):
        personal = path('creatingCUuid', 'collectPersonalQUuid')
        gdpr = path(personal, 'collectPersonalYesAUuid', 'cpersGdprQUuid')
        basis = path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprLegalBasisQUuid')
        replies = {personal: IDS['collectPersonalYesAUuid'], gdpr: IDS['cpersGdprExploreAUuid'],
                   basis: IDS['cpersGdprLegalBasisOtherAUuid'],
                   path(basis, 'cpersGdprLegalBasisOtherAUuid', 'cpersGdprLegalBasisOtherWhichQUuid'): IDS['cpersGdprLegalBasisOtherWhichContractAUuid']}
        output = render_question('src/questions/07-personal-data.html.j2', replies)
        self.assertIn('fulfil contract', output)

    def test_institutional_identifier_assigner_is_not_lost(self):
        datasets = path('preservingCUuid', 'producedDataQUuid')
        publication = path(datasets, 'd1', 'isPublishedDataQUuid')
        distributions = path(publication, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
        identifier = path(distributions, 'r1', 'publishedDataIdentifierQUuid')
        replies = {datasets: ['d1'], publication: IDS['isPublishedDataYesAUuid'], distributions: ['r1'],
                   identifier: IDS['publishedDataIdentifierYesAUuid'],
                   path(identifier, 'publishedDataIdentifierYesAUuid', 'publishedDataIdentifierAssignsQUuid'): IDS['publishedDataIdentifierAssignsInstitDataStewardAUuid']}
        self.assertIn('An institutional data steward', render_question('src/questions/13-persistent-identifier.html.j2', replies))

    def test_ethical_status_does_not_require_a_case_number(self):
        projects = path('adminDetailsCUuid', 'projectsQUuid')
        approval = path(projects, 'p1', 'projEthicalApprovalQUuid')
        records = path(approval, 'projEthicalApprovalYesAUuid', 'projEthicalApprovalAuthQUuid')
        replies = {projects: ['p1'], approval: IDS['projEthicalApprovalYesAUuid'], records: ['a1', 'a2'],
                   path(records, 'a1', 'projEthicalApprovalAuthStatusQUuid'): IDS['projEthicalApprovalAuthStatusPlannedAUuid'],
                   path(records, 'a2', 'projEthicalApprovalAuthCaseQUuid'): 'CASE-2026-B'}
        output = render_question('src/questions/09-ethical-issues.html.j2', replies)
        self.assertIn('Approval is planned.', output)
        self.assertIn('CASE-2026-B', output)
        self.assertEqual(1, output.count('class="ethical-project"'))
        self.assertIn('Approval status has not been provided.', output)


if __name__ == '__main__':
    unittest.main()
