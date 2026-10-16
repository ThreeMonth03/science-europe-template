from __future__ import annotations

import html
import json
import re
import sys
import unittest
from pathlib import Path

from jinja2 import BytecodeCache, ChoiceLoader, DictLoader, Environment, FileSystemLoader, Undefined


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_project_acronym import fixture as project_fixture
from current_support import MARKDOWN_ADAPTER, install_i18n
CONTRACT = json.loads(
    (ROOT / "requirements" / "science-europe-2021.json").read_text(encoding="utf-8")
)


def reply_path(parts):
    return ".".join(str(part) for part in parts)


def reply_str_value(reply):
    if isinstance(reply, Undefined) or reply is None:
        return ""
    if isinstance(reply, str):
        return reply
    if isinstance(reply, dict):
        value = reply.get("value", reply)
        if isinstance(value, dict):
            value = value.get("value", value)
        if isinstance(value, dict):
            return str(value.get("value", ""))
    return str(reply)


def reply_items(reply):
    if isinstance(reply, Undefined) or reply is None:
        return []
    return reply if isinstance(reply, list) else []


class QuestionBytecodeCache(BytecodeCache):
    """Cache compilation only; Jinja verifies each loader source checksum."""
    def __init__(self):
        self.code = {}

    def load_bytecode(self, bucket):
        key = (bucket.key, bucket.checksum)
        if key in self.code:
            bucket.bytecode_from_string(self.code[key])

    def dump_bytecode(self, bucket):
        key = (bucket.key, bucket.checksum)
        if key not in self.code and len(self.code) >= 256:
            self.code.pop(next(iter(self.code)))
        self.code[key] = bucket.bytecode_to_string()


QUESTION_BYTECODE = QuestionBytecodeCache()


def render_question(path: str, replies: dict[str, object], **context) -> str:
    env = Environment(
        loader=ChoiceLoader([DictLoader(MARKDOWN_ADAPTER), FileSystemLoader(ROOT)]),
        extensions=["jinja2.ext.do"],
        autoescape=False,
        bytecode_cache=QUESTION_BYTECODE,
    )
    env.filters.update(
        reply_path=reply_path,
        reply_str_value=reply_str_value,
        reply_items=reply_items,
        markdown=lambda value: value,
        any=any,
        dot=lambda value: f"{value}." if value and not str(value).endswith(".") else value,
    )
    env.tests["true"] = lambda value: value is True
    install_i18n(env, ROOT)
    wrapper = env.from_string(
        "{% import 'src/macros.html.j2' as macros with context %}"
        "{% import 'src/uuids.j2' as uuids with context %}"
        f"{{% include '{path}' with context %}}"
    )
    return wrapper.render(repliesMap=replies, **context)


