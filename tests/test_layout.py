import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.enum.text import WD_LINE_SPACING
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_layout", ROOT / "scripts/prepare_layout.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LayoutTests(unittest.TestCase):
    def test_history_and_provenance_wrap_without_changing_ordinary_layout(self):
        probe_spec = importlib.util.spec_from_file_location('budget_worker', ROOT / 'scripts/probe_budget_word.py')
        worker = importlib.util.module_from_spec(probe_spec)
        probe_spec.loader.exec_module(worker)
        env = Environment(loader=FileSystemLoader(ROOT), autoescape=True)
        env.filters['datetime_format'] = lambda value, fmt: '30 Sep 2026'
        template = env.from_string("{% include 'src/versions.html.j2' %}{% include 'src/document-provenance.html.j2' %}")
        css = (ROOT / 'src/style.css').read_text() + (ROOT / 'src/layout.css').read_text()
        rule = ('html body #dmp-versions td.version-name,\n'
                'html body #dmp-versions td.version-changes,\n'
                'html body .document-provenance { overflow-wrap: anywhere; word-break: break-word; }')
        self.assertEqual(css.count(rule), 1)
        cases = []
        for name, count, title, description, model in [
                ('short', 1, 'Review A', 'Checked the data.', 'Coastal KM'),
                ('missing-description', 1, '核對 A', '', '沿岸觀測'),
                ('many', 24, 'Review A', 'Checked the data.', 'Coastal KM'),
                ('long', 1, 'VERSION' + 'ABCDEFGHIJ' * 18, 'CHANGES' + '0123456789' * 45, 'MODEL' + 'ABCDEFGHIJ' * 18)]:
            dc = dict(project=dict(versions=[dict(name=title, description=description, created_at='')] * count),
                      pkg=dict(name=model, version='2.7.0', organization_id='dsw', km_id='root'),
                      config=dict(service_name='DMP service', service_url='https://example.org/'))
            cases.append(dict(name=name, html=template.render(dc=dc), text=[title, description, model]))
        runner = '''import json,sys,re
from weasyprint import HTML
p=json.load(sys.stdin)
def render(case,css):
    return HTML(string='<html><head><style>'+css+'</style></head><body>'+case['html']+'</body></html>').render()
def boxes(doc):
    return [(i,b.text,b.position_x,b.position_y,b.width,b.height) for i,page in enumerate(doc.pages)
            for b in page._page_box.descendants() if type(b).__name__=='TextBox']
norm=lambda s:re.sub(r'\\s+','',s)
for case in p['cases']:
    doc=render(case,p['css']); current=boxes(doc)
    for i,text,x,y,w,h in current:
        page=doc.pages[i]._page_box; left=page.content_box_x(); right=left+page.width
        assert x>=left-1 and x+w<=right+1,(case['name'],'overflow',text)
    for text in case['text']:
        assert norm(text) in norm(''.join(row[1] for row in current)),(case['name'],'missing',text)
    if case['name']!='long':
        assert current==boxes(render(case,p['css'].replace(p['rule'],''))),(case['name'],'ordinary layout changed')
print(json.dumps({'passed':True,'cases':len(p['cases'])}))
'''
        output = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i',
            '--entrypoint', 'python', worker.IMAGE, '-c', runner],
            input=json.dumps(dict(css=css, rule=rule, cases=cases)).encode(), timeout=180)
        self.assertEqual(json.loads(output), dict(passed=True, cases=4))

    def test_word_styles_and_deterministic_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            font = root / "test.ttf"
            font.write_bytes(b"fixture font asset")
            references = []
            for name in ("first", "second"):
                folder = root / name
                (folder / "src/word").mkdir(parents=True)
                shutil.copyfile(ROOT / "src/layout.css", folder / "src/layout.css")
                shutil.copyfile(
                    ROOT / "src/word/reference.docx", folder / "src/word/reference.docx"
                )
                module.prepare_layout(folder, font, "zh-Hant")
                references.append((folder / "src/word/reference.docx").read_bytes())
                document = Document(folder / "src/word/reference.docx")
                self.assertFalse(document.styles["Heading 2"].paragraph_format.page_break_before)
                self.assertTrue(document.styles["Pilot Label"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Responsibility Summary"].paragraph_format.keep_together)
                self.assertFalse(document.styles["Pilot Responsibility Summary"].paragraph_format.keep_with_next)
                self.assertEqual('Body Text', document.styles["Pilot Responsibility Summary"].base_style.name)
                self.assertTrue(document.styles["Pilot List Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Table Lead"].paragraph_format.keep_with_next)
                self.assertTrue(document.styles["Pilot Table Lead"].paragraph_format.keep_together)
                self.assertTrue(document.styles["Pilot Repository Lead"].paragraph_format.keep_with_next)
                self.assertFalse(document.styles["Pilot Repository Item"].paragraph_format.keep_with_next)
                for name in ["Pilot Repository Lead", "Pilot Repository Item"]:
                    self.assertTrue(document.styles[name].paragraph_format.keep_together)
                    self.assertEqual('Compact', document.styles[name].base_style.name)
                self.assertFalse(document.styles["Heading 4"].font.italic)
                self.assertEqual(0, document.styles["Body Text"].paragraph_format.space_before)
                for style_name in ("Normal", "Body Text", "First Paragraph", "Compact"):
                    item = document.styles[style_name]
                    self.assertEqual(10.5, item.font.size.pt)
                    if style_name == "Normal":
                        self.assertEqual(1.2, item.paragraph_format.line_spacing)
                        self.assertEqual(WD_LINE_SPACING.MULTIPLE, item.paragraph_format.line_spacing_rule)
                    else:
                        self.assertEqual(15.75, item.paragraph_format.line_spacing.pt)
                        self.assertEqual(WD_LINE_SPACING.AT_LEAST, item.paragraph_format.line_spacing_rule)
                    self.assertEqual(2 if style_name == "Compact" else 4, item.paragraph_format.space_after.pt)
                    self.assertTrue(item.paragraph_format.widow_control)
                for level in range(1, 6):
                    item = document.styles[f"Heading {level}"].paragraph_format
                    self.assertEqual(8 if level >= 4 else 12, item.space_before.pt)
                    self.assertEqual(3 if level >= 4 else 4 if level == 3 else 6, item.space_after.pt)
                    self.assertTrue(item.keep_with_next)
                    self.assertTrue(item.keep_together)
                for section in document.sections:
                    for container in (
                        section.header,
                        section.first_page_header,
                        section.even_page_header,
                    ):
                        self.assertFalse(
                            any(e.tag == qn("w:drawing") for e in container._element.iter())
                        )
            self.assertEqual(references[0], references[1])

    def test_english_uses_same_spacing_without_changing_body_font_size(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'src/word').mkdir(parents=True)
            shutil.copyfile(ROOT / 'src/layout.css', root / 'src/layout.css')
            shutil.copyfile(ROOT / 'src/word/reference.docx', root / 'src/word/reference.docx')
            font = root / 'font.ttf'; font.write_bytes(b'fixture font asset')
            module.prepare_layout(root, font, 'en')
            d = Document(root / 'src/word/reference.docx')
            for name in ('Normal', 'Body Text', 'First Paragraph', 'Compact'):
                self.assertEqual(1.2, d.styles[name].paragraph_format.line_spacing)
                self.assertEqual(WD_LINE_SPACING.MULTIPLE, d.styles[name].paragraph_format.line_spacing_rule)
                self.assertEqual(10.5, d.styles[name].font.size.pt)
            self.assertEqual('en-GB', d.styles['Normal'].element.rPr.find(qn('w:lang')).get(qn('w:val')))
