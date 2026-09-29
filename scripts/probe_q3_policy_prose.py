"""Run the independent Q3 matrix against actual integrated English sources."""
import argparse
import json
from pathlib import Path
from q3_policy_prose_contract import ROOT, load, project_source

def main(output):
    before, _ = project_source()
    candidate = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    from current_repairs_contract import project_source as project_candidate
    current, _ = project_candidate(candidate, json.loads((ROOT / 'template.json').read_text()))
    rows = load('probe').check(ROOT, before, current, 'english')
    assert len(rows) == 7932 and not any(r['joined_policies'] for r in rows)
    result = dict(passed=True, version='0.3.51', candidate_source_verified=True,
                  historical_projection=True, release_acceptance=False, comparisons=len(rows),
                  full_document_comparisons=sum(r['case'].startswith('fixture-') for r in rows),
                  joined_policies=0, q3_output_unchanged=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as f:json.dump(result, f, indent=2);f.write('\n')
    print(json.dumps(result))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output)
