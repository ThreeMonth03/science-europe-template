"""Only remove the redundant affirmative sentence when a known assigner states it."""
import copy
from bs4 import BeautifulSoup
from probe_pdf_budget_reading import dom

AFFIRMATIVE = {'english': 'Persistent identifiers will be assigned.', 'chinese': '資料將取得持續識別碼。'}
ASSIGNERS = {
    'english': ['A project data steward or principal investigator will assign the persistent identifier.',
                'An institutional data steward will assign the persistent identifier.',
                'The repository will assign the persistent identifier.'],
    'chinese': ['持續識別碼將由計畫的資料託管員或主持人指派。', '持續識別碼將由機構的資料託管員指派。',
                '持續識別碼將由資料儲存庫指派。'],
}


def expected(before, language):
    result = copy.deepcopy(before)
    changed = 0
    for policy in result.select('#q-persistent-identifier .identifier-arrangement'):
        children = policy.find_all(recursive=False)
        first = children[0]
        assert first.name == 'p' and first.attrs == {'data-fact-id': 'persistent-identifier', 'data-status': 'complete'}
        assert first.get_text() == AFFIRMATIVE[language] and not first.find(True)
        assigners = policy.select('[data-fact-id="identifier-assigner"]')
        if not assigners:
            continue
        assert len(assigners) == 1
        actor = assigners[0]
        assert actor is children[1] and actor.name == 'p' and not actor.find(True)
        assert actor.attrs == {'data-requirement-id': 'SE-5d', 'data-fact-id': 'identifier-assigner', 'data-status': 'complete'}
        assert actor.get_text() in ASSIGNERS[language]
        actor.name = 'span'
        first.clear()
        first.append(actor.extract())
        changed += 1
    return result, changed


def compare(before, after, language):
    result, count = expected(before, language)
    assert dom(result) == dom(after), 'Unexpected HTML, fact, wording or scope edit'
    return count
