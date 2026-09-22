"""Run the sealed Word cases on the pullable, pinned public worker used by CI.

The private markdown-tables worker is not available on a fresh GitHub runner.
These cases already contain HTML, so the public worker tests the same Pandoc
and XML contract without requiring that locally built image.
"""
import importlib.util
from pathlib import Path
from probe_budget_word import IMAGE
from submission_flow_contract import project_source

def main():
    project_source()  # Includes the immutable case/runner recipe hashes.
    path=Path(__file__).resolve().parents[1]/'experiments/empty-question-spacing/engine.py'
    spec=importlib.util.spec_from_file_location('submission_flow_word_cases',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.IMAGE=IMAGE
    module.main()

if __name__=='__main__':main()
