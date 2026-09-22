import importlib.util
from pathlib import Path
import unittest
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('empty_question_' + name, ROOT / 'experiments/empty-question-spacing' / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class EmptyQuestionSpacingTests(unittest.TestCase):
    def test_exact_markers_preserve_all_content_and_review(self):
        recipe = load('recipe'); reuse = recipe.load_reuse()
        before = reuse.overlay(reuse.baseline_sources())
        rows = load('probe').check(ROOT, before, recipe.overlay(before))
        self.assertGreater(len(rows), 100)

    def test_unrelated_source_drift_rejected(self):
        recipe = load('recipe'); reuse = recipe.load_reuse()
        before = reuse.overlay(reuse.baseline_sources()); before['src/layout.css'] += b'\n'
        with self.assertRaises(AssertionError): recipe.overlay(before)

    def test_empty_answer_boxes_remain_in_the_pdf_layout(self):
        css = load('recipe').CSS.split(b'*/', 1)[1]
        self.assertNotIn(b'display:', css)
        self.assertNotIn(b'> .answer {', css)
        self.assertIn(b'break-after: auto;', css)

    def test_word_properties_remain_xml_with_worker_autoescaping(self):
        # Captured include output is Markup when autoescaping is on. Replacing
        # into it with a plain string escapes the new XML even with a final safe.
        paths = [ROOT / 'experiments/empty-question-spacing', ROOT]
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraph = '<w:p><w:pPr><w:pStyle w:val="Heading3" /></w:pPr><w:r><w:t>Original &amp; &lt;w:pPr&gt;</w:t></w:r></w:p>'
        prefix = '<w:document xmlns:w="' + ns['w'] + '"><w:body>'
        suffix = '</w:body></w:document>'
        marked = prefix + '<!--DSW:SE:empty-question:v1:begin-->\n    ' + paragraph + '\n    <!--DSW:SE:empty-question:v1:end-->' + suffix
        for autoescape in [False, True]:
            for value in [marked, Markup(marked)]:
                with self.subTest(autoescape=autoescape, markup=isinstance(value, Markup)):
                    env = Environment(loader=FileSystemLoader(paths), autoescape=autoescape)
                    result = env.get_template('src/word/question-spacing.xml').render(content=value)
                    xml = ET.fromstring(result)
                    p = xml.find('.//w:p', ns)
                    self.assertIsNone(p.text, 'Paragraph properties must be XML nodes, not escaped text')
                    props = p.find('w:pPr', ns)
                    self.assertIsNotNone(props)
                    self.assertEqual('Heading3', props.find('w:pStyle', ns).get('{' + ns['w'] + '}val'))
                    self.assertEqual('0', props.find('w:keepNext', ns).get('{' + ns['w'] + '}val'))
                    self.assertEqual({'{' + ns['w'] + '}before': '80', '{' + ns['w'] + '}after': '0'}, props.find('w:spacing', ns).attrib)
                    props.remove(props.find('w:keepNext', ns)); props.remove(props.find('w:spacing', ns))
                    self.assertEqual(ET.tostring(ET.fromstring(prefix + paragraph + suffix)), ET.tostring(xml))


if __name__ == '__main__': unittest.main()
