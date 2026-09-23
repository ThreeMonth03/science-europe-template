"""Replay the Word prototype's scope tests without changing production sources."""
import argparse, importlib.util, json, tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location('word_sections_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def main(output):
    output.parent.mkdir(parents=True,exist_ok=True)
    actual={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'src').rglob('*') if p.is_file()}
    changed=load('recipe').overlay(actual)
    with tempfile.TemporaryDirectory(prefix='se-word-sections-') as temp:
        target=Path(temp)
        for name,value in changed.items():
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
        result=load('engine').run(ROOT,target,output)
    print(json.dumps(dict(passed=True,cases=len(result['rows']))))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)
