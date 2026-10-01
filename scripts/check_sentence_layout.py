"""Focused non-reuse prose and explicit list-label checks, for either language."""
import itertools
import re

from bs4 import BeautifulSoup
from current_support import IDS, environment, path

AUTHORED = '<p>Keep <strong>Original.csv</strong>; do not change this punctuation: .,</p><ul><li>Reason <strong>A</strong>.</li></ul>'
DECISION = {'en': 'This dataset was considered but will not be re-used.',
            'zh-Hant': '本計畫曾考慮使用此資料集，但決定不採用。'}


def nonreuse_replies(kind='ref', reason='Quality', source='https://example.org/data?a=1&b=2', named=True, detail=AUTHORED):
    parent = path('reusingCUuid', 'preexistingQUuid')
    listing = path(parent, 'preexistingYesAUuid', kind + 'DataQUuid')
    item = path(listing, 'dataset-1')
    use = path(item, kind + 'DataUseQUuid')
    why = path(use, kind + 'DataUseNoAUuid', kind + 'DataUseNoWhyQUuid')
    result = {parent: IDS['preexistingYesAUuid'], listing: ['dataset-1'], use: IDS[kind + 'DataUseNoAUuid']}
    if named: result[path(item, kind + 'DataNameQUuid')] = 'Dataset A'
    if source: result[path(item, kind + 'DataWhereQUuid')] = source
    if reason:
        result[why] = IDS[kind + 'DataUseNo' + reason + 'AUuid'] if reason != 'unknown' else 'obsolete-choice'
    # Even a stale custom reason must not appear behind a different choice.
    result[path(why, kind + 'DataUseNoReasonAUuid', kind + 'DataUseNoReasonQUuid')] = detail
    return result


def folder_replies():
    parent = path('processingCUuid', 'storageConvQUuid')
    fs = path(parent, 'storageConvExploreAUuid', 'storageConvFSysQUuid')
    result = {parent: IDS['storageConvExploreAUuid'], fs: IDS['storageConvFSysYesAUuid']}
    for kind in ['Subj', 'Analysis', 'WorkflowStep']:
        result[path(fs, 'storageConvFSysYesAUuid', 'scFSys' + kind + 'FoldersQUuid')] = IDS['scFSys' + kind + 'FoldersYesAUuid']
    return result


