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
    def test_other_recurring_fees_are_active_independent_complete_facts(self):
        from check_answer_mapping import chapter, question, schema
        from test_science_europe_contract import render_question

        sentences = {
            'Yes': 'There are other recurring fees for keeping data or documents available.',
            'No': 'There are no other recurring fees for keeping data or documents available.',
        }
        fee_path = path('preservingCUuid', 'otherRecurringFeesQUuid')
        fee_qid = IDS['otherRecurringFeesQUuid']

        def fixture(choice, charges=None, datasets=False):
            km = schema()
            preserving = chapter(km, IDS['preservingCUuid'])
            question(km, preserving, fee_qid, 'OptionsQuestion',
                     [IDS['otherRecurringFees' + option + 'AUuid'] for option in ('Yes', 'No')])
            question(km, preserving, IDS['repoChargesQUuid'], 'OptionsQuestion',
                     [IDS['repoCharges' + option + 'AUuid'] for option in ('Yes', 'No')])
            question(km, preserving, IDS['producedDataQUuid'], 'ListQuestion')
            replies = {path('adminDetailsCUuid', 'additionalHWSWQUuid'): IDS['additionalHWSWNoAUuid']}
            if choice is not None:
                replies[fee_path] = IDS.get('otherRecurringFees' + choice + 'AUuid', choice)
            if charges is not None:
                replies[path('preservingCUuid', 'repoChargesQUuid')] = IDS['repoCharges' + charges + 'AUuid']
            if datasets:
                replies[path('preservingCUuid', 'producedDataQUuid')] = ['dataset-1']
            return km, replies

        for profile, choice, charges, datasets, with_km in itertools.product(
                ('submission', 'review'), ('Yes', 'No'), (None, 'Yes', 'No'), (False, True), (False, True)):
            with self.subTest(profile=profile, choice=choice, charges=charges,
                              datasets=datasets, with_km=with_km):
                km, replies = fixture(choice, charges, datasets)
                context = {'output_profile': profile}
                if with_km:
                    context['km'] = km
                soup = BeautifulSoup(render_question(QUESTION, replies, **context), 'html.parser')
                node = soup.select_one('[data-fact-id="other-recurring-fees"]')
                self.assertEqual(sentences[choice], node.get_text())
                self.assertEqual('complete' if choice == 'Yes' else 'explicit-no', node['data-status'])
                self.assertEqual(1, soup.get_text().count(sentences[choice]))
                self.assertIsNone(node.find_parent(class_='project-resources'))
                if charges:
                    charge = soup.select_one('[data-fact-id="repository-charges"]')
                    self.assertEqual('span', charge.name)
                    self.assertEqual('hardware-software', charge.parent['data-fact-id'])
                    self.assertEqual('No repository service charges are expected.' if charges == 'No' else
                                     'The selected repositories charge for their services.', charge.get_text())
                    self.assertNotIn(node, charge.parent.descendants)

        for profile, choice, invalid in itertools.product(
                ('submission', 'review'), ('Yes', 'No'),
                ('missing', 'blank', 'unknown', 'removed-question', 'removed-root-membership',
                 'removed-choice', 'removed-answer', 'wrong-type', 'removed-chapter')):
            with self.subTest(profile=profile, choice=choice, invalid=invalid):
                km, replies = fixture(choice, 'Yes')
                q = km['entities']['questions'][fee_qid]
                aid = IDS['otherRecurringFees' + choice + 'AUuid']
                if invalid == 'missing':
                    replies.pop(fee_path)
                elif invalid == 'blank':
                    replies[fee_path] = ''
                elif invalid == 'unknown':
                    replies[fee_path] = 'future-choice'
                elif invalid == 'removed-question':
                    km['entities']['questions'].pop(fee_qid)
                elif invalid == 'removed-root-membership':
                    km['entities']['chapters'][IDS['preservingCUuid']]['questionUuids'].remove(fee_qid)
                elif invalid == 'removed-choice':
                    q['answerUuids'].remove(aid)
                elif invalid == 'removed-answer':
                    km['entities']['answers'].pop(aid)
                elif invalid == 'wrong-type':
                    q['questionType'] = 'ValueQuestion'
                elif invalid == 'removed-chapter':
                    km['chapterUuids'].remove(IDS['preservingCUuid'])
                soup = BeautifulSoup(render_question(QUESTION, replies, km=km, output_profile=profile), 'html.parser')
                self.assertFalse(soup.select('[data-fact-id="other-recurring-fees"]'))
                self.assertIn('The selected repositories charge for their services.', soup.get_text())

    def test_exact_source_projection_retains_all_other_sources_and_metadata(self):
        sources, metadata = project_source()
        self.assertEqual(metadata['version'], '0.3.40')
        self.assertEqual(sources[QUESTION], historical(QUESTION))
        self.assertNotIn(HELPER, sources)

    def test_choice_matrix_changes_only_the_explicit_owned_pair(self):
        # This exact .40 -> .41 proof must not render later Q15 presentation layers.
        from short_resource_rows_contract import project_source as project_rows
        sources, metadata = project_rows()
        self.assertEqual('0.3.41', metadata['version'])
        old = historical(QUESTION).decode(); new = sources[QUESTION].decode()
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
