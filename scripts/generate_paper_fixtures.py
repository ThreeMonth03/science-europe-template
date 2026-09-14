"""Full long URL, plain citation, duplicate names and an unanswered paper field."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_preservation_fixtures import preservation_cases

LONG_URL = 'https://example.org/papers/' + 'LongReference2027' * 20 + '?version=V1.2&file=Coast%20Study.csv#Methods'
PLAIN_CITATION = 'Chen & Lin (2027). "Coastal <review>"; doi:10.1234/Coast.v1.2.'


def paper_case(language):
    replies = copy.deepcopy(preservation_cases(language)['preservation-complete'])
    data = path('preservingCUuid', 'producedDataQUuid')
    first, second = replies[data]['value']
    third = uid('paper-references/blank-paper')
    replies[data]['value'].append(third)
    for item, value in [(first, LONG_URL), (second, PLAIN_CITATION), (third, ' \n ')]:
        prefix = path(data, item)
        stage = path(prefix, 'producedDataStageQUuid')
        replies[stage] = {'type': 'AnswerReply', 'value': IDS['producedDataStagePublishedAUuid']}
        replies[path(stage, 'producedDataStagePublishedAUuid', 'producedDataPaperQUuid')] = {'type': 'StringReply', 'value': value}
        replies[path(prefix, 'producedDataNameQUuid')] = copy.deepcopy(replies[path(data, first, 'producedDataNameQUuid')])
    replies[path(data, third, 'isPublishedDataQUuid')] = {'type': 'AnswerReply', 'value': IDS['isPublishedDataYesAUuid']}
    return replies


if __name__ == '__main__':
    for language in ['en', 'zh-Hant']:
        folder = ROOT / 'fixtures/pilot' / language
        replies = paper_case(language)
        events = [{'type': 'SetReplyEvent', 'uuid': uid(f'paper-references/{p}'), 'path': p, 'value': v}
                  for p, v in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
        (folder / 'paper-references.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        recipe = json.loads((folder / 'structured.json').read_text())
        recipe.update(name='Science Europe references / paper-references', events_file='paper-references.events.json')
        (folder / 'paper-references.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
