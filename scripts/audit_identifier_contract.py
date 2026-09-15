"""Recheck Q13 follow-ups and the synthetic fixture against isolated compiled KMs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from dsw_document_template_tool.api import DSWApiClient
from generate_pilot_fixtures import IDS
from validate_pilot_fixtures import check

ROOT=Path(__file__).resolve().parents[1]
FIELDS=['publishedDataIdentifierQUuid','publishedDataIdentifierAssignsQUuid','publishedDataIdentifierResolvableQUuid']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain']).strip(), 'Require a committed source'
    report={'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'release_acceptance':False,'locales':{}}
    client=DSWApiClient(api_url='http://localhost:13300/wizard-api',verify_ssl=True)
    project=None
    try:
        client.login(email='albert.einstein@example.com',password='password')
        for locale,filename in [('en','root-2.7.0.km'),('zh-Hant','root-zh-hant-2.7.0.km')]:
            bundle=ROOT/'fixtures/knowledge-models'/filename
            project=client.create_project_from_package(name='Synthetic identifier contract audit',knowledge_model_package_id=str(bundle),
                question_tag_uuids=[],visibility='PrivateProjectVisibility',sharing='RestrictedProjectSharing')
            km=client.get_project_questionnaire(project['uuid'])['knowledgeModel']; entities=km['entities']
            fields={key:{'question':entities['questions'][IDS[key]],
                         'answers':[entities['answers'][a] for a in entities['questions'][IDS[key]]['answerUuids']]} for key in FIELDS}
            parent=entities['answers'][IDS['publishedDataIdentifierYesAUuid']]
            assert {IDS[key] for key in FIELDS[1:]}<=set(parent['followUpUuids'])
            fixture=ROOT/'fixtures/pilot'/locale/'identifier-followups.events.json'
            errors=check(km,{event['path']:event['value'] for event in json.loads(fixture.read_text())})
            assert not errors,errors
            report['locales'][locale]={'km_sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
                'fields':fields,'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'fixture_errors':errors}
            client.delete_project(project['uuid']); project=None
    finally:
        if project: client.delete_project(project['uuid'])
        client.close()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'locales':list(report['locales']),'fixture_errors':0}))


if __name__=='__main__': main()
