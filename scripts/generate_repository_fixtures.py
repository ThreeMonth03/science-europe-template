"""Missing middle destination and a genuinely long authored repository answer."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_answer_state_fixtures import answer_state_cases


def repository_cases(language):
    base = answer_state_cases(language)['support-mixed']
    data = path('preservingCUuid', 'producedDataQUuid')
    dist = path(data, base[data]['value'][0], 'isPublishedDataQUuid', 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
    gap = copy.deepcopy(base)
    missing = path(dist, base[dist]['value'][1], 'publishedDataRepositoryKindQUuid')
    for key in list(gap):
        if key == missing or key.startswith(missing + '.'): gap.pop(key)
    long = copy.deepcopy(base)
    kind = path(dist, base[dist]['value'][0], 'publishedDataRepositoryKindQUuid')
    for key in list(long):
        if key.startswith(kind + '.'): long.pop(key)
    long[kind] = {'type': 'AnswerReply', 'value': IDS['publishedDataRepositoryDomainSpecificAUuid']}
    contact = path(kind, 'publishedDataRepositoryDomainSpecificAUuid', 'domainSpecificRepoContactBeforeQUuid')
    long[contact] = {'type': 'AnswerReply', 'value': IDS['domainSpecificRepoContactBeforeOtherAUuid']}
    text = ('The repository review will retain each supplied decision record without merging its paragraph.' if language == 'en'
            else '資料儲存庫的審查將保留各項決策紀錄，並維持填答者原有的段落。')
    value = '\n\n'.join(f'{text} Repo-review-2027-{i:03d}.csv' for i in range(1, 61))
    long[path(contact, 'domainSpecificRepoContactBeforeOtherAUuid', 'domainSpecificRepoContactBeforeOtherQUuid')] = {'type': 'StringReply', 'value': value}
    return {'repository-gap': gap, 'repository-long': long}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, replies in repository_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p, value in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'structured.json').read_text())
            recipe.update(name=f'Science Europe repository reading / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
