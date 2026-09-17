"""New public synthetic Q3 cases; never rewrite older fixture inputs."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_retention_fixtures import retention_cases

PARENT = path('processingCUuid', 'storageConvQUuid')
SPACE = path(PARENT, 'storageConvExploreAUuid', 'storageSpaceQUuid')
AMOUNT = path(SPACE, 'storageSpaceSpecifyAUuid', 'storageSpaceSpecifyQUuid')
METADATA = path('accessCUuid', 'metadataOpenQUuid')
CASES = ['storage-missing', 'storage-partial', 'storage-zero', 'storage-complete', 'empty', 'negative']


def storage_cases(language):
    minimal = {PARENT: {'type': 'AnswerReply', 'value': IDS['storageConvExploreAUuid']},
               SPACE: {'type': 'AnswerReply', 'value': IDS['storageSpaceSpecifyAUuid']},
               METADATA: {'type': 'AnswerReply', 'value': IDS['metadataOpenYesAUuid']}}
    result = {'storage-missing': minimal}
    for name, value in [('storage-partial', ' \t '), ('storage-zero', '0'), ('storage-complete', '2048')]:
        replies = copy.deepcopy(retention_cases(language)['structured'])
        replies[AMOUNT] = {'type': 'StringReply', 'value': value}
        result[name] = replies
    return result


if __name__ == '__main__':
    for language in ['en', 'zh-Hant']:
        folder = ROOT/'fixtures/pilot'/language
        for name, values in storage_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(name+'/'+p), 'path': p, 'value': v}
                      for p, v in sorted(values.items(), key=lambda x: (x[0].count('.'), x[0]))]
            (folder/(name+'.events.json')).write_text(json.dumps(events, ensure_ascii=False, indent=2)+'\n')
            recipe = json.loads((folder/'structured.json').read_text())
            recipe.update(name='Science Europe storage capacity experiment', events_file=name+'.events.json')
            (folder/(name+'.json')).write_text(json.dumps(recipe, ensure_ascii=False, indent=2)+'\n')
