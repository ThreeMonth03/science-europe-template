import importlib.util
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'experiments/empty-section-spacing'

def load(name):
    spec=importlib.util.spec_from_file_location('section_spacing_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class EmptySectionSpacingTests(unittest.TestCase):
    def test_exact_overlay_and_all_current_fixtures(self):
        r=load('recipe');before=r.baseline_sources();after=r.overlay(before)
        self.assertEqual({n for n in before if before[n]!=after[n]},{'src/layout.css'})
        self.assertGreater(len(load('probe').check(ROOT,before,after)),200)

    def test_rejects_source_asset_and_scope_drift(self):
        r=load('recipe');before=r.baseline_sources();after=r.overlay(before)
        for name in ['src/content.html.j2','src/question-spacing.html.j2','src/layout.css','src/word/reference.docx']:
            with self.assertRaises(AssertionError):r.overlay({**before,name:before[name]+b'!'} )
            with self.assertRaises(AssertionError):r.project_prepared(before,{**after,name:after[name]+b'!'})
        with self.assertRaises(AssertionError):r.project_prepared(before,{**after,'src/new':b''})

    def test_only_print_margins_no_font_word_or_hidden_box_change(self):
        r=load('recipe');css=r.CSS.decode().split('*/',1)[1]
        self.assertEqual(list(r.COUNTS.values()),[2,2,2,3,4,2])
        self.assertIn('@media print {',css)
        for forbidden in ['font-', 'line-height:', 'display:', 'break-', '!important','> .answer']:
            self.assertNotIn(forbidden,css)
        self.assertEqual(css.count(' { margin-bottom: .8em; }'),1)
        self.assertEqual(css.count(' { margin-top: .9em; margin-bottom: .4em; }'),1)

    def test_independent_scope_matrix(self):
        p=load('probe');rows=p.cases();self.assertGreater(len(rows),60)
        selected=[name for name,source in rows if p.expected(BeautifulSoup(source,'html.parser'))]
        self.assertEqual(len(selected),6)
        self.assertTrue(all(name.endswith('-'+('0'*len(name.rsplit('-',1)[1]))) for name in selected))

if __name__=='__main__':unittest.main()
