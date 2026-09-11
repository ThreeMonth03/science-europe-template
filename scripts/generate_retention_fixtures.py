"""Broader bilingual synthetic scenario, plus an independently missing-answer case.

This exercises all fifteen output questions, not every KM branch or every SE topic.
Validate the generated paths against the server-compiled KM before rendering.
"""

import copy
import json

from generate_pilot_fixtures import ROOT, IDS, generate, path, uid


def retention_cases(language):
    replies = generate(language)['populated']

    def text(en, zh):
        return zh if language == 'zh-Hant' else en

    def put(p, value, kind='StringReply'):
        replies[p] = {'type': kind, 'value': value}

    def choose(p, answer):
        put(p, IDS[answer], 'AnswerReply')

    def item(p, name):
        put(p, [uid(name)], 'ItemListReply')
        return path(p, uid(name))

    project = path('adminDetailsCUuid', 'projectsQUuid', uid('project'))
    put(path(project, 'projectAbstractQUuid'), text(
        'Synthetic scenario for testing all fifteen output questions. New coastal temperature measurements will be compared with two open reference datasets. This is not an approved or complete DMP.',
        '本合成案例用於測試十五題的文件輸出。計畫將蒐集新的沿岸水溫觀測資料，並與兩筆開放參考資料集比較。本文件並非已核定或已完成的資料管理方案。'))
    # No is not bound in upstream uuids.j2. Verified against compiled KM 2.7.0.
    put(path(project, 'projEthicalApprovalQUuid'), '2eb83683-86bc-4615-86b7-1d9bf0e414cc', 'AnswerReply')
    measured = path('creatingCUuid', 'measuredQUuid')
    choose(measured, 'measuredYesAUuid')
    dataset = item(path(measured, 'measuredYesAUuid', 'measuredDataQUuid'), 'new-measurements')
    put(path(dataset, 'measuredDataNameQUuid'), text('Coastal temperature measurements', '沿岸水溫觀測資料'))
    choose(path(dataset, 'measuredDataWhoQUuid'), 'measuredDataWhoExpertsOwnAUuid')
    choose(path(dataset, 'measuredDataEquipQUuid'), 'measuredDataEquipDescribedAUuid')
    instrument = item(path(dataset, 'measuredDataInstrQUuid'), 'temperature-sensor')
    put(path(instrument, 'measuredDataInstrNameQUuid'), text('Temperature logger', '水溫紀錄器'))
    put(path(instrument, 'measuredDataInstrDescQUuid'), text(
        'Record temperature every ten minutes; retain UTC timestamps and calibration records.',
        '每十分鐘記錄水溫，保留 UTC 時間戳記與校正紀錄。'))
    quality = path(dataset, 'measuredDataQualityQUuid')
    choose(quality, 'measuredDataQualityYesAUuid')
    for question, answer in [('mdQualityCalibratingQUuid', 'mdQualityCalibratingYesAUuid'), ('mdQualityValidationQUuid', 'mdQualityValidationYesAUuid')]:
        choose(path(quality, 'measuredDataQualityYesAUuid', question), answer)
    choose(path(dataset, 'measuredDataReuseQUuid'), 'measuredDataReuseSameFieldAUuid')

    fmt = item(path('creatingCUuid', 'formatsQUuid'), 'csv-format')
    put(path(fmt, 'formatsNameQUuid'), {'type': 'PlainType', 'value': 'CSV (UTF-8)'}, 'IntegrationReply')
    choose(path(fmt, 'formatsIsStandardQUuid'), 'formatsIsStandardYesAUuid')
    choose(path(fmt, 'formatsIsLTSuitableQUuid'), 'formatsIsLTSuitableYesAUuid')
    volume = path(fmt, 'formatsVolumeQUuid')
    choose(volume, 'formatsVolumeTotalAUuid')
    put(path(volume, 'formatsVolumeTotalAUuid', 'formatsVolumeTotalGBQUuid'), '120')
    metadata = path('creatingCUuid', 'metadataQUuid', 'metadataExploreAUuid', 'metadataStandardsQUuid')
    choose(metadata, 'metadataStandardsExploreAUuid')
    choose(path(metadata, 'metadataStandardsExploreAUuid', 'metadataStandardsDCQUuid'), 'metadataStandardsDCYesAUuid')
    op = path('accessCUuid', 'metadataOpenQUuid')
    choose(op, 'metadataOpenYesAUuid')
    choose(path(op, 'metadataOpenYesAUuid', 'metadataOpenInstrQUuid'), 'metadataOpenInstrYesAUuid')
    choose(path(op, 'metadataOpenYesAUuid', 'metadataOpenFormQUuid'), 'metadataOpenFormYesRepoAUuid')
    storage = path('processingCUuid', 'storageConvQUuid')
    choose(storage, 'storageConvExploreAUuid')
    sp = path(storage, 'storageConvExploreAUuid')
    capacity = path(sp, 'storageSpaceQUuid')
    choose(capacity, 'storageSpaceSpecifyAUuid')
    put(path(capacity, 'storageSpaceSpecifyAUuid', 'storageSpaceSpecifyQUuid'), '2048')
    choose(path(sp, 'storageConvFSysQUuid'), 'storageConvFSysYesAUuid')
    files = path(sp, 'storageConvFSysQUuid', 'storageConvFSysYesAUuid')
    choose(path(files, 'scDocumentVersioningQUuid'), 'scDocumentVersioningYesAUuid')
    put(path(files, 'scFSysAppointmentsQUuid'), text(
        'Name files station_YYYYMMDD.csv and document corrections in CHANGELOG.md.',
        '檔名採 station_YYYYMMDD.csv，並在 CHANGELOG.md 記錄修正。'))
    risks = path('processingCUuid', 'risksQUuid')
    choose(risks, 'risksExploreAUuid')
    for question, answer in [('risksCarryHomeQUuid', 'risksCarryHomeNoAUuid'), ('risksHttpsQUuid', 'risksHttpsYesAUuid'), ('risksInstructedQUuid', 'risksInstructedYesAUuid')]:
        choose(path(risks, 'risksExploreAUuid', question), answer)
    choose(path('creatingCUuid', 'collectPersonalQUuid'), 'collectPersonalNoAUuid')
    choose(path('creatingCUuid', 'ethLegQUuid'), 'ethLegNoAUuid')

    produced = item(path('preservingCUuid', 'producedDataQUuid'), 'published-observations')
    put(path(produced, 'producedDataNameQUuid'), text('Quality-checked coastal observations', '完成品質檢查的沿岸觀測資料'))
    choose(path(produced, 'containPersonalQUuid'), 'containPersonalNoAUuid')
    choose(path(produced, 'containSensitiveQUuid'), 'containSensitiveNoAUuid')
    duration = path(produced, 'publishedDataHowLongQUuid')
    choose(duration, 'publishedDataHowLongFixedAUuid')
    put(path(duration, 'publishedDataHowLongFixedAUuid', 'publishedDataHowLongFixedQUuid'), '10')
    choose(path(produced, 'publishedDataMetadataPersistentQUuid'), 'publishedDataMetadataPersistentYesAUuid')
    publication = path(produced, 'isPublishedDataQUuid')
    choose(publication, 'isPublishedDataYesAUuid')
    published = path(publication, 'isPublishedDataYesAUuid')
    distro = item(path(published, 'publishedDistrosQUuid'), 'institutional-distribution')
    choose(path(distro, 'publishedDataRepositoryKindQUuid'), 'publishedDataRepositoryInstitutionalAUuid')
    choose(path(distro, 'publishedDistroShareQUuid'), 'publishedDistroShareOpenAUuid')
    license_item = item(path(distro, 'publishedDataLicensesQUuid'), 'release-license')
    put(path(license_item, 'publishedDataLicenseStartQUuid'), '2027-12-31')
    choose(path(license_item, 'publishedDataLicenseQUuid'), 'publishedDataLicenseCCBYAUuid')
    pid = path(distro, 'publishedDataIdentifierQUuid')
    choose(pid, 'publishedDataIdentifierYesAUuid')
    choose(path(pid, 'publishedDataIdentifierYesAUuid', 'publishedDataIdentifierAssignsQUuid'), 'publishedDataIdentifierAssignsRepositoryAUuid')
    choose(path(pid, 'publishedDataIdentifierYesAUuid', 'publishedDataIdentifierResolvableQUuid'), 'publishedDataIdentifierResolvableYesAUuid')
    # Upstream's publishedDataIdentifierSpecifyQUuid is absent from KM 2.7.0.
    # Do not invent an unreachable answer just to fill its output branch.
    software = path(published, 'publishedSpecSwUseQUuid')
    choose(software, 'publishedSpecSwUseYesAUuid')
    software_list = path(software, 'publishedSpecSwUseYesAUuid', 'publishedSpecSwUseWhatQUuid')
    sw = item(software_list, 'analysis-software')
    put(path(sw, 'publishedSpecSwUseWhatNameQUuid'), 'CoastView 1.0 (synthetic test tool)')
    put(path(sw, 'publishedSpecSwUseWhatPIDQUuid'), 'https://example.org/coastview/1.0')
    choose(path('preservingCUuid', 'repoChargesQUuid'), 'repoChargesNoAUuid')
    choose(path('preservingCUuid', 'budgetTimeEffortQUuid'), 'budgetTimeEffortYesAUuid')
    partial = copy.deepcopy(replies)
    # Delete a whole selected subtree, never leave unreachable child replies.
    for prefix in (path(sp, 'storageConvFSysQUuid'), software_list):
        for key in list(partial):
            if key == prefix or key.startswith(prefix + '.'):
                del partial[key]
    return {'representative': replies, 'retention-partial': partial}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, replies in retention_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p, value in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'populated.json').read_text())
            recipe.update(name=f'Science Europe retention experiment / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
