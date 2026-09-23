"""Replay all pinned Word scope cases on actual integrated production assets."""
import argparse
import json
from pathlib import Path
import tempfile
from word_empty_section_contract import ROOT, load, project_source

def main(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    before, _ = project_source()
    with tempfile.TemporaryDirectory(prefix='se-word-sections-baseline-') as temp:
        baseline = Path(temp)
        for name, value in before.items():
            path = baseline / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
        result = load('engine').run(baseline, ROOT, output)
    assert len(result['rows']) == 121
    print(json.dumps(dict(passed=True, version='0.3.50', actual_production_assets=True, cases=len(result['rows']))))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output)
