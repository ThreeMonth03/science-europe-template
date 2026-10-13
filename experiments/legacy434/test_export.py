"""Focused synthetic-bundle tests; no document renderer or Server required."""

import gettext
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import polib
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from export_legacy_locale import ExportError, export_bundle  # noqa: E402

FORMATS = [
    ("a9293d08-59a4-4e6b-ae62-7a6a570b031c", "HTML — 內部檢核版"),
    ("68c26e34-5e77-4e15-9bf7-06ff92582257", "PDF — 內部檢核版"),
    ("f4bd941a-dfbe-4226-a1fc-200fb5269311", "Word — 內部檢核版"),
    ("499d9300-0183-5157-b6f4-38e6c2b91600", "HTML — 提交版"),
    ("9fd0a115-4b8b-5013-a084-eaf2890ec940", "PDF — 提交版"),
    ("98081811-41ff-5438-b98a-0472607527c6", "Word — 提交版"),
]
LANGUAGE = "src/locales/language.j2"
MO = "src/i18n/zh-Hant/LC_MESSAGES/dsw.mo"
MESSAGE, TRANSLATION = "Hello %(name)s.", "你好，%(name)s。"
SOURCE = '<p>{{ pgettext("fixture", "Hello %(name)s.", name=name|e) }}</p>'


class ExportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source, self.po = self.directory / "source.zip", self.directory / "zh.po"
        files = [
            {"uuid": f"old-file-{n}", "fileName": path, "content": content}
            for n, (path, content) in enumerate(
                [
                    (LANGUAGE, "{{ ctx.document.locale.code }}"),
                    ("src/index.html.j2", SOURCE),
                    ("src/unchanged.html.j2", "{{ answer|e }}\n{% set count = 1 %}"),
                ]
            )
        ]
        self.binary = {
            "src/word/reference.docx": b"PK\x00\xffFAKE_REFERENCE",
            "src/fonts/example.ttf": b"\x00\x01\x00\x00FAKE_FONT",
        }
        formats = []
        for identifier, label in FORMATS:
            steps = [
                {"name": "jinja", "options": {"template": "src/index.html.j2", "jinja-ext": "do"}},
                {"name": "pandoc", "options": {"args": "--wrap=none"}},
            ]
            if label.startswith("Word"):
                steps.append(
                    {
                        "name": "enrich-docx",
                        "options": {"rewrite:word/styles.xml": "render:src/unchanged.html.j2"},
                    }
                )
            formats.append({"uuid": identifier, "name": "Original label", "steps": steps})
        formats.append({"uuid": "excluded-format", "name": "LaTeX Document", "steps": []})
        self.payload = {
            "id": "fixture-org:fixture-template:0.3.78",
            "organizationId": "fixture-org",
            "templateId": "fixture-template",
            "version": "0.3.78",
            "language": "en",
            "metamodelVersion": "18.0",
            "name": "Fixture",
            "formats": formats,
            "files": files,
            "assets": [
                {
                    "uuid": f"old-asset-{n}",
                    "fileName": path,
                    "contentType": "application/octet-stream",
                }
                for n, path in enumerate(self.binary)
            ],
        }
        with zipfile.ZipFile(self.source, "w") as archive:
            archive.writestr("template/template.json", json.dumps(self.payload))
            archive.writestr("README.txt", b"Unchanged auxiliary member\n")
            for path, data in self.binary.items():
                archive.writestr("template/assets/" + path, data)
        self.original_zip = self.source.read_bytes()
        self.write_po(self.po)

    def write_po(self, path, *, translation=TRANSLATION, flags=(), extra=False, missing=False):
        catalog = polib.POFile()
        catalog.metadata = {"Language": "zh-Hant", "Content-Type": "text/plain; charset=UTF-8"}
        if not missing:
            catalog.append(
                polib.POEntry(
                    msgctxt="fixture", msgid=MESSAGE, msgstr=translation, flags=list(flags)
                )
            )
        if extra:
            catalog.append(
                polib.POEntry(msgctxt="fixture", msgid="Unused message", msgstr="未使用的訊息")
            )
        catalog.save(str(path))

    def read_bundle(self, path):
        with zipfile.ZipFile(path) as archive:
            members = {name: archive.read(name) for name in archive.namelist()}
        return json.loads(members["template/template.json"]), members

    def test_434_profile_options_assets_and_manifest(self):
        output = self.directory / "compat.zip"
        manifest = export_bundle(self.source, self.po, output, "0.3.79", source_commit="a" * 40)
        payload, members = self.read_bundle(output)
        coordinate = "fixture-org:fixture-template-zhtw-compat434:0.3.79"
        self.assertEqual(
            (payload["id"], payload["version"], payload["language"]),
            (coordinate, "0.3.79", "zh-Hant"),
        )
        self.assertEqual(payload["organizationId"], "fixture-org")
        self.assertEqual(payload["templateId"], "fixture-template-zhtw-compat434")
        self.assertEqual(payload["metamodelVersion"], "18.0")
        self.assertIn("4.34", payload["name"])
        self.assertEqual([(f["uuid"], f["name"]) for f in payload["formats"]], FORMATS)
        for fmt in payload["formats"]:
            for step in fmt["steps"]:
                options = step["options"]
                if step["name"] in {"jinja", "enrich-docx"}:
                    self.assertIn("i18n", options["jinja-ext"].split(","))
                    for key, value in {
                        "i18n-dir": "src/i18n",
                        "i18n-domain": "dsw",
                        "i18n-lang": "zh-Hant",
                        "policy.ext.i18n.trimmed": "true",
                    }.items():
                        self.assertEqual(options[key], value)
                    if step["name"] == "jinja":
                        self.assertIn("do", options["jinja-ext"].split(","))
                else:
                    self.assertEqual(options, {"args": "--wrap=none"})
        actual_files = {f["fileName"]: f for f in payload["files"]}
        for original in self.payload["files"]:
            actual = actual_files[original["fileName"]]
            self.assertEqual(
                actual["content"],
                "zh-Hant" if original["fileName"] == LANGUAGE else original["content"],
            )
            self.assertNotEqual(actual["uuid"], original["uuid"])
        self.assertEqual(set(actual_files), {f["fileName"] for f in self.payload["files"]})
        self.assertEqual({a["fileName"] for a in payload["assets"]}, set(self.binary) | {MO})
        for path, data in self.binary.items():
            self.assertEqual(members["template/assets/" + path], data)
        self.assertEqual(members["README.txt"], b"Unchanged auxiliary member\n")
        self.assertEqual(self.source.read_bytes(), self.original_zip)
        self.assertEqual(
            (manifest["profile"], manifest["target_worker"], manifest["template_id"]),
            ("legacy434-zh-Hant-v1", "4.34", coordinate),
        )
        self.assertEqual(manifest["source_commit"], "a" * 40)
        self.assertEqual(manifest["approved_messages"], 1)
        self.assertEqual(manifest["changed_render_source_files"], [LANGUAGE])
        self.assertTrue(manifest["generated_do_not_edit"])
        for key, data in [
            ("source_zip_sha256", self.original_zip),
            ("po_sha256", self.po.read_bytes()),
            ("mo_sha256", members["template/assets/" + MO]),
            ("output_zip_sha256", output.read_bytes()),
        ]:
            self.assertEqual(manifest[key], hashlib.sha256(data).hexdigest())

    def test_mo_context_named_arguments_and_escaping(self):
        output = self.directory / "render-fixture.zip"
        export_bundle(self.source, self.po, output, "0.3.79")
        payload, members = self.read_bundle(output)
        translations = gettext.GNUTranslations(io.BytesIO(members["template/assets/" + MO]))
        self.assertEqual(translations.pgettext("fixture", MESSAGE), TRANSLATION)
        self.assertEqual(translations.pgettext("different-context", MESSAGE), MESSAGE)
        for autoescape in [False, True]:
            env = Environment(extensions=["jinja2.ext.i18n"], autoescape=autoescape)
            env.install_gettext_translations(translations, newstyle=True)
            self.assertEqual(
                env.from_string(SOURCE).render(name="<A&B>"), "<p>你好，&lt;A&amp;B&gt;。</p>"
            )
            helper = next(f["content"] for f in payload["files"] if f["fileName"] == LANGUAGE)
            self.assertEqual(
                env.from_string(helper).render(ctx={"document": {"locale": {"code": "en"}}}),
                "zh-Hant",
            )

    def test_invalid_catalogs_are_rejected_without_output(self):
        cases = {
            "missing": {"missing": True},
            "extra": {"extra": True},
            "fuzzy": {"flags": ["fuzzy"]},
            "untranslated": {"translation": ""},
            "missing-parameter": {"translation": "你好。"},
            "wrong-parameter": {"translation": "你好，%(other)s。"},
            "wrong-type": {"translation": "你好，%(name)d。"},
        }
        for name, changes in cases.items():
            with self.subTest(case=name):
                po, output = self.directory / f"{name}.po", self.directory / f"{name}.zip"
                self.write_po(po, **changes)
                with self.assertRaises(ExportError):
                    export_bundle(self.source, po, output, "0.3.79")
                self.assertFalse(output.exists())

    def test_refuses_existing_zip_or_manifest(self):
        for suffix in ["", ".json"]:
            output = self.directory / ("existing-sidecar.zip" if suffix else "existing.zip")
            existing = Path(str(output) + suffix)
            existing.write_bytes(b"Do not overwrite")
            with self.assertRaises(ExportError):
                export_bundle(self.source, self.po, output, "0.3.79")
            self.assertEqual(existing.read_bytes(), b"Do not overwrite")

    def test_reproducible_zip_and_translation_sensitive_identifiers(self):
        first, second, updated = [
            self.directory / f"{name}.zip" for name in ["first", "second", "updated"]
        ]
        before = export_bundle(self.source, self.po, first, "0.3.79")
        repeated = export_bundle(self.source, self.po, second, "0.3.79")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(before, repeated)
        changed_po = self.directory / "updated.po"
        self.write_po(changed_po, translation="您好，%(name)s。")
        # Same version tests hash sensitivity only, not permission to
        # republish that coordinate.
        after = export_bundle(self.source, changed_po, updated, "0.3.79")
        self.assertNotEqual(before["po_sha256"], after["po_sha256"])
        self.assertEqual(after["po_sha256"], hashlib.sha256(changed_po.read_bytes()).hexdigest())
        old_payload, _ = self.read_bundle(first)
        new_payload, members = self.read_bundle(updated)
        for kind in ["files", "assets"]:
            old_ids = {f["fileName"]: f["uuid"] for f in old_payload[kind]}
            self.assertEqual(set(old_ids), {f["fileName"] for f in new_payload[kind]})
            for item in new_payload[kind]:
                self.assertNotEqual(old_ids[item["fileName"]], item["uuid"])
        translations = gettext.GNUTranslations(io.BytesIO(members["template/assets/" + MO]))
        self.assertEqual(translations.pgettext("fixture", MESSAGE), "您好，%(name)s。")


if __name__ == "__main__":
    unittest.main()
