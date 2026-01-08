# Ephemeral Match Token Protocol (EMTP)

**EMTP** is a small protocol + reference implementation for generating **privacy-preserving, key-rotated match tokens** that let two authorized parties determine whether they are referring to the **same person** *without sharing raw identifiers*.

EMTP is designed for **regulated, governed ecosystems** (e.g., HIPAA entities, financial institutions, government programs) where:
- record linkage is required,
- raw identifiers cannot be exchanged, and
- **persistent global identifiers are unacceptable**.

EMTP achieves this by using a **shared HMAC key schedule** distributed by a controlled **Key Server**, with **rotation + overlap windows** so tokens are *ephemeral* but matching remains continuous.

---

## Quick example

Inputs (canonicalized + expanded into variants):
- name
- DOB
- phone(s)
- address(es)

Keys (from a Key Server):
- current key (`kid=2026-01`)
- prior key (`kid=2025-12`)

Output:
- a **set of HMAC tokens** computed over tuple variants × keys, e.g. hex strings:
  - `c9c6...`
  - `a1b2...`

Two parties match on token intersection, never exchanging demographics.

---

## Design goals

- **No de facto national identifier**
  - keys rotate and tokens expire
  - Key Server never stores demographics
- **Governed access**
  - keys distributed only to credentialed participants
  - key access is a **privacy circuit breaker** (revocable)
- **Match robustness**
  - variant expansion handles typos / formatting differences
  - overlap window (current + prior keys) avoids match discontinuities
- **Implementation simplicity**
  - small, auditable reference code + test vectors

---

## Not a universal internet identity layer

EMTP is **not** intended for arbitrary public use. It is explicitly designed for environments with:
- participant credentialing,
- auditing,
- misuse detection, and
- revocation authority.

---

## Documents

- **Quickstart:** `docs/quickstart.md`
- **Core spec:** `docs/spec.md`
- **Key Server protocol:** `docs/key-server.md`
- **Threat model + safety constraints:** `docs/threat-model.md`
- **Schema:** `schemas/emtp_v1.md`
- **Reference implementation (Python):** `reference/python/emtp.py`
- **Test vectors:** `test_vectors/emtp_v1_vectors.json`

---

## Repo structure (recommended)

```
docs/
schemas/
test_vectors/
reference/
  python/
  go/
```

---

## License

MIT (see `LICENSE`).
