"""Word-only prototype must preserve all unmarked XML and source assets."""
import importlib.util
from pathlib import Path
import unittest
from jinja2 import Environment, DictLoader, UndefinedError
from markupsafe import Markup
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
def recipe():
    spec = importlib.util.spec_from_file_location('word_empty_sections', ROOT / 'experiments/word-empty-section-spacing/recipe.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

class WordEmptySectionsTests(unittest.TestCase):
    def test_only_two_word_helpers_change(self):
        m=recipe(); old=m.baseline_sources(); new=m.overlay(old)
        self.assertEqual({n for n in old if old[n]!=new[n]},m.CHANGED)
        actual={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
        self.assertEqual(actual,old)
        for changed in [{**old,'src/extra':b'x'},{**old,'src/layout.css':old['src/layout.css']+b' '},
                        {n:v for n,v in old.items() if n!=m.XML}]:
            with self.assertRaises(AssertionError):m.overlay(changed)

    def templates(self, autoescape):
        m=recipe(); before=m.baseline_sources(); after=m.overlay(before)
        def env(values):return Environment(loader=DictLoader({n:v.decode() for n,v in values.items() if n.endswith('.xml')}),autoescape=autoescape)
        return [env(v).get_template(m.XML) for v in [before,after]]

    def test_xml_only_spacing_and_no_escaping_regression(self):
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        p='<w:p><w:pPr><w:pStyle w:val="Heading2" /></w:pPr><w:r><w:t>Title &amp; &lt;w:spacing&gt; 原文</w:t></w:r></w:p>'
        start='<w:document xmlns:w="'+ns['w']+'"><w:body>'; end='</w:body></w:document>'
        plain=start+p+end
        marked=start+'<!--DSW:SE:empty-section:v1:begin-->\n    '+p+'\n    <!--DSW:SE:empty-section:v1:end-->'+end
        for autoescape in [False,True]:
            old,new=self.templates(autoescape)
            self.assertEqual(old.render(content=plain),new.render(content=plain))
            for value in [marked,Markup(marked)]:
                result=new.render(content=value); root=etree.fromstring(result.encode())
                props=root.find('.//w:pPr',ns); spacing=props.find('w:spacing',ns)
                self.assertEqual(spacing.attrib,{f'{{{ns["w"]}}}before':'60',f'{{{ns["w"]}}}after':'40'})
                self.assertIsNone(props.find('w:keepNext',ns)); self.assertIsNone(props.getparent().text)
                props.remove(spacing)
                self.assertEqual(etree.tostring(root),etree.tostring(etree.fromstring(plain.encode())))

    def test_malformed_section_markers_fail_closed(self):
        _,new=self.templates(True)
        p='<w:p><w:pPr><w:pStyle w:val="Heading2" /></w:pPr><w:r><w:t>Title</w:t></w:r></w:p>'
        marked='<!--DSW:SE:empty-section:v1:begin-->\n    '+p+'\n    <!--DSW:SE:empty-section:v1:end-->'
        for value in [marked.replace('Heading2','Heading3'),marked.replace('v1:end','v2:end'),
                      marked.replace(p,p+p),marked.replace('\n    ',''),marked.replace('</w:pPr>','<w:spacing/></w:pPr>')]:
            with self.assertRaises(UndefinedError):new.render(content=value)

    def test_link_only_changes_the_known_empty_heading_keep_next(self):
        p='<w:p><w:pPr><w:pStyle w:val="Heading3" /></w:pPr><w:r><w:t>Question</w:t></w:r></w:p>'
        old='<!--DSW:SE:empty-question:v1:begin-->\n    '+p+'\n    <!--DSW:SE:empty-question:v1:end-->'
        marked='<!--DSW:SE:empty-section-link:v1:begin-->\n    '+old+'\n    <!--DSW:SE:empty-section-link:v1:end-->'
        for autoescape in [False,True]:
            original,new=self.templates(autoescape)
            expected=original.render(content=old).replace('<w:keepNext w:val="0"/>','<w:keepNext w:val="1"/>')
            self.assertEqual(new.render(content=marked),expected)
            for bad in [marked.replace('empty-section-link:v1:end','empty-section-link:v2:end'),marked.replace(old,p)]:
                with self.assertRaises(UndefinedError):new.render(content=bad)

if __name__=='__main__':unittest.main()
