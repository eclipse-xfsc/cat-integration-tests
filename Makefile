# see https://makefiletutorial.com/

SHELL := /bin/bash -eu -o pipefail

# ---------------------------------------------------------------------------
# Required environment variables for BDD test targets (run_cat_bdd_*).
# Source env.sh before running:  source env.sh
# ---------------------------------------------------------------------------
REQUIRED_BDD_VARS := CAT_FC_HOST CAT_KEYCLOAK_URL CAT_KEYCLOAK_CLIENT_ID CAT_KEYCLOAK_CLIENT_SECRET CAT_KEYCLOAK_REALM CAT_TEST_USER CAT_TEST_PASSWORD

define check_bdd_env
$(foreach var,$(REQUIRED_BDD_VARS),\
  $(if $($(var)),,$(error $(var) is not set. On local dev stage: run `source env.sh` (see env.sample.sh) or set these manually in your environment.)))
endef

PYTHON_3 ?= python3
PYTHON_D ?= $(HOME)/.python.d
SOURCE_PATHS := "src"

VENV_PATH_DEV := $(PYTHON_D)/dev/eclipse/xfsc/dev-ops/testing/bdd-executor/cat
VENV_PATH_PROD := $(PYTHON_D)/prod/eclipse/xfsc/dev-ops/testing/bdd-executor/cat

# Path to bdd-executor repository root (set via env.sh or override here)
# Default: ../.. (assumes cat-integration-tests is in bdd-executor/implementations/)
EU_XFSC_BDD_CORE_PATH ?= ../..

setup_dev: $(VENV_PATH_DEV)
	mkdir -p .tmp/

$(VENV_PATH_DEV):
	$(PYTHON_3) -m venv $(VENV_PATH_DEV)
	"$(VENV_PATH_DEV)/bin/pip" install -U pip wheel
	cd "$(EU_XFSC_BDD_CORE_PATH)" && "$(VENV_PATH_DEV)/bin/pip" install -e ".[dev]"
	"$(VENV_PATH_DEV)/bin/pip" install -e ".[dev]"
	"$(VENV_PATH_DEV)/bin/pip" freeze > requirements.txt

setup_prod: $(VENV_PATH_PROD)

$(VENV_PATH_PROD):
	$(PYTHON_3) -m venv $(VENV_PATH_PROD)
	"$(VENV_PATH_PROD)/bin/pip" install -U pip wheel
	cd "$(EU_XFSC_BDD_CORE_PATH)" && "$(VENV_PATH_PROD)/bin/pip" install "."
	"$(VENV_PATH_PROD)/bin/pip" install .

isort: setup_dev
	"$(VENV_PATH_DEV)/bin/isort" $(SOURCE_PATHS) tests

pylint: setup_dev
	"$(VENV_PATH_DEV)/bin/pylint" $${ARG_PYLINT_JUNIT:-} $(SOURCE_PATHS) tests

coverage_run: setup_dev
	"$(VENV_PATH_DEV)/bin/coverage" run -m pytest $${ARG_COVERAGE_PYTEST:-} -m "not integration" tests/ src/

coverage_report: setup_dev
	"$(VENV_PATH_DEV)/bin/coverage" report

mypy: setup_dev
	"$(VENV_PATH_DEV)/bin/mypy" $${ARG_MYPY_SOURCE_XML:-} -p eu.xfsc.bdd.cat
	"$(VENV_PATH_DEV)/bin/mypy" $${ARG_MYPY_STEPS_XML:-} steps/ --disable-error-code=misc

code_check: \
	setup_dev \
	isort \
	pylint \
	coverage_run coverage_report \
	mypy

# --- Config-aware BDD targets ---
# MODE selects which server profile the tests run against.
# Usage:
#   make run_cat_bdd_dev MODE=default   # excludes @cfg.strict
#   make run_cat_bdd_dev MODE=strict    # excludes @cfg.default
#   make run_cat_bdd_dev                # default mode
#
# See docs/adr/003-interim-two-config-test-strategy.md

MODE ?= default

# v1 tag syntax: comma = OR, multiple --tags = AND.
# Each negation must be a separate --tags flag for AND semantics.
BEHAVE_TAGS_default := --tags='-@wip' --tags='-@cfg.strict'
BEHAVE_TAGS_strict  := --tags='-@wip' --tags='-@cfg.default'
BEHAVE_TAG_FILTER   := $(BEHAVE_TAGS_$(MODE))
ifeq ($(BEHAVE_TAG_FILTER),)
  $(error Unknown MODE "$(MODE)". Use MODE=default or MODE=strict)
