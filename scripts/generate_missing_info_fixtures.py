"""Deterministic missing-info regressions plus complete/long controls; public synthetic data."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, uid, generate
from generate_preservation_fixtures import preservation_cases
from generate_budget_fixtures import budget_cases


def drop(replies, prefix, field):
    key = prefix + '.' + IDS[field]
    for path in list(replies):
        if path == key or path.startswith(key + '.'): replies.pop(path)


def missing_info_cases(locale):
    base = preservation_cases(locale)['preservation-complete']
    costs = next(p for p in base if p.endswith(IDS['costQUuid']))
    first, second = [costs + '.' + item for item in base[costs]['value']]
    mixed = copy.deepcopy(base)
    drop(mixed, first, 'costDescriptionQUuid'); drop(mixed, first, 'costCurrencyQUuid')
    drop(mixed, second, 'costAmountQUuid')
    third = costs + '.' + uid('missing-info/third-resource')
    mixed[costs]['value'].append(third.rsplit('.', 1)[1])
    for path, value in base.items():
        if path.startswith(second + '.'): mixed[third + path[len(second):]] = copy.deepcopy(value)
    for field in ['costTitleQUuid', 'costAllocationQUuid', 'costCoverQUuid']: drop(mixed, third, field)
    result = {'empty': {}, 'negative': generate(locale)['negative'], 'partial': generate(locale)['partial'],
              'preservation-partial': preservation_cases(locale)['preservation-partial'], 'budget-mixed-gaps': mixed}
    for name, field in [('amount', 'costAmountQUuid'), ('currency', 'costCurrencyQUuid'), ('funding', 'costCoverQUuid')]:
        row = budget_cases(locale)['budget-long']; drop(row, first, field)
        result['budget-long-no-' + name] = row
    row = copy.deepcopy(base)
    drop(row, IDS['creatingCUuid'], 'collectPersonalQUuid')
    parent = IDS['creatingCUuid'] + '.' + IDS['collectPersonalQUuid']
    gdpr = parent + '.' + IDS['collectPersonalYesAUuid'] + '.' + IDS['cpersGdprQUuid']
    row[parent] = {'type': 'AnswerReply', 'value': IDS['collectPersonalYesAUuid']}
    row[gdpr] = {'type': 'AnswerReply', 'value': IDS['cpersGdprExploreAUuid']}
    row[gdpr + '.' + IDS['cpersGdprExploreAUuid'] + '.' + IDS['cpersGdprLegalBasisQUuid']] = {
        'type': 'AnswerReply', 'value': IDS['cpersGdprLegalBasisPublicAUuid']}
    result['personal-data-partial'] = row
    result['preservation-complete'] = base
    result['budget-long'] = budget_cases(locale)['budget-long']
    return result


if __name__ == '__main__':
    for locale in ['en', 'zh-Hant']:
        folder = ROOT/'fixtures/pilot'/locale
        for name, replies in missing_info_cases(locale).items():
            target = folder/(name+'.json')
            if target.exists():
                existing = json.loads(target.read_text())
                events = json.loads((folder/existing['events_file']).read_text())
                assert {e['path']: e['value'] for e in events} == replies, name
                continue
            events = [{'type': 'SetReplyEvent', 'uuid': uid('missing-info/'+name+'/'+p), 'path': p, 'value': v}
                      for p, v in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder/(name+'.events.json')).write_text(json.dumps(events, ensure_ascii=False, indent=2)+'\n')
            recipe = json.loads((folder/'preservation-complete.json').read_text())
            recipe.update(name='Missing information QA / '+name, events_file=name+'.events.json')
            target.write_text(json.dumps(recipe, ensure_ascii=False, indent=2)+'\n')
