"""Exact 0.3.36 -> 0.3.37 projection; retain two independent missing facts."""
import copy
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
from probe_pdf_budget_reading import dom

QUESTION = 'src/questions/03-docs-metadata.html.j2'
FACTS = ('metadata-access-instructions', 'metadata-harvestable')
OLD = {
    'english': ('Information not provided: whether the metadata will include instructions for accessing the data.',
                'Information not provided: whether the metadata will be available in a form that can be harvested and indexed.'),
    'chinese': ('尚待補充：後設資料是否會包含取用資料的說明。', '尚待補充：後設資料是否可供自動擷取並建立索引。'),
}
WORDS = {
    'english': ('Information not provided: ', 'whether the metadata will include instructions for accessing the data',
                '; ', 'whether the metadata will be available in a form that can be harvested and indexed', '.'),
    'chinese': ('尚待補充：', '後設資料是否會包含取用資料的說明', '；', '後設資料是否可供自動擷取並建立索引', '。'),
}
PARENT = '#q-docs-metadata > .answer > .metadata-policy > .reading-gap'


def joined(language):
    lead, first, separator, last, end = WORDS[language]
    return BeautifulSoup('<p class="data-gap metadata-publication-gap">' + lead
        + '<span data-fact-id="' + FACTS[0] + '" data-status="missing">' + first + '</span>' + separator
        + '<span data-fact-id="' + FACTS[1] + '" data-status="missing">' + last + '</span>' + end + '</p>', 'html.parser').p


def old_nodes(language):
    return [BeautifulSoup('<p class="data-gap" data-fact-id="' + fact + '" data-status="missing">' + text + '</p>', 'html.parser').p
            for fact, text in zip(FACTS, OLD[language])]


def project(before, language):
    result = copy.deepcopy(before)
    for group in result.select(PARENT):
        children = group.find_all(recursive=False)
        if [node.get('data-fact-id') for node in children] != list(FACTS):
            continue
        if any(node.get('data-status') != 'missing' for node in children):
            continue
        assert [dom(node) for node in children] == [dom(node) for node in old_nodes(language)], 'Unexpected source gap content'
        group.clear()
        group.append(joined(language))
    return result


def restore(after, language):
    result = copy.deepcopy(after)
    for node in result.select(PARENT + ' > .metadata-publication-gap'):
        assert dom(node) == dom(joined(language)), 'Unexpected joined text, punctuation or fact state'
        assert node.parent.find_all(recursive=False) == [node]
        first, last = old_nodes(language)
        node.insert_before(first)
        node.replace_with(last)
    return result


def compare(before, after, language):
    assert dom(project(before, language)) == dom(after), 'Unexpected Q3 fact, authored content, punctuation or structure change'


def templates(root, frozen, escape=False):
    import test_science_europe_contract as adapter
    env = Environment(loader=FileSystemLoader(root), extensions=['jinja2.ext.do'], autoescape=escape)
    env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v, any=any)
    env.tests['true'] = lambda value: value is True
    prior = env.overlay(loader=ChoiceLoader([DictLoader({QUESTION: frozen.read_text()}), env.loader]))
    wrapper = "{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '" + QUESTION + "' %}"
    return [e.from_string(wrapper) for e in (prior, env)]


def check_roots(root, frozen, language):
    from metadata_followup_contract import scenarios
    counts = dict(comparisons=0, joined=0)
    for escape in (False, True):
        old, new = templates(root, frozen, escape)
        for data in scenarios():
            before, after = [BeautifulSoup(t.render(repliesMap=data), 'html.parser') for t in (old, new)]
            compare(before, after, language)
            assert dom(restore(after, language)) == dom(before)
            assert not after.select('p p, p div, p ul, script')
            counts['comparisons'] += 1
            counts['joined'] += len(after.select('.metadata-publication-gap'))
    return counts
