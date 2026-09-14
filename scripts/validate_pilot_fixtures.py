"""Check fixture paths against the server-compiled KM, not template assumptions."""

import json
from pathlib import Path

from dsw_document_template_tool.api import DSWApiClient

ROOT = Path(__file__).resolve().parents[1]


def check(knowledge_model, replies):
    entities = knowledge_model["entities"]
    visited = set()
    errors = []

    def visit(question_uuid, prefix):
        question = entities["questions"][question_uuid]
        path = prefix + "." + question_uuid
        reply = replies.get(path)
        if reply is None:
            return
        visited.add(path)
        value = reply["value"]
        if question["questionType"] == "OptionsQuestion":
            if value not in question["answerUuids"]:
                errors.append({"path": path, "error": "invalid answer UUID"})
                return
            for child in entities["answers"][value]["followUpUuids"]:
                visit(child, path + "." + value)
        elif question["questionType"] == "MultiChoiceQuestion":
            if not isinstance(value, list) or any(choice not in question['choiceUuids'] for choice in value):
                errors.append({"path": path, "error": "invalid multi-choice UUID"})
        elif question["questionType"] == "ListQuestion":
            for item in value:
                for child in question["itemTemplateQuestionUuids"]:
                    visit(child, path + "." + item)

    for chapter_uuid in knowledge_model["chapterUuids"]:
        for question_uuid in entities["chapters"][chapter_uuid]["questionUuids"]:
            visit(question_uuid, chapter_uuid)
    errors.extend(
        {"path": path, "error": "not reachable in the compiled KM / selected answers"}
        for path in sorted(set(replies) - visited)
    )
    return errors


if __name__ == "__main__":
    client = DSWApiClient(api_url="http://localhost:13300/wizard-api", verify_ssl=True)
    project_uuid = None
    try:
        client.login(email="albert.einstein@example.com", password="password")
        failures = {}
        for locale, filename in (("en", "root-2.7.0.km"), ("zh-Hant", "root-zh-hant-2.7.0.km")):
            project = client.create_project_from_package(
                name="Science Europe fixture validation",
                knowledge_model_package_id=str(ROOT / "fixtures/knowledge-models" / filename),
                question_tag_uuids=[],
                visibility="PrivateProjectVisibility",
                sharing="RestrictedProjectSharing",
            )
            project_uuid = project["uuid"]
            km = client.get_project_questionnaire(project_uuid)["knowledgeModel"]
            for file in sorted((ROOT / "fixtures/pilot" / locale).glob("*.events.json")):
                errors = check(
                    km, {event["path"]: event["value"] for event in json.loads(file.read_text())}
                )
                if errors:
                    failures[str(file.relative_to(ROOT))] = errors
            client.delete_project(project_uuid)
            project_uuid = None
        print(json.dumps({"failures": failures}, indent=2))
        raise SystemExit(1 if failures else 0)
    finally:
        if project_uuid:
            client.delete_project(project_uuid)
        client.close()
