"""Independent format/volume fixtures; all older fixture inputs remain unchanged."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_retention_fixtures import retention_cases


def format_cases(language):
    rich = copy.deepcopy(retention_cases(language)['structured'])
    formats = path('creatingCUuid', 'formatsQUuid')
    for key in list(rich):
        if key == formats or key.startswith(formats + '.'): del rich[key]
    rich[formats] = {'type': 'ItemListReply', 'value': []}
    def item(label, count, size, reason=None):
        ident = uid('format-volume/' + label); rich[formats]['value'].append(ident)
        prefix = path(formats, ident)
        def put(p, val, kind='StringReply'): rich[path(prefix, p)] = {'type': kind, 'value': val}
        put('formatsNameQUuid', {'type': 'PlainType', 'value': label}, 'IntegrationReply')
        put('formatsIsStandardQUuid', IDS['formatsIsStandardNoAUuid'], 'AnswerReply')
        put('formatsIsLTSuitableQUuid', IDS['formatsIsLTSuitableNoAUuid'], 'AnswerReply')
        put('formatsVolumeQUuid', IDS['formatsVolumeFileSizeAUuid'], 'AnswerReply')
        if count is not None: put(path('formatsVolumeQUuid', 'formatsVolumeFileSizeAUuid', 'formatsVolumeFilesQUuid'), count)
        if size is not None: put(path('formatsVolumeQUuid', 'formatsVolumeFileSizeAUuid', 'formatsVolumeFileGBQUuid'), size)
        if reason:
            why = path('formatsIsStandardQUuid', 'formatsIsStandardNoAUuid', 'formatsWhyNonStandardQUuid')
            put(why, IDS['formatsWhyNSAnotherReasonAUuid'], 'AnswerReply')
            put(path(why, 'formatsWhyNSAnotherReasonAUuid', 'formatsWhyNSAnotherReasonQUuid'), reason)
            put(path('formatsIsLTSuitableQUuid', 'formatsIsLTSuitableNoAUuid', 'formatsConvertLTSuitableQUuid'), IDS['formatsConvertLTSuitableNoAUuid'], 'AnswerReply')
        return prefix
    authored = ('JSON, CSV and MyInstrument v1.2 must retain their original case!\n\nKeep station_YYYYMMDD.csv unchanged.\n\n- Record the original format.\n- Retain the conversion log.' if language == 'en' else
                'JSON、CSV 與 MyInstrument v1.2 的大小寫必須保留！\n\nstation_YYYYMMDD.csv 檔名維持不變。\n\n- 記錄原始格式。\n- 保留格式轉換紀錄。')
    item('MyInstrument v1.2', '2', '0.0001', authored)
    complete = copy.deepcopy(rich)
    # Independent known quantities, zero, missing followups, and an unnamed item.
    rich[formats]['value'] = []
    for key in list(rich):
        if key.startswith(formats + '.'): del rich[key]
    item('COUNT-ONLY', '12', None)
    item('SIZE-ONLY', None, '0.25')
    item('ZERO-COUNT', '0', None)
    unnamed = item('UNNAMED', None, '0')
    del rich[path(unnamed, 'formatsNameQUuid')]
    return {'format-rich': complete, 'format-partial': rich}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, values in format_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p, value in sorted(values.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'structured.json').read_text())
            recipe.update(name=f'Science Europe format/volume experiment / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
