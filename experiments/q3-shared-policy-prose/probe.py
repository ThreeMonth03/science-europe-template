"""Independent parsed-DOM projection; preserve every other character and fact."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import sys
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'tests')]
from output_profile_contract import environment, WRAPPER
from generate_metadata_fixtures import PARENT, ACCESS, REASON, DICTIONARY, INSTRUCTIONS, FORM, IDS, path

QUESTION = 'src/questions/03-docs-metadata.html.j2'
HELPER = 'src/metadata-prose.html.j2'
SELECTOR = '#q-docs-metadata > .answer > .metadata-policy'
STANDARDS = path(PARENT, 'metadataExploreAUuid', 'metadataStandardsQUuid')
PROVENANCE = path(PARENT, 'metadataExploreAUuid', 'provenanceW3CQUuid')
KEYWORDS = path(STANDARDS, 'metadataStandardsExploreAUuid', 'metadataStandardsKeywordsQUuid')


def eligible(policy):
    if any(not isinstance(n, Tag) and (type(n) is not NavigableString or str(n).strip()) for n in policy.contents): return False
    nodes = policy.find_all(recursive=False)
    if len(nodes) not in [2,3]: return False
    dictionaries = 0
    for node in nodes:
        if node.name != 'p' or node.find(True): return False
        if node.attrs:
            if node.attrs not in [dict(**{'data-fact-id':'metadata-dictionary','data-status':status}) for status in ['complete','explicit-no']]: return False
            dictionaries += 1
        if any(type(n) is not NavigableString for n in node.contents): return False
        text = node.get_text().strip()
        if not text or text[-1] not in '.。' or any(c in text for c in '<>&'): return False
    return dictionaries <= 1


def separator(left, right):
    first = ord(right[0])
    return '' if left.endswith('。') and (0x3400 <= first <= 0x4DBF or 0x4E00 <= first <= 0x9FFF) else ' '


def projection(policy):
    assert eligible(policy)
    nodes = policy.find_all(recursive=False)
    soup = BeautifulSoup('<p class="metadata-prose"></p>', 'html.parser'); joined = soup.p
    previous = ''; removed = 0
    for node in nodes:
        text = node.get_text().strip()
        if previous:
            joiner = separator(previous, text); joined.append(joiner); removed += int(not joiner)
        if node.attrs:
            span = soup.new_tag('span', attrs=copy.deepcopy(node.attrs)); span.string = text; joined.append(span)
        else: joined.append(text)
        previous = text
    return joined, removed


def project(before):
    result = copy.deepcopy(before); changes = []
    for policy in result.select(SELECTOR):
        if not eligible(policy): continue
        joined, removed = projection(policy)
        original = ''.join(str(n) for n in policy.contents); body = original.strip()
        replacement = BeautifulSoup(original.replace(body, str(joined), 1), 'html.parser')
        policy.clear()
        for child in list(replacement.contents): policy.append(child.extract())
        changes.append(dict(removed_owned_separators=removed))
    return result, changes


def compare(before, after):
    expected, changes = project(before)
    assert str(expected) == str(after), 'Unexpected Q3 fact, original text, punctuation or unrelated structure change'
    return changes


def cases():
    spec = importlib.util.spec_from_file_location('prior_cjk_cases', ROOT/'experiments/cjk-punctuation-probe/probe.py')
    prior = importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
    yield from prior.cases()
    active = next(data for name, data in prior.cases() if name=='join-7-yes-yes')
    for dictionary, access, instruction, form in itertools.product(
        ['', 'unknown', 'metadataDictionaryYesAUuid', 'metadataDictionaryNoAUuid'],
        ['', 'unknown', 'metadataOpenYesAUuid', 'metadataOpenNoAUuid'],
        ['', 'unknown', 'metadataOpenInstrYesAUuid', 'metadataOpenInstrNoAUuid'],
        ['', 'unknown', 'metadataOpenFormNoAUuid', 'metadataOpenFormYesRepoAUuid']):
        values={**active, DICTIONARY:IDS.get(dictionary,dictionary), ACCESS:IDS.get(access,access),
                INSTRUCTIONS:IDS.get(instruction,instruction), FORM:IDS.get(form,form), REASON:''}
        yield 'combined-'+'-'.join([dictionary,access,instruction,form]), values
    for authored in [prior.AUTHORED, '<p>本計畫將建立資料字典或變項定義表。</p><p>後設資料將公開提供。</p>',
                     '<p>原文。  English v1.25.</p>'*100]:
        yield 'authored-'+str(len(authored)), {**active, DICTIONARY:IDS['metadataDictionaryYesAUuid'], REASON:authored}


def check(root, before, after, language):
    decode = lambda src:{n:(v.decode() if isinstance(v,bytes) else v) for n,v in src.items() if n.endswith('.j2')}
    before,after=decode(before),decode(after)
    assert set(after)-set(before)=={HELPER} and not set(before)-set(after)
    assert {n for n in before if before[n]!=after[n]}=={QUESTION}
    wrapper="{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '"+QUESTION+"' %}"
    fixtures=[('EMPTY',{})]
    for file in sorted((root/'fixtures/pilot/en').glob('*.events.json')):
        values={e['path']:({'value':{'value':e['value']['value']}} if e['value']['type']=='IntegrationReply' else e['value']['value']) for e in json.loads(file.read_text())}
        fixtures.append((file.name,values))
    rows=[]
    for escape,profile in itertools.product([False,True],['review','submission','unknown']):
        envs=[environment(root,escape,source) for source in [before,after]]
        partial=[env.from_string(wrapper) for env in envs];full=[env.from_string(WRAPPER) for env in envs]
        for fixtures_only,samples in [(False,cases()),(True,fixtures)]:
            for name,values in samples:
                args=dict(repliesMap=values,output_profile=profile,dc={'project':{'created_by':None},'e':{'choices':{}}})
                old,new=[BeautifulSoup(t.render(**args),'html.parser') for t in (full if fixtures_only else partial)]
                try: changes=compare(old,new)
                except AssertionError as exc: raise AssertionError((name,profile,escape)) from exc
                assert not new.select('p p, p div, p ul, p table, script')
                if fixtures_only:
                    assert len(new.select('.question'))==15 and len(new.select('.dmp-section'))==6
                if profile=='submission':assert not [n for n in new.select('.data-gap') if not n.find_parent(class_='answer-detail')]
                if name.startswith('authored-'):assert not changes
                rows.append(dict(case=('fixture-' if fixtures_only else '')+name,profile=profile,autoescape=escape,
                    joined_policies=len(changes),removed_owned_separators=sum(c['removed_owned_separators'] for c in changes)))
    assert any(r['joined_policies'] for r in rows)
    assert bool(sum(r['removed_owned_separators'] for r in rows)) == (language=='chinese')
    return rows