endif

run_cat_bdd_dev: setup_dev
	$(call check_bdd_env)
	source "$(VENV_PATH_DEV)/bin/activate" && \
		"$(VENV_PATH_DEV)/bin/coverage" run -m behave $(BEHAVE_TAG_FILTER) $${ARG_BDD_JUNIT:-}

run_cat_bdd_dev_html: setup_dev
	$(call check_bdd_env)
	mkdir -p .tmp/behave
	source "$(VENV_PATH_DEV)/bin/activate" && \
		"$(VENV_PATH_DEV)/bin/coverage" run -m behave $(BEHAVE_TAG_FILTER) -f html -o .tmp/behave/behave-report.html

run_cat_bdd_prod: setup_prod
	$(call check_bdd_env)
	source "$(VENV_PATH_PROD)/bin/activate" && behave $(BEHAVE_TAG_FILTER) features/

run_all_test_coverage: coverage_run run_cat_bdd_dev coverage_report

clean_dev:
	rm -rfv "$(VENV_PATH_DEV)"

clean_prod:
	rm -rfv "$(VENV_PATH_PROD)"

activate_env_prod: setup_prod
	@echo "source \"$(VENV_PATH_PROD)/bin/activate\""

activate_env_dev: setup_dev
	@echo "source \"$(VENV_PATH_DEV)/bin/activate\""

licensecheck: setup_dev
	"$(VENV_PATH_DEV)/bin/pip" freeze > ".tmp/requirements.txt"
	cd .tmp/ && "$(VENV_PATH_DEV)/bin/licensecheck" -u requirements > THIRD-PARTY.txt

# --- Fixture Signing (dev-only, rare) ---
# Signs every *.vp.jsonld in fixtures/valid/ → fixtures/valid/<name>.signed.jsonld
# Convention: unsigned fixtures have no .signed suffix, signed ones do.
# Signed fixtures are committed — re-sign only when unsigned content changes.
# Requires: Java 21+, FC_SIGNER_JAR and FC_SIGNER_KEY env vars.
#
# Behind a TLS-intercepting proxy (e.g. Zscaler), set JAVA_TOOL_OPTIONS:
#   export JAVA_TOOL_OPTIONS="-Djavax.net.ssl.trustStore=/path/to/cacerts -Djavax.net.ssl.trustStorePassword=changeit"
#
# Build the signer:
#   cd <federated-catalogue> && mvn package -pl fc-tools/signer -am -DskipTests
#   # Produces: fc-tools/signer/target/fc-tools-signer-2.1.0-SNAPSHOT-full.jar
#
# Usage:
#   FC_SIGNER_JAR=/path/to/fc-tools-signer-2.1.0-SNAPSHOT-full.jar \
#   FC_SIGNER_KEY=/path/to/rsa2048.sign.pem \
#     make sign-fixtures

FIXTURE_DIR := fixtures/valid

# did:web DID — resolves to DID document served by the did-server container.
# The DID document contains the public key JWK with alg and x5u fields.
# See docs/adr/002-did-web-over-did-jwk.md for rationale.
# DID document is generated by: federated-catalogue/docker/did-server/setup.sh
FC_SIGNER_DID := did:web:did-server\#0

sign-fixtures:
ifndef FC_SIGNER_JAR
	$(error FC_SIGNER_JAR is not set. Point it to the fc-tools-signer fat jar.)
endif
ifndef FC_SIGNER_KEY
	$(error FC_SIGNER_KEY is not set. Point it to rsa2048.sign.pem from fc-tools/signer.)
endif
	@unsigned=$$(find $(FIXTURE_DIR) -name '*.vp.jsonld' ! -name '*.signed.jsonld' 2>/dev/null); \
	if [ -z "$$unsigned" ]; then \
		echo "No unsigned .vp.jsonld files found in $(FIXTURE_DIR)/"; exit 1; \
	fi; \
	for src in $$unsigned; do \
		base=$$(basename "$$src" .vp.jsonld); \
		dest="$$(dirname "$$src")/$${base}.vp.signed.jsonld"; \
		echo "Signing $$src → $$dest"; \
		java -jar "$(FC_SIGNER_JAR)" \
			sd="$$(pwd)/$$src" \
			ssd="$$(pwd)/$$dest" \
			prk="$(FC_SIGNER_KEY)" \
			m="$(FC_SIGNER_DID)" || exit 1; \
	done; \
	echo "Done. Signed $$(echo "$$unsigned" | wc -w | tr -d ' ') fixture(s)."
