"""Additional synthetic Q2 reading cases; existing fixtures stay unchanged."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_retention_fixtures import retention_cases


def format_reading_case(language):
    replies = copy.deepcopy(retention_cases(language)['structured'])
    formats = path('creatingCUuid', 'formatsQUuid')
    for key in list(replies):
        if key == formats or key.startswith(formats+'.'): del replies[key]
    replies[formats] = {'type': 'ItemListReply', 'value': []}
    for label, mode, quantities in [
        ('CSV (UTF-8)', 'Total', {'TotalGB': '120'}),
        ('ZERO / v1.2', 'Total', {'TotalGB': '0'}),
        ('SMALL', 'Small', {}),
        ('FILES / station_YYYYMMDD.csv', 'FileSize', {'Files': '12', 'FileGB': '0.0001'}),
    ]:
        ident = uid('format-reading/'+label); replies[formats]['value'].append(ident)
        prefix = path(formats,ident)
        replies[path(prefix,'formatsNameQUuid')] = {'type':'IntegrationReply','value':{'type':'PlainType','value':label}}
        for question,answer in [('IsStandard','IsStandardYes'),('IsLTSuitable','IsLTSuitableYes'),('Volume','Volume'+mode)]:
            replies[path(prefix,'formats'+question+'QUuid')] = {'type':'AnswerReply','value':IDS['formats'+answer+'AUuid']}
        for suffix,value in quantities.items():
            replies[path(prefix,'formatsVolumeQUuid','formatsVolume'+mode+'AUuid','formatsVolume'+suffix+'QUuid')] = {'type':'StringReply','value':value}
    return replies


if __name__ == '__main__':
    for language in ['en','zh-Hant']:
        folder = ROOT/'fixtures/pilot'/language; name = 'format-reading'
        values = format_reading_case(language)
        events = [{'type':'SetReplyEvent','uuid':uid(name+'/'+p),'path':p,'value':v}
                  for p,v in sorted(values.items(),key=lambda x:(x[0].count('.'),x[0]))]
        (folder/(name+'.events.json')).write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
        recipe = json.loads((folder/'structured.json').read_text())
        recipe.update(name='Science Europe format reading experiment',events_file=name+'.events.json')
        (folder/(name+'.json')).write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
