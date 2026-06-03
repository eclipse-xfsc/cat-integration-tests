# ADR-002: Use did:web for Test Fixture Signing

- **Status:** Proposed
- **Date:** 2026-03-02
- **Context:** FACIS-FCE Federated Catalogue BDD test suite (`cat-integration-tests`)

## Problem

Test fixtures contain signed Verifiable Presentations with a `verificationMethod` DID in the proof. The FC server resolves that DID to obtain the public key (for signature verification) and the `x5u` URL (for trust anchor validation). The choice of DID method affects fixture portability across environments and how representative the tests are of production behaviour.

## Decision

Use **`did:web`** for all test fixture signing. A docker-compose service serves the DID document, X.509 certificate chain, and mock trust anchor registry.

Fixture proofs contain `"verificationMethod": "did:web:<service-name>#0"`, where `<service-name>` is the docker-compose service hosting the DID document.

## Rationale

### Indirection enables environment portability

With `did:web`, the DID is a stable pointer. The DID document — containing the public key, `x5u` URL, and algorithm — is served by the environment's infrastructure and can differ per deployment. The fixture's `verificationMethod` stays the same.

This means the **same signed fixtures** work across local, CI, and QA environments. Each environment serves its own DID document with the appropriate `x5u` and certificate chain at the same `did:web` hostname.

### Production alignment

Real Gaia-X participants register credentials using `did:web` with their organisation's domain. Using `did:web` in tests exercises the same DID resolution and verification code paths.

### Infrastructure is needed regardless

The trust mock service (nginx) is required for hosting the X.509 certificate chain (`x5u` target) and mocking the trust anchor registry. Serving a DID document at `/.well-known/did.json` adds negligible complexity to a service that already exists for trust infrastructure.

## Alternatives Considered

### did:jwk

`did:jwk` embeds the full JWK (including `x5u`) in the DID URI itself, making DID resolution a pure computation with no network dependency.

However, because the `x5u` is encoded in the DID string, changing the trust configuration (e.g. pointing to a different certificate chain URL) requires generating a new DID and **re-signing all fixtures**. This makes `did:jwk` impractical for maintaining multiple test profiles (local, CI, QA) from a single fixture set.

Additionally, `did:jwk` URIs are ~800 characters long (base64url-encoded JWK), which exceeds default database column widths and makes debugging harder.

`did:jwk` can be useful as a **diagnostic tool** — when isolating DID resolution problems, it removes the network variable entirely. The `scripts/generate-did-jwk.py` and `scripts/decode-did-jwk.py` utilities are available for this purpose.

## Consequences

- **Single fixture set** for all environments — only the DID document and certificates change per deployment.
- **Simpler QA profile** — deploy a DID document with the QA `x5u` URL and real certificates; no fixture re-signing needed.
- **DID document must stay in sync with the signing key.** If the RSA key changes, the DID document must be regenerated. The `did-server/setup.sh` script handles this.

## References

- [ADR-001: Behave Tag Naming Convention](001-behave-tag-naming-convention.md)
- [Fixture Signing Reference](../../../design-documents/02-insights/testing/bdd-automation-knowledge/fixture-signing.md)
- W3C DID Specification: [`did:web` Method](https://w3c-ccg.github.io/did-method-web/)
- W3C DID Specification: [`did:jwk` Method](https://github.com/quartzjer/did-jwk/blob/main/spec.md)