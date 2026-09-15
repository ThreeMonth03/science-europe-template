"""Public Q9 partial flags, many datasets and long authored-purpose controls."""
import copy
import json
from generate_pilot_fixtures import ROOT,IDS,uid
from generate_personal_data_fixtures import personal_data_cases,personal_paths


def q9_word_cases(locale):
    old=personal_data_cases(locale);base=old['personal-transfer-complete']
    parent=IDS['preservingCUuid']+'.'+IDS['producedDataQUuid']
    first,second=[parent+'.'+v for v in base[parent]['value']]
    answer=lambda name:{'type':'AnswerReply','value':IDS[name]}
    partial=copy.deepcopy(base)
    partial[first+'.'+IDS['containPersonalQUuid']]=answer('containPersonalYesAUuid')
    partial.pop(first+'.'+IDS['containSensitiveQUuid'],None)
    partial.pop(second+'.'+IDS['containPersonalQUuid'],None)
    partial[second+'.'+IDS['containSensitiveQUuid']]=answer('containSensitiveNoAUuid')
    third=uid('q9-word/unspecified');partial[parent]['value'].append(third)
    partial[parent+'.'+third+'.'+IDS['producedDataNameQUuid']]={'type':'StringReply','value':
        'Unspecified ethics flags' if locale=='en' else '尚未填寫倫理資訊的資料集'}
    many=copy.deepcopy(base)
    for i in range(3,9):
        item=uid('q9-word/dataset-'+str(i));many[parent]['value'].append(item);prefix=parent+'.'+item
        many[prefix+'.'+IDS['producedDataNameQUuid']]={'type':'StringReply','value':
            ('Ethics dataset ' if locale=='en' else '倫理檢核資料集 ')+str(i)}
        many[prefix+'.'+IDS['containPersonalQUuid']]=answer('containPersonalYesAUuid' if i%2 else 'containPersonalNoAUuid')
        many[prefix+'.'+IDS['containSensitiveQUuid']]=answer('containSensitiveNoAUuid')
    long=copy.deepcopy(base)
    purpose=personal_paths()['gdpr']+'.'+IDS['cpersGdprExploreAUuid']+'.'+IDS['cpersGdprPurposeQUuid']
    sentence='Retain Ethics-v1.2.csv, the original wording and the review record.' if locale=='en' else '保留 Ethics-v1.2.csv、原始措辭及審查紀錄。'
    prose='\n\n'.join(f'Q9-PARA-{i:03d}: {sentence}' for i in range(1,31))
    prose+=('\n\n- Keep **original order**.\n- Consult the [ethics record](https://example.org/ethics?a=1&b=2).'
            if locale=='en' else '\n\n- 保留**原始順序**。\n- 查閱[倫理紀錄](https://example.org/ethics?a=1&b=2)。')
    long[purpose]={'type':'StringReply','value':prose}
    return {'q9-partial-flags':partial,'q9-many-datasets':many,'q9-long-purpose':long,
            **{k:old[k] for k in ['personal-transfer-complete','empty','negative']}}


if __name__=='__main__':
    for locale in ['en','zh-Hant']:
        folder=ROOT/'fixtures/pilot'/locale
        for name,replies in q9_word_cases(locale).items():
            path=folder/(name+'.json')
            if path.exists():
                recipe=json.loads(path.read_text());events=json.loads((folder/recipe['events_file']).read_text())
                assert {e['path']:e['value'] for e in events}==replies
                continue
            eventfile=folder/(name+'.events.json');assert not eventfile.exists()
            events=[{'type':'SetReplyEvent','uuid':uid('q9-word/'+name+'/'+p),'path':p,'value':v}
                    for p,v in sorted(replies.items(),key=lambda x:(x[0].count('.'),x[0]))]
            eventfile.write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
            recipe=json.loads((folder/'preservation-complete.json').read_text());recipe.update(name='Q9 Word reading QA / '+name,events_file=eventfile.name)
            path.write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
