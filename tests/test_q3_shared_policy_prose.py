"""Renderer-neutral Q3 prose; original answers and diagnostics are barriers."""
import importlib.util
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from jinja2 import Environment
from markupsafe import Markup

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'experiments/q3-shared-policy-prose'


def load(name):
    spec=importlib.util.spec_from_file_location('q3_shared_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class SharedPolicyTests(unittest.TestCase):
    def render(self, value, escape=False):
        env=Environment(extensions=['jinja2.ext.do'],autoescape=escape)
        module=env.from_string((ROOT/'src/metadata-prose.html.j2').read_text()).module
        return str(module.render(Markup(value)))

    def test_shared_boundaries_english_chinese_and_mixed(self):
        for left,right,separator in [('第一句。','第二句。',''),('資料 W3C PROV。','下一句。',''),
            ('First sentence.','Second sentence.',' '),('第一句。','W3C PROV is supported.',' '),
            ('First sentence.','第二句。',' '),('第一句。','「下一句」。',' '),('第一句。','𠀀。',' ')]:
            for escape in [False,True]:
                original='<p>'+left+'</p><p>'+right+'</p>'
                self.assertEqual(self.render(original,escape),original if separator else
                    '<p class="metadata-prose">'+left+right+'</p>')

    def test_one_mixed_boundary_preserves_entire_three_paragraph_run(self):
        examples=['<p>第一句。</p><p>第二句。</p><p>W3C PROV works.</p>',
            '<p>第一句。</p><p>W3C PROV works.</p><p>第三句。</p>',
            '<p>First sentence.</p><p>第二句。</p><p>第三句。</p>']
        probe=load('probe')
        for original in examples:
            self.assertFalse(probe.eligible(BeautifulSoup('<div>'+original+'</div>','html.parser').div))
            for escape in [False,True]:self.assertEqual(self.render(original,escape),original)

    def test_preserves_dictionary_facts_and_internal_spaces(self):
        value='\n  <p>資料 W3C  PROV。</p>\n<p data-fact-id="metadata-dictionary" data-status="explicit-no">本計畫不建立字典。</p>\n<p>後設資料將公開提供。</p>  \n'
        expected='\n  <p class="metadata-prose">資料 W3C  PROV。<span data-fact-id="metadata-dictionary" data-status="explicit-no">本計畫不建立字典。</span>後設資料將公開提供。</p>  \n'
        for escape in [False,True]:self.assertEqual(self.render(value,escape),expected)

    def test_fallback_is_byte_exact_for_authored_gaps_and_unknown_markup(self):
        pair='<p>第一句。</p><p>第二句。</p>'
        examples=['', '<p>單句。</p>',pair+pair,pair+'tail',pair.replace('<p>','<p class="new">',1),
            pair.replace('第二句。','<em>第二句</em>。'),pair.replace('第二句。','第二句'),
            pair.replace('第二句。','A &amp; B。'),pair.replace('第二句。','&#x4e00;。'),
            '<div class="answer-detail">'+pair+'</div>',pair+'<div class="reading-gap"><p>尚待補充。</p></div>',
            pair.replace('<p>','<p data-fact-id="metadata-dictionary" data-status="complete">'),
            pair.replace('<p>','<p data-fact-id="metadata-dictionary" data-status="missing">',1),
            pair.replace('第二句。','<!-- original -->第二句。')]
        for example in examples:
            for escape in [False,True]:self.assertEqual(self.render(example,escape),example)

    def test_exact_source_scope_and_full_english_matrix(self):
        recipe=load('recipe');before=recipe.baseline_sources()
        candidate={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
        import json, sys
        sys.path.insert(0, str(ROOT/'scripts'))
        from current_repairs_contract import project_source as project_candidate
        current,_=project_candidate(candidate,json.loads((ROOT/'template.json').read_text()))
        self.assertEqual(current,recipe.overlay(before))
        rows=load('probe').check(ROOT,before,current,'english')
        self.assertEqual(sum(r['case'].startswith('fixture-') for r in rows),396)
        self.assertGreater(len(rows),7000)

    def test_source_drift_rejected(self):
        recipe=load('recipe');before=dict(recipe.baseline_sources());before['src/layout.css']+=b'/* drift */'
        with self.assertRaises(AssertionError):recipe.overlay(before)

    def test_oracle_protects_original_content_facts_and_boundary_space(self):
        probe=load('probe')
        before=BeautifulSoup('<div id="q-docs-metadata"><div class="answer"><div class="metadata-policy"><p>第一句。</p><p data-fact-id="metadata-dictionary" data-status="complete">W3C PROV works.</p></div><div class="answer-detail"><p>原文。  X</p></div></div></div>','html.parser')
        after,_=probe.project(before);probe.compare(before,after)
        self.assertEqual(str(after),str(before))
        for old,new in [('。</p>','。 </p>'),('原文。  X','原文。X'),('complete','explicit-no'),('PROV','Provenance')]:
            changed=str(after).replace(old,new);self.assertNotEqual(str(after),changed)
            with self.assertRaises(AssertionError):probe.compare(before,BeautifulSoup(changed,'html.parser'))


if __name__=='__main__':unittest.main()
