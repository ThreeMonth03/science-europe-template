import itertools
import sys
import unittest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from test_science_europe_contract import ROOT, render_question
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_sharing_fixtures import sharing_cases
from generate_storage_fixtures import storage_cases
from generate_pilot_fixtures import IDS, path
from check_repository_profiles import preservation_schema
from check_publication_reading import DATASETS, publication_replies

Q10 = 'src/questions/10-share-restrictions.html.j2'
Q11 = 'src/questions/11-data-preservation.html.j2'
AUTHORED = '<p>Keep Access-2027-12-31.csv!</p><p>Second paragraph.</p><ul><li>First.</li><li>Second.</li></ul>'


def matrix_cases():
    base = {p: v['value'] for p, v in storage_cases('en')['storage-sharing'].items()}
    prefix = next(p for p in base if p.endswith(IDS['licenseRestrictConditionsQUuid'])).rsplit('.', 1)[0]
    for access, metadata, has_custom in itertools.product(
        [None, 'licenseRestrictAccessRequestAUuid', 'licenseRestrictAccessCommitteeAUuid', 'licenseRestrictAccessAnotherAUuid'],
        [None, 'licenseRestrictMetadataYesAUuid', 'licenseRestrictMetadataNoAUuid'], [False, True]):
        replies = dict(base)
        ap = path(prefix, 'licenseRestrictAccessQUuid'); mp = path(prefix, 'licenseRestrictMetadataQUuid')
        replies.pop(ap, None); replies.pop(mp, None)
        if access: replies[ap] = IDS[access]
        if metadata: replies[mp] = IDS[metadata]
        if has_custom: replies[path(ap, 'licenseRestrictAccessAnotherAUuid', 'licenseRestrictAccessAnotherQUuid')] = AUTHORED
        yield replies, access, metadata, has_custom


