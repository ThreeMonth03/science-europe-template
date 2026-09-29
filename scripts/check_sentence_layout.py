"""Focused non-reuse prose and explicit list-label checks, for either language."""
import itertools
import re

from bs4 import BeautifulSoup
from current_support import IDS, environment, path

AUTHORED = '<p>Keep <strong>Original.csv</strong>; do not change this punctuation: .,</p><ul><li>Reason <strong>A</strong>.</li></ul>'
DECISION = {'en': 'This dataset was considered but will not be re-used.',
            'zh-Hant': '本計畫曾考慮使用此資料集，但決定不採用。'}


def nonreuse_replies(kind='ref', reason='Quality', source='https://example.org/data?a=1&b=2', named=True, detail=AUTHORED):
    parent = path('reusingCUuid', 'preexistingQUuid')
    listing = path(parent, 'preexistingYesAUuid', kind + 'DataQUuid')
    item = path(listing, 'dataset-1')
    use = path(item, kind + 'DataUseQUuid')
    why = path(use, kind + 'DataUseNoAUuid', kind + 'DataUseNoWhyQUuid')
    result = {parent: IDS['preexistingYesAUuid'], listing: ['dataset-1'], use: IDS[kind + 'DataUseNoAUuid']}
    if named: result[path(item, kind + 'DataNameQUuid')] = 'Dataset A'
    if source: result[path(item, kind + 'DataWhereQUuid')] = source
    if reason:
        result[why] = IDS[kind + 'DataUseNo' + reason + 'AUuid'] if reason != 'unknown' else 'obsolete-choice'
    # Even a stale custom reason must not appear behind a different choice.
    result[path(why, kind + 'DataUseNoReasonAUuid', kind + 'DataUseNoReasonQUuid')] = detail
    return result


def folder_replies():
    parent = path('processingCUuid', 'storageConvQUuid')
    fs = path(parent, 'storageConvExploreAUuid', 'storageConvFSysQUuid')
    result = {parent: IDS['storageConvExploreAUuid'], fs: IDS['storageConvFSysYesAUuid']}
    for kind in ['Subj', 'Analysis', 'WorkflowStep']:
        result[path(fs, 'storageConvFSysYesAUuid', 'scFSys' + kind + 'FoldersQUuid')] = IDS['scFSys' + kind + 'FoldersYesAUuid']
    return result


def check(root, language):
    counts = dict(nonreuse_cases=0, inactive_cases=0, inline_cases=0)
    css = (root / 'src/layout.css').read_text()
    assert 'html body li > strong:first-child {' not in css
    assert 'html body li > strong.item-label { display: block; break-after: avoid; }' in css
    for escape in [False, True]:
        env = environment(root, escape)
        prefix = "{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}"
        template = env.from_string(prefix + "{% include 'src/questions/01-how-data.html.j2' %}")
        folder = env.from_string(prefix + "{% include 'src/questions/03-docs-metadata.html.j2' %}")
        def render(t, replies, profile):
            return BeautifulSoup(t.render(repliesMap=replies, output_profile=profile), 'html.parser')

        for kind, reason, source, named, profile in itertools.product(
                ['ref', 'nref'], ['Data', 'Aspect', 'Quality', 'Cond', 'Reason', '', 'unknown'],
                ['https://example.org/data?a=1&b=2', 'ftp://example.org/data', 'Local archive.', ''],
                [False, True], ['review', 'submission']):
            replies = nonreuse_replies(kind, reason, source, named)
            soup = render(template, replies, profile)
            paragraph = soup.select_one('.nonreuse-summary')
            assert paragraph and DECISION[language] in paragraph.get_text(' ', strip=True)
            assert len(soup.select('.nonreuse-summary')) == 1
            assert not re.search(r'[.。]\s*[,，]', paragraph.get_text())
            if language == 'zh-Hant':
                assert not re.search(r'。[ \u00a0]+[\u3400-\u9fff]', paragraph.get_text())
            assert not soup.select('p p, p div, p ul, p table')
            location = soup.select_one('.dataset-source')
            assert bool(location) == bool(source)
            if source:
                assert source in location.get_text()
                if source.startswith(('https://', 'ftp://')): assert location.a['href'] == source
            if reason == 'Reason':
                detail = soup.select_one('.answer-detail[data-fact-id="nonreuse-reason"]')
                assert detail and str(detail.ul) == str(BeautifulSoup(AUTHORED, 'html.parser').ul)
                assert 'Original.csv' in detail.get_text() and '.,' in detail.get_text()
            else:
                assert 'Original.csv' not in soup.get_text()
            gaps = soup.select('.data-gap[data-fact-id="nonreuse-reason"]')
            assert bool(gaps) == (profile == 'review' and reason in ('', 'unknown'))
            if gaps:
                assert gaps[0]['data-status'] == ('needs-review' if reason == 'unknown' else 'missing')
                if language == 'zh-Hant':
                    assert gaps[0].get_text(' ', strip=True) == '尚待補充：不採用此資料集的原因。'
            if reason in ('Data', 'Aspect', 'Quality', 'Cond'):
                assert paragraph.select_one('[data-fact-id="nonreuse-reason"][data-status="complete"]')
            if not named and profile == 'submission': assert soup.select_one('strong.item-label .dataset-label')
            counts['nonreuse_cases'] += 1

        for kind, profile in itertools.product(['ref', 'nref'], ['review', 'submission']):
            for detail in ['', ' \n ']:
                soup = render(template, nonreuse_replies(kind, 'Reason', detail=detail), profile)
                assert not soup.select('.answer-detail[data-fact-id="nonreuse-reason"]')
                assert bool(soup.select('.data-gap[data-fact-id="nonreuse-reason"]')) == (profile == 'review')
            for selected in ['', IDS[kind + 'DataUseYesAUuid'], 'obsolete']:
                replies = nonreuse_replies(kind)
                key = next(k for k in replies if k.endswith('.' + IDS[kind + 'DataUseQUuid']))
                replies[key] = selected
                assert not render(template, replies, profile).select('.nonreuse-summary')
                counts['inactive_cases'] += 1
        for profile in ['review', 'submission']:
            soup = render(folder, folder_replies(), profile)
            emphasis = soup.select('.storage-conventions-policy li > strong')
            # Reviewed Chinese sentences already omit this English emphasis.
            assert len(emphasis) == (3 if language == 'en' else 0)
            assert all('item-label' not in n.get('class', []) for n in emphasis)
            if language == 'en':
                assert 'There will be a folder for each sample/subject.' in soup.get_text(' ', strip=True).replace(' .', '.')
            else:
                assert [n.get_text(' ', strip=True) for n in soup.select('.storage-conventions-policy li')] == [
                    '每個樣本／研究對象都會有一個資料夾。',
                    '每次分析（包括重新分析）都會使用一個子資料夾。',
                    '分析工作流程的每個步驟都會使用一個子資料夾。']
            counts['inline_cases'] += 1
    return counts
