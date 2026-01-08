# Implementer Quickstart

1. Fetch keys from a Key Server (mTLS-authenticated):
   - current + prior keys

2. Canonicalize + expand tuple variants deterministically.

3. Compute token set:
   - HMAC-SHA256(key, tuple_variant)

4. Publish tokens where required (e.g., registry inputs).

5. Rotate keys on schedule; keep overlap window to maintain match continuity.

See:
- `docs/spec.md`
- `docs/key-server.md`
- `schemas/emtp_v1.md`
