"""Independent answer-state oracle for packaged Q1 preparation prose."""
import itertools
import json
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from output_profile_contract import environment, WRAPPER
from test_answer_retention import IDS, path
from test_structure_bindings import BlockProbe

QUESTION = 'src/questions/01-how-data.html.j2'
START = '    {# Constrains - Data Harmonization #}'
END = '  {%- elif preexistingAUuid == uuids.preexistingNoAUuid -%}'
PRE = path('reusingCUuid', 'preexistingQUuid')
HARM = path(PRE, 'preexistingYesAUuid', 'dataHarmoQUuid')
SHARE = path(HARM, 'dataHarmoYesAUuid', 'dataHarmoOthersQUuid')
CONVERT = path(PRE, 'preexistingYesAUuid', 'dataCompReadQUuid')
VERSION = path(CONVERT, 'dataCompReadYesAUuid', 'dataCompReadItselfQUuid')
METADATA = path(CONVERT, 'dataCompReadYesAUuid', 'dataCompReadOthersQUuid')
STANDARDS = path(METADATA, 'dataCompReadOthersYesAUuid', 'dataCompReadOthersYesStandardsQUuid')
H = 'Before reuse, we need to harmonize existing data from different sources'
C = 'Before reuse, we will need to convert the data into a machine-readable form'
M = 'We will provide others with standardized, machine-readable metadata'
SUFFIX = ' and we will use the following metadata standards:'
JOIN = {
    'harm': {'dataHarmoOthersYesAUuid': ' and will make the results available to others',
             'dataHarmoOthersNoAUuid': ' but will not make the results available to others'},
    'version': {'dataCompReadItselfYesAUuid': ' and will make this version available to others through a standard repository',
                'dataCompReadItselfYesOtherAUuid': ' and will make this version available to others',
                'dataCompReadItselfNoAUuid': ' but will not make this version available to others'},
}
OLD_H = 'We need to harmonize different sources of existing data before reusing them'
OLD_C = 'We will need to (re-)made the data into computer readable form before their using'
OLD_M = 'We will provide machine readable, standardized metadata to others'
OLD_WORDS = {
    H + '.': OLD_H + '.',
    H + JOIN['harm']['dataHarmoOthersYesAUuid'] + '.': OLD_H + ' and we will make this harmonization results available to others.',
    H + JOIN['harm']['dataHarmoOthersNoAUuid'] + '.': OLD_H + " but we won't make this harmonization results available to others.",
    C + '.': OLD_C + '.',
    C + JOIN['version']['dataCompReadItselfYesAUuid'] + '.': OLD_C + ' and we will make this computer readable form available to others through a standard repository.',
    C + JOIN['version']['dataCompReadItselfYesOtherAUuid'] + '.': OLD_C + ' and we will make this computer readable form available to others.',
    C + JOIN['version']['dataCompReadItselfNoAUuid'] + '.': OLD_C + " but we won't make this computer readable form available to others.",
    M + '.': OLD_M + '.',
    M + SUFFIX: OLD_M + ' and we will use following Metadata Standards:',
}


def block(text):
    assert text.count(START) == text.count(END) == 1
    return text[text.index(START):text.index(END)]


def normalize(text):
    return ' '.join(text.split())


def integration(kind, name):
    raw = {'type': kind, 'value': name}
    if kind == 'IntegrationType':
        raw['raw'] = {'name': name, 'doi': '10.0000/example.test', 'id': 'example'}
    return {'value': {'value': raw}}


def cases():
    inactive = [None, '', 'unknown', '0']
    yes = {'parent': 'preexistingYesAUuid', 'harm': 'dataHarmoYesAUuid',
           'version': 'dataCompReadItselfYesAUuid', 'metadata': 'dataCompReadOthersYesAUuid'}
    def row(name, parent=yes['parent'], harm=None, share=None, convert=None, version=None, metadata=None, standards=()):
        choices = {PRE: parent, HARM: harm, SHARE: share, CONVERT: convert, VERSION: version, METADATA: metadata}
        values = {key: IDS.get(value, value) for key, value in choices.items() if value is not None}
        values[STANDARDS] = ['standard-' + str(i) for i in range(len(standards))]
        for i, (kind, label) in enumerate(standards):
            values[path(STANDARDS, 'standard-' + str(i), 'dataCompReadOthersYesStandardQUuid')] = integration(kind, label)
        return dict(name=name, values=values, parent=parent, harm=harm, share=share, convert=convert,
                    version=version, metadata=metadata, standards=standards)
    for i, (harm, share) in enumerate(itertools.product(
            inactive + ['dataHarmoNoAUuid', 'dataHarmoYesAUuid'], inactive + list(JOIN['harm']))):
        yield row('harm-' + str(i), harm=harm, share=share)
    standards_cases = [(), (('PlainType', 'Dublin Core v1.2'),),
        (('IntegrationType', 'Standard A & B'), ('PlainType', '原始名稱。v1.2')),
        (('PlainType', C + '.'),),
        (('PlainType', 'Long metadata standard 名稱 ' * 40),)]
    for i, (convert, version, metadata, standards) in enumerate(itertools.product(
            inactive + ['dataCompReadNoAUuid', 'dataCompReadYesAUuid'],
            inactive + list(JOIN['version']), inactive + ['dataCompReadOthersNoAUuid', 'dataCompReadOthersYesAUuid'], standards_cases)):
        yield row('convert-' + str(i), convert=convert, version=version, metadata=metadata, standards=standards)
    for i, parent in enumerate(inactive + ['preexistingNoAUuid']):
        yield row('stale-parent-' + str(i), parent=parent, harm=yes['harm'], share='dataHarmoOthersYesAUuid',
                  convert='dataCompReadYesAUuid', version=yes['version'], metadata=yes['metadata'], standards=standards_cases[2])
    yield row('both', harm=yes['harm'], share='dataHarmoOthersNoAUuid', convert='dataCompReadYesAUuid',
              version='dataCompReadItselfNoAUuid', metadata=yes['metadata'], standards=standards_cases[2])


