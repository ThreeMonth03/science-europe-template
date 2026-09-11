from __future__ import annotations

import html
import json
import re
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Undefined


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "requirements" / "science-europe-2021.json").read_text(encoding="utf-8")
)


def reply_path(parts):
    return ".".join(str(part) for part in parts)


def reply_str_value(reply):
    if isinstance(reply, Undefined) or reply is None:
        return ""
    if isinstance(reply, str):
        return reply
    if isinstance(reply, dict):
        value = reply.get("value", reply)
        if isinstance(value, dict):
            value = value.get("value", value)
        if isinstance(value, dict):
            return str(value.get("value", ""))
    return str(reply)


def reply_items(reply):
    if isinstance(reply, Undefined) or reply is None:
        return []
    return reply if isinstance(reply, list) else []


def render_question(path: str, replies: dict[str, object]) -> str:
    env = Environment(
        loader=FileSystemLoader(ROOT),
        extensions=["jinja2.ext.do"],
        autoescape=False,
    )
    env.filters.update(
        reply_path=reply_path,
        reply_str_value=reply_str_value,
        reply_items=reply_items,
        markdown=lambda value: value,
        dot=lambda value: f"{value}." if value and not str(value).endswith(".") else value,
    )
    env.tests["true"] = lambda value: value is True
    wrapper = env.from_string(
        "{% import 'src/macros.html.j2' as macros with context %}"
        "{% import 'src/uuids.j2' as uuids with context %}"
        f"{{% include '{path}' with context %}}"
    )
    return wrapper.render(repliesMap=replies)


