"""Independent 0.3.32 Q3 DOM projection; retain every other answer and state."""
import copy
import itertools
from bs4 import BeautifulSoup
from generate_metadata_fixtures import PARENT, DICTIONARY, ACCESS, REASON, INSTRUCTIONS, FORM, IDS, path
from probe_pdf_budget_reading import dom

QUESTION = 'src/questions/03-docs-metadata.html.j2'
WORDS = {
    'english': {
        'yes': 'We will create a data/variable dictionary.',
        'no': 'We will not create a data/variable dictionary.',
        'dictionary-missing': 'Information not provided: whether a data/variable dictionary will be created.',
        'dictionary-review': 'The selected data-dictionary option cannot be represented by this template; please review it.',
        'reason': 'Information not provided: why the metadata will not be openly available.',
        'instructions-missing': 'Information not provided: whether the metadata will include instructions for accessing the data.',
        'instructions-review': 'The selected metadata access-instructions option cannot be represented by this template; please review it.',
        'form-missing': 'Information not provided: whether the metadata will be available in a form that can be harvested and indexed.',
        'form-review': 'The selected metadata harvesting and indexing option cannot be represented by this template; please review it.',
    },
    'chinese': {
        'yes': '本計畫將建立資料字典或變項定義表。',
        'no': '本計畫不會建立資料字典或變項定義表。',
        'dictionary-missing': '尚待補充：是否將建立資料字典或變項定義表。',
        'dictionary-review': '本模板無法呈現所選的資料字典選項，請核對。',
        'reason': '尚待補充：後設資料不公開提供的原因。',
        'instructions-missing': '尚待補充：後設資料是否會包含取用資料的說明。',
        'instructions-review': '本模板無法呈現所選的後設資料取用說明選項，請核對。',
        'form-missing': '尚待補充：後設資料是否可供自動擷取並建立索引。',
        'form-review': '本模板無法呈現所選的後設資料擷取與索引選項，請核對。',
    },
}


def paragraph(fact, status, text):
    node = BeautifulSoup('<p></p>', 'html.parser').p
    node['data-fact-id'] = fact; node['data-status'] = status; node.string = text
    if status in ['missing', 'needs-review']: node['class'] = ['data-gap']
    return node


def group(nodes):
    div = BeautifulSoup('<div class="reading-gap"></div>', 'html.parser').div
    for node in nodes: div.append(node)
    return div


def gap(fact, value, words, prefix):
    review = bool(value.strip())
    return paragraph(fact, 'needs-review' if review else 'missing', words[prefix+('-review' if review else '-missing')])


def expected(before, data, language):
    result = copy.deepcopy(before); words = WORDS[language]
    metadata_active = data.get(PARENT) == IDS['metadataExploreAUuid']
    access = data.get(ACCESS, '')
    if not metadata_active and access not in [IDS['metadataOpenYesAUuid'], IDS['metadataOpenNoAUuid']]: return result
    policy = result.select_one('#q-docs-metadata .metadata-policy')
    if policy is None:
        # The old template hid even supplied dictionary answers behind a whole-Q3 fallback.
        answer = result.select_one('#q-docs-metadata .answer'); assert answer is not None
        children = answer.find_all(recursive=False)
        assert len(children) == 1 and children[0].get('data-status') == 'missing-output'
        answer.clear(); policy = BeautifulSoup('<div class="dataset-policy metadata-policy"></div>', 'html.parser').div
        answer.append(policy)
    if metadata_active:
        value = data.get(DICTIONARY, '')
        if value in [IDS['metadataDictionaryYesAUuid'], IDS['metadataDictionaryNoAUuid']]:
            yes = value == IDS['metadataDictionaryYesAUuid']
            node = paragraph('metadata-dictionary', 'complete' if yes else 'explicit-no', words['yes' if yes else 'no'])
        else: node = group([gap('metadata-dictionary', value, words, 'dictionary')])
        if access in [IDS['metadataOpenYesAUuid'], IDS['metadataOpenNoAUuid']]:
            public = policy.find_all('p', recursive=False)[-1]; public.insert_before(node)
        else: policy.append(node)
    if access == IDS['metadataOpenNoAUuid'] and not data.get(REASON, '').strip():
        detail = policy.select_one('[data-fact-id="metadata-access-explanation"]')
        if detail is not None:
            assert not detail.get_text().strip() and not detail.find(True)
            detail.decompose()
        policy.append(group([paragraph('metadata-access-explanation', 'missing', words['reason'])]))
    if access == IDS['metadataOpenYesAUuid']:
        additions = []
        for field, allowed, fact, prefix in [
            (INSTRUCTIONS, ['metadataOpenInstrYesAUuid', 'metadataOpenInstrNoAUuid'], 'metadata-access-instructions', 'instructions'),
            (FORM, ['metadataOpenFormNoAUuid', 'metadataOpenFormYesRepoAUuid', 'metadataOpenFormYesCareAUuid'], 'metadata-harvestable', 'form')]:
            value = data.get(field, '')
            if value not in [IDS[n] for n in allowed]: additions.append(gap(fact, value, words, prefix))
        if additions: policy.append(group(additions))
    return result


