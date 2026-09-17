import sys
import unittest
from pathlib import Path
from jinja2 import Environment,FileSystemLoader
from markupsafe import Markup
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from storage_context_contract import check_roots,fragments,without_reviewed_context


class StorageContextTests(unittest.TestCase):
    def test_historic_style_gates_only_admit_exact_reviewed_blocks(self):
        for kind,path in [('css','src/layout.css'),('lua','src/word/pilot.lua')]:
            source=(ROOT/path).read_text(); without_reviewed_context(source,kind)
            with self.assertRaises(AssertionError): without_reviewed_context(source+'\n',kind)
            changed=source.replace('break-inside: avoid; }','break-inside: auto; }',1) if kind=='css' else source.replace('units > 900','units > 901')
            with self.assertRaises(AssertionError): without_reviewed_context(changed,kind)
    def test_entire_q5_frozen_behavior_with_all_existing_fixtures(self):
        rows=check_roots(ROOT,ROOT/'fixtures/pilot/en',ROOT/'tests/fixtures/storage-context-0.3.33.en.html.j2')
        self.assertGreater(len(rows),100)
        self.assertEqual({r['eligible'] for r in rows},{True,False})

    def test_exact_fragment_and_conservative_fallback(self):
        for escape in [False,True]:
            env=Environment(loader=FileSystemLoader(ROOT),extensions=['jinja2.ext.do'],autoescape=escape)
            helper=env.get_template('src/storage-reading.html.j2').module
            for name,fragment,selected in fragments():
                expected='<div class="answer'+(' q5-short-context' if selected else '')+'">'+fragment+'</div>'
                self.assertEqual(helper.answer(Markup(fragment) if escape else fragment),expected,(name,escape))
