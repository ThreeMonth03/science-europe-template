"""Reachable dataset-context and post-project archival answers, separate from publication."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_storage_fixtures import storage_cases


def preservation_cases(language):
    replies = copy.deepcopy(storage_cases(language)['storage-sharing'])
    def put(p, value, kind='StringReply'): replies[p] = {'type': kind, 'value': value}
    def choose(p, name): put(p, IDS[name], 'AnswerReply')
    def text(en, zh): return zh if language == 'zh-Hant' else en
    data = path('preservingCUuid', 'producedDataQUuid')
    first = path(data, replies[data]['value'][0])
    put(path(first, 'producedDataDescriptionQUuid'), text(
        'Quality-checked coastal measurements with a station dictionary.\n\nKeep Selection-2027-12-31.csv alongside the processing record.',
        '經品質檢核的沿岸觀測資料，附有測站代碼表。\n\nSelection-2027-12-31.csv 應與處理紀錄一併保留。'))
    stage = path(first, 'producedDataStageQUuid')
    choose(stage, 'producedDataStagePublishedAUuid')
    put(path(stage, 'producedDataStagePublishedAUuid', 'producedDataPaperQUuid'), 'https://example.org/papers/coast-study')
    second_id = uid('preservation/nonpublished-dataset')
    replies[data]['value'].append(second_id)
    second = path(data, second_id)
    put(path(second, 'producedDataNameQUuid'), text('Internal instrument checks', '內部儀器檢核資料'))
    put(path(second, 'producedDataDescriptionQUuid'), text('Instrument test records retained for internal verification.', '供內部查核使用的儀器測試紀錄。'))
    choose(path(second, 'producedDataStageQUuid'), 'producedDataStageIntermediateAUuid')
    publication = path(second, 'isPublishedDataQUuid')
    choose(publication, 'isPublishedDataNoAUuid')
    reason = path(publication, 'isPublishedDataNoAUuid', 'notPublishedReasonQUuid')
    choose(reason, 'notPublishedReasonOtherAUuid')
    reason_text = path(reason, 'notPublishedReasonOtherAUuid', 'notPublishedReasonOtherQUuid')
    put(reason_text, text('The instrument supplier restricts publication of test records.\n\nInternal verification copies will still be kept.\n\n- Record the access decision.\n- Retain the calibration context.',
                          '儀器供應商限制公開測試紀錄。\n\n內部查核用的副本仍會保留。\n\n- 記錄取用決定。\n- 保留校正脈絡。'))
    duration = path(second, 'publishedDataHowLongQUuid')
    choose(duration, 'publishedDataHowLongFixedAUuid')
    put(path(duration, 'publishedDataHowLongFixedAUuid', 'publishedDataHowLongFixedQUuid'), text('15 years', '15 年'))
    choose(path(second, 'publishedDataMetadataPersistentQUuid'), 'publishedDataMetadataPersistentYesAUuid')
    archive = path('preservingCUuid', 'archivedAfterQUuid')
    choose(archive, 'archivedAfterYesAUuid')
    ap = path(archive, 'archivedAfterYesAUuid')
    choose(path(ap, 'archivedAfterPayerQUuid'), 'archivedAfterPayerDepartmentAUuid')
    period = path(ap, 'archivedAfterPeriodQUuid')
    choose(period, 'archivedAfterPeriodYearsAUuid')
    years = path(period, 'archivedAfterPeriodYearsAUuid', 'archivedAfterYearsQUuid')
    put(years, '12')
    extension = path(ap, 'archivedAfterExtendQUuid')
    choose(extension, 'archivedAfterExtendYesAUuid')
    authority = path(extension, 'archivedAfterExtendYesAUuid', 'archivedAfterExtendWhoQUuid')
    choose(authority, 'archivedAfterExtendWhoArchiveAUuid')
    basis = path(extension, 'archivedAfterExtendYesAUuid', 'archivedAfterExtendBasisQUuid')
    put(basis, [IDS[n] for n in ['archivedAfterExtendBasisActualChoiceUuid', 'archivedAfterExtendBasisPredictedChoiceUuid', 'archivedAfterExtendBasisBudgetChoiceUuid']], 'MultiChoiceReply')
    formats = path(ap, 'archivedAfterFormatsQUuid')
    choose(formats, 'archivedAfterFormatsYesAUuid')
    choose(path(ap, 'archivedAfterMediaQUuid'), 'archivedAfterMediaNoAUuid')
    complete = copy.deepcopy(replies)
    for p in [reason_text, years, authority, basis, formats, path(ap, 'archivedAfterPayerQUuid')]: replies.pop(p)
    partial = copy.deepcopy(replies)
    replies = copy.deepcopy(complete)
    choose(period, 'archivedAfterPeriodOtherAUuid'); replies.pop(years)
    put(path(period, 'archivedAfterPeriodOtherAUuid', 'archivedAfterPeriodOtherQUuid'), text(
        'Keep the archive until the named review is completed.\n\nThe review record will identify the applicable end date.\n\n- Preserve the decision record.\n- Do not infer an automatic deletion date.',
        '典藏資料將保留至指定審查完成。\n\n審查紀錄將載明適用的截止日期。\n\n- 保留決策紀錄。\n- 不自行推定自動刪除日期。'))
    choose(extension, 'archivedAfterExtendNoAUuid'); replies.pop(authority); replies.pop(basis)
    choose(path(extension, 'archivedAfterExtendNoAUuid', 'archivedAfterExtendNoReasonQUuid'), 'archivedAfterExtendNoLegalAUuid')
    choose(formats, 'archivedAfterFormatsNoAUuid')
    choose(path(ap, 'archivedAfterMediaQUuid'), 'archivedAfterMediaYesAUuid')
    custom = copy.deepcopy(replies)
    replies = copy.deepcopy(complete)
    choose(archive, 'archivedAfterNoAUuid')
    for p in list(replies):
        if p.startswith(archive + '.'): replies.pop(p)
    return {'preservation-complete': complete, 'preservation-partial': partial,
            'preservation-custom': custom, 'preservation-no-cold': replies}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, replies in preservation_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p,value in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'structured.json').read_text())
            recipe.update(name=f'Science Europe preservation coverage / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
