"""Word-only prototype must preserve all unmarked XML and source assets."""
import importlib.util
from pathlib import Path
import sys
import unittest
from jinja2 import Environment, DictLoader, FileSystemLoader, UndefinedError
from markupsafe import Markup
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from q3_policy_prose_contract import project_source as before_q3
def recipe():
    spec = importlib.util.spec_from_file_location('word_empty_sections', ROOT / 'experiments/word-empty-section-spacing/recipe.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

class WordEmptySectionsTests(unittest.TestCase):
    def test_only_two_word_helpers_change(self):
        m=recipe(); old=m.baseline_sources(); new=m.overlay(old)
        self.assertEqual({n for n in old if old[n]!=new[n]},m.CHANGED)
        actual,_=before_q3()
        self.assertEqual(actual,new)
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

class CurrentContentStartTests(unittest.TestCase):
    NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    BREAK='<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    STYLE='<w:pPr><w:pStyle w:val="Heading2" /></w:pPr>'

    def fixture(self, empty=False):
        heading='<w:p>'+self.STYLE+'<w:r><w:t>First &amp; 原始 &lt;w:p&gt; heading</w:t></w:r></w:p>'
        if empty:
            heading='<!--DSW:SE:empty-section:v1:begin-->\n    '+heading+'\n    <!--DSW:SE:empty-section:v1:end-->'
        return ('<w:document xmlns:w="'+self.NS['w']+'"><w:body>'
            '<w:p><w:r><w:t>Cover</w:t></w:r></w:p>'
            '<w:bookmarkStart w:id="1" w:name="dmp-content" />\n    '+self.BREAK+'\n    '
            '<w:bookmarkStart w:id="2" w:name="sec-data-collection" />\n    '
            '<w:bookmarkStart w:id="3" w:name="first-heading" />\n    '+heading+
            '<w:p><w:r><w:t>Original answer.</w:t></w:r></w:p>'
            '<w:bookmarkEnd w:id="3"/><w:bookmarkEnd w:id="2"/><w:bookmarkEnd w:id="1"/>'
            '<w:p>'+self.STYLE+'<w:r><w:t>Later section</w:t></w:r></w:p>'
            '</w:body></w:document>')

    def render_current(self, value, submission=False, autoescape=False):
        template='src/word/question-spacing.xml' if submission else 'src/word/short-tables.xml'
        return Environment(loader=FileSystemLoader(ROOT),autoescape=autoescape).get_template(template).render(content=value)

    def test_current_break_moves_without_changing_text_styles_or_bookmarks(self):
        original=self.fixture()
        for submission in [False,True]:
            for auto in [False,True]:
                for value in [original,Markup(original)]:
                    result=self.render_current(value,submission,auto)
                    expected=original.replace(self.BREAK+'\n    ','',1).replace(self.STYLE,self.STYLE.replace('</w:pPr>','<w:pageBreakBefore/></w:pPr>'),1)
                    self.assertEqual(result,expected)
                    root=etree.fromstring(result.encode())
                    self.assertEqual(1,len(root.findall('.//w:pageBreakBefore',self.NS)))
                    self.assertEqual(0,len(root.findall('.//w:br',self.NS)))

    def test_current_empty_first_section_retains_compaction_and_page_break(self):
        for auto in [False,True]:
            root=etree.fromstring(self.render_current(self.fixture(True),True,auto).encode())
            properties=root.findall('.//w:pPr',self.NS)
            first,later=properties[0],properties[1]
            self.assertEqual([f'{{{self.NS["w"]}}}'+name for name in ['pStyle','pageBreakBefore','spacing']],[c.tag for c in first])
            self.assertEqual({f'{{{self.NS["w"]}}}before':'60',f'{{{self.NS["w"]}}}after':'40'},first.find('w:spacing',self.NS).attrib)
            self.assertEqual(1,len(later))

    def test_current_absent_marker_and_authored_page_break_are_untouched(self):
        original=self.fixture().replace('w:name="dmp-content"','w:name="authored"')
        for auto in [False,True]:self.assertEqual(original,self.render_current(original,autoescape=auto))
        original=self.fixture().replace('<w:t>Cover</w:t>','<w:t>Cover</w:t><w:br w:type="page"/>')
        output=self.render_current(original)
        root=etree.fromstring(output.encode())
        self.assertEqual(1,len(root.findall('.//w:br',self.NS)))

    def test_current_malformed_native_boundary_fails_closed(self):
        original=self.fixture()
        for value in [original.replace(self.BREAK,''),original.replace(self.BREAK,self.BREAK*2),
                      original.replace('w:name="sec-data-collection"','w:name="authored-section"'),
                      original.replace('w:name="first-heading"','w:name="dmp-content"'),
                      original.replace(self.STYLE,self.STYLE.replace('Heading2','Heading3'),1),
                      original.replace(self.BREAK,self.BREAK+'<w:p><w:r><w:t>Keep this text</w:t></w:r></w:p>')]:
            for auto in [False,True]:
                with self.assertRaises(UndefinedError):self.render_current(value,autoescape=auto)

if __name__=='__main__':unittest.main()
