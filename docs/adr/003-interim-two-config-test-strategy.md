# ADR-003: Interim Two-Config Test Strategy

- **Status:** Proposed
- **Date:** 2026-03-02
- **Context:** FACIS-FCE Federated Catalogue BDD test suite (`cat-integration-tests`)

## Problem

The Federated Catalogue has multiple configuration axes (Gaia-X compliance, SHACL schema validation, signature verification) that change API behaviour. A full test-profile orchestration system has been designed but not yet approved. BDD tests for new features need to be written now, without waiting for the orchestration decision.

## Decision

Use **two configurations** — default and strict — as an interim strategy. A single docker-compose overlay enables all verification flags simultaneously, matching the original 2.0.0 implementation behaviour.

### Configurations

| Config | Compose command | Behaviour |
|---|---|---|
| **Default** | `docker compose up` | Semantics only — Gaia-X off, schema off, signatures off |
| **Strict** | `./dev.sh strict` | Schema validation + signatures on; Gaia-X Trust Framework on |

### Tagging

Tests use two symmetric tags to mark config-specific scenarios:

| Tag | Meaning |
|---|---|
| `@cfg.default` | Scenario expects default behaviour (signatures/schema off) |
| `@cfg.strict` | Scenario expects strict behaviour (schema on, signatures on) |
| *(no @cfg tag)* | Config-agnostic — same expectation in both configs |

```bash
# Default run — excludes strict-only scenarios
make run_cat_bdd_dev MODE=default
# equivalent to: behave --tags='-@wip' --tags='-@cfg.strict'

# Strict run — excludes default-only scenarios
make run_cat_bdd_dev MODE=strict
# equivalent to: behave --tags='-@wip' --tags='-@cfg.default'
```

> **Note:** Behave 1.2.6 uses tag-expressions v1 syntax where negation is `-@tag`,
> not `not @tag`. Each negation needs a separate `--tags` flag because comma = OR in v1.
> See [ADR-001](001-behave-tag-naming-convention.md#ci-usage).

### Overlay

`docker-compose.strict.yml` overrides only the environment variables that differ from the base compose:

```yaml
services:
  server:
    environment:
      FEDERATED_CATALOGUE_VERIFICATION_TRUST_FRAMEWORK_GAIAX_ENABLED: "true"
      FEDERATED_CATALOGUE_VERIFICATION_SCHEMA: "true"
      FEDERATED_CATALOGUE_VERIFICATION_VP_SIGNATURE: "true"
      FEDERATED_CATALOGUE_VERIFICATION_VC_SIGNATURE: "true"
```

Signature verification is disabled in the default profile because without the Gaia-X Trust
Framework, it provides no meaningful security — see the catalogue architecture documentation
(ADR 3: Disable Signature Verification by Default) for the full rationale.

## Rationale

### One overlay instead of many

The original 2.0.0 implementation ran with all verification enabled. Most non-default test scenarios need the same "everything on" configuration. Splitting into per-flag overlays (`gaiax-on`, `schema-on`, `sigs-on`) creates orchestration complexity that the CR is designed to solve. Until the CR lands, a single strict overlay covers the majority of non-default scenarios.

### Forward-compatible with full orchestration

When the CR is approved, `@cfg.strict` scenarios can be re-tagged to granular `@cfg.gaiax-on`, `@cfg.schema-val-on` tags, and the single overlay decomposes into per-profile env directories. No test logic is wasted.

### Fuseki stays separate

The graph database switch (Neo4j vs Fuseki) is a service replacement, not an env var flip. It will be a second independent overlay (`docker-compose.fuseki.yml`) if needed. This is orthogonal to the strict/default split.

## Alternatives Considered

### Default-only (Option A from analysis)

Write all tests for the default configuration and tag non-default scenarios as `@wip`. This is contractually sufficient but leaves the original-implementation regression untested, which defeats the purpose of the current testing effort.

### Full profile orchestration now

Implement `test-profiles.yaml`, `run-profiles.sh`, per-profile env dirs, and CI pipeline. This is the right long-term solution but requires approval. Premature without the go-ahead.

## Consequences

- **Two manual test runs** instead of one automated pipeline. Acceptable for the interim period.
- **`@cfg.strict` is a coarse tag.** It groups scenarios that may eventually need different configurations. This is a known trade-off — granularity comes with the CR.
- **The overlay file is small and stable.** It tracks the base compose's env var naming. If the base compose changes property names, the overlay must be updated.

## References

- [ADR-001: Behave Tag Naming Convention](001-behave-tag-naming-convention.md)
- [ADR-002: Use did:web for Test Fixture Signing](002-did-web-over-did-jwk.md)