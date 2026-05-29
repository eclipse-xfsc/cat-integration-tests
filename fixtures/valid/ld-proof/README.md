# LD-Signature fixtures

VPs secured by a W3C Linked Data Signature (`proof` block) instead of by a
VC-JWT envelope. These are valid under the W3C Verifiable Credentials Data
Model 2.0 but are **not** ICAM 24.07 input shape: §3.6.1 of
`credential_format.md` specifies a VC-JWT (`vp+jwt`) outer Verifiable
Presentation.

These fixtures exercise the FC's LD-Signature handling path — an orthogonal
proof format the FC supports, independent of Loire conformance.
