"""Add reading-unit counterexamples without changing earlier fixture inputs."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_retention_fixtures import retention_cases


def reading_cases(language):
    rich = copy.deepcopy(retention_cases(language)['structured'])
    def put(p, value, kind='StringReply'): rich[p] = {'type': kind, 'value': value}
    def choose(p, answer): put(p, IDS[answer], 'AnswerReply')
    def clear(p):
        for key in list(rich):
            if key == p or key.startswith(p + '.'): del rich[key]
    authored = ('Keep v1.2 and station_YYYYMMDD.csv.\n\nThis is a separate authored paragraph!\n\n- Retain the original record.\n- Record the reason for each correction.' if language == 'en' else
                '保留 v1.2 與 station_YYYYMMDD.csv。\n\n這是使用者另外撰寫的段落！\n\n- 保留原始紀錄。\n- 記錄每次更正的原因。')
    datasets = path('creatingCUuid', 'measuredQUuid', 'measuredYesAUuid', 'measuredDataQUuid')
    dataset = path(datasets, rich[datasets]['value'][0])
    who = path(dataset, 'measuredDataWhoQUuid'); clear(who)
    choose(who, 'measuredDataWhoExternalAUuid')
    ownership = path(who, 'measuredDataWhoExternalAUuid', 'mdExternalOwnershipQUuid')
    choose(ownership, 'mdExternalOwnershipOtherAUuid')
    details = path(ownership, 'mdExternalOwnershipOtherAUuid', 'mdExternalOwnershipOtherQUuid')
    put(details, authored)
    choose(path(dataset, 'measuredDataEquipQUuid'), 'measuredDataEquipCareAUuid')
    metadata = path('accessCUuid', 'metadataOpenQUuid'); clear(metadata)
    choose(metadata, 'metadataOpenNoAUuid')
    put(path(metadata, 'metadataOpenNoAUuid', 'metadataOpenNoExplainQUuid'), authored)
    storage = path('processingCUuid', 'storageConvQUuid', 'storageConvExploreAUuid')
    files = path(storage, 'storageConvFSysQUuid', 'storageConvFSysYesAUuid')
    put(path(files, 'scFSysAppointmentsQUuid'), authored)
    obj = path(storage, 'storageConvObjStoreQUuid'); clear(obj)
    choose(obj, 'storageConvObjStoreYesAUuid')
    put(path(obj, 'storageConvObjStoreYesAUuid', 'scObjStoreNamingQUuid'), authored)
    db = path(storage, 'storageConvRelDbQUuid'); clear(db)
    choose(db, 'storageConvRelDbYesAUuid')
    choose(path(db, 'storageConvRelDbYesAUuid', 'scRelDbHandleChangesQUuid'), 'scRelDbCrudAnswerUuid')
    partial = copy.deepcopy(rich)
    del partial[details]
    del partial[path(dataset, 'measuredDataEquipQUuid')]
    other = uid('reading-unnamed-dataset'); partial[datasets]['value'].append(other)
    # No name, collector or equipment: a visible gap, not a name-only bullet.
    long_table = copy.deepcopy(retention_cases(language)['structured'])
    provenance = next(key for key in long_table if key.endswith(IDS['provenanceOtherQUuid']))
    header = '| Record | Retention |\n|---|---|\n' if language == 'en' else '| 紀錄 | 保存期間 |\n|---|---|\n'
    rows = '\n'.join(f'| ROW-{i:02d} | 10 |' for i in range(1, 49))
    long_table[provenance] = {'type': 'StringReply', 'value': header + rows}
    return {'reading-rich': rich, 'reading-partial': partial, 'table-long': long_table}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, values in reading_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p, value in sorted(values.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'structured.json').read_text())
            recipe.update(name=f'Science Europe reading units experiment / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
