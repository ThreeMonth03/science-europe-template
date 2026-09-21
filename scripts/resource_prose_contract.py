"""Project only the bounded 0.3.41 Q15 presentation delta back to 0.3.40."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'ede928f4950e2d382cd38041d2430765c22aea4e'
QUESTION = 'src/questions/15-required-resources.html.j2'
HELPER = 'src/resource-prose.html.j2'
PDF_HELPER = 'src/pdf/short-resources.html.j2'
START = "    {%- set resourceOverview = namespace(original='', explicitPair=false) -%}\n    {%- set resourceOverview.original -%}\n"
END = """    {% set resourceOverview.explicitPair = additionalHWSWAUuid == uuids.additionalHWSWNoAUuid and repoCharges in [uuids.repoChargesNoAUuid, uuids.repoChargesYesAUuid] -%}
    {%- endset -%}
    {%- import 'src/resource-prose.html.j2' as resourceProse -%}
    {{- resourceProse.render(resourceOverview.original, resourceOverview.explicitPair) -}}
"""
PDF_CHANGES = [
    ("        'table class=\"resource-table\"', 'th scope=\"col\"',\n",
     "        'table class=\"resource-table\"', 'th scope=\"col\"',\n        'span data-fact-id=\"repository-charges\" data-status=\"complete\"',\n"),
    ("          {%- elif name in ['strong', 'em', 'code'] -%}",
     "          {%- elif name == 'span' -%}{%- set legal.ok = parent == 'p data-requirement-id=\"SE-6b\" data-fact-id=\"hardware-software\" data-status=\"explicit-no\"' and question.count('<span ') == 1 -%}\n          {%- elif name in ['strong', 'em', 'code'] -%}"),
    ("not in ['p', 'strong', 'em', 'code', 'li', 'h3', 'h4', 'th']",
     "not in ['p', 'span', 'strong', 'em', 'code', 'li', 'h3', 'h4', 'th']"),
]


def historical(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', BASELINE+':'+path])


def prior_question(source):
    for insertion, anchor in [(START, '    {# additional hw/sw #}\n'), (END, '    {# costs #}\n')]:
        assert source.count(insertion+anchor) == 1, 'Q15 wrapper drift'
        source = source.replace(insertion+anchor, anchor, 1)
    return source


def prior_pdf(source):
    for before, after in PDF_CHANGES:
        assert source.count(after) == 1, 'PDF span grammar drift'
        source = source.replace(after, before, 1)
    return source


def project_source():
    sources = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
    metadata = json.loads((ROOT/'template.json').read_text())
    if metadata['version'] in ['0.3.42', '0.3.43']:
        from short_resource_rows_contract import project_source as project_rows
        sources, metadata = project_rows()
    old = subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASELINE,'src'],text=True).splitlines()
    assert set(sources)-set(old) == {HELPER} and not set(old)-set(sources)
    sources.pop(HELPER)
    sources[QUESTION] = prior_question(sources[QUESTION].decode()).encode()
    sources[PDF_HELPER] = prior_pdf(sources[PDF_HELPER].decode()).encode()
    for name in old: assert sources[name] == historical(name), name
    assert metadata['version'] == '0.3.41'
    metadata['version'] = '0.3.40'
    assert metadata == json.loads(historical('template.json'))
    assert (ROOT/'scripts/prepare_layout.py').read_bytes() == historical('scripts/prepare_layout.py')
    return sources, metadata


def project_prepared(root, hashes):
    project_source()
    result = dict(hashes)
    assert (root/HELPER).read_bytes() == (ROOT/HELPER).read_bytes(), 'Owned join helper must not be translated'
    assert result.pop(HELPER) == hashlib.sha256((ROOT/HELPER).read_bytes()).hexdigest()
    for path, projection in [(QUESTION, prior_question), (PDF_HELPER, prior_pdf)]:
        result[path] = hashlib.sha256(projection((root/path).read_text()).encode()).hexdigest()
    # Caller compares the ENTIRE projected dictionary against frozen 0.3.40
    # prepared-source hashes, including the translated question (not only EN).
    return result
