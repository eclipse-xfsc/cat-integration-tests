# ADR-001: Behave Tag Naming Convention

- **Status:** Accepted
- **Date:** 2026-02-20
- **Context:** FACIS-FCE Federated Catalogue BDD test suite (`cat-integration-tests`)

## Problem

The Federated Catalogue is a configurable system. Different deployments run with different
graph database backends (Neo4j vs Fuseki), different validation policies (forced schema
validation vs on-demand), different trust frameworks (Gaia-X enabled vs disabled), and
different messaging infrastructure. Each configuration variant requires its own subset of
tests to be executed in CI.

At the same time, the FACIS Inspection and Approval process (ref: `01-input/2.0
FACIS_FCE_Inspection_and_Approval.pdf`) defines **7 acceptance gates**, each grouping
multiple SRS requirements. Tests must be traceable to individual requirement IDs and
to the gate they belong to for evidence collection per gate.

Additionally, the catalogue has existing behaviour predating the FACIS requirements that
must continue to work — these "baseline" tests are not tied to any new requirement but
must still run in every configuration.

Without a disciplined naming scheme, tags will collide (e.g. `@schema` — is that the API
domain or the validation config?), CI filters will break silently, and traceability to
requirements will be lost.

## Decision

We adopt a **dot-separated hierarchical tag convention** with 6 dimensions. Each dimension
uses a unique prefix to guarantee disambiguation.

### Tag Dimensions

| Prefix | Dimension | Cardinality | Applied to | Purpose |
|--------|-----------|-------------|------------|---------|
| `@req.` | Requirement ID | 1:N per scenario | Scenarios | Traceability to SRS requirement |
| `@domain.` | API domain | 1 per feature | Features | Which API area is under test |
| `@cfg.` | Config variant | 0:N per scenario | Scenarios | **Where** — which deployment config the scenario runs against |
| _(bare)_ | Test purpose | 1 per feature/scenario | Either | **Why** — why the test exists (`@smoke`, `@baseline`, `@regression`, `@extended`) |
| _(bare)_ | Dev utility | 0:1 | Scenarios | `@wip`, `@skip`, `@this` |

### Requirement Tags (`@req.`)

Format: `@req.CAT-FR-{category}-{number}`

```gherkin
@req.CAT-FR-CO-01  @req.CAT-FR-SF-04  @req.CAT-NFR-01
```

Every scenario that validates a specific SRS requirement MUST carry the corresponding
`@req.` tag. A scenario may carry multiple `@req.` tags if it covers several requirements.

### Domain Tags (`@domain.`)

Format: `@domain.{api-area}`

| Tag | API area | Endpoints |
|-----|----------|-----------|
| `@domain.asset` | Assets | `/assets/*` |
| `@domain.verify` | Verification | `/verification` |
| `@domain.query` | Query | `/query/*` |
| `@domain.schema` | Schemas | `/schemas/*` |
| `@domain.participant` | Participants | `/participants/*` |
| `@domain.user` | Users | `/users/*` |
| `@domain.session` | Session | `/session` |
| `@domain.role` | Roles | `/roles` |
| `@domain.auth` | Authentication | Keycloak token flow |

Applied once per feature file. Prevents collision with config tags (e.g. `@domain.schema`
is unambiguously the API domain, not the validation flag).

### Config Variant Tags (`@cfg.`) — WHERE it runs

Format: `@cfg.{variant}`

These tags declare **which deployment configuration a scenario requires**. CI pipelines
use them to select the correct subset for the currently deployed variant.

Config tags answer: *"Against which server configuration must this scenario execute?"*

**Server configuration profile:**

| Tag | Meaning |
|-----|---------|
| `@cfg.default` | Requires default config (Gaia-X off, schema off). Would fail or be meaningless in strict. |
| `@cfg.strict` | Requires strict config: Gaia-X on, schema validation on, signatures on (see ADR-003) |
| `@cfg.fuseki` | Requires Fuseki backend (`graphstore.impl=fuseki`) |

**Fixture dependency:**

| Tag | Meaning |
|-----|---------|
| `@cfg.test-sig` | Scenario depends on properly signed test fixtures (did:web + trust infrastructure) |

Scenarios **without** any `@cfg.` tag are **config-agnostic** — same assertion holds in
both default and strict. They run in every config.

> **Note:** The granular per-flag tags (`@cfg.gaiax`, `@cfg.forced-schema-val`, `@cfg.neo4j`,
> etc.) defined in the original version of this ADR have been consolidated into
> `@cfg.default` / `@cfg.strict` as an interim simplification
> (see [ADR-003](003-interim-two-config-test-strategy.md)).
> If the test profile orchestration CR is approved, granular tags may be reintroduced.

