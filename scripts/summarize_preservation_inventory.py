"""Extract a bounded, bilingual binding contract from a previously recorded full inventory."""
import argparse
import hashlib
import json
from pathlib import Path
from generate_pilot_fixtures import IDS

SELECTED = ['producedDataDescriptionQUuid', 'producedDataStageQUuid', 'producedDataPaperQUuid',
            'notPublishedReasonQUuid', 'notPublishedReasonOtherQUuid', 'archivedAfterQUuid',
            'archivedAfterPayerQUuid', 'archivedAfterPeriodQUuid', 'archivedAfterYearsQUuid',
            'archivedAfterPeriodOtherQUuid', 'archivedAfterExtendQUuid', 'archivedAfterExtendNoReasonQUuid',
            'archivedAfterExtendWhoQUuid', 'archivedAfterExtendBasisQUuid', 'archivedAfterFormatsQUuid',
            'archivedAfterMediaQUuid']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Never overwrite an earlier mapping record'
    raw = json.loads(args.inventory.read_text()); languages = {}
    for lang, km in raw['knowledge_models'].items():
        by_id = {q['uuid']: q for q in km['questions']}
        selected = {name: by_id[IDS[name]] for name in SELECTED}
        languages[lang] = {'km_sha256': km['km_sha256'], 'inventory_question_count': km['reachable_question_count'],
                           'selected_questions': selected}
    report = {'schema_version': 1, 'scope': 'Selected Q11 additions; static before-state, not DMP completeness',
              'inventory_sha256': hashlib.sha256(args.inventory.read_bytes()).hexdigest(),
              'inventory_checker_sha256': raw['checker_sha256'], 'source_commit': raw['source_commit'],
              'source_template_sha256': raw['template_sha256'], 'knowledge_models': languages,
              'limits': ['These 16 questions were not referenced by the recorded source templates',
                         'A publication decision is not a preservation selection decision',
                         'Post-project cold storage is project-wide, not per produced dataset',
                         'Renewal criteria are not a full initial data-selection policy']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'selected_questions_per_language': len(SELECTED)}))


if __name__ == '__main__': main()