# Public KM paths for the audited blank-value regressions; no project answers.
BLANK_FIELDS = [
    ('adminDetailsCUuid projectsQUuid ITEM costQUuid ITEM', 'costTitleQUuid costDescriptionQUuid costCurrencyQUuid costAmountQUuid'),
    ('adminDetailsCUuid projectsQUuid ITEM costQUuid ITEM costCoverQUuid costCoverGrantAUuid', 'costCoverGrantIdQUuid'),
    ('adminDetailsCUuid projectsQUuid ITEM costQUuid ITEM costCoverQUuid costCoverOtherAUuid', 'costCoverOtherHowQUuid'),
    ('adminDetailsCUuid policiesProceduresQUuid ITEM', 'policiesProceduresNameQUuid policiesProceduresLinkQUuid'),
    ('reusingCUuid preexistingQUuid preexistingYesAUuid refDataQUuid ITEM refDataUseQUuid refDataUseYesAUuid refDataConditionsQUuid refDataConditionsOtherAUuid', 'refDataConditionsOtherQUuid'),
    ('reusingCUuid preexistingQUuid preexistingYesAUuid refDataQUuid ITEM refDataUseQUuid refDataUseYesAUuid refDataVersionedQUuid refDataVersionedYesAUuid', 'refDataVersionedWhichQUuid'),
    ('reusingCUuid preexistingQUuid preexistingYesAUuid refDataQUuid ITEM refDataUseQUuid refDataUseYesAUuid', 'refDataUsageQUuid'),
    ('reusingCUuid preexistingQUuid preexistingYesAUuid nrefDataQUuid ITEM nrefDataUseQUuid nrefDataUseYesAUuid nrefDataConditionsQUuid nrefDataConditionsOtherAUuid', 'nrefDataConditionsOtherQUuid'),
    ('reusingCUuid preexistingQUuid preexistingYesAUuid nrefDataQUuid ITEM nrefDataUseQUuid nrefDataUseYesAUuid', 'nrefDataUsageQUuid'),
    ('reusingCUuid preexistingQUuid preexistingYesAUuid dataCompReadQUuid dataCompReadYesAUuid dataCompReadOthersQUuid dataCompReadOthersYesAUuid dataCompReadOthersYesStandardsQUuid ITEM', 'dataCompReadOthersYesStandardQUuid'),
    ('creatingCUuid metadataQUuid metadataExploreAUuid provenanceQUuid provenanceOtherAUuid', 'provenanceOtherQUuid'),
    ('creatingCUuid measuredQUuid measuredYesAUuid measuredDataQUuid ITEM measuredDataWhoQUuid measuredDataWhoExternalAUuid mdExternalOwnershipQUuid mdExternalOwnershipOtherAUuid', 'mdExternalOwnershipOtherQUuid'),
    ('creatingCUuid collectPersonalQUuid collectPersonalYesAUuid cpersGdprQUuid cpersGdprExploreAUuid cpersGdprLegalBasisQUuid cpersGdprLegalBasisAskAUuid', 'cpersExplainInformedQUuid cpersDescribeProcedureQUuid'),
    ('creatingCUuid collectPersonalQUuid collectPersonalYesAUuid cpersGdprQUuid cpersGdprExploreAUuid', 'cpersGdprPurposeQUuid'),
    ('creatingCUuid ownershipQUuid ownershipOtherAUuid', 'ownershipOtherQUuid'),
    ('processingCUuid storageConvQUuid storageConvExploreAUuid storageConvFSysQUuid storageConvFSysYesAUuid scFSysSubjFoldersQUuid scFSysSubjFoldersYesAUuid', 'scFSysSubjFoldersConvsQUuid'),
    ('processingCUuid storageConvQUuid storageConvExploreAUuid storageConvFSysQUuid storageConvFSysYesAUuid scFSysAnalysisFoldersQUuid scFSysAnalysisFoldersYesAUuid', 'scFSysAnalysisFoldersConvsQUuid'),
    ('processingCUuid storageConvQUuid storageConvExploreAUuid storageConvFSysQUuid storageConvFSysYesAUuid scFSysWorkflowStepFoldersQUuid scFSysWorkflowStepFoldersYesAUuid', 'scFSysWorkflowStepFoldersConvsQUuid'),
    ('processingCUuid storageConvQUuid storageConvExploreAUuid storageConvFSysQUuid storageConvFSysYesAUuid', 'scFSysAppointmentsQUuid'),
    ('processingCUuid storageConvQUuid storageConvExploreAUuid storageConvObjStoreQUuid storageConvObjStoreYesAUuid', 'scObjStoreNamingQUuid'),
    ('processingCUuid risksQUuid risksExploreAUuid risksPersonalDataQUuid risksPersonalDataPseudoAUuid risksPseudonymizationQUuid risksPseudonymizationAnotherAUuid', 'risksPseudonymizationAnotherQUuid'),
    ('preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid isPublishedDataYesAUuid publishedDistrosQUuid ITEM publishedDataRepositoryKindQUuid publishedDataRepositoryDomainSpecificAUuid', 'domainSpecificRepoNameQUuid'),
    ('preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid isPublishedDataYesAUuid publishedDistrosQUuid ITEM publishedDataRepositoryKindQUuid publishedDataRepositoryGeneralPurposeAUuid', 'generalPurposeRepoNameQUuid'),
    ('preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid isPublishedDataYesAUuid publishedDistrosQUuid ITEM publishedDataLicensesQUuid ITEM publishedDataLicenseQUuid publishedDataLicenseRestrictAUuid', 'licenseRestrictConditionsQUuid licenseRestrictLinkQUuid'),
    ('preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid isPublishedDataYesAUuid publishedDistrosQUuid ITEM publishedDataLicensesQUuid ITEM publishedDataLicenseQUuid publishedDataLicenseRestrictAUuid licenseRestrictAccessQUuid licenseRestrictAccessAnotherAUuid', 'licenseRestrictAccessAnotherQUuid'),
    ('preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid isPublishedDataYesAUuid publishedDistrosQUuid ITEM publishedDataLicensesQUuid ITEM', 'publishedDataLicenseStartQUuid'),
    ('preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid isPublishedDataYesAUuid publishedQReferencesQUuid publishedQReferencesYesAUuid publishedQReferencesItemQUuid ITEM', 'publishedQReferenceIdQUuid publishedQReferenceRelQUuid'),
    ('preservingCUuid producedDataQUuid ITEM publishedDataHowLongQUuid publishedDataHowLongFixedAUuid', 'publishedDataHowLongFixedQUuid'),
    ('preservingCUuid repoChargesQUuid repoChargesYesAUuid repoChargesHowPayQUuid repoChargesHowPayOtherAUuid', 'repoChargesHowPayOtherQUuid'),
    ('accessCUuid openImmediatelyQUuid openImmediatelyNoAUuid notOpenLegalReasonsQUuid notOpenLegalReasonsYesAUuid notOpenLegalReasonsPrivacyQUuid notOpenLegalReasonsPrivacyYesAUuid', 'notOpenLegalReasonsPrivacyAccessQUuid'),
    ('accessCUuid openImmediatelyQUuid openImmediatelyNoAUuid notOpenLegalReasonsQUuid notOpenLegalReasonsYesAUuid legalReasonsAuthenticatedQUuid legalReasonsAuthenticatedYesAUuid legalReasonsAuthorizeQUuid legalReasonsAuthorizeOldCommitteeAUuid', 'legalReasonsAuthorizeOldCommitteeQUuid'),
    ('accessCUuid openImmediatelyQUuid openImmediatelyNoAUuid notOpenBusinessReasonsQUuid notOpenBusinessReasonsOtherAUuid', 'notOpenBusinessReasonsOtherQUuid'),
    ('accessCUuid openImmediatelyQUuid openImmediatelyNoAUuid notOpenOtherReasonsQUuid notOpenOtherReasonsOtherAUuid', 'notOpenOtherReasonsOtherQUuid'),
    ('accessCUuid limitedEmbargoQUuid limitedEmbargoYesAUuid', 'limitedEmbargoPeriodQUuid'),
]