class ScienceEuropeContractTests(unittest.TestCase):
    def test_all_six_sections_and_fifteen_questions_are_tracked(self):
        requirements = CONTRACT["requirements"]
        self.assertEqual(15, len(requirements))
        self.assertEqual(list(range(1, 16)), [item["number"] for item in requirements])
        self.assertEqual(
            [
                "SE-1a", "SE-1b", "SE-2a", "SE-2b", "SE-3a", "SE-3b",
                "SE-4a", "SE-4b", "SE-4c", "SE-5a", "SE-5b", "SE-5c",
                "SE-5d", "SE-6a", "SE-6b",
            ],
            [item["id"] for item in requirements],
        )
        self.assertEqual(6, len({item["section"] for item in requirements}))

    def test_template_headings_match_the_recorded_science_europe_questions(self):
        for requirement in CONTRACT["requirements"]:
            source = (ROOT / requirement["template"]).read_text(encoding="utf-8")
            match = re.search(r"<h3>(.*?)</h3>", source, flags=re.DOTALL)
            self.assertIsNotNone(match, requirement["template"])
            heading = " ".join(html.unescape(match.group(1)).split())
            expected = f'{requirement["number"]}. {requirement["question"]}'
            self.assertEqual(expected, heading, requirement["id"])

    def test_experiment_bindings_exist_or_are_explicitly_unmapped(self):
        uuid_source = (ROOT / "src" / "uuids.j2").read_text(encoding="utf-8")
        for requirement in CONTRACT["requirements"]:
            if requirement["implementationStatus"] != "experiment":
                continue
            template_source = (ROOT / requirement["template"]).read_text(encoding="utf-8")
            self.assertIn(f'data-requirement-id="{requirement["id"]}"', template_source)
            for fact in requirement["facts"]:
                if fact["coverage"] == "unmapped":
                    self.assertEqual([], fact["dswBindings"])
                    continue
                for binding in fact["dswBindings"]:
                    self.assertRegex(uuid_source, rf"set\s+{re.escape(binding)}\s*=")

    def test_unanswered_se_1a_is_visible_and_not_rendered_as_no(self):
        output = render_question("src/questions/01-how-data.html.j2", {})
        self.assertIn('data-fact-id="new-data" data-status="missing"', output)
        self.assertIn('data-fact-id="reuse-sources" data-status="missing"', output)
        self.assertIn('data-fact-id="provenance" data-status="missing"', output)
        self.assertNotIn("No new instrument datasets", output)
        self.assertNotIn("No relevant pre-existing datasets", output)

    def test_explicit_no_is_distinct_from_unanswered_for_se_1a(self):
        replies = {
            "b1df3c74-0b1f-4574-81c4-4cc2d780c1af.f87c331d-794a-42c8-a910-61a2a9110dab": "8d384c38-653a-476c-bda1-47ab7d38c9c2",
            "82fd0cce-2b41-423f-92ad-636d0872045c.efc80cc8-8318-4f8c-acb7-dc1c60e491c1": "72cdbc99-2707-4817-ac40-435a03e5e837",
        }
        output = render_question("src/questions/01-how-data.html.j2", replies)
        self.assertIn('data-fact-id="new-data" data-status="explicit-no"', output)
        self.assertIn('data-fact-id="reuse-sources" data-status="explicit-no"', output)
        self.assertNotIn('data-fact-id="new-data" data-status="missing"', output)
        self.assertNotIn('data-fact-id="reuse-sources" data-status="missing"', output)

    def test_unanswered_se_3a_keeps_the_whole_requirement_visible(self):
        output = render_question("src/questions/05-store-backup.html.j2", {})
        for fact_id in ("working-storage-arrangement", "backup-arrangement", "storage-location", "backup-frequency"):
            self.assertIn(f'data-fact-id="{fact_id}" data-status="missing"', output)

    def test_explicit_backup_problem_is_not_reported_as_unanswered(self):
        replies = {
            "10a10ffd-bfe1-4c6b-bbb6-3dfb1e63a5d5.72099c46-16e7-47a2-a320-cc768b7085fe": "1d6ba101-fd62-43c8-ab53-76bc31847f58",
            "10a10ffd-bfe1-4c6b-bbb6-3dfb1e63a5d5.72099c46-16e7-47a2-a320-cc768b7085fe.1d6ba101-fd62-43c8-ab53-76bc31847f58.c1e83bdf-5914-44c2-8414-0a4e7fbaf272": "0c93a407-b04a-4c89-a8e4-299a4d77c21e",
        }
        output = render_question("src/questions/05-store-backup.html.j2", replies)
        self.assertIn('data-fact-id="backup-reliability" data-status="explicit-no"', output)
        self.assertNotIn('data-fact-id="backup-reliability" data-status="missing"', output)

    def test_partial_se_6b_keeps_present_answers_and_marks_missing_costs(self):
        replies = {
            "1e85da40-bbfc-4180-903e-6c569ed2da38.83c0d09d-e74c-4c81-a52c-aaa2e18415ac": "ccdadd45-8aa9-44ed-a669-1827c7813b0a",
            "1e85da40-bbfc-4180-903e-6c569ed2da38.09c7c989-6461-417f-b09e-228491c051c6": "f4da7f1d-f3c6-42e2-a7b5-41c4845ba352",
        }
        output = render_question("src/questions/15-required-resources.html.j2", replies)
        self.assertIn('data-fact-id="specialist-expertise" data-status="explicit-no"', output)
        self.assertIn('data-fact-id="hardware-software" data-status="explicit-no"', output)
        self.assertIn('data-fact-id="resources-costing" data-status="missing"', output)

    def test_populated_se_6b_cost_item_has_no_missing_markers(self):
        admin = "1e85da40-bbfc-4180-903e-6c569ed2da38"
        projects = f"{admin}.c3dabaaf-c946-4a0d-889c-ede966f97667"
        project = f"{projects}.project-1"
        costs = f"{project}.353eeaca-45fa-4958-a33c-ec6de3075701"
        cost = f"{costs}.cost-1"
        cover = f"{cost}.46cd176a-138a-4f6c-8cd5-dfcb1f23f04a"
        replies = {
            f"{admin}.83c0d09d-e74c-4c81-a52c-aaa2e18415ac": "ccdadd45-8aa9-44ed-a669-1827c7813b0a",
            f"{admin}.09c7c989-6461-417f-b09e-228491c051c6": "f4da7f1d-f3c6-42e2-a7b5-41c4845ba352",
            projects: ["project-1"],
            f"{project}.f0ef08fd-d733-465c-bc66-5de0b826c41b": "Example project",
            costs: ["cost-1"],
            f"{cost}.7098b454-bc5e-4f83-a95d-970aa42e1479": "Data curator time",
            f"{cost}.b3d9b6ca-bd24-4fa3-a3bd-d15005b9ae8b": "Prepare and document data for deposit",
            f"{cost}.ac1f8f04-17a2-49e9-b2ad-2a9f8e44efb3": {
                "value": {"value": {"type": "PlainType", "value": "EUR"}}
            },
            f"{cost}.e53fdad9-7799-4eb4-8b4d-fa9aa05f9d2d": "5000",
            f"{cost}.028909e8-7392-4385-96a3-467d79c43a42": [
                "350a6e85-d4b2-4a44-831d-4562e5668208",
                "d2a9d717-c0b2-44ee-8a6d-8476831b6225",
            ],
            cover: "2e37f71b-b7aa-4182-888a-8b7a5156b53c",
            f"{cover}.2e37f71b-b7aa-4182-888a-8b7a5156b53c.2964c7f7-d9be-42ac-8cfe-dbcf4d62f8a2": "institutional funds",
        }
        output = render_question("src/questions/15-required-resources.html.j2", replies)
        self.assertIn("Data curator time", output)
        self.assertIn("The amount is 5000 EUR.", output)
        self.assertNotIn('data-status="missing"', output)


if __name__ == "__main__":
    unittest.main()
