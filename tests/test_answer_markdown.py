"""Transport guards and a batched parser regression in the pinned stock worker."""
import html
import json
import re
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace
import unittest

from jinja2 import Environment, FileSystemLoader
from lxml import html as lhtml
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from current_support import install_i18n
from native_support import answer_markdown_steps


def replies(values):
    return {str(i): {'value': {'type': 'StringReply', 'value': value}}
            for i, value in enumerate(values)}


class AnswerMarkdownTests(unittest.TestCase):
    def environment(self, escape=True):
        env = Environment(loader=FileSystemLoader(ROOT), autoescape=escape)
        env.filters['markdown'] = lambda value: Markup(value)
        install_i18n(env, ROOT)
        return env

    def render(self, source, transport, escape=True):
        env = self.environment(escape)
        template = env.from_string('{% import "src/answer-markdown.html.j2" as answer with context %}{{ answer.markdown(value) }}')
        return template.render(value=source, ctx={'project': {'replies': replies([source])}},
            document=SimpleNamespace(content=transport.encode(), safe_encoding='utf-8'), json=json)

    def fragment(self, source, body='<p>Original rendered answer.</p>'):
        encoded = html.escape(json.dumps(source, ensure_ascii=False), quote=True)
        return '<div id="dsw-md-1" data-source-json="' + encoded + '">' + body + '</div>'

    def test_transport_is_exact_and_only_string_replies_are_parsed(self):
        values = ['', '   ', '\t\n', '1. First\n   - Child\n2. Next',
                  '中英 & "quotes"\n\n</pre><script>literal</script>']
        data = replies(values)
        data['choice'] = {'value': {'type': 'AnswerReply', 'value': 'not Markdown'}}
        for escape in [False, True]:
            rendered = self.environment(escape).get_template('src/answer-markdown-inputs.html.j2').render(
                ctx={'project': {'replies': data}})
            doc = lhtml.fragment_fromstring(rendered, create_parent=True)
            self.assertEqual([json.loads(node.text_content()) for node in doc], values)
            self.assertTrue(all(len(node) == 1 and node[0].tag == 'code' for node in doc))
            self.assertEqual(doc.xpath('./pre/@id'), ['dsw-md-' + str(i + 1) for i in range(len(values))])
            self.assertFalse(doc.xpath('.//script'))
            self.assertEqual(self.environment(escape).get_template('src/answer-markdown-inputs.html.j2').render(
                ctx={'project': {'replies': {}}}), '')

    def test_exact_source_guard_does_not_collapse_spaces_tabs_or_unicode(self):
        for escape in [False, True]:
            for source in ['', '   ', '\t', '1. First\n   - Child\n2. Next', '中 & <literal>']:
                with self.subTest(source=source, escape=escape):
                    self.assertEqual(self.render(source, self.fragment(source), escape), '<p>Original rendered answer.</p>')

    def test_missing_mismatched_duplicate_and_nested_transport_keep_literal_answer(self):
        source = '1. Original\n   - Child & <literal>'
        for escape in [False, True]:
            valid = self.fragment(source)
            invalid = ['', self.fragment(source.replace('   ', '    ')), valid + valid,
                       valid.replace('</div>', ''), self.fragment(source, '<div>wrong nested body</div>')]
            for transport in invalid:
                output = self.render(source, transport, escape)
                doc = lhtml.fragment_fromstring(output)
                self.assertEqual(doc.tag, 'pre')
                self.assertEqual(doc.get('class'), 'answer-markdown-fallback')
                self.assertEqual(doc.text_content(), source)
                self.assertFalse(doc.xpath('.//literal'))

    def test_all_eight_formats_share_the_owned_markdown_prefix(self):
        metadata = json.loads((ROOT / 'template.json').read_text())
        self.assertEqual(len(metadata['formats']), 8)
        for fmt in metadata['formats']:
            self.assertEqual(fmt['steps'][:2], answer_markdown_steps())

    def test_confirmed_free_text_consumers_use_the_owned_parser(self):
        consumers = {
            'src/questions/01-how-data.html.j2': ['refDataUsageReply', 'refDataVersionedWhich', 'refDataConditionsOtherReply', 'nrefDataUsageReply'],
            'src/reuse-summary.html.j2': ['authored'],
            'src/reuse-rightsholder.html.j2': ['owner'],
            'src/nonreuse.html.j2': ['detail'],
            'src/questions/02-what-data.html.j2': ['neqDataSetsDesc', 'entryOther', 'formatsWhyNSAnotherReason', 'ownershipOther'],
            'src/questions/03-docs-metadata.html.j2': ['explanation', 'scFSysSubjFoldersConvs',
                'scFSysAnalysisFoldersConvs', 'scFSysWorkflowStepFoldersConvs',
                'scFSysAppointments', 'scObjStoreNaming'],
            'src/quality-control.html.j2': ['otherText'],
            'src/project-file-naming.html.j2': ['authored'],
            'src/questions/06-access-security.html.j2': ['risksPseudonymizationAnother', 'policiesProceduresItemDescriptionReply'],
            'src/questions/07-personal-data.html.j2': ['personalDataSafeguardElaborateReply', 'personalDataSafeguardTransferMeasuresReply'],
            'src/questions/08-copyright-ipr.html.j2': ['notOpenBusinessReasonsOther', 'notOpenOtherReasonsOther',
                                                       'refDataConditionsOther', 'nrefDataConditionsOther', 'ownershipOther',
                                                       'legalReasonsAuthenticatedOtherReply', 'legalReasonsAuthenticatedCommitteeReply'],
            'src/questions/09-ethical-issues.html.j2': ['cpersExplainInformed', 'cpersDescribeProcedure', 'cpersGdprPurpose'],
            'src/questions/10-share-restrictions.html.j2': ['qref.relation', 'authorizationDetails',
                                                         'licenseRestrictConditions', 'licenseRestrictAccessAnother'],
            'src/reference-publication-plan.html.j2': ['authored'],
            'src/questions/11-data-preservation.html.j2': ['domainSpecificRepoContactBeforeOther', 'repoChargesHowPayOther'],
            'src/reference-maintenance-plan.html.j2': ['authored'],
            'src/preservation-dataset.html.j2': ['producedDescription'],
            'src/preservation-publication-reason.html.j2': ['reasonText'],
            'src/post-project-archive.html.j2': ['arrangement'],
            'src/questions/13-persistent-identifier.html.j2': ['reuseHow'],
            'src/questions/15-required-resources.html.j2': [
                'expertiseTrainText', 'projectCostItemDescriptionReply', 'costCoverOtherHowReply', 'additionalHWSWWhat'],
        }
        for name, values in consumers.items():
            source = (ROOT / name).read_text()
            self.assertIn('import "src/answer-markdown.html.j2" as answerMarkdown with context', source)
            for value in values:
                with self.subTest(file=name, value=value):
                    expected = 2 if value in ['notOpenBusinessReasonsOther', 'notOpenOtherReasonsOther'] else 1
                    self.assertEqual(source.count('answerMarkdown.markdown(' + value + ')'), expected)
                    self.assertFalse(re.search(r'\b' + re.escape(value) + r'\s*\|\s*markdown\b', source))

    def test_q1_dataset_groups_preserve_exact_authored_blocks_and_parent_gates(self):
        from current_support import IDS, PREFIX, environment, path
        from jinja2 import Undefined
        envelope = lambda value, kind='StringReply': {'value': {'type': kind, 'value': value}}
        source = 'Original opening.\n\n1. Parent\n    - Child\n2. Next\n\n| Field | Value |\n| --- | --- |\n| Original | 0 |\n\nLiteral `A<B&C>D`. [Procedure](https://example.org/procedure?a=1&b=2)'
        rich = '<p>Original opening.</p><ol><li>Parent<ul><li>Child</li></ul></li><li>Next</li></ol><table><tr><th>Field</th><th>Value</th></tr><tr><td>Original</td><td>0</td></tr></table><p>Literal <code>A&lt;B&amp;C&gt;D</code>. <a href="https://example.org/procedure?a=1&amp;b=2">Procedure</a></p>'
        for kind in ('measured', 'ref', 'nref'):
            measured = kind == 'measured'
            parent = path('creatingCUuid', 'measuredQUuid') if measured else path('reusingCUuid', 'preexistingQUuid')
            yes, no = ('measuredYesAUuid', 'measuredNoAUuid') if measured else ('preexistingYesAUuid', 'preexistingNoAUuid')
            listing = path(parent, yes, 'measuredDataQUuid' if measured else kind + 'DataQUuid')
            first = path(listing, 'dataset-a')
            values = {parent: envelope(IDS[yes], 'AnswerReply'),
                      listing: envelope(['dataset-a', 'dataset-b'], 'ItemListReply'),
                      path(first, 'measuredDataNameQUuid' if measured else kind + 'DataNameQUuid'): envelope('Dataset A')}
            if measured:
                instruments = path(first, 'measuredDataInstrQUuid')
                values.update({instruments: envelope(['sensor'], 'ItemListReply'),
                    path(instruments, 'sensor', 'measuredDataInstrNameQUuid'): envelope('Sensor A')})
                detail = path(instruments, 'sensor', 'measuredDataInstrDescQUuid')
            else:
                use = path(first, kind + 'DataUseQUuid')
                values[use] = envelope(IDS[kind + 'DataUseYesAUuid'], 'AnswerReply')
                detail = path(use, kind + 'DataUseYesAUuid', kind + 'DataUsageQUuid')
            values[detail] = envelope(source)
            transport = ''.join(self.fragment(reply['value']['value'], rich if key == detail else '<p>' + html.escape(reply['value']['value']) + '</p>').replace('dsw-md-1', 'dsw-md-' + str(i))
                for i, (key, reply) in enumerate(values.items(), 1) if reply['value']['type'] == 'StringReply')
            for escape in (False, True):
                env = environment(ROOT, escape=escape)
                env.loader = FileSystemLoader(ROOT)  # Exercise the real exact-source guard.
                env.filters['reply_str_value'] = lambda reply: '' if isinstance(reply, Undefined) else reply['value']['value'] if isinstance(reply, dict) else reply
                env.filters['reply_items'] = lambda reply: reply['value']['value'] if isinstance(reply, dict) and reply['value']['type'] == 'ItemListReply' else []
                render = env.from_string(PREFIX + "{% include 'src/questions/01-how-data.html.j2' %}").render
                for profile in ('review', 'submission'):
                    def output(data):
                        return render(repliesMap=data, ctx={'project': {'replies': data}}, json=json,
                            document=SimpleNamespace(content=transport.encode(), safe_encoding='utf-8'), output_profile=profile)
                    rendered = output(values)
                    doc = lhtml.fragment_fromstring(rendered, create_parent=True)
                    owners = doc.xpath('.//div[@id="q-how-data"]//div[@class="dataset-list"]/div[@class="dataset-section"]')
                    with self.subTest(kind=kind, escape=escape, profile=profile):
                        self.assertEqual([node.get('data-item-id') for node in owners],
                            [path(listing, item) if measured else item for item in ('dataset-a', 'dataset-b')])
                        self.assertTrue(all(not node.xpath('ancestor::ul | ancestor::ol') for node in owners))
                        self.assertIn(rich, rendered, 'Authored blocks must retain their exact transport bytes')
                        self.assertEqual(len(owners[0].xpath('.//ol/li[1]/ul/li')), 1)
                        self.assertEqual(owners[0].xpath('.//code/text()'), ['A<B&C>D'])
                        self.assertEqual(owners[0].xpath('.//a/@href'), ['https://example.org/procedure?a=1&b=2'])
                        self.assertEqual([[cell.text_content() for cell in row] for row in owners[0].xpath('.//tr')], [['Field', 'Value'], ['Original', '0']])
                        self.assertNotIn('Original opening.', owners[1].text_content())
                        self.assertFalse(doc.xpath('.//pre[@class="answer-markdown-fallback"] | .//p//div | .//p//table | .//p//ol'))
                        inactive = lhtml.fragment_fromstring(output({**values, parent: envelope(IDS[no], 'AnswerReply')}), create_parent=True)
                        self.assertFalse(inactive.xpath('.//div[@class="dataset-section"] | .//ol | .//table'))
                        if profile == 'submission':
                            self.assertFalse(doc.xpath('.//*[@class="data-gap"]'))

    def test_q1_single_multi_and_sparse_instruments_keep_each_exact_description(self):
        from current_support import IDS, PREFIX, environment, path
        from jinja2 import Undefined
        envelope = lambda value, kind='StringReply': {'value': {'type': kind, 'value': value}}
        bodies = {}
        for key in ('A', 'B'):
            source = f'{key} opening.\n\n{key} separate paragraph.\n\n- {key} original item\n\n| Field | Value |\n| --- | --- |\n| {key} | 0 |\n\n[{key} procedure](https://example.org/{key})'
            rich = f'<p>{key} opening.</p><p>{key} separate paragraph.</p><ul><li>{key} original item</li></ul><table><tr><th>Field</th><th>Value</th></tr><tr><td>{key}</td><td>0</td></tr></table><p><a href="https://example.org/{key}">{key} procedure</a></p>'
            bodies[source] = rich
        first, second = bodies
        cases = [[('Sensor A', first)], [('Sensor A', first), ('Sensor B', second)],
                 [('', ''), ('', ''), ('', second)]]
        parent = path('creatingCUuid', 'measuredQUuid')
        listing = path(parent, 'measuredYesAUuid', 'measuredDataQUuid')
        instruments = path(listing, 'dataset', 'measuredDataInstrQUuid')
        for rows in cases:
            values = {parent: envelope(IDS['measuredYesAUuid'], 'AnswerReply'),
                      listing: envelope(['dataset'], 'ItemListReply'),
                      instruments: envelope([str(i) for i in range(1, len(rows) + 1)], 'ItemListReply')}
            for index, (name, description) in enumerate(rows, 1):
                values[path(instruments, str(index), 'measuredDataInstrNameQUuid')] = envelope(name)
                values[path(instruments, str(index), 'measuredDataInstrDescQUuid')] = envelope(description)
            transport = ''.join(self.fragment(reply['value']['value'], bodies.get(reply['value']['value'], '<p>' + html.escape(reply['value']['value']) + '</p>')).replace('dsw-md-1', 'dsw-md-' + str(index))
                for index, reply in enumerate(values.values(), 1) if reply['value']['type'] == 'StringReply')
            for escape in (False, True):
                env = environment(ROOT, escape=escape)
                env.loader = FileSystemLoader(ROOT)
                env.filters['reply_str_value'] = lambda reply: '' if isinstance(reply, Undefined) else reply['value']['value'] if isinstance(reply, dict) else reply
                env.filters['reply_items'] = lambda reply: reply['value']['value'] if isinstance(reply, dict) and reply['value']['type'] == 'ItemListReply' else []
                render = env.from_string(PREFIX + "{% include 'src/questions/01-how-data.html.j2' %}").render
                for profile in ('review', 'submission'):
                    with self.subTest(rows=len(rows), sparse=not rows[0][0], escape=escape, profile=profile):
                        output = render(repliesMap=values, ctx={'project': {'replies': values}}, json=json,
                            document=SimpleNamespace(content=transport.encode(), safe_encoding='utf-8'), output_profile=profile)
                        doc = lhtml.fragment_fromstring(output, create_parent=True)
                        owner = doc.xpath('.//div[@class="dataset-section"]')[0]
                        details = owner.xpath('.//div[@class="answer-detail"]')
                        expected = [(index, name, description) for index, (name, description) in enumerate(rows, 1)
                                    if name or description or profile == 'review']
                        labels = owner.xpath('./div[@class="single-instrument"]/p/strong | ./ul/li/p/strong')
                        self.assertEqual([name or f'Instrument {index}' for index, name, _ in expected], [label.text_content() for label in labels])
                        self.assertEqual(sum(bool(description) for _, description in rows), len(details))
                        for detail, (_, _, description) in zip(details, (row for row in expected if row[2])):
                            self.assertIn(bodies[description], output)
                            self.assertEqual([node.tag for node in detail], ['p', 'p', 'ul', 'table', 'p'])
                            self.assertEqual(detail.xpath('.//a/@href'), ['https://example.org/' + ('A' if description == first else 'B')])
                        self.assertEqual(2 if len(rows) == 3 and profile == 'review' else 0,
                            len(owner.xpath('.//*[@data-fact-id="instrument-details"]')))
                        self.assertFalse(doc.xpath('.//pre[@class="answer-markdown-fallback"] | .//p//div | .//p//table | .//p//ul'))
                        if profile == 'submission': self.assertFalse(doc.xpath('.//*[@class="data-gap"]'))

    def test_q8_ownership_and_q10_relation_retain_exact_owned_transport(self):
        from current_support import IDS, PREFIX, environment, path
        from jinja2 import Undefined
        envelope = lambda value, kind='StringReply': {'value': {'type': kind, 'value': value}}
        ownership = path('creatingCUuid', 'ownershipQUuid')
        ownership_detail = path(ownership, 'ownershipOtherAUuid', 'ownershipOtherQUuid')
        datasets = path('preservingCUuid', 'producedDataQUuid')
        publication = path(datasets, 'dataset-a', 'isPublishedDataQUuid')
        decision = path(publication, 'isPublishedDataYesAUuid', 'publishedQReferencesQUuid')
        listing = path(decision, 'publishedQReferencesYesAUuid', 'publishedQReferencesItemQUuid')
        relation = path(listing, 'relation-only', 'publishedQReferenceRelQUuid')
        identifier = path(listing, 'id-only', 'publishedQReferenceIdQUuid')
        literal_id = 'doi:10.0000/REF_<A&B>'
        source = '| Field | Value |\n| --- | --- |\n| Original | 0 |\n\n1. Parent\n    - Child\n2. Next\n\nLiteral `A<B&C>D`. [Procedure](https://example.org/procedure?a=1&b=2)'
        rich = '<table><tr><th>Field</th><th>Value</th></tr><tr><td>Original</td><td>0</td></tr></table><ol><li>Parent<ul><li>Child</li></ul></li><li>Next</li></ol><p>Literal <code>A&lt;B&amp;C&gt;D</code>. <a href="https://example.org/procedure?a=1&amp;b=2">Procedure</a></p>'
        fixtures = [
            ('src/questions/08-copyright-ipr.html.j2', ownership_detail,
             {ownership: envelope(IDS['ownershipOtherAUuid'], 'AnswerReply')},
             [(ownership, None), (ownership, IDS['ownershipInstituteAUuid'])]),
            ('src/questions/10-share-restrictions.html.j2', relation,
             {datasets: envelope(['dataset-a'], 'ItemListReply'),
              publication: envelope(IDS['isPublishedDataYesAUuid'], 'AnswerReply'),
              decision: envelope(IDS['publishedQReferencesYesAUuid'], 'AnswerReply'),
              listing: envelope(['id-only', 'relation-only', 'empty'], 'ItemListReply'),
              identifier: envelope(literal_id)},
             [(publication, None), (publication, IDS['isPublishedDataNoAUuid']),
              (decision, IDS['publishedQReferencesNoAUuid']), (listing, [])]),
        ]
        for escape in [False, True]:
            env = environment(ROOT, escape=escape)
            env.loader = FileSystemLoader(ROOT)  # Actual exact-source guard, not the identity shim.
            env.filters['reply_str_value'] = lambda reply: '' if isinstance(reply, Undefined) else reply['value']['value'] if isinstance(reply, dict) else reply
            env.filters['reply_items'] = lambda reply: reply['value']['value'] if isinstance(reply, dict) and reply['value']['type'] == 'ItemListReply' else []
            for question, detail_path, parents, inactive_states in fixtures:
                render = env.from_string(PREFIX + "{% include '" + question + "' %}").render
                for profile in ['submission', 'review']:
                    for value in [None, '', ' \t\n\u3000', '0', 'false', source]:
                        data = dict(parents)
                        if value is not None: data[detail_path] = envelope(value)
                        body = rich if value == source else '<p>' + html.escape(value or '') + '</p>'
                        # Supply an independently rendered fragment; this checks transport,
                        # ownership and literal equality, not Markdown parser behaviour.
                        transport = ''.join(self.fragment(reply['value']['value'], body if key == detail_path else '<p>' + html.escape(reply['value']['value']) + '</p>').replace('dsw-md-1', 'dsw-md-' + str(i))
                            for i, (key, reply) in enumerate(data.items(), 1) if reply['value']['type'] == 'StringReply')
                        def output(values):
                            return lhtml.fragment_fromstring(render(repliesMap=values,
                                ctx={'project': {'replies': values}}, json=json,
                                document=SimpleNamespace(content=transport.encode(), safe_encoding='utf-8'),
                                output_profile=profile), create_parent=True)
                        doc = output(data)
                        details = doc.xpath('.//div[@class="answer-detail"]')
                        present = isinstance(value, str) and bool(value.strip())
                        with self.subTest(question=question, value=value, escape=escape, profile=profile):
                            self.assertEqual(len(details), int(present))
                            self.assertFalse(doc.xpath('.//pre[@class="answer-markdown-fallback"]'))
                            self.assertFalse(doc.xpath('.//p//p | .//p//div | .//p//table'))
                            if question.endswith('08-copyright-ipr.html.j2'):
                                if present:
                                    lead = details[0].find('div')
                                    self.assertIsNotNone(lead)
                                    self.assertEqual(lead.get('class'), 'answer-lead')
                                    self.assertEqual([n.tag for n in lead], ['p'])
                                    self.assertEqual(lead.text_content(), 'We have made the following arrangements regarding data ownership:')
                                else: self.assertIn('Rights to the collected data are arranged in another way.', doc.text_content())
                            else:
                                owner = doc.xpath('.//div[@class="dataset-section" and @data-item-id="dataset-a"]')[0]
                                self.assertEqual(len(owner.xpath('./ul/li')), 2 if present else 1)
                                self.assertEqual(owner.xpath('./ul/li[1]/p/em/text()'), [literal_id])
                            if present:
                                authored = list(details[0])[1:] if question.endswith('08-copyright-ipr.html.j2') else details[0]
                                self.assertEqual(''.join(lhtml.tostring(n, encoding='unicode', with_tail=False) for n in authored), body)
                            if value == source:
                                self.assertEqual([[c.text_content() for c in row] for row in details[0].xpath('.//tr')], [['Field', 'Value'], ['Original', '0']])
                                self.assertEqual(len(details[0].xpath('./ol/li[1]/ul/li')), 1)
                                self.assertEqual(details[0].xpath('.//code/text()'), ['A<B&C>D'])
                                self.assertEqual(details[0].xpath('.//a/@href'), ['https://example.org/procedure?a=1&b=2'])
                        for parent, choice in inactive_states:
                            inactive = dict(data)
                            if choice is None: inactive.pop(parent)
                            else: inactive[parent] = envelope(choice, 'ItemListReply' if isinstance(choice, list) else 'AnswerReply')
                            self.assertFalse(output(inactive).xpath('.//div[@class="answer-detail"]'))

    def test_q7_fixed_leads_use_the_existing_word_keep_next_block(self):
        from test_science_europe_contract import render_question
        from native_support import personal_replies as replies, PATHS, QUESTION
        from bs4 import BeautifulSoup
        body = '<p>Original explanation.</p><table><tr><td>Key exports</td><td>0</td></tr></table>'
        for profile in ['submission', 'review']:
            values = replies('personal-transfer-complete')
            values[PATHS['additional']] = values[PATHS['measures']] = body
            soup = BeautifulSoup(render_question(QUESTION, values, output_profile=profile), 'html.parser')
            for fact in ['personal-data-additional-safeguards', 'personal-data-transfer-measures']:
                detail = soup.select_one('[data-fact-id="'+fact+'"][data-status="complete"]')
                lead = detail.find_previous_sibling()
                self.assertEqual(lead.name, 'div')
                self.assertEqual(lead.get('class'), ['answer-lead'])
                self.assertEqual([n.name for n in lead.find_all(recursive=False)], ['p'])
                self.assertEqual([n.name for n in detail.find_all(recursive=False)], ['p', 'table'])
            self.assertFalse(soup.select('p p, p div, p table'))

    def test_q2_nonstandard_reason_uses_exact_owned_rich_transport(self):
        from current_support import IDS, PREFIX, environment, path
        from jinja2 import Undefined
        source = '| Field | Treatment |\n| --- | --- |\n| time | UTC |\n| value | 0 |\n\n1. Parent\n   - Child\n2. Next\n\n```text\nkeep <literal> & 100%\n```'
        rich = '<table><thead><tr><th>Field</th><th>Treatment</th></tr></thead><tbody><tr><td>time</td><td>UTC</td></tr><tr><td>value</td><td>0</td></tr></tbody></table><ol><li>Parent<ul><li>Child</li></ul></li><li>Next</li></ol><pre><code>keep &lt;literal&gt; &amp; 100%</code></pre>'
        listing = path('creatingCUuid', 'formatsQUuid')
        def envelope(value, kind='StringReply'):
            return {'value': {'type': kind, 'value': value}}
        for escape in [False, True]:
            env = environment(ROOT, escape=escape)
            env.loader = FileSystemLoader(ROOT)  # Actual helper, not the body-test shim.
            env.filters['reply_str_value'] = lambda reply: '' if isinstance(reply, Undefined) else reply['value']['value'] if isinstance(reply, dict) and isinstance(reply['value']['value'], str) else reply if isinstance(reply, str) else ''
            env.filters['reply_items'] = lambda reply: reply['value']['value'] if isinstance(reply, dict) and reply['value']['type'] == 'ItemListReply' else []
            render = env.from_string(PREFIX + "{% include 'src/questions/02-what-data.html.j2' %}").render
            for profile in ['submission', 'review']:
                for value in [None, '', ' \t\n\u3000', '0', 'false', source]:
                    data = {listing: envelope(['format-1'], 'ItemListReply')}
                    standard = path(listing, 'format-1', 'formatsIsStandardQUuid')
                    why = path(standard, 'formatsIsStandardNoAUuid', 'formatsWhyNonStandardQUuid')
                    detail = path(why, 'formatsWhyNSAnotherReasonAUuid', 'formatsWhyNSAnotherReasonQUuid')
                    data[standard] = envelope(IDS['formatsIsStandardNoAUuid'], 'AnswerReply')
                    data[why] = envelope(IDS['formatsWhyNSAnotherReasonAUuid'], 'AnswerReply')
                    body = rich if value == source else '<p>' + str(value) + '</p>'
                    transport = ''
                    if value is not None:
                        data[detail] = envelope(value)
                        transport = self.fragment(value, body).replace('dsw-md-1', 'dsw-md-4')
                    def output(values):
                        return render(repliesMap=values, ctx={'project': {'replies': values}},
                            document=SimpleNamespace(content=transport.encode(), safe_encoding='utf-8'), json=json, output_profile=profile)
                    doc = lhtml.fragment_fromstring(output(data), create_parent=True)
                    owned = doc.xpath('.//div[@data-fact-id="nonstandard-reason" and @data-status="complete"]')
                    present = isinstance(value, str) and bool(value.strip())
                    with self.subTest(value=value, escape=escape, profile=profile):
                        self.assertEqual(len(owned), int(present))
                        if present:
                            self.assertIn(body, output(data))
                            self.assertFalse(owned[0].xpath('.//pre[@class="answer-markdown-fallback"]'))
                        if value == source:
                            self.assertEqual([[c.text_content() for c in row] for row in owned[0].xpath('.//tr')], [['Field', 'Treatment'], ['time', 'UTC'], ['value', '0']])
                            self.assertEqual(len(owned[0].xpath('.//ol/li[1]/ul/li')), 1)
                            self.assertIn('keep <literal> & 100%', owned[0].text_content())
                            second = {key.replace('.format-1.', '.format-2.'): item for key, item in data.items() if key.startswith(listing + '.format-1.')}
                            second[detail.replace('.format-1.', '.format-2.')] = envelope('Second owner reason.')
                            multiple = {**data, **second, listing: envelope(['format-1', 'format-2'], 'ItemListReply')}
                            transport += self.fragment('Second owner reason.', '<p>Second owner reason.</p>').replace('dsw-md-1', 'dsw-md-7')
                            records = lhtml.fragment_fromstring(output(multiple), create_parent=True).xpath('.//div[contains(concat(" ", normalize-space(@class), " "), " format-description ") and @data-reading-record="format"]')
                            self.assertEqual([node.get('data-item-id') for node in records], ['format-1', 'format-2'])
                            self.assertEqual(len(records[0].xpath('.//table')), 1)
                            self.assertFalse(records[1].xpath('.//table'))
                            self.assertNotIn('Second owner reason.', records[0].text_content())
                            self.assertIn('Second owner reason.', records[1].text_content())
                    if present:
                        for key, choice in [(standard, IDS['formatsIsStandardYesAUuid']), (standard, False), (why, 'unknown')]:
                            inactive = {**data, key: envelope(choice, 'AnswerReply')}
                            self.assertNotIn(body, output(inactive))
                        self.assertNotIn(body, output({**data, listing: envelope([], 'ItemListReply')}))

    def test_q3_naming_details_use_owned_transport_without_changing_parent_gates(self):
        from current_support import IDS, PREFIX, environment, path
        from jinja2 import Undefined
        storage = path('processingCUuid', 'storageConvQUuid')
        fs = path(storage, 'storageConvExploreAUuid', 'storageConvFSysQUuid')
        obj = path(storage, 'storageConvExploreAUuid', 'storageConvObjStoreQUuid')
        envelope = lambda value, kind='StringReply': {'value': {'type': kind, 'value': value}}
        parents = {storage: envelope(IDS['storageConvExploreAUuid'], 'AnswerReply'),
            fs: envelope(IDS['storageConvFSysYesAUuid'], 'AnswerReply'),
            obj: envelope(IDS['storageConvObjStoreYesAUuid'], 'AnswerReply')}
        details = []
        for stem in ['scFSysSubjFolders', 'scFSysAnalysisFolders', 'scFSysWorkflowStepFolders']:
            question = path(fs, 'storageConvFSysYesAUuid', stem + 'QUuid')
            parents[question] = envelope(IDS[stem + 'YesAUuid'], 'AnswerReply')
            details.append(path(question, stem + 'YesAUuid', stem + 'ConvsQUuid'))
        details += [path(fs, 'storageConvFSysYesAUuid', 'scFSysAppointmentsQUuid'),
                    path(obj, 'storageConvObjStoreYesAUuid', 'scObjStoreNamingQUuid')]
        for escape in [False, True]:
            env = environment(ROOT, escape=escape)
            env.loader = FileSystemLoader(ROOT)  # Real guarded transport helper.
            env.filters['reply_str_value'] = lambda reply: '' if isinstance(reply, Undefined) else reply['value']['value'] if isinstance(reply, dict) else reply
            env.filters['reply_items'] = lambda reply: reply['value']['value'] if isinstance(reply, dict) and reply['value']['type'] == 'ItemListReply' else []
            render = env.from_string(PREFIX + "{% include 'src/questions/03-docs-metadata.html.j2' %}").render
            for profile in ['submission', 'review']:
                for value in [None, '', ' \t\n\u3000', '0', 'false', 'rich']:
                    data, bodies = dict(parents), {}
                    for i, key in enumerate(details, 1):
                        if value is None: continue
                        source = f'| Field | Rule |\n| --- | --- |\n| FIELD-{i} | 0 |\n\nLiteral <analysis>.' if value == 'rich' else value
                        data[key] = envelope(source)
                        bodies[source] = f'<table><tr><th>Field</th><th>Rule</th></tr><tr><td>FIELD-{i}</td><td>0</td></tr></table><p>Literal &lt;analysis&gt;.</p>' if value == 'rich' else '<p>' + html.escape(source) + '</p>'
                    transport = ''.join(self.fragment(reply['value']['value'], bodies[reply['value']['value']]).replace('dsw-md-1', 'dsw-md-' + str(i))
                        for i, reply in enumerate(data.values(), 1) if reply['value']['type'] == 'StringReply')
                    def output(values):
                        return lhtml.fragment_fromstring(render(repliesMap=values, ctx={'project': {'replies': values}},
                            document=SimpleNamespace(content=transport.encode(), safe_encoding='utf-8'), json=json,
                            output_profile=profile), create_parent=True)
                    doc = output(data)
                    owned = doc.xpath('.//div[contains(concat(" ", normalize-space(@class), " "), " answer-detail ")]')
                    with self.subTest(value=value, profile=profile, escape=escape):
                        self.assertEqual(len(owned), 5 if value and value.strip() else 0)
                        self.assertFalse(doc.xpath('.//pre[@class="answer-markdown-fallback"]'))
                        if value in ['0', 'false']:
                            self.assertTrue(all(node.xpath('./p[last()] | ./div[@data-reading-detail="file-naming" or @data-reading-detail="object-naming"]/p[last()]')[0].text_content() == value for node in owned))
                        if value == 'rich':
                            self.assertEqual([node.xpath('.//td')[0].text_content() for node in owned], [f'FIELD-{i}' for i in range(1, 6)])
                            self.assertTrue(all('Literal <analysis>.' in node.text_content() for node in owned))
                            for parent, choice, remaining in [(storage, '', []),
                                (fs, IDS['storageConvFSysNoAUuid'], ['FIELD-5']),
                                (obj, IDS['storageConvObjStoreNoAUuid'], [f'FIELD-{i}' for i in range(1, 5)])]:
                                inactive = output({**data, parent: envelope(choice, 'AnswerReply')})
                                self.assertEqual(inactive.xpath('.//table/tr/td[1]/text()'), remaining)

    def test_q15_training_uses_owned_transport_and_retains_missing_parent_states(self):
        from current_support import IDS, PREFIX, environment, path
        from jinja2 import Undefined
        parent = path('adminDetailsCUuid', 'additionalExpertiseQUuid')
        detail = path(parent, 'additionalExpertiseYesTrainAUuid', 'additionalExpertiseYesTrainTrainingQUuid')
        envelope = lambda value, kind='StringReply': {'value': {'type': kind, 'value': value}}
        source = '| Training | Evidence |\n| --- | --- |\n| Data stewardship | reviewed plan |\n| Record validation | 0 unresolved checks |\n\n1. Parent\n    - Child\n2. Next\n\nLiteral `A<B&C>D`. [Plan](https://example.org/plan?version=1&scope=training)'
        rich = '<table><thead><tr><th>Training</th><th>Evidence</th></tr></thead><tbody><tr><td>Data stewardship</td><td>reviewed plan</td></tr><tr><td>Record validation</td><td>0 unresolved checks</td></tr></tbody></table><ol><li>Parent<ul><li>Child</li></ul></li><li>Next</li></ol><p>Literal <code>A&lt;B&amp;C&gt;D</code>. <a href="https://example.org/plan?version=1&amp;scope=training">Plan</a></p>'
        for escape in [False, True]:
            env = environment(ROOT, escape=escape)
            env.loader = FileSystemLoader(ROOT)
            env.filters['reply_str_value'] = lambda reply: '' if isinstance(reply, Undefined) else reply['value']['value'] if isinstance(reply, dict) else reply
            env.filters['reply_items'] = lambda reply: reply['value']['value'] if isinstance(reply, dict) and reply['value']['type'] == 'ItemListReply' else []
            render = env.from_string(PREFIX + "{% include 'src/questions/15-required-resources.html.j2' %}").render
            for profile in ['submission', 'review']:
                for value in [None, '', ' \t\n\u3000', '0', 'false', 'Training notes.', source]:
                    data = {parent: envelope(IDS['additionalExpertiseYesTrainAUuid'], 'AnswerReply')}
                    body = rich if value == source else '<p>' + html.escape(value or '') + '</p>'
                    transport = ''
                    if value is not None:
                        data[detail] = envelope(value)
                        transport = self.fragment(value, body).replace('dsw-md-1', 'dsw-md-2')
                    def output(replies, word=False):
                        return lhtml.fragment_fromstring(render(repliesMap=replies, ctx={'project': {'replies': replies}},
                            document=SimpleNamespace(content=transport.encode(), safe_encoding='utf-8'), json=json,
                            output_profile=profile, word_budget_reading=word), create_parent=True)
                    doc = output(data)
                    nodes = doc.xpath('.//*[@data-fact-id="specialist-expertise-detail" and @data-status="complete"]')
                    present = isinstance(value, str) and bool(value.strip())
                    with self.subTest(value=value, profile=profile, escape=escape):
                        word = output(data, word=True)
                        marked = word.xpath('.//div[@class="q15-terminal-gap"]')
                        self.assertEqual(len(marked), 2 if present and profile == 'review' else 0)
                        self.assertFalse(doc.xpath('.//div[@class="q15-terminal-gap"]'))
                        self.assertEqual([lhtml.tostring(p, with_tail=False) for p in word.xpath('.//p')], [lhtml.tostring(p, with_tail=False) for p in doc.xpath('.//p')], 'Word hints must not rewrite any original paragraph')
                        self.assertEqual(len(nodes), int(present))
                        self.assertFalse(doc.xpath('.//pre[@class="answer-markdown-fallback"]'))
                        self.assertEqual(len(doc.xpath('.//*[@data-fact-id="specialist-expertise" and @data-status="partial"]')), int(not present))
                        self.assertEqual(len(doc.xpath('.//*[@data-fact-id="specialist-expertise-detail" and @data-status="missing"]')), int(not present and profile == 'review'))
                        if value == source:
                            self.assertEqual([[c.text_content() for c in row] for row in nodes[0].xpath('.//tr')], [['Training', 'Evidence'], ['Data stewardship', 'reviewed plan'], ['Record validation', '0 unresolved checks']])
                            self.assertEqual(len(nodes[0].xpath('.//ol/li[1]/ul/li')), 1)
                            self.assertEqual(nodes[0].xpath('.//code/text()'), ['A<B&C>D'])
                            self.assertEqual(nodes[0].xpath('.//a/@href'), ['https://example.org/plan?version=1&scope=training'])
                        elif present:
                            self.assertEqual(nodes[0].text_content().strip(), value)
                        for choice in [IDS['additionalExpertiseNoAUuid'], IDS['additionalExpertiseYesHireAUuid'], '', 'unknown']:
                            inactive = output({**data, parent: envelope(choice, 'AnswerReply')})
                            self.assertFalse(inactive.xpath('.//*[@data-fact-id="specialist-expertise-detail" and @data-status="complete"]'))
                            self.assertFalse(output({**data, parent: envelope(choice, 'AnswerReply')}, word=True).xpath('.//div[@class="q15-terminal-gap"]'))


    def test_stock_435_parser_preserves_eof_tables_nested_lists_and_literal_sources(self):
        self.test_stock_parser_preserves_eof_tables_nested_lists_and_literal_sources(
            'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3')

    def test_q10_authorization_keeps_only_owned_short_body_rows(self):
        """Q8 fact-owned authorization and Q10 share only independent row keeps."""
        from jinja2 import StrictUndefined
        from lxml import etree
        marker = '<!--DSW:SE:authored-authorization-row:v1-->'
        table = '<table><thead><tr><th>Action</th><th>Value</th></tr></thead><tbody><tr><td>AUTH-OTHER</td><td>0</td></tr></tbody></table>'
        def question(body, qid='q-share-restrictions', detail='authorization-details', attrs=''):
            return '<div id="'+qid+'" class="question"><div class="answer"'+attrs+'><div class="'+detail+'">'+body+'</div></div></div>'
        def q8(body, heading='<h4 data-fact-id="authorization-arrangements">Authentication and Authorization of Users</h4>',
               qid='q-copyright-ipr', detail='answer-detail', attrs='', between='', detail_attrs=''):
            return '<div id="'+qid+'" class="question"><div class="answer"'+attrs+'>'+heading+between+'<div class="'+detail+'"'+detail_attrs+'><div class="answer-lead"><p>We will make use of an existing data committee:</p></div>'+body+'</div></div></div>'
        tail = '<ol><li>Preserve the source.<ul><li>Check the original value.</li></ul></li><li>Record the decision.</li></ol><p>Keep literal &lt;A&amp;B&gt;.</p>'
        mixed = '<table><thead><tr><th>Action</th><th>Value</th></tr></thead><tbody>' + ''.join(
            '<tr><td>AUTH-LONG-R'+str(i).zfill(2)+'</td><td>'+('Check release record '+str(i).zfill(2)+'.' if i < 32 else 'Confirm release scope. ' * 4).strip()+'</td></tr>'
            for i in range(1, 33)) + '</tbody></table>'
        mixed_zh = '<table><thead><tr><th>作業</th><th>數值</th></tr></thead><tbody>' + ''.join(
            '<tr><td>AUTH-LONG-R'+str(i).zfill(2)+'</td><td>'+('核對提供紀錄'+str(i).zfill(2)+'。' if i < 32 else '核對提供範圍。' * 6)+'</td></tr>'
            for i in range(1, 33)) + '</tbody></table>'
        cases = [
            ('short', question(table + tail), 1),
            ('long', question(table.replace('AUTH-OTHER', 'Long authored value. ' * 20) + tail), 0),
            ('complex', question(table.replace('AUTH-OTHER', '<code>AUTH-OTHER</code>') + tail), 0),
            ('other-question', question(table + tail, qid='q-access-data'), 0),
            ('other-detail', question(table + tail, detail='answer-detail'), 0),
            ('attributed-answer', question(table + tail, attrs=' data-extra="unowned"'), 0),
            ('nested-table', question('<div>' + table + '</div>' + tail), 0),
            ('q8-short', q8(table + tail), 1),
            ('q8-other-authorization', q8(table + tail).replace('We will make use of an existing data committee:', 'We will use the following authorization arrangements:'), 1),
            ('q8-mixed-32-body-rows', q8(mixed + tail), 31),
            ('q8-mixed-32-body-rows-zh', q8(mixed_zh + tail), 31),
            ('q8-long', q8(table.replace('AUTH-OTHER', 'Long authored value. ' * 20) + tail), 0),
            ('q8-ascii40', q8(table.replace('AUTH-OTHER', 'X' * 40)), 1),
            ('q8-ascii41', q8(table.replace('AUTH-OTHER', 'X' * 41)), 0),
            ('q8-weighted80', q8(table.replace('AUTH-OTHER', '中' * 40)), 1),
            ('q8-weighted82', q8(table.replace('AUTH-OTHER', '中' * 41)), 0),
            ('q8-complex', q8(table.replace('AUTH-OTHER', '<code>AUTH-OTHER</code>') + tail), 0),
            ('q8-no-heading', q8(table + tail, heading=''), 0),
            ('q8-wrong-fact', q8(table + tail, heading='<h4 data-fact-id="custom-reason">Reason</h4>'), 0),
            ('q8-wrong-heading-level', q8(table + tail, heading='<h3 data-fact-id="authorization-arrangements">Authorization</h3>'), 0),
            ('q8-attributed-heading', q8(table + tail, heading='<h4 data-fact-id="authorization-arrangements" data-extra="unowned">Authorization</h4>'), 0),
            ('q8-classed-heading', q8(table + tail, heading='<h4 data-fact-id="authorization-arrangements" class="unowned">Authorization</h4>'), 0),
            ('q8-duplicate-heading', q8(table + tail, heading='<h4 data-fact-id="authorization-arrangements">Authorization</h4>' * 2), 0),
            ('q8-intervening-block', q8(table + tail, between='<p>Another owned fact.</p>'), 0),
            ('q8-wrong-question', q8(table + tail, qid='q-access-security'), 0),
            ('q8-wrong-detail', q8(table + tail, detail='authorization-details'), 0),
            ('q8-attributed-answer', q8(table + tail, attrs=' data-extra="unowned"'), 0),
            ('q8-attributed-detail', q8(table + tail, detail_attrs=' data-extra="unowned"'), 0),
            ('q8-nested-table', q8('<div>' + table + '</div>' + tail), 0),
            ('q8-list-table', q8('<ul><li>' + table + '</li></ul>' + tail), 0),
        ]
        runner = '''import json,subprocess,sys,tempfile,zipfile
from pathlib import Path
p=json.load(sys.stdin); result=[]
with tempfile.TemporaryDirectory() as temp:
 filters=[]
 for index,source in enumerate(p['lua']):
  f=Path(temp)/('filter-'+str(index)+'.lua');f.write_text(source);filters.append('--lua-filter='+str(f))
 for name,body,expected in p['cases']:
  out=Path(temp)/'sample.docx'
  subprocess.run(['pandoc','--from=html','--to=docx',*filters,'-o',str(out)],input=body.encode(),check=True)
  with zipfile.ZipFile(out) as archive: result.append(archive.read('word/document.xml').decode())
print(json.dumps(result))
'''
        raw = subprocess.check_output([
            'docker', 'run', '--rm', '--network', 'none', '--log-driver', 'none',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--user', '1000:1000', '--read-only', '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m',
            '--memory', '512m', '--cpus', '1', '--pids-limit', '64', '-i', '--entrypoint', 'python',
            'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3', '-c', runner],
            input=json.dumps({'lua': [(ROOT / 'src/word' / name).read_text() for name in ['pilot.lua', 'preservation-reading.lua', 'short-tables.lua']], 'cases': cases}).encode(), timeout=120)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        for (name, _, expected), before in zip(cases, json.loads(raw)):
            with self.subTest(case=name):
                self.assertEqual(before.count(marker), expected)
                for escape in [False, True]:
                    template = Environment(loader=FileSystemLoader(ROOT), undefined=StrictUndefined, autoescape=escape).get_template('src/word/short-tables.xml')
                    after = template.render(content=before)
                    self.assertNotIn(marker, after)
                    old = etree.fromstring(before.replace(marker, '').encode(), etree.XMLParser(remove_blank_text=True))
                    new = etree.fromstring(after.encode(), etree.XMLParser(remove_blank_text=True))
                    kept = new.xpath('//w:tr/w:trPr/w:cantSplit', namespaces=ns)
                    self.assertEqual(len(kept), expected)
                    self.assertFalse(new.xpath('//w:tr[w:trPr/w:tblHeader]/w:trPr/w:cantSplit', namespaces=ns))
                    self.assertFalse(new.xpath('//w:pPr/w:keepNext', namespaces=ns))
                    if name.startswith('q8-mixed-32-body-rows'):
                        self.assertEqual([bool(row.xpath('./w:trPr/w:cantSplit', namespaces=ns))
                                          for row in new.xpath('//w:tbl/w:tr', namespaces=ns)],
                                         [False] + [True] * 31 + [False], 'Each short row is independent; header and long R32 stay splittable')
                    for keep in kept:
                        row_properties = keep.getparent(); row_properties.remove(keep)
                        if not len(row_properties): row_properties.getparent().remove(row_properties)
                    self.assertEqual(etree.tostring(new), etree.tostring(old), 'Only the bounded body-row keep may change')

    def test_stock_parser_preserves_eof_tables_nested_lists_and_literal_sources(self, image=None):
        from native_support import IMAGE
        sources = [
            '| Record | Validation |\n| --- | --- |\n| A | First |\n| B | Last |',
            '1. Parent\n   - Child\n2. Next',
            '1. Parent\n    - Child\n2. Next',
            '```text\n   - FENCE literal\n<span>literal & text</span>\n```',
            '', '   ', '\t', '中英 & <literal>',
            '</pre><script>RAW-TOKEN</script>\n\nVISIBLE-AFTER-RAW',
            '[unsafe](javascript:alert%281%29) [local](file:///etc/passwd) ![label](https://example.org/trap.png)',
        ]
        runner = '''import html,json,subprocess,sys,tempfile
from pathlib import Path
p=json.load(sys.stdin)
with tempfile.TemporaryDirectory() as temp:
 f=Path(temp)/'answer.lua';f.write_text(p['lua'])
 transport=''.join('<pre id="dsw-md-'+str(i+1)+'" class="dsw-answer-markdown"><code>'+html.escape(json.dumps(s,ensure_ascii=False))+'</code></pre>' for i,s in enumerate(p['sources']))
 print(subprocess.check_output(['pandoc','--from=html','--to=html','--wrap=none','--lua-filter='+str(f)],input=transport.encode()).decode())
'''
        output = subprocess.check_output([
            'docker', 'run', '--rm', '--network', 'none', '--log-driver', 'none',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--user', '1000:1000', '--read-only', '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m',
            '--memory', '512m', '--cpus', '1', '--pids-limit', '64', '-i',
            '--entrypoint', 'python', image or IMAGE, '-c', runner],
            input=json.dumps({'lua': (ROOT / 'src/answer-markdown.lua').read_text(),
                              'sources': sources}).encode(), timeout=120)
        doc = lhtml.fragment_fromstring(output.decode(), create_parent=True)
        fragments = list(doc)
        self.assertEqual(len(fragments), len(sources))
        self.assertEqual([json.loads(node.get('data-source-json')) for node in fragments], sources)
        self.assertEqual([[cell.text_content() for cell in row.xpath('./th|./td')]
                          for row in fragments[0].xpath('.//tr')],
                         [['Record', 'Validation'], ['A', 'First'], ['B', 'Last']])
        for node in fragments[1:3]:
            self.assertEqual(len(node.xpath('./ol/li')), 2)
            self.assertEqual(len(node.xpath('./ol/li[1]/ul/li')), 1)
            self.assertFalse(node.xpath('./ol/li[2]/ul'))
        self.assertIn('   - FENCE literal\n<span>literal & text</span>', fragments[3].text_content())
        self.assertEqual(len(fragments[3].xpath('./pre/code')), 1)
        self.assertFalse(doc.xpath('.//script|.//style|.//img'))
        self.assertFalse(doc.xpath('.//a[starts-with(@href,"javascript:") or starts-with(@href,"file:")]'))
        self.assertIn('javascript:alert%281%29', fragments[-1].text_content())
        self.assertIn('file:///etc/passwd', fragments[-1].text_content())
        # Parser changes must not silently disable the existing bounded table keep.
        from current_support import environment
        # Preserve the actual Pandoc bytes: lxml may switch attribute quote style.
        transport = output.decode().split('<div id="dsw-md-2"', 1)[0]
        env = environment(ROOT)
        env.loader = FileSystemLoader(ROOT)  # Real parser helper, never the body-test shim.
        helper = env.get_template('src/macros.html.j2').make_module({
            'ctx': {'project': {'replies': replies([sources[0]])}}, 'json': json,
            'document': SimpleNamespace(content=transport.encode(), safe_encoding='utf-8')})
        self.assertIn('class="short-table-unit"', str(helper.provenanceReading(sources[0])))


if __name__ == '__main__': unittest.main()
