"""Reachable Q7 safeguards must not disappear behind an answered legal basis."""
import re
import unittest
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, render_question

QUESTION = 'src/questions/07-personal-data.html.j2'
UUIDS = dict(re.findall(r'set\s+(\w+)\s*=\s*"([^"]+)"', (ROOT/'src/uuids.j2').read_text()))


def case(collect='collectPersonalYesAUuid', explore=True, legal=True, safeguards=None):
    parent = '.'.join(UUIDS[k] for k in ['creatingCUuid', 'collectPersonalQUuid'])
    gdpr = parent + '.' + UUIDS['collectPersonalYesAUuid'] + '.' + UUIDS['cpersGdprQUuid']
    prefix = gdpr + '.' + UUIDS['cpersGdprExploreAUuid']
    replies = {parent: UUIDS[collect]}
    if explore: replies[gdpr] = UUIDS['cpersGdprExploreAUuid']
    if legal: replies[prefix+'.'+UUIDS['cpersGdprLegalBasisQUuid']] = UUIDS['cpersGdprLegalBasisPublicAUuid']
    if safeguards: replies[prefix+'.'+UUIDS['cpersGdprSafeguardsQUuid']] = safeguards
    return replies


class PersonalDataGapTests(unittest.TestCase):
    def gap(self, replies):
        return BeautifulSoup(render_question(QUESTION, replies), 'html.parser').select('[data-fact-id="personal-data-safeguards"][data-status="missing"]')

    def test_answered_legal_basis_does_not_hide_missing_safeguards(self):
        replies = case()
        self.assertEqual(1, len(self.gap(replies)))
        self.assertIn('based on public interest.', render_question(QUESTION, replies))

    def test_missing_legal_basis_still_prompts_for_reachable_safeguards(self):
        self.assertEqual(1, len(self.gap(case(legal=False))))

    def test_inactive_parents_do_not_report_unreachable_safeguards(self):
        for replies in [{}, case(collect='collectPersonalNoAUuid'), case(explore=False)]:
            self.assertEqual([], self.gap(replies))

    def test_answered_safeguards_are_not_marked_unanswered(self):
        self.assertEqual([], self.gap(case(safeguards=UUIDS['cpersGdprSafeguardsAUuid'])))
