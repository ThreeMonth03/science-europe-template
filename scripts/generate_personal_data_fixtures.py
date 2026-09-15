"""Reachable Q7/Q9 follow-ups, with public synthetic prose and explicit controls."""
import argparse
import copy
import json
from pathlib import Path
from generate_pilot_fixtures import ROOT, IDS, uid
from generate_missing_info_fixtures import missing_info_cases, drop


def personal_paths():
    parent = IDS['creatingCUuid'] + '.' + IDS['collectPersonalQUuid']
    gdpr = parent + '.' + IDS['collectPersonalYesAUuid'] + '.' + IDS['cpersGdprQUuid']
    explore = gdpr + '.' + IDS['cpersGdprExploreAUuid']
    legal = explore + '.' + IDS['cpersGdprLegalBasisQUuid']
    safeguards = explore + '.' + IDS['cpersGdprSafeguardsQUuid']
    detail = safeguards + '.' + IDS['cpersGdprSafeguardsAUuid']
    transfer = detail + '.' + IDS['cpersGdprSafeguardsTransferQUuid']
    return dict(parent=parent, gdpr=gdpr, legal=legal, safeguards=safeguards,
                other=legal+'.'+IDS['cpersGdprLegalBasisOtherAUuid']+'.'+IDS['cpersGdprLegalBasisOtherWhichQUuid'],
                identifiability=detail+'.'+IDS['cpersGdprSafeguardsIdentifQUuid'],
                additional=detail+'.'+IDS['cpersGdprSafeguardElaborateQUuid'], transfer=transfer,
                measures=transfer+'.'+IDS['cpersGdprSafeguardsTransferYesAUuid']+'.'+IDS['cpersGdprSafeguardsTransferMeasuresQUuid'])


def personal_data_cases(locale):
    old = missing_info_cases(locale)
    paths = personal_paths()
    def answer(binding): return {'type': 'AnswerReply', 'value': IDS[binding]}
    partial = copy.deepcopy(old['personal-data-partial'])
    # Explicit ethical-legislation "No" is removed here: absence must not be
    # mistaken for "not subject to ethical legislation" in Q9.
    drop(partial, IDS['creatingCUuid'], 'ethLegQUuid')
    partial[paths['legal']] = answer('cpersGdprLegalBasisOtherAUuid')
    partial[paths['safeguards']] = answer('cpersGdprSafeguardsAUuid')
    complete = copy.deepcopy(partial)
    complete[paths['other']] = answer('cpersGdprLegalBasisOtherWhichContractAUuid')
    complete[paths['identifiability']] = answer('cpersGdprSafeguardsIdentifPseudoAUuid')
    prose = ('Access is limited to the named research team.\n\nReview **permissions** every month.\n\n'
             '- Record access in Audit-2027.csv.\n- Retain the original order.') if locale == 'en' else (
             '僅限本計畫指定的研究人員存取資料。\n\n每月檢查**存取權限**。\n\n'
             '- 將存取紀錄寫入 Audit-2027.csv。\n- 保留原始順序。')
    measures = ('Encrypt the transfer and verify the recipient.\n\nKeep the [transfer record](https://example.org/transfer?a=1&b=2).\n\n'
                '- Check the recipient agreement.\n- Record the verification date.') if locale == 'en' else (
                '以加密方式傳輸，並確認接收者身分。\n\n保留[傳輸紀錄](https://example.org/transfer?a=1&b=2)。\n\n'
                '- 檢查與接收者的協議。\n- 記錄確認日期。')
    complete[paths['additional']] = {'type': 'StringReply', 'value': prose}
    complete[paths['transfer']] = answer('cpersGdprSafeguardsTransferYesAUuid')
    complete[paths['measures']] = {'type': 'StringReply', 'value': measures}
    missing = copy.deepcopy(complete)
    del missing[paths['legal']]; del missing[paths['other']]; del missing[paths['measures']]
    negative = copy.deepcopy(complete)
    negative[paths['transfer']] = answer('cpersGdprSafeguardsTransferNoAUuid')
    del negative[paths['measures']]
    return {'personal-followups-empty': partial, 'personal-transfer-missing': missing,
            'personal-transfer-complete': complete, 'personal-transfer-no': negative,
            **{k: old[k] for k in ['personal-data-partial', 'empty', 'negative', 'preservation-complete']}}


def generate(output):
    for locale in ['en', 'zh-Hant']:
        folder = output/locale; folder.mkdir(parents=True, exist_ok=True)
        for name, replies in personal_data_cases(locale).items():
            target = folder/(name+'.json')
            if target.exists():
                existing = json.loads(target.read_text())
                events = json.loads((folder/existing['events_file']).read_text())
                assert {e['path']: e['value'] for e in events} == replies, (locale, name)
                continue
            events = [{'type': 'SetReplyEvent', 'uuid': uid('personal-followups/'+name+'/'+p), 'path': p, 'value': v}
                      for p, v in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            event_file = folder/(name+'.events.json'); assert not event_file.exists()
            event_file.write_text(json.dumps(events, ensure_ascii=False, indent=2)+'\n')
            recipe = json.loads((ROOT/'fixtures/pilot'/locale/'preservation-complete.json').read_text())
            recipe.update(name='Personal data follow-up QA / '+name, events_file=name+'.events.json')
            target.write_text(json.dumps(recipe, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT/'fixtures/pilot')
    generate(p.parse_args().output)
