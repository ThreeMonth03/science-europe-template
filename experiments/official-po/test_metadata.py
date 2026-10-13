"""Focused PO metadata regression; run with the locked 4.35 dependencies."""
import copy
import gettext
import io
from pathlib import Path
from types import SimpleNamespace as Obj
import unittest

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
import polib

ROOT = Path(__file__).resolve().parents[2]
PHASES = [
    ('b101f2d0-2476-452d-aa8d-95a41a02b52c', 'Before Submitting the Proposal', '提交計畫申請書前'),
    ('1796fa3c-9f53-475f-89ff-c66a0453c42e', 'Before Submitting the DMP', '提交資料管理計畫前'),
    ('adc9133d-afcd-4616-9aea-db5f475898a2', 'Before Finishing the Project', '計畫結束前'),
    ('1ace0fc6-a949-495f-a32e-e948f3f6bed1', 'After Finishing the Project', '計畫結束後'),
]
MISSING = object()


class MetadataTests(unittest.TestCase):
    def render(self, language, current=MISSING, legacy=MISSING, phases=None, profile='review', escape=True, entry='src/document-provenance.html.j2'):
        env = Environment(loader=ChoiceLoader([DictLoader({'src/answer-markdown.html.j2': ''}), FileSystemLoader(ROOT)]),
            extensions=['jinja2.ext.i18n', 'jinja2.ext.do'], autoescape=escape)
        translations = (gettext.GNUTranslations(io.BytesIO(polib.pofile(str(ROOT/'locales/zh-Hant.po')).to_binary()))
                        if language == 'zh-Hant' else gettext.NullTranslations())
        env.install_gettext_translations(translations, newstyle=True)
        env.filters.update(markdown=lambda v: v, dot=lambda v: v, reply_items=lambda v: [], reply_str_value=lambda v: '',
                           datetime_format=lambda value, fmt: '2026-10-13')
        ctx = {'project': {}}
        if current is not MISSING: ctx['project']['phaseUuid'] = current
        if legacy is not MISSING: ctx['phaseUuid'] = legacy
        km = {'entities': {'phases': phases if phases is not None else {uid: {'title': en} for uid, en, zh in PHASES}}}
        dc = Obj(project=Obj(name='Workspace <A> & B', versions=[]), document=Obj(name='Different document', created_at='date'),
                 pkg=Obj(name='KM', version='2.7.0', organization_id='dsw', km_id='root'),
                 config=Obj(service_name='DSW', service_url='https://example.org', service_domain_name='example.org'))
        before = copy.deepcopy(ctx)
        text = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids %}{% include entry %}").render(
            ctx=ctx, km=km, dc=dc, repliesMap={}, output_profile=profile, entry=entry)
        self.assertEqual(ctx, before)
        return text

    def test_four_official_phases_in_both_languages_and_metadata_callers(self):
        for uid, en, zh in PHASES:
            for lang, expected in [('en', en), ('zh-Hant', zh)]:
                for entry in ['src/document-provenance.html.j2', 'src/header.html.j2']:
                    with self.subTest(phase=uid, language=lang, entry=entry):
                        self.assertIn(expected, self.render(lang, current=uid, entry=entry))

    def test_project_field_authority_and_legacy_fallback(self):
        uid, en, zh = PHASES[2]
        for lang, expected in [('en', en), ('zh-Hant', zh)]:
            self.assertIn(expected, self.render(lang, current=uid, legacy=PHASES[0][0]))
            self.assertIn(expected, self.render(lang, legacy=uid))
            for current in [None, '', 'unknown']:
                with self.subTest(language=lang, current=current):
                    self.assertNotIn('Project phase:', self.render(lang, current=current, legacy=uid))
                    self.assertNotIn('計畫階段：', self.render(lang, current=current, legacy=uid))
            self.assertNotIn('Project phase:', self.render(lang))
            self.assertNotIn('計畫階段：', self.render(lang))

    def test_custom_or_already_translated_phase_titles_are_preserved_and_escaped(self):
        uid, en, zh = PHASES[2]
        for lang in ['en', 'zh-Hant']:
            for custom_uid, title in [(uid, zh), (uid, 'Custom phase'), ('custom', en), (uid, '<b>A&B</b>')]:
                for escape in [False, True]:
                    with self.subTest(language=lang, title=title, escape=escape):
                        text = self.render(lang, current=custom_uid, phases={custom_uid: {'title': title}}, escape=escape)
                        if '<' in title:
                            self.assertIn('&lt;b&gt;A&amp;B&lt;/b&gt;', text)
                            self.assertNotIn('&amp;lt;', text)
                        else: self.assertIn(title, text)
            for title in [None, '']:
                text = self.render(lang, current=uid, phases={uid: {'title': title}})
                self.assertNotIn('計畫階段：', text); self.assertNotIn('Project phase:', text)

    def test_project_identity_and_submission_hiding(self):
        for lang, label in [('en', 'Project:'), ('zh-Hant', '專案名稱：')]:
            for escape in [False, True]:
                text = self.render(lang, current=PHASES[2][0], escape=escape)
                self.assertIn(label, text)
                self.assertIn('Workspace &lt;A&gt; &amp; B', text)
                self.assertNotIn('Different document', text)
                self.assertNotIn('文件名稱：', text); self.assertNotIn('Document:', text)
                self.assertFalse(self.render(lang, current=PHASES[2][0], profile='submission', escape=escape).strip())


if __name__ == '__main__': unittest.main()
