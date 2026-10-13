"""Owned paragraphs and bounded table hints must not alter authored blocks."""
import itertools
import unittest
from bs4 import BeautifulSoup
from test_answer_retention import IDS, path
from test_science_europe_contract import render_question
from test_quality_reading import MEASURED, DATASETS, DATASET
from test_structure_bindings import BlockProbe

Q2 = 'src/questions/02-what-data.html.j2'
Q3 = 'src/questions/03-docs-metadata.html.j2'
AUTHORED = '<p>Keep v1.2; do not rewrite!</p><p>Second paragraph。</p><ul><li>Check A.</li><li>Check B</li></ul>'


def collection(who=None, equipment=None):
    values = {MEASURED: IDS['measuredYesAUuid'], DATASETS: ['test-dataset'],
              path(DATASET, 'measuredDataNameQUuid'): 'Coastal observations'}
    if who: values[path(DATASET, 'measuredDataWhoQUuid')] = IDS[who]
    if equipment: values[path(DATASET, 'measuredDataEquipQUuid')] = IDS[equipment]
    return values


class ReadingUnitTests(unittest.TestCase):
    def test_policy_table_lead_selector_is_owned_and_narrow(self):
        import json
        import subprocess
        from test_science_europe_contract import ROOT
        selector = 'html body #q-access-security > .answer > ul > li > strong:first-child:has(+ table)'
        self.assertIn(selector + ' { display: block; break-after: avoid; }', (ROOT/'src/layout.css').read_text())
        table = '<table><tr><td>Original cell.</td></tr></table>'
        def question(body, qid='q-access-security'):
            return '<div id="'+qid+'"><div class="answer"><ul><li>'+body+'</li></ul></div></div>'
        cases = [
            (question('<strong id="en">Record policy</strong>'+table), ['en']),
            (question('<strong id="zh">資料管理政策</strong>'+table), ['zh']),
            (question('<strong id="paragraph">Record policy</strong><p>Original prose.</p>'+table), []),
            (question('<strong id="link">Record policy</strong><span>–</span>https://example.org/'+table), []),
            (question('<strong id="nested">Record policy</strong><div>'+table+'</div>'), []),
            (question('<p>Original <strong id="emphasis">emphasis</strong>.</p>'+table), []),
            (question('<ul><li><strong id="authored">Authored label</strong>'+table+'</li></ul>'), []),
            (question('<strong id="other">Record policy</strong>'+table, 'q-other'), []),
            (question(table), []),
        ]
        runner = 'import json,sys,xml.etree.ElementTree as ET\nfrom cssselect2 import ElementWrapper,compile_selector_list\np=json.load(sys.stdin);s=compile_selector_list(p["selector"])\nprint(json.dumps([[n.etree_element.get("id") for n in ElementWrapper.from_html_root(ET.fromstring("<html><body>"+h+"</body></html>")).iter_subtree() if any(c.test(n) for c in s)] for h in p["html"]]))'
        image = 'datastewardshipwizard/document-worker@sha256:726b2906b3eee3fa7301ffdd723901397518c61e112f054ff53fabe07538fad3'
        raw = subprocess.check_output(['docker','run','--rm','--pull=never','--network','none','--log-driver','none','-i','--entrypoint','python',image,'-c',runner],
            input=json.dumps(dict(selector=selector,html=[html for html,_ in cases])).encode(),timeout=60)
        self.assertEqual([expected for _,expected in cases], json.loads(raw))

    def assert_valid(self, output):
        probe = BlockProbe(); probe.feed(output)
        self.assertEqual([], probe.errors); self.assertEqual([], probe.stack)

    def test_collector_equipment_matrix_keeps_known_sibling(self):
        collectors = [None, 'measuredDataWhoExpertsOwnAUuid', 'measuredDataWhoExpertsOutAUuid', 'measuredDataWhoExternalAUuid']
        equipment = [None, 'measuredDataEquipDescribedAUuid', 'measuredDataEquipCareAUuid']
        for who, equip in itertools.product(collectors, equipment):
            html = render_question(Q2, collection(who, equip)); self.assert_valid(html)
            soup = BeautifulSoup(html, 'html.parser')
            summary = soup.select_one('.collection-summary')
            self.assertIn('Coastal observations', summary.get_text())
            self.assertFalse(summary.select('p, ul, li, br'))
            self.assertEqual(not who, bool(soup.select('[data-fact-id="data-collector"]')))
            self.assertEqual(not equip, bool(soup.select('[data-fact-id="equipment-documentation"]')))
            if who: self.assertIn('will be collected', summary.get_text())
            if equip: self.assertIn('equipment', summary.get_text())
            if not who and not equip: self.assertIn('has not yet been described.', summary.get_text())

    def test_external_ownership_free_answer_and_missing_are_distinct(self):
        values = collection('measuredDataWhoExternalAUuid', 'measuredDataEquipCareAUuid')
        owner = path(DATASET, 'measuredDataWhoQUuid', 'measuredDataWhoExternalAUuid', 'mdExternalOwnershipQUuid')
        for answer, phrase in [('mdExternalOwnershipPartyAUuid', 'remain with the external party'), ('mdExternalOwnershipPartnersAUuid', 'full ownership')]:
            values[owner] = IDS[answer]
            self.assertIn(phrase, render_question(Q2, values))
        values[owner] = IDS['mdExternalOwnershipOtherAUuid']
        self.assertIn('data-fact-id="external-ownership" data-status="missing"', render_question(Q2, values))
        values[path(owner, 'mdExternalOwnershipOtherAUuid', 'mdExternalOwnershipOtherQUuid')] = AUTHORED
        html = render_question(Q2, values); self.assert_valid(html)
        detail = BeautifulSoup(html, 'html.parser').select_one('[data-fact-id="external-ownership"]')
        detail.select_one('.answer-lead').decompose()
        self.assertEqual(AUTHORED, detail.decode_contents().strip())

    def test_custom_non_equipment_dataset_does_not_emit_an_empty_type_paragraph(self):
        parent = path('creatingCUuid', 'neqDataQUuid')
        items = path(parent, 'neqDataYesAUuid', 'neqDataSetsQUuid')
        values = {
            parent: IDS['neqDataYesAUuid'],
            items: ['custom'],
            path(items, 'custom', 'neqDataSetsNameQUuid'): 'Custom registry extract',
        }
        soup = BeautifulSoup(render_question(Q2, values), 'html.parser')
        self.assertIn('Custom registry extract', soup.get_text())
        self.assertFalse([node for node in soup.find_all('p') if not node.get_text(strip=True)])

    def test_metadata_explanation_is_not_escaped_or_nested_in_paragraph(self):
        meta = path('accessCUuid', 'metadataOpenQUuid')
        values = {meta: IDS['metadataOpenNoAUuid'], path(meta, 'metadataOpenNoAUuid', 'metadataOpenNoExplainQUuid'): AUTHORED}
        html = render_question(Q3, values); self.assert_valid(html)
        soup = BeautifulSoup(html, 'html.parser')
        self.assertIn('Metadata will not be available openly.', soup.get_text())
        self.assertEqual(AUTHORED, soup.select_one('[data-fact-id="metadata-access-explanation"]').decode_contents())

    def test_file_and_object_conventions_preserve_paragraphs(self):
        storage = path('processingCUuid', 'storageConvQUuid')
        prefix = path(storage, 'storageConvExploreAUuid')
        files = path(prefix, 'storageConvFSysQUuid')
        objects = path(prefix, 'storageConvObjStoreQUuid')
        values = {storage: IDS['storageConvExploreAUuid'], files: IDS['storageConvFSysYesAUuid'], objects: IDS['storageConvObjStoreYesAUuid'],
                  path(files, 'storageConvFSysYesAUuid', 'scFSysAppointmentsQUuid'): AUTHORED,
                  path(objects, 'storageConvObjStoreYesAUuid', 'scObjStoreNamingQUuid'): AUTHORED}
        html = render_question(Q3, values); self.assert_valid(html)
        soup = BeautifulSoup(html, 'html.parser')
        for name in ('file-naming', 'object-naming'):
            detail = soup.select_one(f'[data-fact-id="{name}"]'); detail.select_one('.answer-lead').decompose()
            self.assertEqual(AUTHORED, detail.decode_contents())

    def test_provenance_table_hint_is_conservative_and_lossless(self):
        from current_support import environment
        from test_science_europe_contract import ROOT
        env = environment(ROOT)
        env.filters['markdown'] = lambda v: v
        render = env.from_string("{% import 'src/macros.html.j2' as m %}{{ m.provenanceReading(value) }}").render
        def table(rows=2, cols=2, cell='Value'):
            return '<p>Authored lead.</p><table><thead><tr>' + '<th>Header</th>' * cols + '</tr></thead><tbody>' + ('<tr>' + f'<td>{cell}</td>' * cols + '</tr>') * rows + '</tbody></table>'
        small = table()
        for value, expected in [(small, True), (table(rows=4), False), (table(cols=5), False), (table(cell='字' * 81), False), (small * 2, False), (small + '<img src="x">', False), (small.replace('<td>', '<td style="text-align:left">'), False), (AUTHORED, False)]:
            output = render(value=value)
            soup = BeautifulSoup(output, 'html.parser'); hint = soup.select_one('.short-table-unit')
            self.assertEqual(expected, hint is not None)
            self.assertEqual(value, hint.decode_contents() if hint else output.strip())
