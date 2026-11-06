.PHONY: test verify check check-current package audit-upstream knowledge-models export-compat434 test-compat434 pot
.DEFAULT_GOAL := test

PYTHON ?= python3
DSW_TDK ?= dsw-tdk
PO ?=
ENGLISH_ZIP ?=
COMPAT_VERSION ?=
COMPAT_OUTPUT ?= outputs/compat434/template.zip
SOURCE_COMMIT ?=
POT_OUTPUT ?= outputs/template.pot
PACKAGE_OUTPUT ?= outputs/package
PACKAGE_PREVIEW ?=

pot:
	$(PYTHON) scripts/export_pot.py --output "$(POT_OUTPUT)"

export-compat434:
	$(if $(strip $(PO)),,$(error Set PO to the authoritative Chinese repository catalog))
	$(PYTHON) scripts/export_legacy_locale.py --source-zip "$(ENGLISH_ZIP)" --po "$(PO)" --output "$(COMPAT_OUTPUT)" --version "$(COMPAT_VERSION)" $(if $(SOURCE_COMMIT),--source-commit "$(SOURCE_COMMIT)")

test-compat434:
	$(PYTHON) -m unittest discover -s experiments/legacy434 -v

knowledge-models:
	$(PYTHON) scripts/prepare_knowledge_models.py

test: knowledge-models
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) -m unittest discover -s experiments/legacy434 -v

verify:
	$(DSW_TDK) --no-config verify .

check: test verify

check-current:
	$(PYTHON) scripts/check_current.py

package:
	$(PYTHON) scripts/build_package.py --output "$(PACKAGE_OUTPUT)" --tdk "$(DSW_TDK)" $(if $(filter 1 true,$(PACKAGE_PREVIEW)),--preview)

audit-upstream:
	$(PYTHON) scripts/audit_upstream.py --target upstream/main
