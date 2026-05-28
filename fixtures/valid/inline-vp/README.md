# Inline-VP fixtures

VPs that are bare JSON-LD with bare inline `VerifiableCredential` objects in
`verifiableCredential` — **no** JWS envelope at either VP or VC level.

The Federated Catalogue accepts this shape under the permissive default
config (`verifyVCSignatures=false`, `verifyVPSignatures=false`) and rejects
it under strict config (no JWS means no signature to verify).

**This shape is not ICAM 24.07 input shape.** ICAM 24.07 `credential_format.md`
§3.6.1 specifies a VC-JWT (`vp+jwt`) outer Verifiable Presentation. Loire-shape
fixtures live in `fixtures/loire/` and `fixtures/enveloped/`; new tests SHOULD
prefer those.

These fixtures exist to keep coverage of the bare-JSON-LD-VP path
discoverable and clearly labelled.
