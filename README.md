# Ephemeral Match Token Protocol (EMTP)

**EMTP** is a privacy-preserving convention for two parties to determine whether they are referring to the **same person** without exchanging raw identifiers.

Each party locally normalizes demographic inputs into a set of **identifier tuple variants**, computes **HMAC-based ephemeral tokens** using rotating keys, and shares only the resulting tokens.  
A third-party **Key Server** distributes rotating HMAC keys to credentialed participants and can revoke access for misuse.

EMTP is designed to:
- enable **matchability without central demographic storage**
- avoid creation of a persistent global identifier
- support **collision reduction** by allowing optional identifier suffixes (e.g., last4/last5) without typing them as SSN/DL/etc.
- be transport-agnostic (tokens can be exchanged via **STP**, message buses, files, APIs, etc.)

---

## Quick example

Input demographic data (local only):

```json
{
  "name": "MR. JRR TOlkein",
  "dob": "1892-01-03",
  "phones": ["+1 (212) 555-1212"],
  "addresses": ["20 Northmoor Rd, Oxford, UK"],
  "id_numbers": ["12345", "987654"]
}
```

Token generation produces a set like:

```
HMAC(key_current, tuple_variant_1)
HMAC(key_current, tuple_variant_2)
...
HMAC(key_prior, tuple_variant_1)
...
```

Only these tokens are shared; the Key Server and any registry **never receive demographics**.

---

## Why EMTP (vs fixed hashes / plaintext identifiers)

- **Plain identifiers** (name/DOB/address) are sensitive and linkable
- **Fixed hashes** are vulnerable to dictionary attacks and become de facto identifiers
- **Rotating HMAC keys** make tokens *ephemeral* and resistant to reverse-mapping
- **Key access control** enables a privacy circuit-breaker (revocation)

---

## Core Concepts

### 1) Inputs → Tuple Variants (normalization)
Implementations normalize and expand inputs into multiple variants to increase match likelihood across messy real-world data:

- names: casing, punctuation removal, spacing, initials collapse/expansion
- honorific removal ("Mr", "Ms", "Dr") and suffix parsing ("Jr", "Sr", "IV")
- phone normalization (E.164 variants)
- address normalization (tokenized/abbrev variants)

### 2) Optional identifier suffixes (`id_numbers`)
To reduce collisions, participants MAY include `id_numbers`: strings containing **4+ digits** representing suffixes of any identifier (SSN, DL, member ID, account ID, national ID, etc.).

Identifier types MUST be ignored; only digit suffixes are used.

For each `id_numbers` entry:
- extract the longest contiguous digit sequence of length ≥ 4
- generate:
  - `id4:<last4>`
  - `id5:<last5>` (if ≥ 5 digits)
- and SHOULD generate:
  - `id6:<last6>` (if ≥ 6 digits)

Tokens that include `id5` or `id6` SHOULD be treated as higher-confidence than demographic-only matches.

### 3) Ephemeral HMAC tokens (rotating keys)
Tokens are computed as:

```
token = HMAC(key, canonical_tuple_bytes)
```

Keys rotate on a fixed cadence (e.g., monthly) with overlap windows (e.g., current + prior).  
Participants compute tokens with both keys to maintain continuity across rotations.

---

## Key Server (distribution + revocation)
The Key Server provides:
- authenticated key distribution to credentialed participants
- key rotation cadence
- revocation / misuse circuit-breaker

See `docs/key-server.md`.

---

## Docs

- `docs/spec.md` — full protocol spec
- `docs/normalization.md` — recommended normalization + tuple variants
- `docs/key-server.md` — key server behavior and endpoints
- `examples/` — reference inputs + expected token counts
- `test-vectors/` — deterministic vectors for interop

---

## License

MIT (see `LICENSE`).