class SharingPreservationTests(unittest.TestCase):
    def test_collaboration_fact_survives_missing_agreement_without_inference(self):
        parent = path('creatingCUuid', 'collabQUuid')
        agreement = path(parent, 'collabYesAUuid', 'collabAgreeQUuid')
        fact = 'This project involves collaboration between different groups and institutions.'
        for choice, detail, profile in itertools.product(('Yes', 'No', None, 'unknown'),
                ('Yes', 'No', None, 'unknown'), ('review', 'submission')):
            replies = {}
            if choice is not None: replies[parent] = IDS.get('collab'+choice+'AUuid', choice)
            if detail is not None: replies[agreement] = IDS.get('collabAgree'+detail+'AUuid', detail)
            with self.subTest(choice=choice, detail=detail, profile=profile):
                soup = BeautifulSoup(render_question(Q10, replies, output_profile=profile), 'html.parser')
                text = soup.get_text(' ', strip=True)
                self.assertEqual(choice == 'Yes', fact in text)
                self.assertEqual(choice == 'Yes' and detail == 'Yes', 'A collaboration agreement is in place' in text)
                self.assertEqual(choice == 'Yes' and detail == 'No', 'However, no collaboration agreement is in place' in text)
                if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))

    def test_embargo_does_not_infer_a_legal_reason(self):
        opened = path('accessCUuid', 'openImmediatelyQUuid')
        legal = path(opened, 'openImmediatelyNoAUuid', 'notOpenLegalReasonsQUuid')
        embargo = path('accessCUuid', 'limitedEmbargoQUuid')
        for reason, profile in itertools.product(('Yes', 'No', None, 'unknown'), ('review', 'submission')):
            replies = {opened: IDS['openImmediatelyNoAUuid'], embargo: IDS['limitedEmbargoYesAUuid'],
                path(embargo, 'limitedEmbargoYesAUuid', 'limitedEmbargoPeriodQUuid'): '180 days'}
            if reason is not None: replies[legal] = IDS.get('notOpenLegalReasons'+reason+'AUuid', reason)
            with self.subTest(reason=reason, profile=profile):
                text = BeautifulSoup(render_question(Q10, replies, output_profile=profile), 'html.parser').get_text(' ', strip=True)
                self.assertNotIn('Data cannot be completely open due to legal reasons.', text)
                self.assertIn('Data not subject to legal restrictions will be released openly after a fixed time period.', text)
                self.assertIn('The embargo period will be 180 days.', text)
                q8 = BeautifulSoup(render_question('src/questions/08-copyright-ipr.html.j2', replies,
                    output_profile=profile), 'html.parser').get_text(' ', strip=True)
                self.assertEqual(reason == 'Yes', 'The data cannot be made fully open because of legal restrictions.' in q8)

    def test_publication_children_require_yes_without_hiding_identifier_siblings(self):
        # Stored Yes follow-ups are historical, not independent answers, when
        # their publication parent is missing, unknown or explicitly No.
        for publication, profile in itertools.product(['Yes', 'No', None, 'obsolete'], ['review', 'submission']):
            replies = publication_replies(publication, 'Soon', 'Yes')
            pub = path(DATASETS, 'dataset-a', 'isPublishedDataQUuid', 'isPublishedDataYesAUuid')
            refs = path(pub, 'publishedQReferencesQUuid')
            items = path(refs, 'publishedQReferencesYesAUuid', 'publishedQReferencesItemQUuid')
            identifiers = path(DATASETS, 'dataset-a', 'producedDataIdentifiersQUuid')
            replies.update({refs: IDS['publishedQReferencesYesAUuid'], items: ['reference-a'],
                path(items, 'reference-a', 'publishedQReferenceIdQUuid'): 'Reference-01',
                path(items, 'reference-a', 'publishedQReferenceRelQUuid'): 'Derived from reference data.',
                identifiers: ['identifier-a'],
                path(identifiers, 'identifier-a', 'dataIdentifierTypeQUuid'): IDS['dataIdentifierTypeDoiAUuid'],
                path(identifiers, 'identifier-a', 'dataIdentifierIdentifierQUuid'): '10.1234/retained'})
            with self.subTest(publication=publication, profile=profile):
                soup = BeautifulSoup(render_question(Q10, replies, output_profile=profile), 'html.parser')
                dataset = soup.select_one('.dataset-section[data-item-id="dataset-a"]')
                text = dataset.get_text()
                self.assertEqual(publication == 'Yes', 'published as soon as possible' in text)
                self.assertEqual(publication == 'Yes', 'at least one data catalogue' in text)
                self.assertEqual(publication == 'Yes', 'Reference-01' in text)
                self.assertEqual(publication == 'Yes', 'Derived from reference data.' in text)
                self.assertEqual(publication == 'No', 'This dataset will not be published.' in text)
                self.assertEqual('https://doi.org/10.1234/retained', dataset.select_one('a')['href'])
                if publication == 'Yes':
                    self.assertEqual('Derived from reference data.', dataset.select_one('.answer-detail').get_text())
                if profile == 'submission':
                    self.assertFalse(soup.select('.data-gap, .data-review'))

    def test_identifier_siblings_survive_unpublished_or_missing_decision(self):
        for publication, profile in itertools.product(['Yes', 'No', None, 'obsolete'], ['review', 'submission']):
            replies = publication_replies(publication, None, None, name=None)
            listing = path(DATASETS, 'dataset-a', 'producedDataIdentifiersQUuid')
            ark = path(listing, 'type-only', 'dataIdentifierTypeQUuid')
            value = path(listing, 'with-value', 'dataIdentifierIdentifierQUuid')
            distribution = path(DATASETS, 'dataset-a', 'isPublishedDataQUuid', 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
            replies.update({listing: ['type-only', 'with-value'], ark: IDS['dataIdentifierTypeArkAUuid'],
                path(listing, 'type-only', 'dataIdentifierIdentifierQUuid'): ' \n ',
                path(ark, 'dataIdentifierTypeOtherAUuid', 'dataIdentifierTypeOtherTypeQUuid'): 'Stale custom type',
                path(listing, 'with-value', 'dataIdentifierTypeQUuid'): IDS['dataIdentifierTypeDoiAUuid'],
                value: '10.1234/retained',
                path(listing, 'deleted', 'dataIdentifierIdentifierQUuid'): 'Stale deleted identifier',
                distribution: ['distro-a'],
                path(distribution, 'distro-a', 'publishedDistroShareQUuid'): IDS['publishedDistroShareOpenAUuid']})
            with self.subTest(publication=publication, profile=profile):
                soup = BeautifulSoup(render_question(Q10, replies, output_profile=profile), 'html.parser')
                dataset = soup.select_one('.dataset-section[data-item-id="dataset-a"]')
                entries = dataset.select(':scope > ul > li')
                self.assertEqual(['ARK', 'DOI: 10.1234/retained'], [entry.get_text() for entry in entries])
                self.assertFalse(entries[0].select('strong, a, .data-gap'))
                self.assertEqual('https://doi.org/10.1234/retained', entries[1].a['href'])
                self.assertIn('Identifier information for this dataset:', dataset.get_text())
                self.assertNotIn('has the following identifiers', dataset.get_text())
                self.assertNotIn('Stale', dataset.get_text())
                self.assertEqual(publication == 'Yes', bool(dataset.select('.distribution-section')))
                if profile == 'submission':
                    self.assertTrue(dataset.select_one('.dataset-label[data-list-index="1"]'))
                    self.assertFalse(soup.select('.data-gap, .data-review'))
            replies[DATASETS] = []
            soup = BeautifulSoup(render_question(Q10, replies, output_profile=profile), 'html.parser')
            self.assertFalse(soup.select('.dataset-section'))
            self.assertNotIn('10.1234/retained', soup.get_text())

    def test_authenticated_access_does_not_invent_sharing_agreement(self):
        parent = path('accessCUuid', 'openImmediatelyQUuid')
        reason = path(parent, 'openImmediatelyNoAUuid', 'notOpenLegalReasonsQUuid')
        auth = path(reason, 'notOpenLegalReasonsYesAUuid', 'legalReasonsAuthenticatedQUuid')
        who = path(auth, 'legalReasonsAuthenticatedYesAUuid', 'legalReasonsAuthorizeQUuid')
        base = {parent: IDS['openImmediatelyNoAUuid'], reason: IDS['notOpenLegalReasonsYesAUuid'],
                auth: IDS['legalReasonsAuthenticatedYesAUuid']}
        choices = {'Member': 'People can apply to one of the project members.',
                   'NewCommittee': 'People can apply to the data access committee that we will set up.',
                   'OldCommittee': 'People can apply to the following data access committee:',
                   'Other': 'For the authorization of potential users, we will make special arrangements:'}
        for choice, profile in itertools.product([*choices, None], ['review', 'submission']):
            replies = dict(base)
            for detail in ('OldCommittee', 'Other'):
                replies[path(who, 'legalReasonsAuthorize'+detail+'AUuid', 'legalReasonsAuthorize'+detail+'QUuid')] = AUTHORED
            if choice:
                replies[who] = IDS['legalReasonsAuthorize'+choice+'AUuid']
            soup = BeautifulSoup(render_question(Q10, replies, output_profile=profile), 'html.parser')
            lead = soup.select_one('[data-fact-id="authenticated-access"]')
            text = ' '.join(lead.get_text().split())
            self.assertEqual('We will permit authenticated access to the data.' +
                             (' ' + choices[choice] if choice else ''), text)
            self.assertNotIn('sharing agreement', text)
            detail = soup.select_one('.authorization-details')
            self.assertEqual(choice in ('OldCommittee', 'Other'), bool(detail))
            if detail:
                self.assertEqual(AUTHORED, detail.decode_contents())
            self.assertFalse(soup.select('p p, p div, p ul, p table'))
        for key in (parent, reason, auth):
            replies = {**base, who: IDS['legalReasonsAuthorizeOtherAUuid'],
                       path(who, 'legalReasonsAuthorizeOtherAUuid', 'legalReasonsAuthorizeOtherQUuid'): AUTHORED}
            del replies[key]
            soup = BeautifulSoup(render_question(Q10, replies, output_profile='submission'), 'html.parser')
            self.assertFalse(soup.select('[data-fact-id="authenticated-access"], .authorization-details'))
            self.assertNotIn('Access-2027-12-31.csv', soup.get_text())

    def test_date_hint_is_scoped_and_does_not_rewrite_free_text(self):
        env = Environment(loader=FileSystemLoader(ROOT), extensions=['jinja2.ext.do'])
        env.filters['markdown'] = lambda v: v
        render = env.from_string("{% import 'src/macros.html.j2' as m %}{{ m.calendarDate(value) }}").render
        for value in ('2027-12-31', '2028-02-29'):
            soup = BeautifulSoup(render(value=value), 'html.parser')
            self.assertEqual(value, soup.select_one('.date-value')['data-iso-date'])
            self.assertEqual(value, soup.get_text())
        for value in ('Access-2027-12-31.csv', '2027-1-1', '2027-12-31 or later', '２０２７-１２-３１', '<b>planned</b>'):
            soup = BeautifulSoup(render(value=value), 'html.parser')
            self.assertFalse(soup.select('.date-value, b'))
            self.assertEqual(value, soup.get_text())

    def test_process_matrix_distinguishes_no_unknown_and_authored_details(self):
        for replies, access, metadata, has_custom in matrix_cases():
            soup = BeautifulSoup(render_question(Q10, replies), 'html.parser')
            proc = soup.select_one('.restriction-process')
            self.assertEqual(access is None, bool(proc.select('[data-fact-id="restriction-access-process"]')))
            selected = access == 'licenseRestrictAccessAnotherAUuid'
            self.assertEqual(selected and not has_custom, bool(proc.select('[data-fact-id="restriction-custom-process"][data-status="missing"]')))
            self.assertEqual(metadata is None, bool(proc.select('[data-fact-id="restriction-metadata-publication"]')))
            self.assertEqual(metadata == 'licenseRestrictMetadataNoAUuid', 'will not be published' in proc.get_text())
            self.assertEqual(selected and has_custom, 'Access-2027-12-31.csv' in proc.get_text())
            detail = proc.select_one('.answer-detail')
            if selected and has_custom: self.assertEqual(AUTHORED, detail.decode_contents())
            self.assertFalse(soup.select('p p, p div, p ul'))

    def test_restricted_summary_contains_date_but_not_free_conditions(self):
        replies = {p: v['value'] for p,v in storage_cases('en')['storage-sharing'].items()}
        soup = BeautifulSoup(render_question(Q10, replies), 'html.parser')
        entry = soup.select_one('.license-entry:not(.joined-policy)')
        self.assertEqual(2, len(entry.select('.license-summary > p')))
        self.assertIn('2027-06-01', entry.select_one('.license-summary').get_text())
        self.assertFalse(entry.select('.license-summary .answer-detail, .joined-policy'))

    def test_preservation_gaps_break_runs_without_hiding_metadata(self):
        replies = {p: v['value'] for p,v in sharing_cases('en')['sharing-missing'].items()}
        soup = BeautifulSoup(render_question(Q11, replies, km=preservation_schema()), 'html.parser')
        summary = soup.select_one('.preservation-summary')
        self.assertEqual(2, len(summary.select('.reading-gap')))
        self.assertFalse(summary.select(':scope > p.data-gap'))
        self.assertIn('The metadata will be available even when the data no longer exists.', summary.get_text())

    def test_preservation_cost_free_answer_has_separate_label_and_blocks(self):
        replies = {p: v['value'] for p,v in sharing_cases('en')['sharing-custom'].items()}
        key = next(p for p in replies if p.endswith(IDS['repoChargesHowPayOtherQUuid']))
        replies[key] = AUTHORED
        soup = BeautifulSoup(render_question(Q11, replies), 'html.parser')
        resources = soup.select_one('.preservation-resources')
        self.assertEqual(AUTHORED, resources.select_one('.answer-detail').decode_contents())
        self.assertEqual('Other arrangements for paying repository costs:', resources.select_one('.answer-lead').get_text())
        self.assertFalse(soup.select('p p, p div, p ul'))
        fallback = 'Other arrangements are planned for paying repository service fees.'
        for profile, detail in itertools.product(('review', 'submission'), (None, '', ' \t\n\u3000')):
            partial = dict(replies)
            if detail is None: partial.pop(key)
            else: partial[key] = detail
            rendered = BeautifulSoup(render_question(Q11, partial, output_profile=profile), 'html.parser')
            self.assertIn(fallback, rendered.get_text(' ', strip=True))
            self.assertNotIn('Other arrangements for paying repository costs:', rendered.get_text(' ', strip=True))
            self.assertFalse(rendered.select('p p, p div, p ul'))
