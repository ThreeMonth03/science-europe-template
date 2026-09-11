"""Record relevant compiled-KM questions and verify option membership, not just UUID presence."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from dsw_document_template_tool.api import DSWApiClient

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ['sharedWorkspaceQUuid', 'sharedSpecialistsQUuid', 'sharedReliableBackupQUuid',
             'archivedDuringQUuid', 'archivedDuringReQUuid', 'archivedDuringReFrequentBackupsQUuid',
             'archivedDuringRelyQUuid', 'archiveMediumQUuid', 'archiveRemoteQUuid']
MEMBERSHIP = {
    'sharedSpecialistsQUuid': ['sharedSpecialistsYesAUuid', 'sharedSpecialistsNoAUuid'],
    'archivedDuringQUuid': ['archivedDuringYesAUuid', 'archivedDuringNoAUuid'],
    'archivedDuringReQUuid': ['archivedDuringReYesAUuid', 'archivedDuringReNoAUuid'],
    'archivedDuringReFrequentBackupsQUuid': ['archivedDuringReFrequentBackupsYesAUuid', 'archivedDuringReFrequentBackupsNoAUuid'],
    'archivedDuringRelyQUuid': ['archivedDuringRelyYesAUuid', 'archivedDuringRelyNoAUuid'],
    'archiveMediumQUuid': ['archiveMediumDiskAUuid', 'archiveMediumTapeAUuid', 'archiveMediumOtherAUuid'],
    'archiveRemoteQUuid': ['archiveRemoteYesAUuid', 'archiveRemoteNoAUuid'],
}


def inspect(km, ids):
    e = km['entities']; paths = {}
    def visit(uid, prefix):
        question = e['questions'][uid]; paths[uid] = prefix + [uid]
        for aid in question.get('answerUuids', []):
            for child in e['answers'][aid]['followUpUuids']: visit(child, prefix + [uid, aid])
        for child in question.get('itemTemplateQuestionUuids', []): visit(child, prefix + [uid, 'ITEM'])
    for c in km['chapterUuids']:
        for q in e['chapters'][c]['questionUuids']: visit(q, [c])
    for question, answers in MEMBERSHIP.items():
        for answer in answers:
            assert ids[answer] in e['questions'][ids[question]]['answerUuids'], (question, answer)
    rows = []
    for binding in QUESTIONS:
        uid = ids[binding]; q = e['questions'][uid]
        rows.append({'binding': binding, 'uuid': uid, 'path': paths[uid], 'title': q['title'], 'text': q.get('text'),
                     'answers': [{'uuid': aid, 'label': e['answers'][aid]['label']} for aid in q.get('answerUuids', [])]})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    ids = dict(re.findall(r'set\s+(\w+)\s*=\s*"([0-9a-f-]{36})"', (ROOT / 'src/uuids.j2').read_text()))
    client = DSWApiClient(api_url='http://localhost:13300/wizard-api', verify_ssl=True)
    project = None; reports = {}
    try:
        client.login(email='albert.einstein@example.com', password='password')
        for language, file in [('en', 'root-2.7.0.km'), ('zh-Hant', 'root-zh-hant-2.7.0.km')]:
            bundle = ROOT / 'fixtures/knowledge-models' / file
            project = client.create_project_from_package(name='Synthetic storage mapping audit', knowledge_model_package_id=str(bundle), question_tag_uuids=[], visibility='PrivateProjectVisibility', sharing='RestrictedProjectSharing')
            reports[language] = {'km_sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(), 'questions': inspect(client.get_project_questionnaire(project['uuid'])['knowledgeModel'], ids)}
            client.delete_project(project['uuid']); project = None
    finally:
        if project: client.delete_project(project['uuid'])
        client.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'knowledge_models': reports, 'selected_option_membership_passed': True,
        'release_acceptance': False, 'limits': ['Selected storage/archival paths only', 'Frequent-backup need is not an operational schedule', 'Archive medium/remote decision do not name storage sites']}, ensure_ascii=False, indent=2) + '\n')
    print('Selected option membership and question paths verified in both KMs')


if __name__ == '__main__': main()
