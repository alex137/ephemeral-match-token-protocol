# Ephemeral Match Token Protocol (EMTP)

**EMTP** is a small, privacy-preserving convention for letting multiple parties determine whether they are referring to the **same person** *without sharing raw identifiers* (name, DOB, address, phone, etc.).

It works by having participants compute **rotating HMAC-based match tokens** from common identifier tuples using **time-limited shared keys** distributed by a trusted **Key Server**. Parties exchange only tokens (not demographics). Matches are computed locally by set intersection.

EMTP is designed to be:
- **Ephemeral:** tokens rotate (e.g., monthly) and do not become a persistent identifier
- **Privacy-preserving:** the key server never receives demographics; registries can store only tokens
- **Fault-tolerant:** variants handle messy real-world identity strings
- **Standardizable:** a shared algorithm + test vectors enables interop across ecosystems

---

## TL;DR

1. A **Key Server** publishes rotating HMAC keys to **credentialed participants**.
2. Each participant canonicalizes a person’s identifiers into multiple **normalized variants**.
3. The participant computes a **set of HMAC tokens** over those variants for **current + prior keys**.
4. Parties exchange tokens (e.g., via STP tables, files, APIs).
5. A match is determined by local intersection of token sets.

**No party needs to reveal raw identity data to another party** to discover matches.

---

## Why EMTP?

Identity matching is everywhere:
- healthcare (patient matching)
- finance (KYC / fraud / AML)
- insurance (claims)
- travel (loyalty / passenger identity)
- consumer platforms (account linking)
- research + RWE (recruitment, longitudinal linkage)

Today, most matching requires sending raw PII to a counterparty or a central broker.

**EMTP provides a middle path:** *match without disclosure*, using short-lived keyed tokens that are useless outside the rotation window.

---

## Threat Model (high level)

EMTP aims to prevent:
- A registry or broker from becoming a permanent “national identifier” database
- Token reuse across time (tracking / correlation)
- Reverse-mapping tokens back to demographics (without possession of keys and large auxiliary datasets)
- Untrusted entities from mass-producing tokens (access is credentialed)

EMTP does **not** magically eliminate all risks:
- Key leakage compromises the window of tokens derived from those keys
- Small candidate sets can still enable inference attacks
- Organizations must still follow privacy law and minimization norms

EMTP’s design is about making the *default* behavior safer and harder to abuse.

---

## Core Concepts

### Match Token
A match token is an HMAC of a canonicalized identifier tuple variant:

```
token = HMAC(key, tuple_variant_bytes)
```

Tokens are represented as lowercase hex strings.

### Tuple Variant
A tuple variant is one normalized combination of:
- **name**
- **date_of_birth**
- **address**
- **phone**
- **id_numbers** *(optional: last4/last5/last6 digits of any IDs)*

Because real-world data is messy, each field expands into multiple variants.

### Rotating Keys
Keys are rotated on a fixed cadence (e.g., monthly) with overlap windows:
- participants compute tokens using **current + prior** keys
- matching remains continuous across rotation
- tokens are not stable identifiers over time

---

## Key Server (Protocol Overview)

A Key Server MUST provide:
- **Key distribution endpoint** (authenticated; credentialed participants only)
- **Key schedule** (rotation cadence, overlap rules)
- **Key identifiers** (key_id) included in responses
- **Revocation mechanism** (cut off key access for abusive participants)
- **Auditability** (key issuance logs at the server side)

Recommended:
- rotate monthly (or weekly in high-risk environments)
- include at least **current + prior** keys in each response
- publish clear norms for how long prior keys remain valid for matching

### Example distribution response (illustrative)

```json
{
  "schema": "emtp_keys_v1",
  "issued_at": "2026-01-01T00:00:00Z",
  "keys": [
    {"key_id": "2026-01", "hmac_key_b64": "....", "not_before": "...", "not_after": "..."},
    {"key_id": "2025-12", "hmac_key_b64": "....", "not_before": "...", "not_after": "..."}
  ]
}
```

