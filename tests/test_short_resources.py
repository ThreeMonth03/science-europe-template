import unittest
from pathlib import Path
import sys
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from markupsafe import Markup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from short_resources_contract import ENTRY, HELPER, HINT, OPENING, project_source, historical
from probe_short_resources import cases, check, fragment


class ShortResourcesTests(unittest.TestCase):
    def test_exact_pdf_entry_delta_retains_all_other_source_bytes(self):
        sources,metadata=project_source()
        self.assertEqual(metadata['version'],'0.3.39')
        self.assertNotIn(HELPER,sources)
        self.assertEqual(sources[ENTRY],historical(ENTRY))

    def test_independent_grammar_and_width_boundaries_with_both_escape_modes(self):
        rows=check(ROOT)
        self.assertEqual(len(rows),len(cases())*2)
        self.assertEqual({r['autoescape'] for r in rows},{False,True})

    def test_only_pdf_entry_adds_the_hint(self):
        for escape in (False,True):
            source=fragment()
            env=Environment(loader=ChoiceLoader([DictLoader({'src/index.html.j2':'{{ specimen }}'}),FileSystemLoader(ROOT)]),extensions=['jinja2.ext.do'],autoescape=escape)
            value=Markup(source) if escape else source
            self.assertEqual(env.get_template('src/index.html.j2').render(specimen=value),source)
            result=env.get_template(ENTRY).render(specimen=value)
            self.assertEqual(result.count(HINT),1)
            # Submission includes the same PDF entry; no separate rule.
            self.assertEqual(env.get_template('src/submission/pdf.html.j2').render(specimen=value),result)

    def test_matrix_keeps_long_missing_complex_and_unknown_cases_unmodified(self):
        names={name:selected for name,_,selected in cases()}
        for name in ('rows-3','rows-8','missing-fact','missing-class','link','image','nested-table','nested-list','two-projects','whole-1201','authored-lookalike'):
            self.assertFalse(names[name],name)
        for name in ('rows-1','whole-1200','authored-warning','chinese-authored-warning'):
            self.assertTrue(names[name],name)

    def test_no_budget_short_unit_is_kept_but_long_or_linked_prose_is_not(self):
        source = (
            '<section>' + OPENING + '<h3>15. Resources?</h3><div class="answer">'
            '<p data-requirement-id="SE-6b" data-fact-id="specialist-expertise" '
            'data-status="complete">Support is available.</p><h4>Data-management budget</h4>'
            '<div class="project-resources" data-item-id="aa.1">'
            '<p class="data-gap" data-requirement-id="SE-6b" data-fact-id="resources-costing" '
            'data-status="missing">Budget details are pending.</p></div></div></div></section>'
        )
        for escape in (False, True):
            env = Environment(loader=FileSystemLoader(ROOT), extensions=['jinja2.ext.do'], autoescape=escape)
            helper = env.get_template(HELPER).module
            value = Markup(source) if escape else source
            selected = str(helper.no_budget_document(value))
            self.assertEqual(1, selected.count(HINT))
            self.assertEqual(source.replace(OPENING, HINT, 1), selected)
            for changed in (
                source.replace('Budget details are pending.', 'x' * 181),
                source.replace('Budget details are pending.', '<a href="https://example.org">Budget</a>'),
            ):
                value = Markup(changed) if escape else changed
                self.assertEqual(changed, str(helper.no_budget_document(value)))


if __name__=='__main__':unittest.main()
