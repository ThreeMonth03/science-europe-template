"""Three reachable gap controls, preserving every other existing synthetic reply."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, uid

CASES={
    'archive-migration-gaps':('personal-transfer-complete',['archivedAfterFormatsQUuid','archivedAfterMediaQUuid']),
    'archive-single-gap':('personal-transfer-complete',['archivedAfterPayerQUuid']),
    'budget-long-archive-gaps':('budget-long-no-currency',['archivedAfterPayerQUuid','archivedAfterYearsQUuid',
        'archivedAfterExtendWhoQUuid','archivedAfterExtendBasisQUuid','archivedAfterFormatsQUuid']),
}


def cases(locale):
    root=ROOT/'fixtures/pilot'/locale;result={}
    for name,(source,fields) in CASES.items():
        events=json.loads((root/(source+'.events.json')).read_text())
        replies={e['path']:e['value'] for e in events}
        for field in fields:
            matches=[k for k in replies if k.endswith(IDS[field])];assert len(matches)==1
            replies.pop(matches[0])
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
            recipe=json.loads((root/(CASES[name][0]+'.json')).read_text())
            recipe.update(name='Archive gap panel QA / '+name,events_file=events.name)
            events.write_text(json.dumps(values,ensure_ascii=False,indent=2)+'\n')
            target.write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
