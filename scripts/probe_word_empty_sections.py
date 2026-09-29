"""Verify current sources, then replay the exact historical Word spacing delta."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
from word_empty_section_contract import ROOT, load, project_source

def main(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    before, _ = project_source()
    after = load('recipe').overlay(before)
    with tempfile.TemporaryDirectory(prefix='se-word-sections-baseline-') as temp:
        # Mount only the public fixture subtree, not TemporaryDirectory's
        # owner-only (0700) root: the pinned worker runs as a different CI UID.
        baseline = Path(temp) / 'baseline'
        candidate = Path(temp) / 'candidate'
        for root, values in ((baseline, before), (candidate, after)):
            for name, value in values.items():
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
        try:
            result = load('engine').run(baseline, candidate, output)
        except RuntimeError:
            failure = output.with_suffix('.failure.log')
            if failure.is_file():
                print(failure.read_text(), file=sys.stderr)
            raise
    assert len(result['rows']) == 121
    result.update(current_source_verified=True, historical_scope=True, comparison_version='0.3.50')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, version=json.loads((ROOT/'template.json').read_text())['version'],
        comparison_version='0.3.50', current_source_verified=True, historical_scope=True, cases=len(result['rows']))))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output)
