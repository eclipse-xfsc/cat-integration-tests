# Default-config-only fixtures

Fixtures here are valid **only** under the FC's permissive default config
(`verifyVCSignatures=false`, `verifyVPSignatures=false`). They intentionally
deviate from ICAM 24.07 input shape — typically bare JSON-LD VPs with bare
inline VCs, or VCs using pre-Loire type namespaces — and exercise the FC's
acceptance of off-spec input when signature verification is disabled.

Under `@cfg.strict` these inputs are expected to be rejected.

These fixtures do **not** advocate Loire conformance. Loire-shape fixtures
live in `fixtures/loire/` and `fixtures/enveloped/`.
