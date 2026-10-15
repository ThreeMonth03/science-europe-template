# Science Europe DMP template

This repository owns the shared English Jinja, answer mapping and PDF/Word layout
for the customised Science Europe template. Traditional Chinese translations are
maintained only in the companion
[Chinese repository](https://github.com/ThreeMonth03/science-europe-template-zhtw),
in `locales/zh-Hant.po`.

## Current architecture

- `template.json` declares the English source template and output formats.
- `src/` contains shared Jinja, language-aware CSS, Word assets and filters.
- The Chinese repository pins an exact English commit and Tool commit in
  `pipeline.yml`, then builds both runtime deliveries from the same source.
- DSW 4.34 uses a generated Chinese compatibility ZIP with an embedded MO catalog.
  DSW 4.35 uses the English ZIP with a separately attached Chinese PO locale.
- Generated ZIPs, MO files and Chinese render trees are outputs, not editable sources.

Review and submission are formats of the same template, not separate branches.
Submission retains the 15 Science Europe questions, meaningful partial answers
and neutral unnamed-record labels without internal missing-information prompts.
Review additionally exposes bounded missing-information notices. Neither profile
displays the document export timestamp.

## Development and verification

Install the declared dependencies in an isolated Python environment, then use:

```sh
python -m pip install -r requirements-dev.txt
make check
make check-current
make test-compat434
```

See [testing and translation boundaries](docs/testing.md) for requirements and
acceptance limits. CI validates the current tree; it does not deploy a template
or replace page-by-page PDF/Word review.

## Upstream and standard provenance

This is a derivative of official `dsw:science-europe:1.30.1`, not an official
Science Europe or DSW release. The original template commit and change-risk
groups are recorded in [.upstream/base.json](.upstream/base.json).
The standard topic map is in
[requirements/science-europe-2021.json](requirements/science-europe-2021.json);
its coverage notes are not a claim of complete standard compliance.

Follow the [upstream upgrade policy](docs/upstream-upgrades.md). Source, translation
and runtime upgrades are separate changes and require their own checks.

## History

Retired pre-PO conversion code, experiment snapshots and per-round reports are
available in Git history. The last tree before the legacy cleanup is
`69135b204414442376388430ab4867968a2574ed`. Use `git show COMMIT:path` to inspect
a historical file; do not use an old guide as the current build procedure.

The stable description embedded in distributable packages is
`PACKAGE_README.md`; this navigation README is not packaged. See `LICENSE`.
