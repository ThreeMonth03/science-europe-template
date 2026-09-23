"""Exact owned-paragraph projection, never a global whitespace normalizer."""
import copy
import itertools
import json
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from output_profile_contract import environment, WRAPPER
from generate_metadata_fixtures import PARENT, ACCESS, REASON, IDS, path
from metadata_followup_contract import scenarios

QUESTION = 'src/questions/03-docs-metadata.html.j2'
STANDARDS = path(PARENT, 'metadataExploreAUuid', 'metadataStandardsQUuid')
PROVENANCE = path(PARENT, 'metadataExploreAUuid', 'provenanceW3CQUuid')
KEYWORDS = path(STANDARDS, 'metadataStandardsExploreAUuid', 'metadataStandardsKeywordsQUuid')
ZH_KEYWORDS = '我們將納入關鍵字與相關本體參照，以提高資料被找到及再次使用的可能性。'
ZH_PROVENANCE = '資料溯源將以 W3C PROV 記錄。'
SELECTOR = '#q-docs-metadata > .answer > .metadata-policy'
AUTHORED = '<p>原文）。 下一句。  Keep  two spaces; v1.25.</p><p><strong>DDI (Original)</strong> <a href="https://example.org/a?x=1&amp;y=2">原始連結。  X</a></p>'


def zh_parts(mask, keywords, provenance):
    labels = [s for i, s in enumerate(['Dublin Core', 'DataCite', 'DDI（Data Documentation Initiative）']) if mask & (1 << i)]
    result = []
    if labels:
        joined = labels[0] if len(labels) == 1 else (' 與 '.join(labels) if len(labels) == 2 else labels[0]+'、'+labels[1]+' 與 '+labels[2])
        result.append('我們將使用 ' + joined + ' 後設資料標準記錄資料。')
    if keywords: result.append(ZH_KEYWORDS)
    if provenance: result.append(ZH_PROVENANCE)
    return result


ALLOWED = {' '.join(parts): ''.join(parts)
           for mask, keywords, provenance in itertools.product(range(8), [False, True], [False, True])
           if len(parts := zh_parts(mask, keywords, provenance)) > 1}


def changes(before, language):
    if language != 'chinese': return []
    result = []
    for policy in before.select(SELECTOR):
        node = policy.find('p', recursive=False)
        if node is None or node.attrs or node.find(True): continue
        text = node.get_text()
        if text in ALLOWED:
            assert node == policy.find(recursive=False), 'Owned summary must precede dictionary/publication'
            result.append((text, ALLOWED[text]))
    assert len(result) <= 1
    return result


def project(before, language):
    result = copy.deepcopy(before)
    expected = changes(before, language)
    if expected:
        node = result.select_one(SELECTOR).find('p', recursive=False)
        assert str(node.string) == expected[0][0]
        node.string.replace_with(expected[0][1])
    return result


def compare(before, after, language):
    assert str(project(before, language)) == str(after), 'Unexpected whitespace, authored text, markup or fact delta'


def cases():
    for i, data in enumerate(scenarios()): yield 'prior-' + str(i), data
    states = ['', 'unknown', 'no', 'yes']
    for mask, keywords, provenance in itertools.product(range(8), states, states):
        data = {PARENT: IDS['metadataExploreAUuid'], STANDARDS: IDS['metadataStandardsExploreAUuid'],
                ACCESS: IDS['metadataOpenNoAUuid'], REASON: AUTHORED}
        for i, name in enumerate(['DC', 'DataCite', 'DDI']):
            data[path(STANDARDS, 'metadataStandardsExploreAUuid', 'metadataStandards'+name+'QUuid')] = (
                IDS['metadataStandards'+name+'YesAUuid'] if mask & (1 << i) else '')
        data[KEYWORDS] = IDS['metadataStandardsKeywordsYesAUuid'] if keywords == 'yes' else keywords
        data[PROVENANCE] = IDS['provenanceW3CYesAUuid'] if provenance == 'yes' else provenance
        yield f'join-{mask}-{keywords}-{provenance}', data
    active = dict(data)
    for field in [PARENT, STANDARDS]:
        for value in ['', 'unknown', 'no']:
            yield 'stale-' + field + '-' + value, {**active, field: value}


def check(root, before, after, language='english'):
    decode = lambda src: {n: (v.decode() if isinstance(v, bytes) else v) for n, v in src.items() if n.endswith('.j2')}
    before, after = decode(before), decode(after)
    assert set(before) == set(after)
    assert {n for n in before if before[n] != after[n]} == {QUESTION}
    wrapper = "{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '" + QUESTION + "' %}"
    fixtures = [('EMPTY', {})]
    for file in sorted((root / 'fixtures/pilot/en').glob('*.events.json')):
        values = {e['path']: ({'value': {'value': e['value']['value']}} if e['value']['type'] == 'IntegrationReply'
                   else e['value']['value']) for e in json.loads(file.read_text())}
        fixtures.append((file.name, values))
    rows = []
    for escape, profile in itertools.product([False, True], ['review', 'submission', 'unknown']):
        environments = [environment(root, escape, src) for src in [before, after]]
        templates = [env.from_string(wrapper) for env in environments]
        full = [env.from_string(WRAPPER) for env in environments]
        for fixtures_only, samples in [(False, cases()), (True, fixtures)]:
            for name, values in samples:
                args = dict(repliesMap=values, output_profile=profile, dc={'project': {'created_by': None}, 'e': {'choices': {}}})
                old, new = [BeautifulSoup(t.render(**args), 'html.parser') for t in (full if fixtures_only else templates)]
                compare(old, new, language)
                delta = changes(old, language)
                assert not new.select('p p, p div, p ul, p table, script')
                if fixtures_only:
                    assert len(new.select('.question')) == 15 and len(new.select('.dmp-section')) == 6
                if profile == 'submission':
                    assert not [n for n in new.select('.data-gap') if not n.find_parent(class_='answer-detail')]
                rows.append(dict(case=('fixture-' if fixtures_only else '') + name, profile=profile,
                    autoescape=escape, removed_owned_separators=sum(len(a)-len(b) for a,b in delta)))
    assert language != 'chinese' or sum(r['removed_owned_separators'] for r in rows) > 0
    return rows