def partial_fixture(chain):
    from check_answer_mapping import chapter, question, schema
    parts = chain.split(); km = schema(); children = chapter(km, IDS[parts[0]]); replies = {}
    for i, part in enumerate(parts[1:], 1):
        if part == 'ITEM':
            replies[path(*parts[:i])] = ['ITEM']
            children = node['itemTemplateQuestionUuids']
        elif part.endswith('AUuid'):
            replies[path(*parts[:i])] = IDS[part]
            children = km['entities']['answers'][IDS[part]]['followUpUuids']
        else:
            following = parts[i+1] if i+1 < len(parts) else ''
            kind = 'ListQuestion' if following == 'ITEM' else 'OptionsQuestion' if following.endswith('AUuid') else 'ValueQuestion'
            node = question(km, children, IDS[part], kind, [IDS[following]] if kind == 'OptionsQuestion' else [])
    return km, replies, path(*parts)


def check_partial_answers(env, language):
    from current_support import PREFIX
    template = env.from_string(PREFIX + "{% include 'src/content.html.j2' %}")
    counts = dict(blank_field_cases=0, partial_record_cases=0, personal_sentence_cases=0)
    norm = lambda text: ' '.join(text.split())
    def render(km, replies, profile):
        soup = BeautifulSoup(template.render(km=km, repliesMap=replies, output_profile=profile), 'html.parser')
        assert len(soup.select('.question')) == 15
        if profile == 'submission': assert not soup.select('.data-gap,.data-review,.empty-value')
        return soup
    def signature(soup):
        return (norm(soup.get_text()), [(n.get('data-fact-id'), n.get('data-status'), norm(n.get_text())) for n in soup.select('[data-status]')])
    for prefix, fields in BLANK_FIELDS:
        for field in fields.split():
            km, base, key = partial_fixture(prefix + ' ' + field)
            integration = field in ['costCurrencyQUuid', 'dataCompReadOthersYesStandardQUuid', 'domainSpecificRepoNameQUuid', 'generalPurposeRepoNameQUuid']
            token = '0' if field == 'costAmountQUuid' else '2026-10-01' if field == 'publishedDataLicenseStartQUuid' else 'Original-UNIQUE-value'
            for profile in ['review', 'submission']:
                missing = signature(render(km, base, profile))
                for value in [None, '', ' \t\n\u3000', token]:
                    replies = dict(base)
                    if value is not None:
                        replies[key] = {'value': {'value': {'type':'PlainType', 'value':value}}} if integration else value
                    soup = render(km, replies, profile)
                    assert 'only.We use' not in soup.get_text(), (language, field, 'Missing sentence space')
                    if value != token: assert signature(soup) == missing, (language, profile, field, repr(value))
                    else: assert token in soup.get_text(), (language, profile, field, 'Filled value lost')
                    counts['blank_field_cases'] += 1
    for chain, fields in [
            ('adminDetailsCUuid policiesProceduresQUuid ITEM', ['policiesProceduresNameQUuid', 'policiesProceduresLinkQUuid', 'policiesProceduresDescriptionQUuid']),
            ('preservingCUuid producedDataQUuid ITEM isPublishedDataQUuid isPublishedDataYesAUuid publishedQReferencesQUuid publishedQReferencesYesAUuid publishedQReferencesItemQUuid ITEM', ['publishedQReferenceIdQUuid', 'publishedQReferenceRelQUuid'])]:
        km, base, _ = partial_fixture(chain + ' ' + fields[0])
        for mask, profile in itertools.product(range(2 ** len(fields)), ['review', 'submission']):
            replies = dict(base)
            for i, field in enumerate(fields): replies[path(*(chain + ' ' + field).split())] = 'Retain-FIELD-'+str(i) if mask & (1 << i) else ' \n '
            soup = render(km, replies, profile)
            for i in range(len(fields)): assert ('Retain-FIELD-'+str(i) in soup.get_text()) == bool(mask & (1 << i)), (language, mask, fields)
            assert not any(not li.get_text(strip=True) for li in soup.select('#q-access-security li,#q-share-restrictions li'))
            counts['partial_record_cases'] += 1
    chain = 'reusingCUuid preexistingQUuid preexistingYesAUuid nrefDataQUuid ITEM nrefDataUseQUuid nrefDataUseYesAUuid nrefDataPersonalQUuid nrefDataPersonalYesAUuid nrefDataPersonalLegalBasisQUuid'
    km, base, key = partial_fixture(chain)
    for basis, child, profile in itertools.product([None, 'PubInterest', 'Consent', 'Other'], [None, 'Yes', 'No'], ['review', 'submission']):
        replies = dict(base)
        if basis: replies[key] = IDS['nrefDataPersonalLebalBasisOtherAUuid' if basis == 'Other' else 'nrefDataPersonalLegalBasis'+basis+'AUuid']
        if child: replies[path(key, 'nrefDataPersonalLegalBasisConsentAUuid', 'nrefDataPersonalLegalBasisConsentReuseQUuid')] = IDS['nrefDataPersonalLegalBasisConsentReuse'+child+'AUuid']
        soup = render(km, replies, profile)
        text = soup.select_one('#q-how-data').get_text(' ', strip=True)
        assert 'legaly' not in text and 'This data include' not in text
        assert not re.search(r'based on(?:\s|$)', text)
        assert ('This dataset contains personal data.' if language == 'en' else '此資料集含個人資料。') in text
        consent = 'The consent also covers our reuse.' if language == 'en' else '該同意亦涵蓋本計畫的資料再利用。'
        assert (consent in text) == (basis == 'Consent' and child == 'Yes')
        counts['personal_sentence_cases'] += 1
    return counts


