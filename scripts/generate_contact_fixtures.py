"""Reachable Other-contact answers: rich text, missing, and identical distinct fields."""
import copy
import json
from generate_pilot_fixtures import ROOT, IDS, path, uid
from generate_answer_state_fixtures import answer_state_cases


def contact_case(language):
    replies = copy.deepcopy(answer_state_cases(language)['support-mixed'])
    data = path('preservingCUuid', 'producedDataQUuid')
    first, second = replies[data]['value']
    text = ('Contact the repository directly to confirm its deposit requirements.' if language == 'en'
            else '先直接聯繫儲存庫，確認資料接收條件。')
    rich = text + '\n\n' + ('Keep Contact-2027.csv unchanged.' if language == 'en' else '保留原始檔名 Contact-2027.csv。')
    rich += '\n\n- Contact-list-2027.csv\n- https://example.org/contact/review\n\n| Record | Owner |\n| --- | --- |\n| Contact-table-2027.csv | Review team |'
    repeated = 'Same-contact-2027.csv'
    for item, values in [(first, [rich, None, repeated]), (second, [repeated])]:
        pub = path(data, item, 'isPublishedDataQUuid')
        replies[pub] = {'type': 'AnswerReply', 'value': IDS['isPublishedDataYesAUuid']}
        if item == second:
            for key in list(replies):
                if key.startswith(pub + '.'): replies.pop(key)
            replies[path(data, item, 'producedDataNameQUuid')] = copy.deepcopy(replies[path(data, first, 'producedDataNameQUuid')])
        dist = path(pub, 'isPublishedDataYesAUuid', 'publishedDistrosQUuid')
        if item == second:
            replies[dist] = {'type': 'ItemListReply', 'value': [uid('contact-mixed/second/distribution')]}
        for distro, value in zip(replies[dist]['value'], values):
            kind = path(dist, distro, 'publishedDataRepositoryKindQUuid')
            for key in list(replies):
                if key.startswith(kind + '.'): replies.pop(key)
            replies[kind] = {'type': 'AnswerReply', 'value': IDS['publishedDataRepositoryDomainSpecificAUuid']}
            contact = path(kind, 'publishedDataRepositoryDomainSpecificAUuid', 'domainSpecificRepoContactBeforeQUuid')
            replies[contact] = {'type': 'AnswerReply', 'value': IDS['domainSpecificRepoContactBeforeOtherAUuid']}
            if value is not None:
                replies[path(contact, 'domainSpecificRepoContactBeforeOtherAUuid', 'domainSpecificRepoContactBeforeOtherQUuid')] = {'type': 'StringReply', 'value': value}
    return replies


if __name__ == '__main__':
    for language in ['en', 'zh-Hant']:
        folder = ROOT / 'fixtures/pilot' / language
        replies = contact_case(language)
        events = [{'type': 'SetReplyEvent', 'uuid': uid(f'contact-mixed/{p}'), 'path': p, 'value': v}
                  for p, v in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
        (folder / 'contact-mixed.events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        recipe = json.loads((folder / 'structured.json').read_text())
        recipe.update(name='Science Europe repository contact / contact-mixed', events_file='contact-mixed.events.json')
        (folder / 'contact-mixed.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
