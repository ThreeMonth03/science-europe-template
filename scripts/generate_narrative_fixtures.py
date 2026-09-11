"""Additional counterexamples; earlier storage fixtures remain byte-identical."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_storage_fixtures import storage_cases


def narrative_cases(language):
    original = storage_cases(language)['storage-sharing']
    archive = path('preservingCUuid', 'archivedDuringQUuid')
    archive_only = {k: copy.deepcopy(v) for k, v in original.items() if k == archive or k.startswith(archive + '.')}
    for k in archive_only:
        if k.endswith(IDS['archivedDuringReFrequentBackupsQUuid']):
            archive_only[k]['value'] = IDS['archivedDuringReFrequentBackupsNoAUuid']
    long = copy.deepcopy(original)
    key = next(k for k in long if k.endswith(IDS['licenseRestrictConditionsQUuid']))
    sentence = ('Extended access condition remains in the document.' if language == 'en'
                else '延伸取用條件仍須完整保留於文件中。')
    long[key]['value'] += '\n\n' + '\n\n'.join(sentence + f' [{i:02d}]' for i in range(1, 81))
    return {'archive-only': archive_only, 'narrative-long': long}


if __name__ == '__main__':
    for language in ('en', 'zh-Hant'):
        folder = ROOT / 'fixtures/pilot' / language
        for case, replies in narrative_cases(language).items():
            events = [{'type': 'SetReplyEvent', 'uuid': uid(f'{case}/{p}'), 'path': p, 'value': value}
                      for p, value in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
            (folder / f'{case}.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
            recipe = json.loads((folder / 'structured.json').read_text())
            recipe.update(name=f'Science Europe narrative experiment / {case}', events_file=f'{case}.events.json')
            (folder / f'{case}.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