def check(root, language):
    counts = dict(nonreuse_cases=0, inactive_cases=0, inline_cases=0, missing_name_cases=0, quality_other_cases=0,
                  reference_identity_cases=0, instrument_cases=0, missing_detail_cases=0,
                  blank_field_cases=0, partial_record_cases=0, personal_sentence_cases=0)
    css = (root / 'src/layout.css').read_text()
    assert 'html body li > strong:first-child {' not in css
    assert 'html body li > strong.item-label { display: block; break-after: avoid; }' in css
    for escape in [False, True]:
        env = environment(root, escape)
        for name, count in check_partial_answers(env, language).items(): counts[name] += count
        prefix = "{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}"
        template = env.from_string(prefix + "{% include 'src/questions/01-how-data.html.j2' %}")
        folder = env.from_string(prefix + "{% include 'src/questions/03-docs-metadata.html.j2' %}")
        names = env.from_string(prefix + "{% include 'src/questions/01-how-data.html.j2' %}{% include 'src/questions/02-what-data.html.j2' %}{% include 'src/questions/04-quality-control.html.j2' %}")
        def render(t, replies, profile):
            return BeautifulSoup(t.render(repliesMap=replies, output_profile=profile), 'html.parser')

        publication = path('preservingCUuid', 'producedDataQUuid', 'dataset-1', 'isPublishedDataQUuid')
        reason = path(publication, 'isPublishedDataNoAUuid', 'notPublishedReasonQUuid')
        archive = path('preservingCUuid', 'archivedAfterQUuid')
        period = path(archive, 'archivedAfterYesAUuid', 'archivedAfterPeriodQUuid')
        for filename, base, detail, fact in [
                ('preservation-publication-reason', {reason: IDS['notPublishedReasonOtherAUuid']},
                 path(reason, 'notPublishedReasonOtherAUuid', 'notPublishedReasonOtherQUuid'), 'nonpublication-reason'),
                ('post-project-archive', {archive: IDS['archivedAfterYesAUuid'], period: IDS['archivedAfterPeriodOtherAUuid']},
                 path(period, 'archivedAfterPeriodOtherAUuid', 'archivedAfterPeriodOtherQUuid'), 'archive-minimum-period')]:
            section = env.from_string(prefix + "{% set isPublishedDataPath = '"+publication+"' %}{% include 'src/"+filename+".html.j2' %}")
            for value, profile in itertools.product([None, '', ' \t\n\u3000', AUTHORED], ['review', 'submission']):
                replies = dict(base)
                if value is not None: replies[detail] = value
                soup = render(section, replies, profile)
                filled = bool((value or '').strip())
                assert len(soup.select('.answer-lead')) == int(filled or profile == 'review')
                body = soup.select_one('.answer-detail[data-fact-id="'+fact+'"]')
                assert bool(body) == filled
                if body: assert body.decode_contents() == AUTHORED
                assert bool(soup.select('.data-gap[data-fact-id="'+fact+'"]')) == (not filled and profile == 'review')
                if profile == 'submission': assert not soup.select('.data-gap,.data-review,.empty-value')
                counts['missing_detail_cases'] += 1

        resources = env.from_string(prefix + "{% include 'src/questions/15-required-resources.html.j2' %}")
        expertise = path('adminDetailsCUuid', 'additionalExpertiseQUuid')
        hardware = path('adminDetailsCUuid', 'additionalHWSWQUuid')
        for parent, choice, leaf, fact, gap in [
                (expertise, 'additionalExpertiseYesTrainAUuid', 'additionalExpertiseYesTrainTrainingQUuid', 'specialist-expertise', 'specialist-expertise-detail'),
                (expertise, 'additionalExpertiseYesHireAUuid', 'additionalExpertiseYesHireExpertiseQUuid', 'specialist-expertise', 'specialist-expertise-detail'),
                (hardware, 'additionalHWSWYesAUuid', 'additionalHWSWYesWhatQUuid', 'hardware-software', 'hardware-software-detail')]:
            for value, profile in itertools.product([None, '', ' \t\n\u3000', AUTHORED], ['review', 'submission']):
                replies = {parent: IDS[choice]}
                if value is not None: replies[path(parent, choice, leaf)] = value
                soup = render(resources, replies, profile)
                filled = bool((value or '').strip())
                assert soup.select_one('[data-fact-id="'+fact+'"]')['data-status'] == ('complete' if filled else 'partial')
                assert bool(soup.select('.answer-detail')) == filled
                assert bool(soup.select('.data-gap[data-fact-id="'+gap+'"]')) == (not filled and profile == 'review')
                if filled:
                    assert AUTHORED in str(soup)
                    if choice == 'additionalExpertiseYesHireAUuid' and language == 'zh-Hant':
                        assert soup.select_one('.answer-detail strong').get_text() == '擬聘人員所需專長'
                else:
                    empty = dict(replies); empty[path(parent, choice, leaf)] = ''
                    assert str(soup) == str(render(resources, empty, profile))
                if profile == 'submission': assert not soup.select('.data-gap,.data-review,.empty-value')
                counts['missing_detail_cases'] += 1

        reference = env.from_string(prefix + "{% include 'src/questions/01-how-data.html.j2' %}{% include 'src/questions/08-copyright-ipr.html.j2' %}")
        for kind, choice, name, source, profile in itertools.product(
                ['ref', 'nref'], ['Yes', 'No', None, 'obsolete'], ['', ' \t\n\u3000', 'Dataset A'],
                ['', ' \t\n\u3000', 'https://example.org/source?a=1&b=2', 'Local archive.'], ['review', 'submission']):
            parent = path('reusingCUuid', 'preexistingQUuid')
            listing = path(parent, 'preexistingYesAUuid', kind + 'DataQUuid')
            item = path(listing, 'dataset-1'); use = path(item, kind + 'DataUseQUuid')
            replies = {parent: IDS['preexistingYesAUuid'], listing: ['dataset-1'],
                       path(item, kind + 'DataNameQUuid'): name, path(item, kind + 'DataWhereQUuid'): source,
                       path(use, kind + 'DataUseYesAUuid', kind + 'DataUsageQUuid'): 'ACTIVE-USE-PURPOSE',
                       path(use, kind + 'DataUseYesAUuid', kind + 'DataConditionsQUuid'): IDS[kind + 'DataConditionsCCBYAUuid']}
            if choice: replies[use] = IDS.get(kind + 'DataUse' + choice + 'AUuid', choice)
            soup = render(reference, replies, profile)
            q1 = soup.select_one('#q-how-data')
            locations = q1.select('[data-fact-id="dataset-source"][data-status="complete"]')
            assert len(locations) == int(bool(source.strip()))
            if source.strip():
                assert source in locations[0].get_text()
                if source.startswith('https://'): assert locations[0].a['href'] == source
            assert ('ACTIVE-USE-PURPOSE' in soup.get_text()) == (choice == 'Yes')
            assert all(n.get_text(strip=True) for n in q1.select('h5,strong.item-label'))
            if not name.strip() and profile == 'submission':
                assert q1.select_one('.dataset-label[data-list-index="1"]')
                if choice == 'Yes': assert soup.select_one('#q-copyright-ipr .dataset-label[data-list-index="1"]')
            if choice in [None, 'obsolete']:
                decisions = q1.select('[data-fact-id="reuse-decision"]')
                assert len(decisions) == int(profile == 'review')
                assert all(n['data-status'] == 'missing' for n in decisions)
            if profile == 'submission': assert not soup.select('.data-gap,.data-review,.empty-value')
            counts['reference_identity_cases'] += 1

        measured = path('creatingCUuid', 'measuredQUuid')
        listing = path(measured, 'measuredYesAUuid', 'measuredDataQUuid')
        instruments = path(listing, 'dataset-1', 'measuredDataInstrQUuid')
        base = {measured: IDS['measuredYesAUuid'], listing: ['dataset-1'],
                instruments: ['empty', 'partial', 'complete'],
                path(instruments, 'complete', 'measuredDataInstrNameQUuid'): 'Sensor C'}
        for name, description, profile in itertools.product(['', ' \t\n\u3000', 'Sensor B'], ['', ' \t\n\u3000', 'Original detail.'], ['review', 'submission']):
            replies = dict(base)
            replies[path(instruments, 'partial', 'measuredDataInstrNameQUuid')] = name
            replies[path(instruments, 'partial', 'measuredDataInstrDescQUuid')] = description
            soup = render(template, replies, profile)
            rows = soup.select('#q-how-data [data-item-id] > ul > li')
            visible = bool(name.strip() or description.strip())
            assert len(rows) == (3 if profile == 'review' else 1 + int(visible))
            assert all(n.get_text(strip=True) and n.strong.get_text(strip=True) for n in rows)
            assert len(soup.select('span.separator')) == int(bool(description.strip()))
            assert ('Original detail.' in soup.get_text()) == bool(description.strip())
            if not name.strip() and (visible or profile == 'review'):
                assert ('Instrument 2' if language == 'en' else '儀器 2') in rows[-2].strong.get_text()
            assert len(soup.select('[data-fact-id="instrument-details"]')) == (1 + int(not visible) if profile == 'review' else 0)
            empty = render(template, {measured: IDS['measuredYesAUuid'], listing: ['dataset-1'], instruments: ['empty']}, profile)
            if profile == 'submission':
                assert not empty.select('#q-how-data [data-item-id] > ul')
                assert len(empty.select('#q-how-data h5')) == 1
                assert not empty.select('#q-how-data .quality-context'), 'Dataset label repeated beneath its existing Q1 heading'
            counts['instrument_cases'] += 1

        quality = [env.from_string(prefix + "{% include 'src/questions/" + name + ".html.j2' %}")
                   for name in ['01-how-data', '04-quality-control']]
        measured = path('creatingCUuid', 'measuredQUuid')
        listing = path(measured, 'measuredYesAUuid', 'measuredDataQUuid')
        item = path(listing, 'dataset-1')
        control = path(item, 'measuredDataQualityQUuid')
        methods = path(control, 'measuredDataQualityYesAUuid')
        other = path(methods, 'mdQualityOtherQUuid')
        detail = path(other, 'mdQualityOtherYesAUuid', 'mdQualityOtherWhatQUuid')
        base = {measured: IDS['measuredYesAUuid'], listing: ['dataset-1'],
                path(item, 'measuredDataNameQUuid'): 'Dataset A', control: IDS['measuredDataQualityYesAUuid']}
        for choice, value, fixed, profile in itertools.product(
                ['Yes', 'No', None, 'obsolete'], [None, '', ' \t\n\u3000', AUTHORED],
                [False, True], ['review', 'submission']):
            replies = dict(base)
            if choice: replies[other] = IDS.get('mdQualityOther' + choice + 'AUuid', choice)
            if value is not None: replies[detail] = value
            if fixed: replies[path(methods, 'mdQualityCalibratingQUuid')] = IDS['mdQualityCalibratingYesAUuid']
            facts = []
            for question in quality:
                soup = render(question, replies, profile)
                node = soup.select_one('[data-fact-id="quality-other"]')
                has_detail = choice == 'Yes' and bool((value or '').strip())
                assert bool(node) == (choice == 'Yes')
                assert bool(soup.select('.answer-detail[data-fact-id="quality-other"]')) == has_detail
                assert bool(soup.select('.answer-lead')) == has_detail
                if node:
                    assert node['data-status'] == ('complete' if has_detail else 'partial' if profile == 'submission' else 'missing')
                    assert node.get_text(strip=True)
                    if has_detail:
                        assert len(node.find_all(recursive=False)) == 1 and node.div is not None
                        assert node.div.decode_contents() == AUTHORED
                assert ('Original.csv' in soup.get_text()) == has_detail
                if fixed: assert soup.select_one('[data-fact-id="quality-methods"][data-status="complete"]')
                if profile == 'submission': assert not soup.select('.data-gap,.data-review,.empty-value')
                facts.append([str(n) for n in soup.select('[data-fact-id^="quality-"]')])
                if value and not value.strip():
                    empty = dict(replies); empty[detail] = ''
                    assert str(soup) == str(render(question, empty, profile))
            assert facts[0] == facts[1]
            counts['quality_other_cases'] += 1
        for parent, profile in itertools.product([None, IDS['measuredDataQualityNoAUuid'], 'obsolete'], ['review', 'submission']):
            replies = dict(base, **{other: IDS['mdQualityOtherYesAUuid'], detail: AUTHORED})
            if parent: replies[control] = parent
            else: replies.pop(control)
            for question in quality:
                soup = render(question, replies, profile)
                assert not soup.select('[data-fact-id="quality-other"]') and 'Original.csv' not in soup.get_text()
            counts['quality_other_cases'] += 1

        for name, profile in itertools.product([None, '', ' \t\n\u3000', 'Survey A'], ['review', 'submission']):
            measured = path('creatingCUuid', 'measuredQUuid')
            instruments = path(measured, 'measuredYesAUuid', 'measuredDataQUuid')
            other = path('creatingCUuid', 'neqDataQUuid')
            datasets = path(other, 'neqDataYesAUuid', 'neqDataSetsQUuid')
            formats = path('creatingCUuid', 'formatsQUuid')
            replies = {measured: IDS['measuredYesAUuid'], other: IDS['neqDataYesAUuid']}
            for listing, field in [(instruments, 'measuredDataNameQUuid'), (datasets, 'neqDataSetsNameQUuid'), (formats, 'formatsNameQUuid')]:
                replies[listing] = ['first', 'second']
                for item in replies[listing]:
                    base = path(listing, item)
                    if name is not None:
                        replies[path(base, field)] = {'value': {'value': {'type': 'PlainType', 'value': name}}} if listing == formats else name
                    if listing == instruments:
                        replies[path(base, 'measuredDataWhoQUuid')] = IDS['measuredDataWhoExpertsOwnAUuid']
                        replies[path(base, 'measuredDataQualityQUuid')] = IDS['measuredDataQualityNoAUuid']
                    elif listing == datasets:
                        replies[path(base, 'neqDataSetsDescQUuid')] = '<p>Original '+item+' description.</p>'
                    else:
                        volume = path(base, 'formatsVolumeQUuid')
                        replies[volume] = IDS['formatsVolumeTotalAUuid']
                        replies[path(volume, 'formatsVolumeTotalAUuid', 'formatsVolumeTotalGBQUuid')] = '0' if item == 'first' else '120'
            soup = render(names, replies, profile)
            for node in soup.select('h5,.collection-summary strong,.quality-summary strong,strong.item-label'):
                assert node.get_text(strip=True), (language, profile, repr(name), 'Blank dataset label')
            assert 'Original first description.' in soup.get_text() and 'Original second description.' in soup.get_text()
            for label in soup.select('#q-what-data strong.item-label'):
                assert label.parent.name == 'p'
                assert label.parent.parent.get('class') == ['answer-lead']
                detail = label.parent.parent.find_next_sibling('div')
                assert detail.get('class') == ['answer-detail']
                assert len(detail.find_all(recursive=False)) == 1 and detail.div is not None
                assert detail.div.decode_contents() in ['<p>Original first description.</p>', '<p>Original second description.</p>']
            summaries = soup.select('.format-summary')
            assert len(summaries) == 2
            for index, summary in enumerate(summaries, 1):
                assert ('0\xa0GB' if index == 1 else '120\xa0GB') in summary.get_text()
                if not (name or '').strip() and profile == 'submission':
                    assert summary.p.get_text() == (f'Data format {index}.' if language == 'en' else f'資料格式 {index}。')
            if profile == 'submission':
                assert not soup.select('.data-gap,.data-review,.empty-value')
                labels = soup.select('.dataset-label')
                assert len(labels) == (0 if (name or '').strip() else 10)
                assert all(n['data-list-index'] in ['1', '2'] for n in labels)
            else:
                assert len(soup.select('[data-fact-id="format-name"][data-status="missing"]')) == (0 if (name or '').strip() else 2)
            for description in ['', ' \n ']:
                partial = dict(replies)
                for item in ['first', 'second']: partial[path(datasets, item, 'neqDataSetsDescQUuid')] = description
                empty = render(names, partial, profile).select_one('#q-what-data')
                assert len(empty.select('strong.item-label')) == 2
                assert not empty.select('li > .answer-lead, li > .answer-detail')
            counts['missing_name_cases'] += 1

        for kind, reason, source, named, profile in itertools.product(
                ['ref', 'nref'], ['Data', 'Aspect', 'Quality', 'Cond', 'Reason', '', 'unknown'],
                ['https://example.org/data?a=1&b=2', 'ftp://example.org/data', 'Local archive.', ''],
                [False, True], ['review', 'submission']):
            replies = nonreuse_replies(kind, reason, source, named)
            soup = render(template, replies, profile)
            paragraph = soup.select_one('.nonreuse-summary')
            assert paragraph and DECISION[language] in paragraph.get_text(' ', strip=True)
            assert len(soup.select('.nonreuse-summary')) == 1
            assert not re.search(r'[.。]\s*[,，]', paragraph.get_text())
            if language == 'zh-Hant':
                assert not re.search(r'。[ \u00a0]+[\u3400-\u9fff]', paragraph.get_text())
            assert not soup.select('p p, p div, p ul, p table')
            location = soup.select_one('.dataset-source')
            assert bool(location) == bool(source)
            if source:
                assert source in location.get_text()
                if source.startswith(('https://', 'ftp://')): assert location.a['href'] == source
            if reason == 'Reason':
                detail = soup.select_one('.answer-detail[data-fact-id="nonreuse-reason"]')
                assert detail and str(detail.ul) == str(BeautifulSoup(AUTHORED, 'html.parser').ul)
                assert 'Original.csv' in detail.get_text() and '.,' in detail.get_text()
            else:
                assert 'Original.csv' not in soup.get_text()
            gaps = soup.select('.data-gap[data-fact-id="nonreuse-reason"]')
            assert bool(gaps) == (profile == 'review' and reason in ('', 'unknown'))
            if gaps:
                assert gaps[0]['data-status'] == ('needs-review' if reason == 'unknown' else 'missing')
                if language == 'zh-Hant':
                    assert gaps[0].get_text(' ', strip=True) == '尚待補充：不採用此資料集的原因。'
            if reason in ('Data', 'Aspect', 'Quality', 'Cond'):
                assert paragraph.select_one('[data-fact-id="nonreuse-reason"][data-status="complete"]')
            if not named and profile == 'submission': assert soup.select_one('strong.item-label .dataset-label')
            counts['nonreuse_cases'] += 1

        for kind, profile in itertools.product(['ref', 'nref'], ['review', 'submission']):
            for detail in ['', ' \n ']:
                soup = render(template, nonreuse_replies(kind, 'Reason', detail=detail), profile)
                assert not soup.select('.answer-detail[data-fact-id="nonreuse-reason"]')
                assert bool(soup.select('.data-gap[data-fact-id="nonreuse-reason"]')) == (profile == 'review')
            for selected in ['', IDS[kind + 'DataUseYesAUuid'], 'obsolete']:
                replies = nonreuse_replies(kind)
                key = next(k for k in replies if k.endswith('.' + IDS[kind + 'DataUseQUuid']))
                replies[key] = selected
                assert not render(template, replies, profile).select('.nonreuse-summary')
                counts['inactive_cases'] += 1
        for profile in ['review', 'submission']:
            soup = render(folder, folder_replies(), profile)
            emphasis = soup.select('.storage-conventions-policy li > strong')
            # Reviewed Chinese sentences already omit this English emphasis.
            assert len(emphasis) == (3 if language == 'en' else 0)
            assert all('item-label' not in n.get('class', []) for n in emphasis)
            if language == 'en':
                assert 'There will be a folder for each sample/subject.' in soup.get_text(' ', strip=True).replace(' .', '.')
            else:
                assert [n.get_text(' ', strip=True) for n in soup.select('.storage-conventions-policy li')] == [
                    '每個樣本／研究對象都會有一個資料夾。',
                    '每次分析（包括重新分析）都會使用一個子資料夾。',
                    '分析工作流程的每個步驟都會使用一個子資料夾。']
            counts['inline_cases'] += 1
    return counts
