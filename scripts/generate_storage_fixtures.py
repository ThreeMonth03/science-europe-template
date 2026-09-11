"""Synthetic, reachable storage/sharing cases; leave earlier fixtures unchanged."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_retention_fixtures import retention_cases


def storage_cases(language):
    replies = copy.deepcopy(retention_cases(language)['structured'])
    def choose(p, name): replies[p] = {'type': 'AnswerReply', 'value': IDS[name]}
    def put(p, value, kind='StringReply'): replies[p] = {'type': kind, 'value': value}
    def text(en, zh): return zh if language == 'zh-Hant' else en
    choose(path('processingCUuid', 'sharedWorkspaceQUuid', 'sharedWorkspaceYesAUuid', 'sharedSpecialistsQUuid'), 'sharedSpecialistsYesAUuid')
    archive = path('preservingCUuid', 'archivedDuringQUuid')
    choose(archive, 'archivedDuringYesAUuid')
    prefix = path(archive, 'archivedDuringYesAUuid')
    choose(path(prefix, 'archiveMediumQUuid'), 'archiveMediumTapeAUuid')
    choose(path(prefix, 'archiveRemoteQUuid'), 'archiveRemoteYesAUuid')
    changing = path(prefix, 'archivedDuringReQUuid')
    choose(changing, 'archivedDuringReYesAUuid')
    choose(path(changing, 'archivedDuringReYesAUuid', 'archivedDuringReFrequentBackupsQUuid'), 'archivedDuringReFrequentBackupsYesAUuid')
    choose(path(changing, 'archivedDuringReYesAUuid', 'archivedDuringRelyQUuid'), 'archivedDuringRelyYesAUuid')
    produced = path('preservingCUuid', 'producedDataQUuid', uid('published-observations'))
    distributions = path(produced, 'isPublishedDataQUuid', 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
    second = uid('controlled-distribution')
    replies[distributions]['value'].append(second)
    dist = path(distributions, second)
    choose(path(dist, 'publishedDataRepositoryKindQUuid'), 'publishedDataRepositorySpecialAUuid')
    choose(path(dist, 'publishedDistroShareQUuid'), 'publishedDistroShareSharedAUuid')
    license_list = path(dist, 'publishedDataLicensesQUuid')
    put(license_list, [uid('restricted-license')], 'ItemListReply')
    license_item = path(license_list, uid('restricted-license'))
    put(path(license_item, 'publishedDataLicenseStartQUuid'), '2027-06-01')
    license_type = path(license_item, 'publishedDataLicenseQUuid')
    choose(license_type, 'publishedDataLicenseRestrictAUuid')
    restrictions = path(license_type, 'publishedDataLicenseRestrictAUuid')
    put(path(restrictions, 'licenseRestrictConditionsQUuid'), text(
        'This preliminary release is limited to the project review group.\n\n- Do not redistribute the preliminary files.\n- Cite the release identifier in review notes.',
        '此初步發布版本僅提供計畫審閱小組使用。\n\n- 不得轉散布初步檔案。\n- 審閱紀錄須註明發布版本的識別碼。'))
    choose(path(restrictions, 'licenseRestrictAccessQUuid'), 'licenseRestrictAccessRequestAUuid')
    put(path(restrictions, 'licenseRestrictLinkQUuid'), 'https://example.org/coast/review-terms')
    choose(path(restrictions, 'licenseRestrictMetadataQUuid'), 'licenseRestrictMetadataYesAUuid')
    pid = path(dist, 'publishedDataIdentifierQUuid')
    choose(pid, 'publishedDataIdentifierYesAUuid')
    choose(path(pid, 'publishedDataIdentifierYesAUuid', 'publishedDataIdentifierAssignsQUuid'), 'publishedDataIdentifierAssignsInstitDataStewardAUuid')
    choose(path(pid, 'publishedDataIdentifierYesAUuid', 'publishedDataIdentifierResolvableQUuid'), 'publishedDataIdentifierResolvableYesAUuid')
    partial = copy.deepcopy(replies)
    # Remove independent siblings, not their supplied licence, date or PID answers.
    for p in (path(prefix, 'archiveRemoteQUuid'), path(changing, 'archivedDuringReYesAUuid', 'archivedDuringReFrequentBackupsQUuid'),
              path(dist, 'publishedDataRepositoryKindQUuid'), path(dist, 'publishedDistroShareQUuid')):
        del partial[p]
    return {'storage-sharing': replies, 'storage-sharing-partial': partial}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, replies in storage_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p, value in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'structured.json').read_text())
            recipe.update(name=f'Science Europe storage/sharing experiment / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
