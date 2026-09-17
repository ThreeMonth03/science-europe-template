"""New reachable public Q3 fixtures; do not rewrite older fixture inputs."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_retention_fixtures import retention_cases
from generate_storage_gap_fixtures import AMOUNT

PARENT = path('creatingCUuid', 'metadataQUuid')
DICTIONARY = path(PARENT, 'metadataExploreAUuid', 'metadataDictionaryQUuid')
ACCESS = path('accessCUuid', 'metadataOpenQUuid')
REASON = path(ACCESS, 'metadataOpenNoAUuid', 'metadataOpenNoExplainQUuid')
INSTRUCTIONS = path(ACCESS, 'metadataOpenYesAUuid', 'metadataOpenInstrQUuid')
FORM = path(ACCESS, 'metadataOpenYesAUuid', 'metadataOpenFormQUuid')
CASES = ['metadata-dictionary', 'metadata-dictionary-no', 'metadata-partial', 'metadata-private',
         'metadata-private-text', 'metadata-complete', 'empty', 'negative']


def metadata_cases(language):
    answer = lambda name: {'type': 'AnswerReply', 'value': IDS[name]}
    result = {}
    for name, state in [('metadata-dictionary', 'Yes'), ('metadata-dictionary-no', 'No')]:
        result[name] = {PARENT: answer('metadataExploreAUuid'), DICTIONARY: answer('metadataDictionary'+state+'AUuid')}
    for name in ['metadata-partial', 'metadata-private', 'metadata-private-text', 'metadata-complete']:
        values = copy.deepcopy(retention_cases(language)['structured'])
        if name == 'metadata-partial':
            del values[INSTRUCTIONS]; del values[FORM]
            values[AMOUNT] = {'type': 'StringReply', 'value': ' \t '}
        else:
            values[DICTIONARY] = answer('metadataDictionaryYesAUuid')
            if name.startswith('metadata-private'):
                values[ACCESS] = answer('metadataOpenNoAUuid')
                del values[INSTRUCTIONS]; del values[FORM]
                text = ' \t ' if name == 'metadata-private' else (
                    'Access is restricted during the project.\n\nKeep **Original.csv** and document the decision.\n\n- Retain CHANGELOG.md.\n- Review [access conditions](https://example.org/metadata-policy?a=1&b=2).'
                    if language == 'en' else
                    '計畫期間限制取用。\n\n保留 **Original.csv**，並記錄決策依據。\n\n- 保留 CHANGELOG.md。\n- 檢視[取用條件](https://example.org/metadata-policy?a=1&b=2)。')
                values[REASON] = {'type': 'StringReply', 'value': text}
            else:
                values[INSTRUCTIONS] = answer('metadataOpenInstrNoAUuid')
                values[FORM] = answer('metadataOpenFormNoAUuid')
        result[name] = values
    return result


if __name__ == '__main__':
    for language in ['en', 'zh-Hant']:
        folder = ROOT/'fixtures/pilot'/language
        for name, values in metadata_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(name+'/'+p), 'path': p, 'value': v}
                      for p, v in sorted(values.items(), key=lambda x: (x[0].count('.'), x[0]))]
            (folder/(name+'.events.json')).write_text(json.dumps(events, ensure_ascii=False, indent=2)+'\n')
            recipe = json.loads((folder/'structured.json').read_text())
            recipe.update(name='Science Europe metadata follow-up experiment', events_file=name+'.events.json')
            (folder/(name+'.json')).write_text(json.dumps(recipe, ensure_ascii=False, indent=2)+'\n')
