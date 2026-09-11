"""Static template references versus an isolated server's compiled public KM.

Presence is not proof that a branch is reachable or that an answer is rendered.
This report deliberately does not call its counts 'answer coverage'.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from jinja2 import Environment, nodes
from dsw_document_template_tool.api import DSWApiClient

ROOT = Path(__file__).resolve().parents[1]


def audit(km):
    ids = dict(re.findall(r'set\s+(\w+)\s*=\s*"([0-9a-f-]{36})"', (ROOT / 'src/uuids.j2').read_text()))
    entities = {key: value for group in km['entities'].values() if isinstance(group, dict) for key, value in group.items()}
    env = Environment(extensions=['jinja2.ext.do'])
    result = []
    for file in sorted((ROOT / 'src/questions').glob('*.html.j2')):
        references = sorted({node.attr for node in env.parse(file.read_text()).find_all(nodes.Getattr)
                             if isinstance(node.node, nodes.Name) and node.node.name == 'uuids'})
        result.append({
            'template': str(file.relative_to(ROOT)),
            'referenced_bindings': len(references),
            'unbound_variables': [name for name in references if name not in ids],
            'absent_entities': [{'binding': name, 'uuid': ids[name]} for name in references if name in ids and ids[name] not in entities],
        })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    bundle = ROOT / 'fixtures/knowledge-models/root-2.7.0.km'
    client = DSWApiClient(api_url='http://localhost:13300/wizard-api', verify_ssl=True)
    project = None
    try:
        client.login(email='albert.einstein@example.com', password='password')
        project = client.create_project_from_package(name='Synthetic KM binding audit', knowledge_model_package_id=str(bundle),
            question_tag_uuids=[], visibility='PrivateProjectVisibility', sharing='RestrictedProjectSharing')
        questions = audit(client.get_project_questionnaire(project['uuid'])['knowledgeModel'])
    finally:
        if project:
            client.delete_project(project['uuid'])
        client.close()
    report = {
        'scope': 'Static references in fifteen question templates; Common DSW KM 2.7.0 only; not answer coverage',
        'source_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'source_dirty': bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).strip()),
        'km_sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
        'templates': questions,
        'release_acceptance': False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(args.output), 'templates': len(questions),
        'unbound_variable_occurrences': sum(len(q['unbound_variables']) for q in questions),
        'absent_entity_occurrences': sum(len(q['absent_entities']) for q in questions)}))


if __name__ == '__main__':
    main()
