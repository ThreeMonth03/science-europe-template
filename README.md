# Science Europe DMP template

This repository owns the shared English Jinja, answer mapping and PDF/Word layout
for the customised Science Europe template. Traditional Chinese translations are
maintained only in the companion
[Chinese repository](https://github.com/ThreeMonth03/science-europe-template-zhtw),
in `locales/zh-Hant.po`.

## Current architecture

- `template.json` declares the English source template and output formats.
- `src/` contains shared Jinja, language-aware CSS, Word assets and filters.
- This repository owns English preparation and packaging, including fonts,
  Word reference preparation and public KM test fixtures.
- The Chinese repository pins an exact English commit in `pipeline.yml`, then
  builds both runtime deliveries from the same source and its reviewed PO.
- DSW 4.34 uses a generated Chinese compatibility ZIP with an embedded MO catalog.
  DSW 4.35 uses the English ZIP with a separately attached Chinese PO locale.
- The same English ZIP also supports stock DSW 4.34: descriptor options activate
  null English gettext on its Jinja-powered steps, without fixing a catalog or
  changing the Worker. DSW 4.35 still selects its attached locale normally.
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

Build the prepared English ZIP without a Chinese or Tool checkout:

```sh
make package PACKAGE_OUTPUT=outputs/english-NEW
```

The output directory must be new. The standalone builder requires clean,
committed source and full Git history; `--preview` on `scripts/build_package.py`
is only for unaccepted local development. It never edits the source assets.

See [testing and translation boundaries](docs/testing.md) for requirements and
acceptance limits. CI validates the current tree; it does not deploy a template
or replace page-by-page PDF/Word review.

## Translation workflow

This repository owns the translation message contract as well as the English
text: Jinja markers, contexts, placeholders and POT extraction. The Chinese
repository owns PO merging, translation review, version pairing and bilingual
runtime deliveries. Neither repository requires `dsw-document-template-tool` to
build or test this customised template. The Tool's separate legacy workflow is
not changed by this ownership boundary.

From a clean, committed English checkout, generate a new POT with:

```sh
make pot POT_OUTPUT=outputs/template-NEW.pot
```

`scripts/export_pot.py` uses the official DSW extractor through
`scripts/template_catalog.py`; it does not infer sentence boundaries or rewrite
Jinja. The shared helper is also used by `scripts/check_catalog.py`. Extraction
fails on unparseable files or an empty catalog, rather than publishing a partial
POT. The output must not already exist.

The POT records the template coordinate and full English commit. For Chinese
work, use exactly the commit pinned in the Chinese `pipeline.yml`, then pass the
POT to that repository's `scripts/refresh_po.py --pot ...`. A different or
unidentified source is rejected. Commit a deliberate source change and update
the pin before refreshing translations; never follow a floating branch silently.

POT is generated source-language input, not an editable translation or a second
source of truth. It may be saved outside this checkout. Only the Chinese
repository's `locales/zh-Hant.po` is authoritative for Traditional Chinese; neither
extraction nor a PO review draft automatically approves translations.

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