def compare(before, after, data, language):
    assert dom(expected(before, data, language)) == dom(after), 'Unexpected metadata, authored-answer, capacity or punctuation delta'


def scenarios():
    authored = '<p>Keep <strong>Original.csv</strong>.</p><p>Second paragraph.</p><ul><li><a href="https://example.org/metadata?a=1&amp;b=2">CHANGELOG.md</a></li></ul>'
    dictionaries = ['', ' \t ', IDS['metadataDictionaryYesAUuid'], IDS['metadataDictionaryNoAUuid'], 'unknown']
    for parent, dictionary, access, reason in itertools.product(
        ['', IDS['metadataExploreAUuid'], 'unknown'], dictionaries,
        ['', IDS['metadataOpenYesAUuid'], IDS['metadataOpenNoAUuid'], 'unknown'], ['', ' \t\n ', '0', authored]):
        yield {PARENT: parent, DICTIONARY: dictionary, ACCESS: access, REASON: reason,
               INSTRUCTIONS: IDS['metadataOpenInstrNoAUuid'], FORM: IDS['metadataOpenFormNoAUuid']}
    for dictionary, instr, form in itertools.product(dictionaries,
        ['', ' \t ', IDS['metadataOpenInstrYesAUuid'], IDS['metadataOpenInstrNoAUuid'], 'unknown'],
        ['', ' \t ', IDS['metadataOpenFormNoAUuid'], IDS['metadataOpenFormYesRepoAUuid'], IDS['metadataOpenFormYesCareAUuid'], 'unknown']):
        yield {PARENT: IDS['metadataExploreAUuid'], DICTIONARY: dictionary, ACCESS: IDS['metadataOpenYesAUuid'], INSTRUCTIONS: instr, FORM: form, REASON: authored}
    for mask, dictionary in itertools.product(range(8), dictionaries):
        standards = path(PARENT, 'metadataExploreAUuid', 'metadataStandardsQUuid')
        data = {PARENT: IDS['metadataExploreAUuid'], DICTIONARY: dictionary, standards: IDS['metadataStandardsExploreAUuid']}
        for i, name in enumerate(['DC', 'DataCite', 'DDI']):
            if mask & (1 << i): data[path(standards, 'metadataStandardsExploreAUuid', 'metadataStandards'+name+'QUuid')] = IDS['metadataStandards'+name+'YesAUuid']
        yield data
    from storage_gap_contract import scenarios as capacity_scenarios
    yield from capacity_scenarios()


def check_roots(root, frozen, language):
    from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
    import test_science_europe_contract as adapter
    wrapper = "{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '"+QUESTION+"' %}"
    count = 0
    for escape in [False, True]:
        env = Environment(loader=FileSystemLoader(root), extensions=['jinja2.ext.do'], autoescape=escape)
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v, any=any)
        env.tests['true'] = lambda value: value is True
        prior = env.overlay(loader=ChoiceLoader([DictLoader({QUESTION: frozen.read_text()}), env.loader]))
        old, new = prior.from_string(wrapper), env.from_string(wrapper)
        for data in scenarios():
            before, after = [BeautifulSoup(t.render(repliesMap=data), 'html.parser') for t in [old, new]]
            compare(before, after, data, language)
            assert not after.select('p p, p div, p ul, script')
            count += 1
    return count
