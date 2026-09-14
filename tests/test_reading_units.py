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
        from jinja2 import Environment, FileSystemLoader
        from test_science_europe_contract import ROOT
        env = Environment(loader=FileSystemLoader(ROOT), extensions=['jinja2.ext.do'])
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
