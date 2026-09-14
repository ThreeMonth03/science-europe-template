"""Inventory compiled public KM paths and static template references, not answer coverage."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from jinja2 import Environment, nodes
from dsw_document_template_tool.api import DSWApiClient

ROOT = Path(__file__).resolve().parents[1]


def inventory(km, root=ROOT):
    ids = dict(re.findall(r'set\s+(\w+)\s*=\s*"([0-9a-f-]{36})"', (root / 'src/uuids.j2').read_text()))
    env = Environment(extensions=['jinja2.ext.do'])
    references = {}
    for file in sorted((root / 'src').rglob('*.j2')):
        for node in env.parse(file.read_text()).find_all(nodes.Getattr):
            if isinstance(node.node, nodes.Name) and node.node.name == 'uuids' and node.attr in ids:
                references.setdefault(ids[node.attr], set()).add(str(file.relative_to(root)))
    e = km['entities']; rows = []
    def visit(uid, prefix):
        assert uid not in prefix, 'Cyclic KM question path'
        q = e['questions'][uid]; path = prefix + [uid]
        choices = [{'uuid': a, 'label': e['answers'][a]['label'],
                    'follow_up_uuids': e['answers'][a].get('followUpUuids', [])}
                   for a in q.get('answerUuids', [])]
        rows.append({'uuid': uid, 'path': path, 'type': q['questionType'],
                     'title': q['title'], 'guidance': q.get('text'), 'choices': choices,
                     'multi_choices': [{'uuid': c, 'label': e['choices'][c]['label']} for c in q.get('choiceUuids', [])],
                     'bindings': sorted(n for n,v in ids.items() if v == uid),
                     'static_template_references': sorted(references.get(uid, []))})
        for choice in choices:
            for child in choice['follow_up_uuids']: visit(child, path + [choice['uuid']])
        for child in q.get('itemTemplateQuestionUuids', []): visit(child, path + ['ITEM'])
    for chapter in km['chapterUuids']:
        for q in e['chapters'][chapter]['questionUuids']: visit(q, [chapter])
    return {'chapters': [{'uuid': c, 'title': e['chapters'][c]['title']} for c in km['chapterUuids']],
            'questions': rows, 'reachable_question_count': len({r['uuid'] for r in rows}),
            'unreachable_question_uuids': sorted(set(e['questions']) - {r['uuid'] for r in rows})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Do not overwrite an earlier audit'
    client = DSWApiClient(api_url='http://localhost:13300/wizard-api', verify_ssl=True)
    project = None; reports = {}
    try:
        client.login(email='albert.einstein@example.com', password='password')
        for language, name in [('en', 'root-2.7.0.km'), ('zh-Hant', 'root-zh-hant-2.7.0.km')]:
            bundle = ROOT / 'fixtures/knowledge-models' / name
            project = client.create_project_from_package(name='Synthetic answer destination audit',
                knowledge_model_package_id=str(bundle), question_tag_uuids=[],
                visibility='PrivateProjectVisibility', sharing='RestrictedProjectSharing')
            reports[language] = {'km_sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
                                **inventory(client.get_project_questionnaire(project['uuid'])['knowledgeModel'])}
            client.delete_project(project['uuid']); project = None
    finally:
        if project: client.delete_project(project['uuid'])
        client.close()
    report = {'scope': 'Compiled public Common KM 2.7.0 paths and static Jinja references only',
              'source_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
              'source_dirty': bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).strip()),
              'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'template_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted((ROOT / 'src').rglob('*.j2'))},
              'knowledge_models': reports, 'release_acceptance': False,
              'limits': ['A static reference does not prove a reachable answer appears in output',
                         'No reference does not prove a question is required by Science Europe',
                         'No project answers or production credentials are exported']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({language: r['reachable_question_count'] for language,r in reports.items()}))


if __name__ == '__main__': main()
