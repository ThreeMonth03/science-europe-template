"""Shared synthetic-reply adapter for current behaviour checks, not frozen oracles."""
from pathlib import Path
import re

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, Undefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[1]
IDS = dict(re.findall(r'set\s+(\w+)\s*=\s*"([0-9a-f-]{36})"', (ROOT / 'src/uuids.j2').read_text()))
PREFIX = "{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}"
WRAPPER = PREFIX + "{% include 'src/projects.html.j2' %}{% include 'src/content.html.j2' %}"


def path(*names):
    return '.'.join(IDS.get(name, name) for name in names)


def reply_str_value(reply):
    if isinstance(reply, Undefined) or reply is None:
        return ''
    if isinstance(reply, str):
        return reply
    if isinstance(reply, dict):
        value = reply.get('value', reply)
        if isinstance(value, dict): value = value.get('value', value)
        if isinstance(value, dict): return str(value.get('value', ''))
    return str(reply)


def reply_items(reply):
    return reply if isinstance(reply, list) else []


def environment(root, escape=False, overrides=None):
    loaders = ([DictLoader(overrides)] if overrides else []) + [FileSystemLoader(root)]
    env = Environment(loader=ChoiceLoader(loaders), extensions=['jinja2.ext.do'], autoescape=escape)
    env.filters.update(reply_path=lambda parts: '.'.join(map(str, parts)), reply_items=reply_items,
        reply_str_value=reply_str_value, markdown=lambda v: Markup(v) if escape else v,
        any=any, dot=lambda v: str(v) + ('' if str(v).endswith('.') else '.'))
    env.tests['true'] = lambda v: v is True
    return env


def support_replies(choices=(None,), repository='Special', publication='Yes'):
    data = path('preservingCUuid', 'producedDataQUuid')
    pub = path(data, 'dataset-a', 'isPublishedDataQUuid')
    dist = path(pub, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
    replies = {data: ['dataset-a'], dist: [f'distro-{i}' for i in range(len(choices))]}
    if publication: replies[pub] = IDS[f'isPublishedData{publication}AUuid']
    for i, choice in enumerate(choices):
        kind = path(dist, f'distro-{i}', 'publishedDataRepositoryKindQUuid')
        if repository: replies[kind] = IDS[f'publishedDataRepository{repository}AUuid']
        prefix = path(kind, 'publishedDataRepositorySpecialAUuid')
        if choice is not None:
            replies[path(prefix, 'specialRepoLongTermSupportQUuid')] = IDS.get(f'specialRepoLongTermSupport{choice}AUuid', choice)
        replies[path(prefix, 'specialRepoServiceLevelQUuid')] = IDS['specialRepoServiceLevelAdvancedAUuid']
    return replies


def identifier_replies(identifier='Yes', assigns='Repository', resolves='Yes', repository='Institutional', count=2):
    replies = support_replies(('Yes',) * count, repository='Institutional')
    for kind in [p for p in replies if p.endswith(IDS['publishedDataRepositoryKindQUuid'])]:
        base = kind.rsplit('.', 1)[0]
        if repository: replies[kind] = IDS.get('publishedDataRepository' + repository + 'AUuid', repository)
        else: replies.pop(kind, None)
        question = path(base, 'publishedDataIdentifierQUuid')
        if identifier: replies[question] = IDS.get('publishedDataIdentifier' + identifier + 'AUuid', identifier)
        else: replies.pop(question, None)
        for name, value in [('Assigns', assigns), ('Resolvable', resolves)]:
            key = path(question, 'publishedDataIdentifierYesAUuid', 'publishedDataIdentifier' + name + 'QUuid')
            if value: replies[key] = IDS.get('publishedDataIdentifier' + name + value + 'AUuid', value)
            else: replies.pop(key, None)
    return replies
