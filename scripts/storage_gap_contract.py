"""Independent whole-Q3 projection of frozen 0.3.31, not a second template."""
import copy
import itertools
from bs4 import BeautifulSoup
from generate_storage_gap_fixtures import PARENT, SPACE, AMOUNT, METADATA, IDS, path
from probe_pdf_budget_reading import dom

QUESTION = 'src/questions/03-docs-metadata.html.j2'
WORDS = {
    'english': {
        'old': ('We estimate the storage space that the project will require for all data and software (including temporary storage) to ', ' gigabytes.'),
        'new': ('We estimate the storage space that the project will require for all data and software (including temporary storage) to be ', ' gigabytes.'),
        'missing': 'Information not provided: the estimated storage space for all project data and software, including temporary storage (GB).',
    },
    'chinese': {
        'old': ('我們估計本專案所有資料與軟體（包含暫存空間）所需的儲存空間為 ', ' GB。'),
        'new': ('預估計畫所有資料與軟體（含暫存空間）所需的儲存容量為 ', ' GB。'),
        'missing': '尚待補充：計畫所有資料與軟體（含暫存空間）所需的預估儲存容量（GB）。',
    },
}


def active(data):
    return data.get(PARENT) == IDS['storageConvExploreAUuid'] and data.get(SPACE) == IDS['storageSpaceSpecifyAUuid']


def expected(before, data, language, sentinel=None):
    """Only replace/insert the first template-owned capacity block.

    Adapter tests render the old quantity with a sentinel so imported HTML cannot
    corrupt the baseline DOM; native comparisons use the actual old quantity.
    All other nodes, attributes, authored answers and punctuation stay exact.
    """
    result = copy.deepcopy(before)
    if not active(data): return result
    policy = result.select_one('.storage-conventions-policy'); assert policy is not None
    value = data.get(AMOUNT, '')
    words = WORDS[language]
    if value:
        old = policy.find('p', recursive=False); assert old is not None
        assert old.get_text() == words['old'][0]+(sentinel if sentinel is not None else value)+words['old'][1], repr(old.get_text())
        assert not old.attrs
        old.decompose()
    if value.strip():
        node = BeautifulSoup('<p></p>', 'html.parser').p
        node.string = words['new'][0]+value+words['new'][1]
    else:
        node = BeautifulSoup('<div class="reading-gap"><p class="data-gap" data-fact-id="storage-capacity" data-status="missing"></p></div>', 'html.parser').div
        node.p.string = words['missing']
    policy.insert(0, node)
    return result


def compare(before, after, data, language, sentinel=None):
    assert dom(expected(before, data, language, sentinel)) == dom(after), 'Unexpected Q3 answer, state, structure or punctuation delta'


def scenarios():
    values = [None, '', ' \t\n ', '0', '2048', '0.0001', ' 12 ', '-2', '1e3', 'unknown', '<b>7</b>', '</p><script>bad</script>']
    for parent, space, value, metadata in itertools.product(
        ['', 'unknown', IDS['storageConvExploreAUuid']],
        ['', 'unknown', IDS['storageSpaceLittleAUuid'], IDS['storageSpaceSpecifyAUuid']],
        values, ['', IDS['metadataOpenNoAUuid'], IDS['metadataOpenYesAUuid']]):
        data = {PARENT: parent, SPACE: space, METADATA: metadata}
        if value is not None: data[AMOUNT] = value
        # Authored blocks and explicit No technology are independent of capacity.
        fs = path(PARENT, 'storageConvExploreAUuid', 'storageConvFSysQUuid')
        data[fs] = IDS['storageConvFSysYesAUuid']
        data[path(fs, 'storageConvFSysYesAUuid', 'scFSysAppointmentsQUuid')] = '<p>Keep <strong>Original.csv</strong>.</p><p>Second.</p><ul><li>CHANGELOG.md.</li></ul>'
        data[path(PARENT, 'storageConvExploreAUuid', 'storageConvObjStoreQUuid')] = IDS['storageConvObjStoreNoAUuid']
        yield data
    yield {}


def check_roots(root, frozen, language):
    from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
    import test_science_europe_contract as adapter
    wrapper = "{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '"+QUESTION+"' %}"
    count = 0
    for escape in [False, True]:
        env = Environment(loader=FileSystemLoader(root), extensions=['jinja2.ext.do'], autoescape=escape)
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v, any=any)
        env.tests['true'] = lambda v: v is True
        old = env.overlay(loader=ChoiceLoader([DictLoader({QUESTION: frozen.read_text()}), env.loader]))
        old_template, new_template = old.from_string(wrapper), env.from_string(wrapper)
        for data in scenarios():
            prior = dict(data); sentinel = 'CAPACITY_ORACLE_VALUE'
            if active(data) and data.get(AMOUNT): prior[AMOUNT] = sentinel
            before = BeautifulSoup(old_template.render(repliesMap=prior), 'html.parser')
            after = BeautifulSoup(new_template.render(repliesMap=data), 'html.parser')
            compare(before, after, data, language, sentinel)
            gaps = after.select('[data-fact-id="storage-capacity"][data-status="missing"]')
            assert len(gaps) == int(active(data) and not data.get(AMOUNT, '').strip())
            assert not after.select('p p, p div, p ul, script')
            count += 1
    return count
