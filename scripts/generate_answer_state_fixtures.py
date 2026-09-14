"""One reachable synthetic case with three independently answered repositories."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_preservation_fixtures import preservation_cases


def answer_state_cases(language):
    replies = copy.deepcopy(preservation_cases(language)['preservation-complete'])
    data = path('preservingCUuid', 'producedDataQUuid')
    pub = path(data, replies[data]['value'][0], 'isPublishedDataQUuid')
    dist = path(pub, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
    replies[dist]['value'].append(uid('support-missing-distribution'))
    for item, support, service in zip(replies[dist]['value'], ['Yes', 'No', None], ['Download', 'Simple', 'Advanced']):
        kind = path(dist, item, 'publishedDataRepositoryKindQUuid')
        for key in list(replies):
            if key.startswith(kind + '.'): replies.pop(key)
        replies[kind] = {'type': 'AnswerReply', 'value': IDS['publishedDataRepositorySpecialAUuid']}
        prefix = path(kind, 'publishedDataRepositorySpecialAUuid')
        if support:
            replies[path(prefix, 'specialRepoLongTermSupportQUuid')] = {'type': 'AnswerReply', 'value': IDS[f'specialRepoLongTermSupport{support}AUuid']}
        replies[path(prefix, 'specialRepoServiceLevelQUuid')] = {'type': 'AnswerReply', 'value': IDS[f'specialRepoServiceLevel{service}AUuid']}
    return {'support-mixed': replies}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, replies in answer_state_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p, value in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'structured.json').read_text())
            recipe.update(name=f'Science Europe answer states / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
