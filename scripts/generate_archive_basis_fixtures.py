"""Two reachable choice-count controls; existing synthetic answers stay unchanged."""
import copy
import json
from generate_pilot_fixtures import ROOT,IDS,uid
from generate_personal_data_fixtures import personal_data_cases


def cases(locale):
    base=personal_data_cases(locale)['personal-transfer-complete'];result={}
    key=next(p for p in base if p.endswith(IDS['archivedAfterExtendBasisQUuid']))
    for name,choices in [('archive-basis-single',['Budget']),('archive-basis-pair',['Actual','Predicted'])]:
        replies=copy.deepcopy(base)
        replies[key]={'type':'MultiChoiceReply','value':[IDS['archivedAfterExtendBasis'+n+'ChoiceUuid'] for n in choices]}
        result[name]=replies
    return result


if __name__=='__main__':
    for locale in ['en','zh-Hant']:
        root=ROOT/'fixtures/pilot'/locale
        for name,replies in cases(locale).items():
            target=root/(name+'.json');events=root/(name+'.events.json')
            assert not target.exists() and not events.exists()
            values=[{'type':'SetReplyEvent','uuid':uid(name+'/'+p),'path':p,'value':v}
                    for p,v in sorted(replies.items(),key=lambda item:(item[0].count('.'),item[0]))]
            recipe=json.loads((root/'personal-transfer-complete.json').read_text())
            recipe.update(name='Archive basis reading QA / '+name,events_file=events.name)
            events.write_text(json.dumps(values,ensure_ascii=False,indent=2)+'\n')
            target.write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