### Test Purpose Tags (bare, no prefix) — WHY it exists

These tags classify **why a test was written**. They are orthogonal to config tags — a
`@baseline` test can be `@cfg.default`, `@cfg.strict`, or config-agnostic.

Purpose tags answer: *"What role does this test play in the overall suite?"*

| Tag | Meaning | Applied to |
|-----|---------|------------|
| `@smoke` | Minimal happy-path coverage — runs in every CI pipeline | Scenarios |
| `@baseline` | Pre-FACIS behaviour that must continue to work. Not tied to a new requirement. | Features |
| `@extended` | New behaviour added by FACIS requirements (CAT-FR-*) | Features |
| `@regression` | Validates that original implementation (2.0.0) behaviour is preserved under strict config | Features |

### Dev Utility Tags (bare, no prefix)

| Tag | Meaning |
|-----|---------|
| `@wip` | Work in progress — excluded from CI |
| `@skip` | Temporarily disabled |
| `@this` | Developer focus tag for local runs |

## Example

```gherkin
@domain.verify @baseline
Feature: Credential Verification
  As a Federated Catalogue API consumer
  I want to verify a Credential
  So that I can check its validity before submitting it

  @smoke @cfg.test-sig
  Scenario: Verify credential with unrecognised type returns semantic error

  @smoke @req.CAT-FR-CO-01 @cfg.default @cfg.test-sig
  Scenario: Verify credential with correct ontology type passes semantic check

  @smoke
  Scenario: Verify an invalid credential returns error


  @req.CAT-FR-SF-04 @cfg.strict @cfg.test-sig
  Scenario: Verify credential with forced schema validation enabled

```

## CI Usage

> **Tag expression syntax:** Behave 1.2.6 uses **tag-expressions v1** by default. In v1:
>
> - Negation uses the `-` prefix (not the `not` keyword).
> - **Comma = OR** within a single `--tags` flag.
> - **Multiple `--tags` flags = AND**.
> - The `not`/`and`/`or` keywords require tag-expressions v2, which behave 1.2.6 does
>   not use even when the package is installed.
>
> **Common mistake:** `--tags='-@wip,-@cfg.strict'` means NOT-wip **OR** NOT-strict,
> which is almost always true. Use separate `--tags` flags for AND:

```bash
# Default config — all tests that are not strict-only
behave --tags='-@wip' --tags='-@cfg.strict' --tags='-@cfg.test-sig'

# Strict config — all tests that are not default-only
behave --tags='-@wip' --tags='-@cfg.default'

# Smoke tests on default config
behave --tags='@smoke' --tags='-@wip' --tags='-@cfg.strict' --tags='-@cfg.test-sig'

# All compliance-related tests (filter by requirement category)
behave --tags='@req.CAT-FR-CO'

# Fuseki backend (future)
behave --tags='@cfg.fuseki'
```

The Makefile provides `MODE=default` / `MODE=strict` targets that apply the correct filters
automatically:

```bash
make run_cat_bdd_dev MODE=default
make run_cat_bdd_dev MODE=strict
```

## Consequences

**Benefits:**
- Every tag dimension has a unique prefix — no naming collisions possible.
- `@req.` gives direct traceability to SRS requirements. Acceptance gates can be derived
  by filtering on requirement category (e.g. `@req.CAT-FR-CO` for gate CO1).
- `@cfg.` tags allow CI to deploy a specific catalogue configuration and run exactly the
  matching test subset, without maintaining separate feature files per variant.
- `@baseline` clearly separates pre-FACIS behaviour from new requirement coverage.
- New config dimensions (e.g. a future `@cfg.dch-reachable` for Gaia-X DCH dependency)
  can be added without touching existing tags.

**Trade-offs:**
- Dot-separated prefixes are more verbose than bare tags. This is deliberate — we
  prioritise disambiguation over brevity.
- Feature files may accumulate many tags on scenarios that span multiple requirements
  and config variants. This is acceptable because the tags serve as machine-readable
  metadata for CI and traceability, not prose.

## References

- FACIS Inspection and Approval Requirements (`01-input/2.0 FACIS_FCE_Inspection_and_Approval.pdf`) — gate-to-requirement mapping
- FACIS SRS — requirement IDs (`CAT-FR-*`)
- Behave tag expressions: https://behave.readthedocs.io/en/stable/tag_expressions.html