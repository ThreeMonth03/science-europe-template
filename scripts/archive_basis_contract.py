"""Exact Q11 fixed-choice-list transformation; no authored prose is rewritten."""
import copy
from bs4 import BeautifulSoup
from probe_pdf_budget_reading import dom

FACTS = ['archive-extension-actual-use', 'archive-extension-predicted-use', 'archive-extension-budget']
LABELS = {
    'english': ['actual use of the archived data', 'predicted use of the archived data', 'available budget'],
    'chinese': ['典藏資料的實際使用情況', '典藏資料的預期使用情況', '可用預算'],
}
LEAD = {'english': 'The extension decision will take the following into account:',
        'chinese': '是否延長保存期限，將考量以下因素：'}
PREFIX = {'english': 'Basis for extending the archival period: ', 'chinese': '延長保存期限的考量因素：'}
SEPARATOR = {'english': ', ', 'chinese': '、'}
STOP = {'english': '.', 'chinese': '。'}
REVIEW = {'english': 'Some selected reasons for extending the archival period cannot be interpreted by this template. Please review the answer.',
          'chinese': '部分已選取的延長保存期限考量因素無法由本模板辨識，請核對填答內容。'}


def expected(before, language, *, unknown=False):
    result = copy.deepcopy(before)
    leads = [n for n in result.select('.post-project-archive > .dataset-policy > .answer-lead')
             if n.get_text(strip=True) == LEAD[language]]
    assert len(leads) <= 1
    changes = 0
    for lead in leads:
        items = lead.find_next_sibling()
        assert items.name == 'ul' and not items.attrs
        assert all(n.name == 'li' for n in items.find_all(recursive=False))
        spans = []
        for node in items.find_all('li', recursive=False):
            index = FACTS.index(node['data-fact-id'])
            assert node.attrs == {'data-fact-id': FACTS[index], 'data-status': 'complete'}
            old = LABELS[language][index]
            if language == 'english': old = old[0].upper() + old[1:]
            assert node.get_text() == old + STOP[language] and not node.find(True)
            assert not spans or FACTS.index(spans[-1]['data-fact-id']) < index
            node.name = 'span'; node.clear(); node.append(LABELS[language][index])
            spans.append(node.extract())
        if spans:
            block = result.new_tag('div', attrs={'class': 'archive-extension-basis-summary'})
            p = result.new_tag('p'); block.append(p); p.append(PREFIX[language])
            for index, span in enumerate(spans):
                if index: p.append(SEPARATOR[language])
                p.append(span)
            p.append(STOP[language]); lead.insert_before(block)
        if unknown:
            block = result.new_tag('div', attrs={'class': 'reading-gap'})
            p = result.new_tag('p', attrs={'class': 'data-gap', 'data-fact-id': 'archive-extension-basis', 'data-status': 'needs-review'})
            p.append(REVIEW[language]); block.append(p); lead.insert_before(block)
        assert spans or unknown, 'Old list empty without a declared unsupported selection'
        lead.decompose(); items.decompose(); changes += 1
    return result, changes


def compare(before, after, language, *, unknown=False):
    result, count = expected(before, language, unknown=unknown)
    assert dom(result) == dom(after), 'Unexpected Q11 HTML, fact, punctuation or authored-answer change'
    return count


def scenarios():
    """Reachable subsets plus adapter-only unsupported/stale values, independently of source."""
    import itertools
    from test_preservation_coverage import plain, AUTHORED
    from generate_pilot_fixtures import IDS, path
    base = plain()
    archive = path('preservingCUuid', 'archivedAfterQUuid')
    extension = path(archive, 'archivedAfterYesAUuid', 'archivedAfterExtendQUuid')
    basis = path(extension, 'archivedAfterExtendYesAUuid', 'archivedAfterExtendBasisQUuid')
    options = [IDS['archivedAfterExtendBasis'+n+'ChoiceUuid'] for n in ['Actual','Predicted','Budget']]
    choices = [list(c for c, use in zip(options, flags) if use) for flags in itertools.product([False, True], repeat=3)]
    choices += [list(reversed(options)), options+options, ['unrecognized-option'], [options[0], '<script>unknown</script>'], None, '', ' '+options[0]]
    for parent, child, selected in itertools.product(['Yes', 'No', None], ['Yes','No',None], choices):
        replies = copy.deepcopy(base)
        replies[archive] = IDS['archivedAfter'+parent+'AUuid'] if parent else ''
        replies[extension] = IDS['archivedAfterExtend'+child+'AUuid'] if child else ''
        replies[basis] = selected
        unknown = isinstance(selected, list) and any(v not in options for v in selected)
        active = parent == child == 'Yes'
        yield replies, active and unknown, [FACTS[i] for i,c in enumerate(options) if active and isinstance(selected,list) and c in selected]
    for name in ['preservation-partial','preservation-custom']:
        replies = plain(name)
        if name == 'preservation-custom':
            for field in ['producedDataDescriptionQUuid', 'notPublishedReasonOtherQUuid', 'archivedAfterPeriodOtherQUuid']:
                replies[next(k for k in replies if k.endswith(IDS[field]))] = AUTHORED
        yield replies, False, []


def check_roots(current, frozen, language):
    """Compare the entire Q11 DOM, with autoescape both off and on."""
    from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
    import test_science_europe_contract as adapter
    wrapper = "{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include 'src/questions/11-data-preservation.html.j2' %}"
    rows = 0
    for autoescape in [False, True]:
        env = Environment(loader=FileSystemLoader(current), extensions=['jinja2.ext.do'], autoescape=autoescape)
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v:v)
        old = env.overlay(loader=ChoiceLoader([DictLoader({'src/post-project-archive.html.j2': frozen.read_text()}), env.loader]))
        before, after = old.from_string(wrapper), env.from_string(wrapper)
        for replies, unknown, facts in scenarios():
            a,b = [BeautifulSoup(t.render(repliesMap=replies), 'html.parser') for t in [before,after]]
            compare(a,b,language,unknown=unknown)
            summaries = b.select('.archive-extension-basis-summary')
            assert bool(summaries) == bool(facts)
            assert [n['data-fact-id'] for n in b.select('.archive-extension-basis-summary span')] == facts
            assert not b.select('p p, p div, p ul, script')
            assert 'unrecognized-option' not in b.get_text()
            assert bool(b.select('[data-fact-id="archive-extension-basis"][data-status="needs-review"]')) == unknown
            rows += 1
    return rows
