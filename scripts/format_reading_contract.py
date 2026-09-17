"""Independent, narrow projection of the frozen 0.3.30 Q2 DOM."""
import copy
import itertools
from bs4 import BeautifulSoup
from probe_pdf_budget_reading import dom

WORDS = {
    'english': {
        'standard': 'It is a standardized format.',
        'archive': 'This is a suitable format for long-term archiving.',
        'combined': 'It is a standardized format suitable for long-term archiving.',
        'small': ('We will have only a small amount of data stored in this format.', 'Only a small volume of data is expected.'),
        'total': ('We expect to have ', ' of data in this format.', 'The estimated data volume is ', '.'),
        'count': ('We expect ', ' files in this format.', 'We expect ', ' files.'),
        'size': ('The estimated average file size is ', '.'),
        'both': ('We expect ', ' files, with an estimated average size of ', '.'),
    },
    'chinese': {
        'standard': '此格式為標準化格式。',
        'archive': '此格式適合長期封存。',
        'combined': '採用標準化格式，適合長期封存。',
        'small': ('以此格式儲存的資料量預計很少。', '預估資料量不大。'),
        'total': ('以此格式儲存的資料量預計為 ', '。', '預估資料量為 ', '。'),
        'count': ('此格式的檔案數預計為 ', ' 個。', '預估共有 ', ' 個檔案。'),
        'size': ('每個檔案的平均大小預計為 ', '。'),
        'both': ('預估共有 ', ' 個檔案，平均每個檔案約 ', '。'),
    },
}


def inner(node, prefix, suffix):
    source = node.decode_contents()
    if source.startswith(prefix) and source.endswith(suffix):
        return source[len(prefix):-len(suffix)]
    return None


def replace(node, html):
    node.clear()
    for child in list(BeautifulSoup(html, 'html.parser').contents): node.append(child.extract())


def expected(before, language):
    result = copy.deepcopy(before); words = WORDS[language]; changed = []
    for summary in result.select('.format-description > .format-summary'):
        old = ' '.join(p.get_text() for p in summary.find_all('p', recursive=False))
        paragraphs = summary.find_all('p', recursive=False)
        for p in paragraphs:
            if p.parent is None: continue
            following = p.find_next_sibling()
            if p.get_text() == words['standard'] and following and following.get_text() == words['archive']:
                assert not p.attrs and not following.attrs and not p.find(True) and not following.find(True)
                replace(p, words['combined']); following.decompose()
            elif p.get_text() == words['small'][0]:
                assert not p.attrs and not p.find(True)
                replace(p, words['small'][1])
            elif (quantity := inner(p, *words['total'][:2])) is not None:
                assert not p.attrs
                replace(p, words['total'][2]+quantity+words['total'][3])
            elif (count := inner(p, *words['count'][:2])) is not None:
                assert not p.attrs
                size = inner(following, *words['size']) if following and following.name == 'p' else None
                if size is not None:
                    assert not following.attrs
                    start, middle, end = words['both']
                    replace(p, start+count+middle+size+end); following.decompose()
                else: replace(p, words['count'][2]+count+words['count'][3])
        new = ' '.join(p.get_text() for p in summary.find_all('p', recursive=False))
        if old != new: changed.append((old,new))
    return result, changed


def compare(before, after, language):
    projected, changed = expected(before, language)
    assert dom(projected) == dom(after), 'Unexpected Q2 structure, answer, quantity, gap or punctuation change'
    return changed


def scenarios():
    import test_format_volume as f
    # All parent states, including unsupported IDs and stale descendants.
    for standard, archive, volume in itertools.product(['Yes','No','','unknown'], ['Yes','No','','unknown'], ['Small','Total','FileSize','','unknown']):
        data=f.values()
        data.update({f.STANDARD:f.IDS.get('formatsIsStandard'+standard+'AUuid',standard),
                     f.ARCHIVE:f.IDS.get('formatsIsLTSuitable'+archive+'AUuid',archive),
                     f.VOLUME:f.IDS.get('formatsVolume'+volume+'AUuid',volume),
                     f.COUNT:'0', f.SIZE:'0.0001', f.TOTAL:'120', f.REASON:f.AUTHORED,
                     f.WHY:f.IDS['formatsWhyNSAnotherReasonAUuid'], f.CONVERT:f.IDS['formatsConvertLTSuitableNoAUuid']})
        yield data
    for data,_,_ in f.volume_cases(): yield data
    for why,convert in itertools.product(['ThereIsNoStandard','ItIsOptimized','AnotherReason','','unknown'],['Yes','No','','unknown']):
        data=f.values();data.update({f.STANDARD:f.IDS['formatsIsStandardNoAUuid'],f.ARCHIVE:f.IDS['formatsIsLTSuitableNoAUuid'],
            f.WHY:f.IDS.get('formatsWhyNS'+why+'AUuid',why),f.CONVERT:f.IDS.get('formatsConvertLTSuitable'+convert+'AUuid',convert),f.REASON:f.AUTHORED})
        yield data
    for count,size in [('2.5','invalid'),('1e3','0.5'),('-2','-0.01'),('<b>7</b>','<script>x</script>'),(' 12 ',' 0.25 ')]:
        data=f.values();data.update({f.VOLUME:f.IDS['formatsVolumeFileSizeAUuid'],f.COUNT:count,f.SIZE:size});yield data
    yield {};yield {f.FORMATS:['format-1']}


def check_roots(root, frozen, language):
    from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
    import test_science_europe_contract as adapter
    question='src/questions/02-what-data.html.j2'
    wrapper="{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '"+question+"' %}"
    checks=0
    for escape in [False,True]:
        env=Environment(loader=FileSystemLoader(root),extensions=['jinja2.ext.do'],autoescape=escape)
        env.filters.update(reply_path=adapter.reply_path,reply_items=adapter.reply_items,reply_str_value=adapter.reply_str_value,markdown=lambda v:v)
        old=env.overlay(loader=ChoiceLoader([DictLoader({question:frozen.read_text()}),env.loader]))
        templates=[old.from_string(wrapper),env.from_string(wrapper)]
        for data in scenarios():
            before,after=[BeautifulSoup(t.render(repliesMap=data),'html.parser') for t in templates]
            compare(before,after,language)
            assert not after.select('p p, p div, p ul, script')
            checks+=1
    return checks
