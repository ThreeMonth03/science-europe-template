"""New synthetic counterexamples; never modify the earlier comparison inputs."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_retention_fixtures import retention_cases

METHODS = ('Calibrating', 'Repetition', 'Standardized', 'Validation', 'PeerReview', 'Vocabularies', 'Consistency')


def quality_cases(language):
    rich = copy.deepcopy(retention_cases(language)['structured'])
    datasets = path('creatingCUuid', 'measuredQUuid', 'measuredYesAUuid', 'measuredDataQUuid')
    first = path(datasets, rich[datasets]['value'][0])
    quality = path(first, 'measuredDataQualityQUuid')
    prefix = path(quality, 'measuredDataQualityYesAUuid')
    for name in METHODS:
        rich[path(prefix, f'mdQuality{name}QUuid')] = {'type': 'AnswerReply', 'value': IDS[f'mdQuality{name}YesAUuid']}
    second = uid('quality-second-dataset')
    rich[datasets]['value'].append(second)
    second_path = path(datasets, second)
    rich[path(second_path, 'measuredDataNameQUuid')] = {'type': 'StringReply', 'value': 'Salinity observations' if language == 'en' else '鹽度觀測資料'}
    second_quality = path(second_path, 'measuredDataQualityQUuid')
    rich[second_quality] = {'type': 'AnswerReply', 'value': IDS['measuredDataQualityYesAUuid']}
    second_prefix = path(second_quality, 'measuredDataQualityYesAUuid')
    rich[path(second_prefix, 'mdQualityValidationQUuid')] = {'type': 'AnswerReply', 'value': IDS['mdQualityValidationYesAUuid']}
    other = path(second_prefix, 'mdQualityOtherQUuid')
    rich[other] = {'type': 'AnswerReply', 'value': IDS['mdQualityOtherYesAUuid']}
    authored = ('Preserve v1.2 and the threshold 0.05.\n\nThis is a separate authored paragraph!\n\n- Retain the original record.\n- Record the reason for each correction.\n\n' if language == 'en' else
                '保留 v1.2 與門檻值 0.05。\n\n這是使用者另外撰寫的段落！\n\n- 保留原始紀錄。\n- 記錄每次更正的原因。\n\n')
    sentence = 'Extended quality procedure remains separate.' if language == 'en' else '延伸品質管控程序須保留獨立段落。'
    authored += '\n\n'.join(sentence + f' [{i:02d}]' for i in range(1, 21))
    rich[path(other, 'mdQualityOtherYesAUuid', 'mdQualityOtherWhatQUuid')] = {'type': 'StringReply', 'value': authored}
    partial = copy.deepcopy(rich)
    # Unknown first dataset quality; second says Yes but has no method/details.
    for key in list(partial):
        if key == quality or key.startswith(quality + '.') or key.startswith(second_prefix + '.'):
            del partial[key]
    partial[other] = {'type': 'AnswerReply', 'value': IDS['mdQualityOtherYesAUuid']}
    return {'quality-rich': rich, 'quality-partial': partial}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, values in quality_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p, value in sorted(values.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'structured.json').read_text())
            recipe.update(name=f'Science Europe quality reading experiment / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
