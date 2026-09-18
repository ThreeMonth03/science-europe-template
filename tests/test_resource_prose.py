"""Only two answered, template-owned Q15 sentences may share a paragraph."""
import itertools
import sys
import unittest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from markupsafe import Markup
from bs4 import BeautifulSoup
from test_science_europe_contract import ROOT, reply_path, reply_str_value, reply_items

sys.path.insert(0, str(ROOT/'scripts'))
from generate_pilot_fixtures import IDS, path
from resource_prose_contract import QUESTION, HELPER, historical, project_source

OPEN = '<p data-requirement-id="SE-6b" data-fact-id="hardware-software" data-status="explicit-no">'
SPAN = '<span data-fact-id="repository-charges" data-status="complete">'


def render(source, replies, escaped=False):
    env = Environment(loader=ChoiceLoader([DictLoader({QUESTION:source}), FileSystemLoader(ROOT)]),
                      extensions=['jinja2.ext.do'], autoescape=escaped)
    env.filters.update(reply_path=reply_path, reply_str_value=reply_str_value,
                       reply_items=reply_items, markdown=lambda s: Markup(s))
    return env.from_string("{% import 'src/uuids.j2' as uuids %}{% include '"+QUESTION+"' %}").render(repliesMap=replies)


class ResourceProseTests(unittest.TestCase):
    def test_exact_source_projection_retains_all_other_sources_and_metadata(self):
        sources, metadata = project_source()
        self.assertEqual(metadata['version'], '0.3.40')
        self.assertEqual(sources[QUESTION], historical(QUESTION))
        self.assertNotIn(HELPER, sources)

    def test_choice_matrix_changes_only_the_explicit_owned_pair(self):
        old = historical(QUESTION).decode(); new = (ROOT/QUESTION).read_text()
        for hw, charges, details, escaped in itertools.product(
                [None, '', 'unknown', 'No', 'Yes'], [None, '', 'unknown', 'No', 'Yes'],
                ['', '<p>Original.csv: 0. 尚待補充：保留。  不刪。</p>'], [False, True]):
            replies = {path('adminDetailsCUuid','additionalHWSWQUuid','additionalHWSWYesAUuid','additionalHWSWYesWhatQUuid'): details}
            for value, names, key in [(hw, ('adminDetailsCUuid','additionalHWSWQUuid'), 'additionalHWSW'),
                                      (charges, ('preservingCUuid','repoChargesQUuid'), 'repoCharges')]:
                if value is not None: replies[path(*names)] = IDS.get(key+value+'AUuid', value)
            before = render(old,replies,escaped); after = render(new,replies,escaped)
            selected = hw == 'No' and charges in ('No','Yes')
            with self.subTest(hw=hw,charges=charges,details=bool(details),escaped=escaped):
                if not selected:
                    self.assertEqual(after,before)
                else:
                    soup = BeautifulSoup(before,'html.parser'); a=soup.find(attrs={'data-fact-id':'hardware-software'}); b=a.find_next_sibling()
                    first,last=a.get_text(),b.get_text()
                    start=before.index(OPEN); end=before.index('</p>',before.index('<p>',start+len(str(a))))+4
                    expected=before[:start]+OPEN+first+' '+SPAN+last+'</span></p>'+before[end:]
                    self.assertEqual(after,expected)
                    actual=BeautifulSoup(after,'html.parser')
                    self.assertEqual(actual.select_one('[data-fact-id="repository-charges"]')['data-status'],'complete')
                    self.assertFalse(actual.select('p p, p div, p ul'))

    def test_chinese_separator_and_both_escape_modes_preserve_all_punctuation(self):
        for escaped in (False,True):
            env=Environment(loader=FileSystemLoader(ROOT),extensions=['jinja2.ext.do'],autoescape=escaped)
            helper=env.get_template(HELPER).module
            for first,last,separator in [('No extra equipment.','No service charges.',' '),
                ('除機構通常提供的資源外，我們不需要其他硬體或軟體。','預計使用的資料儲存庫不收取服務費。',''),
                ('除機構通常提供的資源外，我們不需要其他硬體或軟體。','預計使用的資料儲存庫會收取服務費。','')]:
                source='\n'+OPEN+first+'</p>\n <p>'+last+'</p>\n'
                source=Markup(source) if escaped else source
                self.assertEqual(str(helper.render(source,True)),'\n'+OPEN+first+separator+SPAN+last+'</span></p>\n')
                self.assertEqual(str(helper.render(source,False)),source)

    def test_unsupported_shape_and_longer_translation_fail_closed(self):
        helper=Environment(loader=FileSystemLoader(ROOT),extensions=['jinja2.ext.do']).get_template(HELPER).module
        source=OPEN+'No equipment.</p><p>No charges.</p>'
        for original in [source+source, source.replace('<p>No','<p class="data-gap">No'),
                         source.replace('No charges.','<em>No charges.</em>'),source.replace('No equipment.','x'*161+'.'),
                         source.replace('No charges.','是否收費？'),source.replace('</p><p>','</p><!-- keep --><p>')]:
            self.assertEqual(str(helper.render(original,True)),original)


if __name__ == '__main__': unittest.main()
