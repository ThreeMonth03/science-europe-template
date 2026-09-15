"""Reachable Q13 follow-up gaps, independent negative answers and a complete control."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_preservation_fixtures import preservation_cases


def identifier_case(language):
    replies = copy.deepcopy(preservation_cases(language)['preservation-complete'])
    data = path('preservingCUuid', 'producedDataQUuid')
    distros = path(data, replies[data]['value'][0], 'isPublishedDataQUuid', 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
    first, second = replies[distros]['value']
    third, fourth = [uid('identifier-followups/' + label) for label in ['missing-assigner', 'missing-resolution']]
    source = path(distros, first)
    cloned = [(k,v) for k,v in replies.items() if k.startswith(source + '.')]
    for item in [third, fourth]:
        for key,value in cloned:
            replies[path(distros,item) + key[len(source):]] = copy.deepcopy(value)
    replies[distros]['value'].extend([third, fourth])
    for item,assigns,resolves in [(first,None,None),(second,'InstitDataSteward','No'),
                                 (third,None,'No'),(fourth,'ProjectDataSteward',None)]:
        parent = path(distros,item,'publishedDataIdentifierQUuid')
        replies[parent] = {'type':'AnswerReply','value':IDS['publishedDataIdentifierYesAUuid']}
        for label,choice in [('Assigns',assigns),('Resolvable',resolves)]:
            key = path(parent,'publishedDataIdentifierYesAUuid','publishedDataIdentifier'+label+'QUuid')
            if choice: replies[key] = {'type':'AnswerReply','value':IDS['publishedDataIdentifier'+label+choice+'AUuid']}
            else: replies.pop(key,None)
    return replies


if __name__=='__main__':
    for language in ['en','zh-Hant']:
        folder=ROOT/'fixtures/pilot'/language
        events=[{'type':'SetReplyEvent','uuid':uid('identifier-followups/'+key),'path':key,'value':value}
                for key,value in sorted(identifier_case(language).items(),key=lambda kv:(kv[0].count('.'),kv[0]))]
        (folder/'identifier-followups.events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
        recipe=json.loads((folder/'structured.json').read_text())
        recipe.update(name='Science Europe identifier follow-ups',events_file='identifier-followups.events.json')
        (folder/'identifier-followups.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
