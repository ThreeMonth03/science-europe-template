"""Public synthetic long and many-entry Q8 controls; never overwrite fixtures."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, uid
from generate_personal_data_fixtures import personal_data_cases


def q8_word_cases(locale):
    old = personal_data_cases(locale); base = old['personal-transfer-complete']
    references = next(p for p in base if p.endswith(IDS['refDataQUuid']))
    first = references+'.'+base[references]['value'][0]
    used = first+'.'+IDS['refDataUseQUuid']+'.'+IDS['refDataUseYesAUuid']
    conditions = used+'.'+IDS['refDataConditionsQUuid']
    long = copy.deepcopy(base)
    long[conditions] = {'type': 'AnswerReply', 'value': IDS['refDataConditionsOtherAUuid']}
    text = 'Retain Original-v1.2.csv, the request record and the review date.' if locale == 'en' else '保留 Original-v1.2.csv、申請紀錄與審查日期。'
    prose = '\n\n'.join(f'Q8-PARA-{i:03d}: {text}' for i in range(1, 31))
    prose += ('\n\n- Keep **original wording**.\n- See the [access record](https://example.org/access?a=1&b=2).'
              if locale == 'en' else '\n\n- 保留**原始措辭**。\n- 參閱[取用紀錄](https://example.org/access?a=1&b=2)。')
    long[conditions+'.'+IDS['refDataConditionsOtherAUuid']+'.'+IDS['refDataConditionsOtherQUuid']] = {'type':'StringReply', 'value':prose}
    many = copy.deepcopy(base)
    for i in range(3, 9):
        item = uid('q8-word/reference-'+str(i)); prefix = references+'.'+item
        many[references]['value'].append(item)
        for path, value in base.items():
            if path.startswith(first+'.'): many[prefix+path[len(first):]] = copy.deepcopy(value)
        many[prefix+'.'+IDS['refDataNameQUuid']] = {'type':'StringReply', 'value':
            ('Open coastal observations — station ' if locale == 'en' else '開放海岸觀測資料——測站 ')+str(i)}
    return {'q8-long-permissions':long, 'q8-many-references':many,
            **{k:old[k] for k in ['personal-transfer-complete','empty','negative','preservation-complete']}}


if __name__ == '__main__':
    for locale in ['en','zh-Hant']:
        folder = ROOT/'fixtures/pilot'/locale
        for name,replies in q8_word_cases(locale).items():
            target = folder/(name+'.json')
            if target.exists():
                recipe = json.loads(target.read_text()); events=json.loads((folder/recipe['events_file']).read_text())
                assert {e['path']:e['value'] for e in events} == replies
                continue
            event_file = folder/(name+'.events.json'); assert not event_file.exists()
            events=[{'type':'SetReplyEvent','uuid':uid('q8-word/'+name+'/'+p),'path':p,'value':v}
                    for p,v in sorted(replies.items(),key=lambda x:(x[0].count('.'),x[0]))]
            event_file.write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
            recipe=json.loads((folder/'preservation-complete.json').read_text())
            recipe.update(name='Q8 Word continuity QA / '+name,events_file=event_file.name)
            target.write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
