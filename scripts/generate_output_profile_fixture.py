"""One synthetic bilingual pilot: partial facts and authored warning-like prose."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_metadata_fixtures import metadata_cases

CASE = 'profile-partial'
AUTHORED = {
    'en': 'Information not provided: this is authored method text, not a template warning. Keep Original.csv and https://example.org/method?a=1&b=2.',
    'zh-Hant': '尚待補充：這是使用者填寫的方法說明，不是模板提示。保留 Original.csv 與 https://example.org/method?a=1&b=2。',
}


def values(language):
    result = copy.deepcopy(metadata_cases(language)['metadata-partial'])
    quality = path('creatingCUuid', 'measuredQUuid', 'measuredYesAUuid', 'measuredDataQUuid', uid('new-measurements'),
                   'measuredDataQualityQUuid', 'measuredDataQualityYesAUuid')
    for question in ('mdQualityCalibratingQUuid', 'mdQualityValidationQUuid'):
        del result[path(quality, question)]
    purpose = path('reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid', 'refDataQUuid', uid('dataset-1'),
                   'refDataUseQUuid', 'refDataUseYesAUuid', 'refDataUsageQUuid')
    result[purpose]['value'] += '\n\n' + AUTHORED[language]
    return result


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        recipe = folder / (CASE + '.json')
        events_file = folder / (CASE + '.events.json')
        assert not recipe.exists() and not events_file.exists(), 'Do not overwrite earlier fixtures'
        events = [{'type': 'SetReplyEvent', 'uuid': uid(CASE + '/' + p), 'path': p, 'value': value}
                  for p, value in sorted(values(language).items(), key=lambda x: (x[0].count('.'), x[0]))]
        events_file.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        config = json.loads((folder / 'metadata-partial.json').read_text())
        config.update(name='Science Europe output profiles pilot', events_file=events_file.name)
        recipe.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