class ScienceEuropeContractTests(unittest.TestCase):
    def test_repository_destinations_are_complete_and_keep_integration_links(self):
        from itertools import product
        from bs4 import BeautifulSoup
        from current_support import IDS, path, environment, PREFIX, support_replies
        names = [None, {'type': 'PlainType', 'value': 'Coastal Archive'},
                 {'type': 'IntegrationType', 'raw': {'name': 'Coastal Archive', 'doi': '10.1234/example'}},
                 {'type': 'IntegrationType', 'raw': {'name': 'Coastal Archive', 'id': 'bsg-s000001'}}]
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX + "{% include 'src/questions/10-share-restrictions.html.j2' %}")
            for kind, name, profile, publication in product(
                    ('DomainSpecific', 'GeneralPurpose'), names, ('review', 'submission'), ('Yes', 'No', None)):
                with self.subTest(escape=escape, kind=kind, name=name, profile=profile, publication=publication):
                    replies = support_replies(repository=kind, publication=publication)
                    base = path('preservingCUuid', 'producedDataQUuid', 'dataset-a', 'isPublishedDataQUuid',
                                'isPublishedDataYesAUuid', 'publishedDistrosQUuid', 'distro-0',
                                'publishedDataRepositoryKindQUuid', 'publishedDataRepository' + kind + 'AUuid')
                    field = 'domainSpecificRepoNameQUuid' if kind == 'DomainSpecific' else 'generalPurposeRepoNameQUuid'
                    if name is not None: replies[path(base, field)] = {'value': {'value': name}}
                    if kind == 'DomainSpecific':
                        replies[path(base, 'domainSpecificRepoContactBeforeQUuid')] = IDS['domainSpecificRepoContactBeforeYesAlreadyAUuid']
                    soup = BeautifulSoup(template.render(repliesMap=replies, output_profile=profile), 'html.parser')
                    arrangement = soup.select_one('.repository-arrangement')
                    if publication != 'Yes':
                        self.assertIsNone(arrangement)
                        self.assertNotIn('Coastal Archive', soup.get_text())
                        self.assertNotIn('We have already contacted the repository.', soup.get_text())
                        continue
                    self.assertIn('joined-policy', arrangement['class'])
                    sentence = arrangement.find('p', recursive=False)
                    self.assertIsNotNone(sentence)
                    category = 'domain-specific' if kind == 'DomainSpecific' else 'general-purpose'
                    destination = (f'This distribution will be deposited in the {category} repository Coastal Archive.'
                                   if name else f'This distribution will be deposited in a {category} repository.')
                    self.assertTrue(sentence.get_text().startswith(destination), sentence)
                    link = sentence.find('a')
                    if name and name['type'] == 'IntegrationType':
                        raw = name['raw']
                        self.assertEqual('Coastal Archive', link.get_text())
                        self.assertEqual('https://doi.org/' + raw['doi'] if 'doi' in raw else
                                         'https://fairsharing.org/' + raw['id'], link['href'])
                    else: self.assertIsNone(link)
                    if kind == 'DomainSpecific': self.assertIn('We have already contacted the repository.', sentence.get_text())
                    self.assertFalse(soup.select('p p, p div, p ul, p table'))
                    if profile == 'submission': self.assertFalse(soup.select('.data-gap, .data-review'))

    def test_dmp_creator_role_does_not_imply_implementation_or_revision(self):
        from itertools import product
        from bs4 import BeautifulSoup
        from current_support import environment, PREFIX
        from check_responsibility_reading import contributor_replies, ROLES, SENTENCES
        role_sets = ([ROLES[-1]], [ROLES[3], ROLES[-1]], ROLES, [ROLES[3]])
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX + "{% include 'src/questions/14-dm-responsible.html.j2' %}")
            for roles, name, profile in product(role_sets, ('Alex Chen', None), ('review', 'submission')):
                with self.subTest(escape=escape, roles=roles, name=name, profile=profile):
                    people = [('unassigned', None, []), ('author', name, roles)]
                    soup = BeautifulSoup(template.render(repliesMap=contributor_replies(people), output_profile=profile), 'html.parser')
                    owner = soup.select_one('.person-responsibilities')
                    self.assertEqual('author', owner['data-contributor-id'])
                    self.assertEqual('2', owner['data-contributor-index'])
                    actor = name or 'Contributor 2'
                    expected = ' '.join(sentence.format(actor=actor) for role, sentence in zip(ROLES, SENTENCES['en']) if role in roles)
                    text = owner.select_one('.responsibility-summary').get_text().strip()
                    self.assertEqual(expected, text)
                    self.assertEqual(ROLES[-1] in roles, f'{actor} is a creator of the data management plan.' in text)
                    for invented in ('implementing the data management plan', 'reviewed and revised'):
                        self.assertNotIn(invented, text)
                    self.assertEqual(profile == 'review' and not name, bool(owner.select('.data-gap')))
                    self.assertFalse(soup.select('p p, p div, p ul, p table'))

    def test_format_policies_preserve_question_scope_without_inventing_conversion(self):
        from itertools import product
        from bs4 import BeautifulSoup
        from current_support import IDS, path, environment, PREFIX
        formats = path('creatingCUuid', 'formatsQUuid')
        owner = path(formats, 'format-a')
        standard_path = path(owner, 'formatsIsStandardQUuid')
        suitable_path = path(owner, 'formatsIsLTSuitableQUuid')
        conversion_path = path(suitable_path, 'formatsIsLTSuitableNoAUuid', 'formatsConvertLTSuitableQUuid')
        why_path = path(standard_path, 'formatsIsStandardNoAUuid', 'formatsWhyNonStandardQUuid')
        reason = '<p>Keep Original.csv unchanged.</p><ul><li>Preserve <strong>original</strong> readings.</li></ul>'
        base = {formats: ['format-a'], path(owner, 'formatsNameQUuid'):
                {'value': {'value': {'type': 'PlainType', 'value': 'Original format'}}},
                path(owner, 'formatsVolumeQUuid'): IDS['formatsVolumeSmallAUuid'],
                why_path: IDS['formatsWhyNSAnotherReasonAUuid'],
                path(why_path, 'formatsWhyNSAnotherReasonAUuid', 'formatsWhyNSAnotherReasonQUuid'): reason}
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX + "{% include 'src/questions/02-what-data.html.j2' %}")
            for standard, suitable, conversion, profile in product(
                    (None, 'unknown', 'Yes', 'No'), (None, 'unknown', 'Yes', 'No'),
                    (None, 'unknown', 'Yes', 'No'), ('review', 'submission')):
                with self.subTest(escape=escape, standard=standard, suitable=suitable,
                                  conversion=conversion, profile=profile):
                    replies = dict(base)
                    for question, prefix, value in ((standard_path, 'formatsIsStandard', standard),
                            (suitable_path, 'formatsIsLTSuitable', suitable),
                            (conversion_path, 'formatsConvertLTSuitable', conversion)):
                        if value is not None: replies[question] = IDS.get(prefix + value + 'AUuid', value)
                    output = template.render(repliesMap=replies, output_profile=profile)
                    soup = BeautifulSoup(output, 'html.parser')
                    text = soup.select_one('.format-summary').get_text(' ', strip=True)
                    self.assertEqual(standard == 'Yes', 'It is a standard format widely used by researchers in this field' in text)
                    self.assertEqual(standard == 'No', 'This format is not a standard widely used by researchers in this field.' in text)
                    self.assertNotIn('We are not using a standardized format', text)
                    self.assertEqual(suitable == 'Yes', 'is suitable for sharing and long-term archiving.' in text)
                    self.assertEqual(suitable == 'No', 'not suitable for both sharing and long-term archiving' in text)
                    self.assertEqual(suitable == 'No' and conversion == 'Yes', 'we plan to convert' in text)
                    self.assertEqual(suitable == 'No' and conversion == 'No', 'we do not plan to convert' in text)
                    if suitable == 'No' and conversion in ('Yes', 'No'):
                        self.assertIn('to a format more suitable for archiving later.', text)
                    self.assertNotIn('before the end of the project', output)
                    self.assertEqual(int(standard == 'No'), output.count(reason))
                    for fact, missing in (('format-standard', standard not in ('Yes', 'No')),
                            ('format-archiving', suitable not in ('Yes', 'No')),
                            ('format-conversion', suitable == 'No' and conversion not in ('Yes', 'No'))):
                        gap = soup.select_one(f'[data-fact-id="{fact}"]')
                        self.assertEqual(profile == 'review' and missing, gap is not None)
                        if gap: self.assertEqual('missing', gap['data-status'])
                    if profile == 'submission': self.assertFalse(soup.select('.data-gap'))
            # A parent No denies the conjunction, not standardization alone.
            # Only explicit reasons justify the narrower non-standard claim.
            reason_path = path(why_path, 'formatsWhyNSAnotherReasonAUuid', 'formatsWhyNSAnotherReasonQUuid')
            for (why, body), profile in product(
                    ((None, ''), ('unknown', ''), ('ThereIsNoStandard', ''),
                     ('ItIsOptimized', ''), ('AnotherReason', ''), ('AnotherReason', reason)),
                    ('review', 'submission')):
                with self.subTest(escape=escape, why=why, authored=bool(body), profile=profile):
                    replies = {**base, standard_path: IDS['formatsIsStandardNoAUuid'], reason_path: body}
                    if why is None: replies.pop(why_path)
                    else: replies[why_path] = IDS.get('formatsWhyNS' + why + 'AUuid', why)
                    output = template.render(repliesMap=replies, output_profile=profile)
                    soup = BeautifulSoup(output, 'html.parser')
                    text = soup.select_one('.format-summary').get_text(' ', strip=True)
                    explicit = why in ('ThereIsNoStandard', 'ItIsOptimized')
                    self.assertEqual(explicit, 'We are not using a standardized format' in text)
                    self.assertEqual(not explicit, 'This format is not a standard widely used by researchers in this field.' in text)
                    self.assertEqual(int(why == 'AnotherReason' and bool(body)), output.count(reason))
                    if why == 'AnotherReason' and body:
                        self.assertEqual('Reason for choosing this format:', soup.select_one(
                            '[data-fact-id="nonstandard-reason"] .answer-lead').get_text())
                    gap = soup.select_one('[data-fact-id="nonstandard-reason"][data-status="missing"]')
                    self.assertEqual(profile == 'review' and not explicit and not body, gap is not None)
                    if gap: self.assertEqual('reason for choosing this format', gap.get_text())

    def test_identifier_repository_labels_are_plain_below_dataset_boundaries(self):
        from bs4 import BeautifulSoup
        from current_support import identifier_replies
        repositories = [('DomainSpecific', 'Domain-specific repository'),
                        ('GeneralPurpose', 'General-purpose repository'),
                        ('National', 'National repository'),
                        ('Institutional', 'Institutional repository'),
                        ('Special', 'Special-purpose repository')]
        for kind, label in repositories:
            for count in (1, 2):
                for profile in ('review', 'submission'):
                    with self.subTest(repository=kind, count=count, profile=profile):
                        soup = BeautifulSoup(render_question(
                            'src/questions/13-persistent-identifier.html.j2',
                            identifier_replies(repository=kind, count=count),
                            output_profile=profile), 'html.parser')
                        dataset = soup.select_one('.dataset-section[data-item-id="dataset-a"]')
                        self.assertIsNotNone(dataset.select_one('h5'))
                        distributions = dataset.select('.distribution-section')
                        self.assertEqual(count, len(distributions))
                        for index, distribution in enumerate(distributions, 1):
                            labels = distribution.select('.identifier-heading > p.answer-lead')
                            if count > 1:
                                self.assertEqual(2, len(labels))
                                self.assertEqual(label, labels[-1].get_text(' ', strip=True))
                                self.assertFalse(labels[-1].select('strong,b,h1,h2,h3,h4,h5,h6'))
                                self.assertEqual(f'Distribution {index}', labels[0].strong.get_text(strip=True))
                            else:
                                self.assertFalse(labels)
                                sentence = distribution.select_one('.identifier-arrangement').get_text(' ', strip=True)
                                self.assertEqual(f'The {label.lower()} will assign the persistent identifier and ensure that it resolves to a digital object.', sentence)
                            for fact in ('persistent-identifier', 'identifier-assigner', 'identifier-resolution'):
                                self.assertEqual('complete', distribution.select_one(
                                    f'[data-fact-id="{fact}"]')['data-status'])

    def test_reference_version_flows_without_an_outer_information_table(self):
        from bs4 import BeautifulSoup
        from current_support import IDS, path
        reused = path('reusingCUuid', 'preexistingQUuid')
        listing = path(reused, 'preexistingYesAUuid', 'refDataQUuid')
        used = path(listing, 'record', 'refDataUseQUuid')
        version = path(used, 'refDataUseYesAUuid', 'refDataVersionedQUuid')
        value = path(version, 'refDataVersionedYesAUuid', 'refDataVersionedWhichQUuid')
        policy = path(version, 'refDataVersionedYesAUuid', 'refDataVersionedChangeQUuid')
        base = {reused: IDS['preexistingYesAUuid'], listing: ['record'],
                used: IDS['refDataUseYesAUuid'], version: IDS['refDataVersionedYesAUuid'],
                policy: IDS['refDataVersionedChangeStayAUuid']}
        # The body adapter supplies exact HTML, not proof of native conversion.
        bodies = [('<p>2.1</p>', True), ('<p>版本 &lt;2 &amp; v1.2</p>', True),
                  ('<p>' + 'Original version note. ' * 80 + '</p>', False),
                  ('<p><strong>2.1</strong> <code>v2</code></p>', False),
                  ('<p><a href="https://example.org/?a=1&amp;b=2">2.1</a></p>', False),
                  ('<ul><li>2.1</li><li>Original note.</li></ul>', False),
                  ('<p class="original">2.1</p>', False), ('<p></p>', False), ('<p>   </p>', False),
                  ('<p>2.1\nOriginal note.</p>', False),
                  ('<p>Version opening.</p><table><tbody><tr><td>Original revision.</td>'
                   '<td>Original evidence.</td></tr></tbody></table><p>Version ending.</p>', False)]
        for profile in ('submission', 'review'):
            for body, compact in bodies:
                with self.subTest(profile=profile, body=body[:30]):
                    output = render_question('src/questions/01-how-data.html.j2',
                                             {**base, value: body}, output_profile=profile)
                    soup = BeautifulSoup(output, 'html.parser')
                    detail = soup.select_one('div.dataset-version[data-fact-id="dataset-version"]')
                    self.assertIsNotNone(detail)
                    self.assertEqual('complete', detail['data-status'])
                    self.assertIsNone(detail.find_parent('table'))
                    self.assertFalse(soup.select('table.dataset-version'))
                    if compact:
                        self.assertIsNone(detail.find('div', recursive=False))
                        self.assertEqual(1, len(detail.find_all('p', recursive=False)))
                        self.assertEqual('Version:', detail.p.strong.get_text())
                        self.assertTrue(str(detail.p).endswith(body[3:]))
                    else:
                        lead = detail.find('div', recursive=False)
                        self.assertEqual(['answer-lead'], lead['class'])
                        self.assertEqual('Version', lead.get_text())
                        # Scope the normalized DOM check, and check original bytes separately.
                        self.assertEqual(1, detail.decode_contents().count(str(BeautifulSoup(body, 'html.parser'))))
                        self.assertIn(body, output)
                    if '<table>' in body:
                        self.assertEqual(detail, detail.table.parent)
                    self.assertIn('the current version will continue to be used.',
                                  detail.find_next_sibling('p').get_text())
                    self.assertIn('the current version will continue to be used.', output)
            # The decision follows rendered Markdown, not a short raw source.
            from current_support import environment, PREFIX
            from markupsafe import Markup
            for escape in (False, True):
                env = environment(ROOT, escape)
                template = env.from_string(PREFIX + "{% include 'src/questions/01-how-data.html.j2' %}")
                for body, compact in bodies:
                    env.filters['markdown'] = lambda source: Markup(body)
                    output = template.render(repliesMap={**base, value: 'v2'}, output_profile=profile)
                    detail = BeautifulSoup(output, 'html.parser').select_one('.dataset-version')
                    self.assertEqual(compact, detail.find('div', recursive=False) is None)
                    if compact: self.assertTrue(str(detail.p).endswith(body[3:]))
                    else:
                        self.assertEqual(1, detail.decode_contents().count(str(BeautifulSoup(body, 'html.parser'))))
                        self.assertIn(body, output)
            for missing in (None, '', ' \t\n\u3000'):
                values = dict(base)
                if missing is not None: values[value] = missing
                output = render_question('src/questions/01-how-data.html.j2', values,
                                         output_profile=profile)
                soup = BeautifulSoup(output, 'html.parser')
                self.assertFalse(soup.select('.dataset-version'))
                self.assertEqual(profile == 'review', bool(soup.select('[data-fact-id="dataset-version"]')))
                self.assertIn('the current version will continue to be used.', output)
            for stale in ('missing-version-selector', 'not-reused'):
                values = {**base, value: bodies[-1][0]}
                if stale == 'missing-version-selector': del values[version]
                else: values[used] = IDS['refDataUseNoAUuid']
                output = render_question('src/questions/01-how-data.html.j2', values,
                                         output_profile=profile)
                self.assertNotIn('Original revision.', output)
                self.assertFalse(BeautifulSoup(output, 'html.parser').select('.dataset-version'))

    def test_single_instrument_keeps_owner_ordinals_and_authored_blocks(self):
        from bs4 import BeautifulSoup
        from current_support import IDS, path, environment, PREFIX
        measured = path('creatingCUuid', 'measuredQUuid')
        datasets = path(measured, 'measuredYesAUuid', 'measuredDataQUuid')
        owner = path(datasets, 'first')
        instruments = path(owner, 'measuredDataInstrQUuid')
        base = {measured: IDS['measuredYesAUuid'], datasets: ['first', 'second'],
                path(datasets, 'second', 'measuredDataNameQUuid'): 'Other dataset',
                path(owner, 'measuredDataQualityQUuid'): IDS['measuredDataQualityYesAUuid'],
                path(owner, 'measuredDataQualityQUuid', 'measuredDataQualityYesAUuid',
                     'mdQualityCalibratingQUuid'): IDS['mdQualityCalibratingYesAUuid']}
        bodies = ['', '<p>Keep Original.csv, exactly!</p>',
                  '<p>Original opening.</p><ul><li>Keep <strong>A</strong>.</li></ul>',
                  '<p><a href="https://example.org/?a=1&amp;b=2">Original link</a></p>',
                  '<table><tbody><tr><td>Original value</td></tr></tbody></table>']
        for escape in (False, True):
            template = environment(ROOT, escape).from_string(PREFIX + "{% include 'src/questions/01-how-data.html.j2' %}")
            for profile in ('review', 'submission'):
                for named in (False, True):
                    for name in ('Sensor A', '', '<img src="not-a-picture">'):
                        for body in bodies:
                            values = {**base, instruments: ['instrument'],
                                      path(instruments, 'instrument', 'measuredDataInstrNameQUuid'): name,
                                      path(instruments, 'instrument', 'measuredDataInstrDescQUuid'): body}
                            if named: values[path(owner, 'measuredDataNameQUuid')] = 'Dataset A'
                            output = template.render(repliesMap=values, output_profile=profile)
                            soup = BeautifulSoup(output, 'html.parser')
                            item = soup.select_one(f'.dataset-section[data-item-id="{owner}"]')
                            single = item.select_one('.single-instrument')
                            self.assertEqual(bool(name or body), bool(single))
                            self.assertEqual(2, len(soup.select('#q-how-data > .answer > .dataset-list > .dataset-section')))
                            self.assertIsNone(item.find_parent('ul'))
                            self.assertEqual('Dataset A' if named else 'Instrument dataset 1' if profile == 'submission'
                                             else '(no name given)', item.h5.get_text(' ', strip=True))
                            if single:
                                self.assertIsNone(single.find('ul', recursive=False))
                                self.assertFalse(single.select('img'))
                                self.assertEqual(name or 'Instrument 1', single.p.strong.get_text())
                                self.assertEqual(bool(body), bool(single.select('.answer-detail')))
                                if body: self.assertEqual(body, single.select_one('.answer-detail').decode_contents())
                            self.assertFalse(soup.select('p p,p div,p ul,p table'))
                            self.assertEqual(1 if named else 0, item.get_text().count('Dataset A'))
                            if profile == 'submission': self.assertFalse(soup.select('.data-gap'))
            # One visible row from a longer source list retains its original list/ordinal.
            values = {**base, instruments: ['empty', 'partial'],
                      path(instruments, 'partial', 'measuredDataInstrDescQUuid'): '<p>Original detail.</p>'}
            soup = BeautifulSoup(template.render(repliesMap=values, output_profile='submission'), 'html.parser')
            self.assertFalse(soup.select('.single-instrument'))
            self.assertIn('Instrument 2', soup.select_one(f'.dataset-section[data-item-id="{owner}"] > ul > li').get_text())
            self.assertIn('Original detail.', soup.get_text())

    def test_shared_reference_rules_keep_individual_purposes_and_versions(self):
        events = json.loads((ROOT / "fixtures/pilot/en/populated.events.json").read_text())
        replies = {event["path"]: event["value"]["value"] for event in events}
        source = (ROOT / "src/uuids.j2").read_text()
        def uuid(name):
            return re.search(rf'set {name} = "([^"]+)"', source)[1]
        output = render_question("src/questions/01-how-data.html.j2", replies)
        self.assertEqual(1, output.count('class="shared-reference-policy"'))
        from lxml import html as dom
        shared = dom.fromstring(output).xpath('//div[@class="shared-reference-policy"]')[0]
        self.assertEqual([node.tag for node in shared[:2]], ['p', 'div'])
        self.assertEqual(shared[1].get('class'), 'answer-lead')
        self.assertEqual(shared[1].text_content(), 'The following arrangements apply to all reference datasets selected for re-use above.')
        self.assertNotEqual(shared[2].get('class'), 'answer-lead', 'Keep only the owned scope sentence, not the whole policy')
        self.assertEqual(1, output.count("We will retain a copy"))
        self.assertEqual(2, output.count('data-fact-id="reuse-purpose"'))
        self.assertEqual(2, output.count('data-fact-id="dataset-version"'))
        conditions = [path for path in replies if path.endswith(uuid("refDataConditionsQUuid"))]
        self.assertEqual(2, len(conditions))
        replies[conditions[1]] = uuid("refDataConditionsCC0AUuid")
        distinct = render_question("src/questions/01-how-data.html.j2", replies)
        self.assertNotIn('class="shared-reference-policy"', distinct)
        self.assertEqual(2, distinct.count("We will retain a copy"))
        self.assertIn("freely available for any use", distinct)
        self.assertIn("obligation to cite the source", distinct)
        del replies[conditions[1]]
        unknown = render_question("src/questions/01-how-data.html.j2", replies)
        self.assertNotIn('class="shared-reference-policy"', unknown)

    def test_empty_answers_do_not_leave_empty_titles_or_promise_other_answers(self):
        for filename in (
            "03-docs-metadata", "06-access-security", "07-personal-data",
            "09-ethical-issues", "10-share-restrictions", "11-data-preservation",
            "12-access-data", "13-persistent-identifier", "04-quality-control",
            "08-copyright-ipr", "14-dm-responsible",
        ):
            with self.subTest(question=filename):
                result = render_question(f"src/questions/{filename}.html.j2", {})
                self.assertIn('data-status="missing-output"', result)
                self.assertNotIn("described in Section", result)
                self.assertNotIn("are documented under Section", result)
                self.assertNotIn("There are no published data", result)
                self.assertNotIn("<h4>", result)

    def test_question_ids_are_unique(self):
        ids = []
        for requirement in CONTRACT["requirements"]:
            text = (ROOT / requirement["template"]).read_text()
            ids.append(re.search(r'<div id="([^"]+)" class="question"', text)[1])
        self.assertEqual(len(ids), len(set(ids)))

    def test_empty_funding_is_not_a_negative_answer(self):
        source = (ROOT / "src/projects.html.j2").read_text()
        self.assertNotIn("Did not apply", source)
        self.assertIn("Funding information has not been provided.", source)

    def test_all_six_sections_and_fifteen_questions_are_tracked(self):
        requirements = CONTRACT["requirements"]
        self.assertEqual(15, len(requirements))
        self.assertEqual(list(range(1, 16)), [item["number"] for item in requirements])
        self.assertEqual(
            [
                "SE-1a", "SE-1b", "SE-2a", "SE-2b", "SE-3a", "SE-3b",
                "SE-4a", "SE-4b", "SE-4c", "SE-5a", "SE-5b", "SE-5c",
                "SE-5d", "SE-6a", "SE-6b",
            ],
            [item["id"] for item in requirements],
        )
        self.assertEqual(6, len({item["section"] for item in requirements}))

    def test_template_headings_match_the_recorded_science_europe_questions(self):
        from bs4 import BeautifulSoup
        # Reviewed display decomposition; the independent official questions
        # below and in requirements stay unchanged, including every example.
        split_questions = {
            13: (
                'How will the application of a unique and persistent identifier (such as a Digital Object Identifier (DOI)) to each data set be ensured?',
                '13. How will you ensure that each dataset is assigned a unique and persistent identifier?',
                'A Digital Object Identifier, or DOI, is one example.'),
            14: (
                'Who (for example role, position, and institution) will be responsible for data management (i.e. the data steward)?',
                '14. Who will be responsible for data management?',
                'This refers to the data steward. Details may include their role, position, and institution.'),
            15: (
                'What resources (for example financial and time) will be dedicated to data management and ensuring that data will be FAIR (Findable, Accessible, Interoperable, Re-usable)?',
                '15. What resources will be dedicated to data management and ensuring that the data are FAIR?',
                'Resources may include funding and time. FAIR means Findable, Accessible, Interoperable, and Re-usable.'),
        }
        for requirement in CONTRACT["requirements"]:
            # Compare the actual default-English heading, not the gettext call
            # in marked source. The independent recorded questions stay exact.
            document = BeautifulSoup(render_question(requirement["template"], {}), 'html.parser')
            match = document.select_one('.question > h3')
            self.assertIsNotNone(match, requirement["template"])
            heading = " ".join(match.get_text().split())
            expected = f'{requirement["number"]}. {requirement["question"]}'
            if requirement['number'] in split_questions:
                official, expected, explanation = split_questions[requirement['number']]
                self.assertEqual(official, requirement['question'])
                guidance = document.select_one('.question > .question-guidance')
                self.assertIsNotNone(guidance)
                self.assertEqual([node.name for node in guidance.find_all(recursive=False)], ['p'])
                self.assertEqual(explanation, guidance.get_text())
                self.assertEqual(guidance, match.find_next_sibling())
                self.assertIn('answer', guidance.find_next_sibling()['class'])
            else:
                self.assertIsNone(document.select_one('.question-guidance'))
            self.assertEqual(expected, heading, requirement["id"])

    def test_experiment_bindings_exist_or_are_explicitly_unmapped(self):
        uuid_source = (ROOT / "src" / "uuids.j2").read_text(encoding="utf-8")
        for requirement in CONTRACT["requirements"]:
            if requirement["implementationStatus"] != "experiment":
                continue
            template_source = (ROOT / requirement["template"]).read_text(encoding="utf-8")
            self.assertIn(f'data-requirement-id="{requirement["id"]}"', template_source)
            for fact in requirement["facts"]:
                if fact["coverage"] == "unmapped":
                    self.assertEqual([], fact["dswBindings"])
                    continue
                for binding in fact["dswBindings"]:
                    self.assertRegex(uuid_source, rf"set\s+{re.escape(binding)}\s*=")

    def test_unanswered_se_1a_is_visible_and_not_rendered_as_no(self):
        output = render_question("src/questions/01-how-data.html.j2", {})
        self.assertIn('data-fact-id="new-data" data-status="missing"', output)
        self.assertIn('data-fact-id="reuse-sources" data-status="missing"', output)
        self.assertIn('data-fact-id="provenance" data-status="missing"', output)
        self.assertNotIn("No new instrument datasets", output)
        self.assertNotIn("No relevant pre-existing datasets", output)

    def test_explicit_no_is_distinct_from_unanswered_for_se_1a(self):
        replies = {
            "b1df3c74-0b1f-4574-81c4-4cc2d780c1af.f87c331d-794a-42c8-a910-61a2a9110dab": "8d384c38-653a-476c-bda1-47ab7d38c9c2",
            "82fd0cce-2b41-423f-92ad-636d0872045c.efc80cc8-8318-4f8c-acb7-dc1c60e491c1": "72cdbc99-2707-4817-ac40-435a03e5e837",
        }
        output = render_question("src/questions/01-how-data.html.j2", replies)
        self.assertIn('data-fact-id="new-data" data-status="explicit-no"', output)
        self.assertIn('data-fact-id="reuse-sources" data-status="explicit-no"', output)
        self.assertNotIn('data-fact-id="new-data" data-status="missing"', output)
        self.assertNotIn('data-fact-id="reuse-sources" data-status="missing"', output)

    def test_unanswered_se_3a_keeps_the_whole_requirement_visible(self):
        output = render_question("src/questions/05-store-backup.html.j2", {})
        for fact_id in ("working-storage-arrangement", "backup-arrangement"):
            self.assertIn(f'data-fact-id="{fact_id}" data-status="missing"', output)
        for fact_id in ("storage-location", "backup-frequency"):
            self.assertIn(f'data-fact-id="{fact_id}" data-status="unmapped"', output)

    def test_explicit_backup_problem_is_not_reported_as_unanswered(self):
        replies = {
            "10a10ffd-bfe1-4c6b-bbb6-3dfb1e63a5d5.72099c46-16e7-47a2-a320-cc768b7085fe": "1d6ba101-fd62-43c8-ab53-76bc31847f58",
            "10a10ffd-bfe1-4c6b-bbb6-3dfb1e63a5d5.72099c46-16e7-47a2-a320-cc768b7085fe.1d6ba101-fd62-43c8-ab53-76bc31847f58.c1e83bdf-5914-44c2-8414-0a4e7fbaf272": "0c93a407-b04a-4c89-a8e4-299a4d77c21e",
        }
        output = render_question("src/questions/05-store-backup.html.j2", replies)
        self.assertIn('data-fact-id="backup-reliability" data-status="explicit-no"', output)
        self.assertNotIn('data-fact-id="backup-reliability" data-status="missing"', output)

    def test_partial_se_6b_keeps_present_answers_and_marks_missing_costs(self):
        replies = {
            "1e85da40-bbfc-4180-903e-6c569ed2da38.83c0d09d-e74c-4c81-a52c-aaa2e18415ac": "ccdadd45-8aa9-44ed-a669-1827c7813b0a",
            "1e85da40-bbfc-4180-903e-6c569ed2da38.09c7c989-6461-417f-b09e-228491c051c6": "f4da7f1d-f3c6-42e2-a7b5-41c4845ba352",
        }
        output = render_question("src/questions/15-required-resources.html.j2", replies)
        self.assertIn('data-fact-id="specialist-expertise" data-status="explicit-no"', output)
        self.assertIn('data-fact-id="hardware-software" data-status="explicit-no"', output)
        self.assertIn('data-fact-id="resources-costing" data-status="missing"', output)

    def test_populated_se_6b_cost_item_has_no_missing_markers(self):
        admin = "1e85da40-bbfc-4180-903e-6c569ed2da38"
        projects = f"{admin}.c3dabaaf-c946-4a0d-889c-ede966f97667"
        project = f"{projects}.project-1"
        costs = f"{project}.353eeaca-45fa-4958-a33c-ec6de3075701"
        cost = f"{costs}.cost-1"
        cover = f"{cost}.46cd176a-138a-4f6c-8cd5-dfcb1f23f04a"
        replies = {
            f"{admin}.83c0d09d-e74c-4c81-a52c-aaa2e18415ac": "ccdadd45-8aa9-44ed-a669-1827c7813b0a",
            f"{admin}.09c7c989-6461-417f-b09e-228491c051c6": "f4da7f1d-f3c6-42e2-a7b5-41c4845ba352",
            projects: ["project-1"],
            f"{project}.f0ef08fd-d733-465c-bc66-5de0b826c41b": "Example project",
            costs: ["cost-1"],
            f"{cost}.7098b454-bc5e-4f83-a95d-970aa42e1479": "Data curator time",
            f"{cost}.b3d9b6ca-bd24-4fa3-a3bd-d15005b9ae8b": "Prepare and document data for deposit",
            f"{cost}.ac1f8f04-17a2-49e9-b2ad-2a9f8e44efb3": {
                "value": {"value": {"type": "PlainType", "value": "EUR"}}
            },
            f"{cost}.e53fdad9-7799-4eb4-8b4d-fa9aa05f9d2d": "5000",
            f"{cost}.028909e8-7392-4385-96a3-467d79c43a42": [
                "350a6e85-d4b2-4a44-831d-4562e5668208",
                "d2a9d717-c0b2-44ee-8a6d-8476831b6225",
            ],
            cover: "2e37f71b-b7aa-4182-888a-8b7a5156b53c",
            f"{cover}.2e37f71b-b7aa-4182-888a-8b7a5156b53c.2964c7f7-d9be-42ac-8cfe-dbcf4d62f8a2": "institutional funds",
        }
        km, _ = project_fixture(None, 'Example project', 'project-1')
        from check_answer_mapping import question
        from current_support import IDS
        children = km['entities']['questions'][IDS['projectsQUuid']]['itemTemplateQuestionUuids']
        children = question(km, children, IDS['costQUuid'], 'ListQuestion')['itemTemplateQuestionUuids']
        for field in ('costTitleQUuid', 'costDescriptionQUuid', 'costAmountQUuid'):
            question(km, children, IDS[field], 'ValueQuestion')
        question(km, children, IDS['costCurrencyQUuid'], 'IntegrationQuestion')
        question(km, children, IDS['costAllocationQUuid'], 'MultiChoiceQuestion',
                 [IDS['costAllocation' + option + 'AUuid'] for option in
                  ('Findability', 'Accessibility', 'Interoperability', 'Reusability')] + [IDS['costManagementAUuid']])
        question(km, children, IDS['costCoverQUuid'], 'OptionsQuestion',
                 [IDS['costCoverGrantAUuid'], IDS['costCoverOtherAUuid']])
        for option, field in (('Grant', 'costCoverGrantIdQUuid'), ('Other', 'costCoverOtherHowQUuid')):
            question(km, km['entities']['answers'][IDS['costCover' + option + 'AUuid']]['followUpUuids'],
                     IDS[field], 'ValueQuestion')
        output = render_question("src/questions/15-required-resources.html.j2", replies, km=km)
        self.assertIn("Data curator time", output)
        self.assertIn("5000 EUR", output)
        self.assertIn('class="resource-table"', output)
        self.assertNotIn('data-fact-id="resource-amount" data-status="missing"', output)
        self.assertNotIn('data-fact-id="cost-coverage" data-status="missing"', output)


if __name__ == "__main__":
    unittest.main()
