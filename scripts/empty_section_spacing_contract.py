"""Verify every 0.3.48 byte before offering an exact test-only 0.3.47 view."""
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASELINE='2eebf1f783a6017fe25712c1b01c6a708adfedab'
PROTOTYPE='c875c950353fae1e36fc4df547e856249f9a7b72'

@lru_cache(maxsize=None)
def historical(name,commit=BASELINE):
    return subprocess.check_output(['git','-C',str(ROOT),'show',commit+':'+name])

def load(name):
    path=ROOT/'experiments/empty-section-spacing'/(name+'.py')
    assert path.read_bytes()==historical(str(path.relative_to(ROOT)),PROTOTYPE),'Prototype recipe changed'
    spec=importlib.util.spec_from_file_location('integrated_sections_'+name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

@lru_cache(maxsize=1)
def css():return load('recipe').CSS

def prior_css(source):
    marker='/* BEGIN empty section spacing v1:'
    if marker not in source:return source
    delta=css().decode()
    assert source.count(marker)==source.count(delta)==1,'Modified or duplicate section CSS'
    # Historical probes may append a separately verified retired rule. Preserve
    # every surrounding byte; the caller's historical hash gate checks them.
    # Actual 0.3.48 sources are still checked against the complete exact overlay.
    return source.replace(delta,'',1)

def project_source(sources=None,metadata=None):
    if sources is None:sources={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
    if metadata is None:metadata=json.loads((ROOT/'template.json').read_text())
    if metadata['version']=='0.3.49':
        from reuse_preparation_contract import project_source as before_preparation
        sources,metadata=before_preparation(sources,metadata)
    recipe=load('recipe');before=recipe.baseline_sources(ROOT)
    assert sources==recipe.overlay(before,ROOT),'Unreviewed 0.3.48 source, inventory or asset'
    previous=json.loads(historical('template.json'))
    assert metadata==dict(previous,version='0.3.48'),'Unreviewed identity or conversion step'
    for name in ['scripts/prepare_layout.py','PACKAGE_README.md','LICENSE']:
        assert (ROOT/name).read_bytes()==historical(name),name
    for name in ['probe','engine']:load(name)
    return dict(before),previous
