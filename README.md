# CAT Integration Tests

BDD acceptance tests for the Eclipse XFSC Federated Catalogue, using the [bdd-executor](https://github.com/eclipse-xfsc/bdd-executor) framework (Python Behave).

## Prerequisites

- Python 3.12+
- Running Federated Catalogue docker-compose stack (see `federated-catalogue/docker/`)
- `127.0.0.1 key-server` in `/etc/hosts`
- Keycloak user with Federated Catalogue roles (see [Keycloak Setup](#keycloak-setup) below)

## Setup

```bash
# Configure environment 
cp env.sample.sh env.sh # done once initially

# Edit env.sh - set CAT_ENV to your target (docker-compose / minikube / qa)
#             -  set EU_XFSC_BDD_CORE_PATH if not using default location
#             -  set Keycloak credentials as described in Keycloak Setup below
source env.sh # done for each new terminal session to load proper env vars

# Install dependencies and set up virtual environment
make setup_dev
```

## Keycloak Setup

The tests authenticate via **Resource Owner Password Grant** (not client credentials). You need a Keycloak user with the correct Federated Catalogue roles.

### 1. Create a test user

1. Open Keycloak Admin Console: <http://key-server:8080/admin/> (admin / admin for docker-compose)
2. Select the **gaia-x** realm
3. Go to **Users** > **Add user**
4. Set username to `admin` (or whatever `CAT_TEST_USER` is set to in `env.sh`)
5. Save

### 2. Set a permanent password

1. Go to the user's **Credentials** tab
2. Click **Set password**
3. Enter the password matching `CAT_TEST_PASSWORD` in `env.sh` (default: `admin`)
4. Set **Temporary** to **OFF**
5. Save

### 3. Clear required actions

1. Go to the user's **Details** tab
2. Remove all entries from **Required User Actions** (e.g. "Update Password", "Verify Email")
3. Save

If required actions remain, the password grant will fail with: `invalid_grant: Account is not fully set up`.

### 4. Assign Federated Catalogue roles

1. Go to the user's **Role mapping** tab
2. Click **Assign role**
3. Filter by client: **federated-catalogue**
4. Assign the roles needed for your test scenarios:

| Role | Required for |
|------|-------------|
| `Ro-MU-CA` | Catalogue Admin (full access) |
| `Ro-MU-A` | User management |
| `Ro-AS-A` | Asset management (create, delete, revoke) |
| `Ro-PA-A` | Participant management |

For running all tests, assign **Ro-MU-CA** (includes all permissions).

### 5. Add the client secret to `dev.env`
1. Go to **Clients** > **federated-catalogue** > **Credentials** tab
2. Copy the **Secret** value
3. Paste it into `dev.env` as the value for `FC_CLIENT_SECRET`

### 6. Verify

```bash
# Quick check that the token grant works (make sure env.sh is sourced first):
curl -s -X POST "${CAT_KEYCLOAK_URL}/realms/${CAT_KEYCLOAK_REALM}/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=${CAT_KEYCLOAK_CLIENT_ID}" \
  -d "client_secret=${CAT_KEYCLOAK_CLIENT_SECRET}" \
  -d "username=${CAT_TEST_USER}" \
  -d "password=${CAT_TEST_PASSWORD}" \
  -d "scope=${CAT_KEYCLOAK_SCOPE}" | python3 -m json.tool | head -5
```

You should see `"access_token": "eyJ..."` in the response.

## Running Tests

```bash
source env.sh

# Run all BDD features
make run_cat_bdd_dev

# Run with HTML report, you will find the report in .tmp/behave/behave-report.html
make run_cat_bdd_dev_html

# Run code quality checks
make code_check
```

## Project Structure

```
features/                    # Gherkin .feature files
steps/                       # Behave step definitions
  keycloak.py                #   Auth steps (CatKeycloakServer — password grant)
  fc_server.py               #   FC API steps (CRUD, verify, query, etc.)
  rest.py                    #   Additional HTTP status assertions (422)
src/eu/xfsc/bdd/cat/        # Shared Python package
  env.py                     #   OS env var bindings
  defaults.py                #   Constants (PREFIX="CAT")
  components/
    fc_server.py             #   Server wrapper (BaseServiceKeycloak)
    keycloak.py              #   CatKeycloakServer (password grant override)
fixtures/                    # Test payloads
  valid/                     #   VC 2.0 JSON-LD fixtures (unsigned, for skip-signature tests)
  loire/valid/               #   Loire JWT fixtures (signed, for signature-verification tests)
  enveloped/valid/           #   EnvelopedVerifiableCredential/Presentation fixtures
  vc20/invalid/              #   VC 2.0 negative test fixtures (bad signature, expired, etc.)
  invalid/                   #   Deliberately broken payloads for negative tests
  schemas/                   #   SHACL and JSON/XML Schema fixtures
scripts/                     # Dev / diagnostic utilities
  generate-jwt-fixture.py    #   Sign JSON-LD payloads as JWT fixtures (Ed25519/EdDSA)
  generate-did-jwk.py        #   Generate did:jwk DID (diagnostic — not used in normal workflow)
  decode-did-jwk.py          #   Decode did:jwk DID to inspect embedded JWK (diagnostic)
tests/                       # Unit tests for shared utilities
archived/                    # Legacy Postman collection (reference only)
environment.py               # Behave hooks (before_all)
```

## Tag Convention

Tests use a dot-separated hierarchical tagging scheme (see [ADR-001](docs/adr/001-behave-tag-naming-convention.md) for full rationale).

### Dimensions

| Prefix | Dimension | Example |
|--------|-----------|---------|
| `@req.` | SRS requirement | `@req.CAT-FR-CO-01` |
| `@gate.` | FACIS I&A acceptance gate | `@gate.GD1`, `@gate.CO1` |
| `@domain.` | API area under test | `@domain.asset`, `@domain.verify` |
| `@cfg.` | Required deployment config | `@cfg.neo4j`, `@cfg.gaiax` |
| _(bare)_ | Test purpose | `@smoke`, `@baseline`, `@regression` |
| _(bare)_ | Dev utility | `@wip`, `@skip`, `@this` |

### Running subsets

```bash
# Smoke tests (default config)
behave --tags="@smoke"

# All baseline (pre-FACIS) behaviour
behave --tags="@baseline"

# Everything for a specific acceptance gate
behave --tags="@gate.CO1"

# Only tests that apply to Fuseki backend
behave --tags="@cfg.fuseki"

# Smoke tests excluding Fuseki-specific and Gaia-X-specific scenarios
behave --tags="@smoke and not @cfg.fuseki and not @cfg.gaiax"
```

### Acceptance Gates

| Tag | Gate | SRS Requirements |
|-----|------|-----------------|
| `@gate.AM1` | Asset Management | CAT-FR-AM-01, -02, -03 |
| `@gate.GD1` | Claim Extraction | CAT-FR-GD-01, -02, -09 |
| `@gate.GD2` | Switchable Graph Backends | CAT-FR-GD-03 thru -08 |
| `@gate.AC1` | Access Control | CAT-FR-AC-01, -02 |
| `@gate.LS1` | Lifecycle and Storage | CAT-FR-LM-01 thru -04, CAT-FR-SF-01 thru -04 |
| `@gate.CO1` | Compliance and Validation | CAT-FR-CO-01 thru -05 |
| `@gate.AU1` | Administration UI | CAT-FR-AU-01 |

### Config variants

The Federated Catalogue is deployed with different configurations (graph backends,
validation policies, trust frameworks). `@cfg.*` tags mark which configuration a
scenario requires, so CI can run exactly the right subset per deployment variant.

| Tag | Config property | Value |
|-----|----------------|-------|
| `@cfg.neo4j` | `graphstore.impl` | `neo4j` |
| `@cfg.fuseki` | `graphstore.impl` | `fuseki` |
| `@cfg.forced-schema-val` | `verification.schema` | `true` |
| `@cfg.no-schema-val` | `verification.schema` | `false` |
| `@cfg.gaiax` | `trust-framework.gaiax.enabled` | `true` |
| `@cfg.no-gaiax` | `trust-framework.gaiax.enabled` | `false` |
| `@cfg.real-sig` | Signature verification | enabled (real DIDs) |
| `@cfg.test-sig` | Signature verification | enabled (did-server test infrastructure) |

Scenarios without `@cfg.*` tags are config-agnostic and run in every variant.

## Signed Test Fixtures

The FC server verifies JWT signatures on uploaded credentials by resolving the DID in the JWT `kid` header, fetching the public key from the DID document, and verifying the signature. Linked Data proof verification was removed with the Tagus-era cleanup (CAT-TECH-01) — only JWT and Enveloped Credential formats are accepted.

Test fixtures use **`did:web`** — the same DID method that real Gaia-X participants use. The DID resolves to a DID document hosted by the docker-compose `did-server` service, which also serves the X.509 certificate chain and mocks the trust anchor registry. See [ADR-002](docs/adr/002-did-web-over-did-jwk.md) for the rationale behind this choice.

### Pre-signed fixtures (committed to repo)

Signed JWT fixtures in `fixtures/loire/valid/` and `fixtures/enveloped/valid/` are committed to git and work out of the box. **You do not need to re-sign them for normal test runs.**

### When to re-sign

Re-sign only when you **change the content** of a JSON-LD source file (e.g. different `credentialSubject` fields, new `@type`). Changing the payload content invalidates the existing JWT signature.

### How to sign (JWT — current)

```bash
# Prerequisites: pip install PyJWT[crypto] cryptography

# Sign a Loire VC (auto-detects typ/cty from payload)
python3 scripts/generate-jwt-fixture.py \
    --payload fixtures/loire/valid/participant.loire.jsonld

# Sign a Loire VP with inner VC embedding
python3 scripts/generate-jwt-fixture.py \
    --payload fixtures/loire/valid/participant-vp.loire.jsonld \
    --embed-vc fixtures/loire/valid/participant.loire.jsonld

# Produce an EnvelopedVerifiableCredential (Gaia-X ICAM 24.07)
python3 scripts/generate-jwt-fixture.py \
    --payload fixtures/loire/valid/participant.loire.jsonld \
    --wrap-as evc --out fixtures/enveloped/valid/participant.evc.jsonld

# Use existing key (recommended for reproducibility)
python3 scripts/generate-jwt-fixture.py \
    --payload fixtures/loire/valid/participant.loire.jsonld \
    --key keys/jwt-signing.pem
```

See `scripts/generate-jwt-fixture.py --help` for all options.

### Fixture directories

| Directory | Purpose |
|-----------|---------|
| `valid/` | VC 2.0 JSON-LD (unsigned) — for skip-signature and SHACL tests |
| `loire/valid/` | Loire JWT fixtures (signed Ed25519/EdDSA) — for signature-verification tests |
| `enveloped/valid/` | EnvelopedVerifiableCredential/Presentation wrappers |
| `vc20/invalid/` | VC 2.0 negative tests (bad signature, expired, mismatched issuer) |
| `invalid/` | Structurally broken payloads (missing fields) |
| `schemas/` | SHACL, JSON Schema, XML Schema fixtures |

### Naming conventions

| Pattern | Meaning |
|---------|---------|
| `*.jsonld` | JSON-LD source (human-readable, diffable) |
| `*.signed.jwt` | Signed JWT output (generated from matching `.jsonld`) |
| `*.loire.jsonld` | Loire format (claims at top level, `typ: vc+jwt`) |
| `*.vc2.jsonld` | Danubetech VC 2.0 format (`vc` wrapper claim) |
| `*-vp.*` / `*.vp2.*` | Verifiable Presentation (may embed inner VC) |
| `*.evc.jsonld` / `*.evp.jsonld` | Enveloped credential/presentation |

### Key material

JWT fixtures are signed with **Ed25519** (algorithm: `EdDSA`). The signing key is generated by `generate-jwt-fixture.py` on first use. The corresponding public key JWK is added to the `did:web:did-server` DID document (`docker/did-server/www/.well-known/did.json`). See `generate-jwt-fixture.py` output for the DID document snippet to copy.

## Test Profiles & Trust Configuration

Signature verification in the Federated Catalogue relies on a **trust chain**: the proof's `verificationMethod` DID resolves to a JWK, the JWK's `x5u` field points to an X.509 certificate chain, and that chain is validated against a trust anchor registry. The configuration of this trust chain differs fundamentally between local and real environments.

### Local (docker-compose)

The local stack is **fully self-contained** — no external services or real certificates required.

| Component | How it works locally                                                                   |
|-----------|----------------------------------------------------------------------------------------|
| DID method | `did:web:did-server` — resolves to DID document hosted by nginx container              |
| DID document | `/.well-known/did.json` — contains public key JWK with `alg` and `x5u` |
| `x5u` URL | `https://did-server/certs/chain.pem` — served by a local nginx container               |
| Certificate | Self-signed by a local CA (generated in `federated-catalogue/docker/certs/` by `did-server/setup.sh`)          |
| Trust anchor registry | Mocked by did-server nginx (returns 200 for any POST to `/api/trustAnchor/chain/file`) |
| JVM truststore | Custom `cacerts` with the local CA cert added                                          |

This means tests tagged `@cfg.real-sig` pass without any external infrastructure. The trade-off is that **no real Gaia-X trust validation happens** — the mock registry accepts any certificate.

To inspect the DID document (serverd in the local docker container):
```bash
curl -sk https://did-server/.well-known/did.json | python3 -m json.tool
```

### QA / Staging (real Gaia-X trust anchor)

A real QA environment would validate signatures against the **actual Gaia-X Trust Anchor registry** (e.g. `https://registry.lab.gaia-x.eu/v1/api/trustAnchor/chain/file`). This requires:

| Component | What's needed |
|-----------|--------------|
| Certificate | Signed by a CA that the Gaia-X registry trusts (not self-signed) |
| `x5u` URL | Publicly reachable HTTPS URL hosting the cert chain PEM |
| Trust anchor URL | Real registry endpoint (configured via `FEDERATED_CATALOGUE_VERIFICATION_TRUST_FRAMEWORK_GAIAX_TRUST_ANCHOR_URL`) |
| DID resolution | Universal Resolver must be reachable for `did:web` resolution |
| JVM truststore | Default cacerts (no custom CA needed if using a publicly trusted certificate) |

Fixtures signed for local testing **will not pass** QA verification — the local CA cert is not trusted by the real registry. However, because `did:web` provides indirection, the **same signed fixtures** can be reused across environments — only the DID document and certificates served at the `did:web` hostname need to change (see [ADR-002](docs/adr/002-did-web-over-did-jwk.md)).

### Profile summary

| Aspect | Local (docker-compose) | QA (real trust anchor) |
|--------|----------------------|----------------------|
| Trust anchor | Mock (did-server nginx) | Real Gaia-X registry |
| Certificate authority | Self-signed local CA | Gaia-X-trusted CA |
| `x5u` hosting | did-server container | Public HTTPS endpoint |
| Fixture portability | Works out of the box | Same fixtures — only DID document + certs differ |
| Network dependencies | None (all in Docker network) | Internet access to registry + x5u host |
| Behave tags | `@cfg.real-sig` | `@cfg.real-sig` (same tests, different infra) |

### What's not yet implemented

There is currently no QA test profile. The `qa` target in `env.sh` configures Keycloak and FC host endpoints but does **not** address the trust chain (signing key, certificates, trust anchor URL). Setting up a real QA profile requires:

1. Obtaining a certificate from a Gaia-X-trusted CA for the test signing key
2. Hosting the DID document and cert chain at a stable, publicly reachable HTTPS URL that matches the `did:web` hostname in the fixtures
3. Configuring the FC server to use the real trust anchor registry URL

Because `did:web` provides indirection, the signed fixtures do **not** need to be re-signed for QA — only the DID document and certificates at the `did:web` host need to change.

## Known Issues

### Infrastructure

- **`FC_CLIENT_SECRET` in `dev.env`** — The default `dev.env` ships with `FC_CLIENT_SECRET=**********` (placeholder). This must be replaced with the actual Keycloak client secret, otherwise `GET /session`, `GET /participants`, and all user endpoints return 500 (the FC server fails to authenticate to Keycloak admin API).
- **`docker compose restart` does not pick up env var changes.** Use `docker compose up -d <service>` to recreate containers when you change `dev.env` or compose overrides.

### Signature Verification

- **JWT signatures only** — The FC only accepts JWT (EdDSA, PS256, RS256) and Enveloped Credential formats. Linked Data proofs (`JsonWebSignature2020`, `Ed25519Signature2018`) are rejected with `"Linked Data proof verification is not supported"`. All signed fixtures must be JWT.
- **`assets.validators` column width** — The default varchar(256) column in PostgreSQL may truncate long DIDs. With `did:web` this is not an issue, but if `did:jwk` is used for debugging, its ~800-char URIs require a database migration to `varchar(2048)[]`.
- **Python `requests.post(data=string)` sends wrong encoding** — Passing a JSON-LD string directly as `data=` adds charset headers that confuse the FC server's Jackson parser (returns 400: `"Unexpected end-of-input"`). Fix: always use `data=payload.encode("utf-8")`. Already applied in `src/eu/xfsc/bdd/cat/components/fc_server.py`.

### Fixtures & Content

- **VC 2.0 context required** — All credentials must include `https://www.w3.org/ns/credentials/v2` in their `@context`. VC 1.1 (`https://www.w3.org/2018/credentials/v1`) is no longer accepted (CAT-TECH-01).
- **Fixture `@type` namespace** — Valid test fixtures use `https://w3id.org/gaia-x/2511#LegalPerson` (via `gx:` prefix with `https://w3id.org/gaia-x/2511#` context). The legacy `http://w3id.org/gaia-x/participant#Participant` namespace is used only in negative test fixtures for semantic rejection.

### Upstream

- The upstream bdd-executor `KeycloakServer.fetch_token()` hardcodes `client_credentials` grant. This is overridden locally via `CatKeycloakServer`. A PR to make grant type configurable is planned.

## Background

The original implementation of the federated catalogue came with a set of pre-acceptance tests
that can be found at https://gitlab.com/gaia-x/data-infrastructure-federation-services/cat/pre-acceptance-testing/-/blob/main/Test_Stand.postman_collection.json?ref_type=heads.

These were based on a Postman collection that is archived in the `archived/` folder.
There is a newer collection at https://github.com/eclipse-xfsc/federated-catalogue/tree/main/fc-tools, but that one was lacking concrete payloads and assertions.