> **Important:** The Key Server never receives demographics. Participants request keys, then compute tokens locally.

---

## Canonicalization and Variant Expansion

EMTP’s effectiveness comes from canonicalization + variants.

### Names

Real inputs can look like:
- `"MR. JRR TOlkein"`
- `"John R. R. Tolkien Sr"`
- `"J. R. R. Tolkien"`
- `"Tolkien, John Ronald Reuel"`

EMTP handles this by:
1. **Lowercasing**
2. Removing punctuation
3. Removing or ignoring common **honorifics** (mr, mrs, dr, prof, etc.)
4. Collapsing whitespace
5. Recognizing and separating **suffixes** (jr, sr, ii, iii, iv, v)
6. Generating variants such as:
   - full first name vs initial
   - with/without middle names
   - with/without suffix
   - “last, first” vs “first last” normalization

**Suffix parsing is required** because it is a critical disambiguator.

> Why keep suffix separate? Because a single freeform name field may include it, and the library must standardize it.

### DOB
DOB must normalize to ISO: `YYYY-MM-DD`.
Variants may include:
- full DOB
- year-only (optional, controlled by policy)
- month+year (optional)

### Phone
Normalize to E.164 when possible.
Variants may include:
- last 4 digits (optional; policy-controlled)
- stripped digits only

### Address
Canonicalize using:
- uppercase/lowercase normalization
- street suffix normalization (st/street)
- unit/apartment normalization
- ZIP truncation (5-digit vs 9-digit)

### ID Numbers (optional)
EMTP supports a generic `id_numbers` field containing **digits** from any identifier source (SSN, driver license, passport fragments, member IDs, etc.) without requiring type tags.

From any supplied digit string, EMTP derives variants:
- last4
- last5
- last6 *(optional)*

This allows disambiguation when two people share name + DOB + address.

> Many workflows request **last5** (common in healthcare). Supporting last4/last5/last6 provides flexibility without standardizing every ID format.

---

## Collision Handling

It is possible for two distinct individuals to collide (e.g., family members sharing address and DOB).

EMTP is designed so collisions can be resolved by:
- including additional tuple fields (phone, id_numbers fragments)
- using higher-quality input normalization
- applying policy: if multiple matches, require user confirmation or stronger identifiers

Collisions are not catastrophic—they are surfaced for resolution rather than silently producing false certainty.

---

## Using EMTP with STP (Recommended)

EMTP is transport-agnostic. Tokens can be exchanged via:
- STP tables
- files
- APIs
- message queues

But STP is a natural fit:
- STP provides a minimal, auditable streaming table format
- EMTP tokens become the “Record” field value(s)

Example STP row:

```
[SeqNo] \t [TS] \t + \t [Endpoint_URL] \t [token1 token2 token3 ...]
```

---

## Reference Implementation

This repo contains:
- **Spec** describing canonicalization + token generation
- **Schemas** for key distribution + token sets
- **Test vectors** to ensure interoperability
- **Reference code** (planned / in progress) in one or more languages

See:
- `docs/spec.md`
- `schemas/`
- `test_vectors/`

---

## Design Goals

EMTP is optimized for:
- **privacy** (no raw PII exchange)
- **interoperability** (shared normalization + test vectors)
- **rotation** (ephemeral tokens)
- **auditability** (deterministic functions, reproducible results)
- **practicality** (works with messy data)

---

## Non-Goals

EMTP is *not*:
- a full identity proofing system
- a substitute for legal consent / authorization
- a guarantee of uniqueness
- a cryptographic multi-party computation protocol

It is a pragmatic standard for safer matching.

---

## Contributing

PRs welcome. High-impact contributions:
- additional locale-aware normalization rules
- reference implementations (Go, Python, JS)
- better address canonicalization strategies
- expanded test vectors (edge cases, international names)
- key server operational guidance

---

## License

MIT (see `LICENSE`).
