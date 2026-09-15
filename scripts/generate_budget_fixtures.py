"""Budget-only long/many counterexamples; keep previous fixtures unchanged."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, uid
from generate_preservation_fixtures import preservation_cases


def budget_cases(language):
    base=preservation_cases(language)['preservation-complete']
    costs=next(k for k in base if k.endswith(IDS['costQUuid']))
    first=costs+'.'+base[costs]['value'][0]
    long=copy.deepcopy(base)
    key=first+'.'+IDS['costDescriptionQUuid']
    sentence='Retain the original resource justification and its audit trail.' if language=='en' else '保留此資源用途的原始說明及其查核紀錄。'
    long[key]['value']+='\n\n'+'\n\n'.join(f'BUDGET-PARA-{i:02d}: {sentence}' for i in range(1,61))
    long[key]['value']+='\n\n- Preserve Budget-2027-12-31.csv.\n- Keep the [funding record](https://example.org/budget/record).'
    many=copy.deepcopy(base)
    for n in range(3,9):
        item=uid('budget/resource-'+str(n)); many[costs]['value'].append(item)
        target=costs+'.'+item
        for k,v in base.items():
            if k.startswith(first+'.'): many[target+k[len(first):]]=copy.deepcopy(v)
        many[target+'.'+IDS['costTitleQUuid']]['value']=('Budget resource ' if language=='en' else '預算資源 ')+str(n)
        many[target+'.'+IDS['costAmountQUuid']]['value']=str(n*100)
    return {'budget-long':long,'budget-many':many}


if __name__=='__main__':
    for language in ['en','zh-Hant']:
        folder=ROOT/'fixtures/pilot'/language
        for case,replies in budget_cases(language).items():
            events=[{'type':'SetReplyEvent','uuid':uid(case+'/'+p),'path':p,'value':v} for p,v in sorted(replies.items(),key=lambda kv:(kv[0].count('.'),kv[0]))]
            (folder/(case+'.events.json')).write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
            recipe=json.loads((folder/'preservation-complete.json').read_text())
            recipe.update(name='Science Europe budget pagination / '+case,events_file=case+'.events.json')
            (folder/(case+'.json')).write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
