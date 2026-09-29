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
REPOSITORY_COMPOUND = {
    'english': {
        'Yes': 'The repository will assign the persistent identifier and ensure that it resolves to a digital object.',
        'No': 'The repository will assign the persistent identifier but will not guarantee that it resolves to a digital object.',
    },
    'chinese': {
        'Yes': '儲存庫將指派持續識別碼，並確保該識別碼能解析至數位物件。',
        'No': '儲存庫將指派持續識別碼，但不保證該識別碼能解析至數位物件。',
    },
}
RESOLUTIONS = {
    'english': {
        'Yes': 'The repository will make sure the persistent identifier can be resolved to a digital object.',
        'No': 'The repository will not make sure the persistent identifier can be resolved to a digital object.',
    },
    'chinese': {
        'Yes': '資料儲存庫將確保持續識別碼可解析至數位物件。',
        'No': '資料儲存庫將不保證持續識別碼可解析至數位物件。',
    },
}


def expected(before, language, repository_compound=False):
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
        resolution = next((node for node in children[2:]
                           if node.name == 'p' and node.get('data-fact-id') == 'identifier-resolution'), None)
        repository = actor.get_text() == ASSIGNERS[language][-1]
        resolution_choice = next((key for key, text in RESOLUTIONS[language].items()
                                  if resolution is not None and resolution.get_text() == text), None)
        actor.name = 'span'
        if repository_compound and repository and resolution_choice:
            status = 'complete' if resolution_choice == 'Yes' else 'explicit-no'
            assert resolution.attrs == {
                'data-requirement-id': 'SE-5d', 'data-fact-id': 'identifier-resolution',
                'data-status': status,
            }
            resolution.name = 'span'
            resolution.clear()
            resolution.append(REPOSITORY_COMPOUND[language][resolution_choice])
            actor.clear()
            actor.append(resolution.extract())
        first.clear()
        first.append(actor.extract())
        changed += 1
    return result, changed


def compare(before, after, language, repository_compound=False):
    result, count = expected(before, language, repository_compound)
    assert dom(result) == dom(after), 'Unexpected HTML, fact, wording or scope edit'
    return count
