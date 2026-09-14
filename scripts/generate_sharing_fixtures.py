"""Reachable custom-process and missing-answer cases; never overwrite older fixtures."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_storage_fixtures import storage_cases


def sharing_cases(language):
    replies = copy.deepcopy(storage_cases(language)['storage-sharing'])
    def put(p, value, kind='StringReply'): replies[p] = {'type': kind, 'value': value}
    def choose(p, name): put(p, IDS[name], 'AnswerReply')
    def text(en, zh): return zh if language == 'zh-Hant' else en
    conditions = next(p for p in replies if p.endswith(IDS['licenseRestrictConditionsQUuid']))
    prefix = conditions.rsplit('.', 1)[0]
    access = path(prefix, 'licenseRestrictAccessQUuid')
    choose(access, 'licenseRestrictAccessAnotherAUuid')
    custom = path(access, 'licenseRestrictAccessAnotherAUuid', 'licenseRestrictAccessAnotherQUuid')
    put(custom, text('Submit form Access-2027-12-31.csv without changing the file name.\n\nThe review contact confirms permission before files are provided.\n\n- Keep the request identifier.\n- Do not infer approval from submission.',
                    '請提交 Access-2027-12-31.csv 表單，檔名不得更動。\n\n由審閱聯絡人確認許可後，才提供檔案。\n\n- 保留申請識別碼。\n- 提出申請不代表已獲核准。'))
    choose(path(prefix, 'licenseRestrictMetadataQUuid'), 'licenseRestrictMetadataNoAUuid')
    charges = path('preservingCUuid', 'repoChargesQUuid')
    payment = path(charges, 'repoChargesYesAUuid', 'repoChargesHowPayQUuid')
    choose(payment, 'repoChargesHowPayOtherAUuid')
    put(path(payment, 'repoChargesHowPayOtherAUuid', 'repoChargesHowPayOtherQUuid'), text(
        'The shared infrastructure fund will pay the repository invoice.\n\nRecord the payment in Budget-2027-12-31.csv; preserve the original file name.',
        '由共用研究設施基金支付資料儲存庫帳單。\n\n付款紀錄登錄於 Budget-2027-12-31.csv，保留原始檔名。'))
    missing = copy.deepcopy(replies)
    for p in (conditions, custom, path(prefix, 'licenseRestrictMetadataQUuid')): del missing[p]
    license_item = prefix.rsplit('.', 2)[0]
    del missing[path(license_item, 'publishedDataLicenseStartQUuid')]
    duration = next(p for p in missing if p.endswith(IDS['publishedDataHowLongFixedQUuid']))
    del missing[duration]
    # No repository charge is not silently reconciled with the prepaid choice.
    missing[charges] = {'type': 'AnswerReply', 'value': IDS['repoChargesNoAUuid']}
    for p in list(missing):
        if p.startswith(charges + '.'): del missing[p]
    return {'sharing-custom': replies, 'sharing-missing': missing}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, replies in sharing_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p, value in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'structured.json').read_text())
            recipe.update(name=f'Science Europe sharing/preservation experiment / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
