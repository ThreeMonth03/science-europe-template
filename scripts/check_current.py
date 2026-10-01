"""One entry point for current EN/ZH behaviour; no historical-source projection."""
import argparse
import importlib
import json
from pathlib import Path
import time
import traceback

from current_support import ROOT

SUITES = {
    'answer_mapping': dict(research_combinations=1024, inactive_branches=10, owner_cases=48, full_documents=4, authorization_cases=180),
    'sentence_layout': dict(nonreuse_cases=448, inactive_cases=24, inline_cases=4, missing_name_cases=16, quality_other_cases=140,
                            reference_identity_cases=384, instrument_cases=36, missing_detail_cases=80),
    'responsibility_reading': dict(role_subsets=512, identity_cases=32, missing_name_cases=12, full_documents=4),
    'access_reading': dict(access_cases=384, software_cases=64, software_followups=128, inactive_software=32,
                          identifier_cases=960, reuse_cases=300, inactive_reuse=44, reuse_identity=4,
                          identity_cases=4, full_documents=4),
    'project_acronym': dict(value_cases=108, inactive_cases=40, identity_cases=4, full_documents=4,
                           funding_cases=1080, inactive_funding=36, funding_identity=4,
                           project_values=96, project_titles=64, project_subsets=32,
                           inactive_overview=100, header_metadata=8, project_identity=4, budget_identity=144),
    'ethics_reading': dict(dataset_cases=320, approval_cases=960, identity_cases=4, full_documents=4),
    'publication_reading': dict(summary_cases=1792, record_cases=4, identifier_cases=336, full_documents=4),
    'repository_profiles': dict(repository_cases=2240, preservation_cases=320, inactive_preservation=112,
                               identity_cases=8, full_documents=8),
}


def run_suite(name, root, language):
    start = time.monotonic()
    counts = importlib.import_module('check_' + name).check(root, language)
    assert counts == SUITES[name], (name, 'Unexpected coverage', counts)
    return dict(suite=name, language=language, cases=sum(counts.values()), seconds=round(time.monotonic()-start, 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--root', type=Path, default=ROOT)
    source.add_argument('--build', type=Path, help='Prepared bilingual build containing en/ and translated/')
    parser.add_argument('--language', choices=['en', 'zh-Hant'], default='en')
    parser.add_argument('--suite', choices=SUITES, action='append', help='Repeat to run only selected suites')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    targets = [(args.build/'en', 'en'), (args.build/'translated', 'zh-Hant')] if args.build else [(args.root, args.language)]
    report = dict(passed=True, release_acceptance=False, rows=[], failures=[])
    for root, language in targets:
        for name in args.suite or SUITES:
            try:
                row = dict(passed=True, **run_suite(name, root.resolve(), language))
            except Exception as exc:
                row = dict(passed=False, suite=name, language=language, error=f'{type(exc).__name__}: {exc}')
                traceback.print_exc()
                report['passed'] = False
                report['failures'].append(row)
            report['rows'].append(row)
            print(json.dumps(row), flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__': main()