def expected(case, words=None, chinese=None):
    chinese = bool(words) if chinese is None else chinese
    words = words or {}
    tr = lambda s: words[s] if words else s
    if case['parent'] != 'preexistingYesAUuid':
        return []
    paragraphs = []
    if case['harm'] == 'dataHarmoYesAUuid':
        paragraphs.append(tr(H + JOIN['harm'].get(case['share'], '') + '.'))
    if case['convert'] == 'dataCompReadYesAUuid':
        text = tr(C + JOIN['version'].get(case['version'], '') + '.')
        if case['metadata'] == 'dataCompReadOthersYesAUuid':
            text += '' if chinese else ' '
            if case['standards']:
                separator, stop = ('、', '。') if chinese else (', ', '.')
                text += tr(M + SUFFIX) + ('' if chinese else ' ')
                text += separator.join(label for _, label in case['standards']) + stop
            else:
                text += tr(M + '.')
        paragraphs.append(normalize(text))
    return paragraphs


def check(root, before, after, words=None, old_words=None):
    decode = lambda values: {n: v.decode() if isinstance(v, bytes) and n.endswith('.j2') else v for n, v in values.items()}
    before, after = decode(before), decode(after)
    assert set(before) == set(after)
    assert {n for n in before if before[n] != after[n]} == {QUESTION}
    assert before[QUESTION].replace(block(before[QUESTION]), '') == after[QUESTION].replace(block(after[QUESTION]), '')
    rows = []
    # Full production fixture contexts retain all other questions and original markup.
    fixtures = [('EMPTY', {})]
    for file in sorted((root / 'fixtures/pilot/en').glob('*.events.json')):
        values = {e['path']: ({'value': {'value': e['value']['value']}} if e['value']['type'] == 'IntegrationReply'
                   else e['value']['value']) for e in json.loads(file.read_text())}
        fixtures.append((file.name, values))
    for escape, profile in itertools.product([False, True], ['review', 'submission', 'unknown']):
        overrides = {n: v for n, v in after.items() if n.endswith('.j2')}
        wrapper = ("{% import 'src/macros.html.j2' as macros with context %}"
                   "{% import 'src/uuids.j2' as uuids with context %}"
                   "{% set preexistingPath = [uuids.reusingCUuid, uuids.preexistingQUuid]|reply_path %}"
                   "{% if repliesMap[preexistingPath]|reply_str_value == uuids.preexistingYesAUuid %}"
                   + block(after[QUESTION]) + '{% endif %}')
        template = environment(root, escape, overrides).from_string(wrapper)
        old_template = environment(root, escape, {n: v for n, v in before.items() if n.endswith('.j2')}).from_string(
            wrapper.replace(block(after[QUESTION]), block(before[QUESTION])))
        for case in cases():
            html = template.render(repliesMap=case['values'], output_profile=profile)
            structural = BlockProbe(); structural.feed(html)
            assert not structural.errors and not structural.stack, case['name']
            soup = BeautifulSoup(html, 'html.parser')
            assert [normalize(p.get_text()) for p in soup.find_all('p')] == expected(case, words), (case['name'], profile, escape)
            old_soup = BeautifulSoup(old_template.render(repliesMap=case['values'], output_profile=profile), 'html.parser')
            assert [normalize(p.get_text()) for p in old_soup.find_all('p')] == expected(
                case, old_words or OLD_WORDS, chinese=bool(words)), ('baseline', case['name'], profile, escape)
            assert [str(a) for a in old_soup.find_all('a')] == [str(a) for a in soup.find_all('a')]
            expected_links = [label for kind, label in case['standards'] if kind == 'IntegrationType'] if (
                case['parent'] == 'preexistingYesAUuid' and case['convert'] == 'dataCompReadYesAUuid'
                and case['metadata'] == 'dataCompReadOthersYesAUuid') else []
            assert [(a.get_text(), a.get('href')) for a in soup.find_all('a')] == [
                (label, 'https://doi.org/10.0000/example.test') for label in expected_links]
            rows.append(dict(case=case['name'], profile=profile, autoescape=escape))
        controls = [environment(root, escape, {**{n: v for n, v in source.items() if n.endswith('.j2')},
            QUESTION: source[QUESTION].replace(block(source[QUESTION]), '')}).from_string(WRAPPER) for source in [before, after]]
        full = environment(root, escape, overrides).from_string(WRAPPER)
        for name, values in fixtures:
            args = dict(repliesMap=values, output_profile=profile, dc={'project': {'created_by': None}, 'e': {'choices': {}}})
            assert controls[0].render(**args) == controls[1].render(**args), name
            soup = BeautifulSoup(full.render(**args), 'html.parser')
            assert len(soup.select('.question')) == 15 and len(soup.select('.dmp-section')) == 6
            assert not soup.select('p p, p div, p ul, p table')
            rows.append(dict(case='fixture-' + name, profile=profile, autoescape=escape))
    return rows
