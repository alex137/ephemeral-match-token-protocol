# EMTP Core Spec (v1)

## Overview

EMTP defines:
1) how a **Key Server** distributes a rotating set of HMAC keys to authorized participants
2) how clients canonicalize + expand identifiers into **tuple variants**
3) how clients compute a **set of HMAC tokens** for matching

The registry/server never receives demographics and never stores a stable identifier.

---

## Token definition

Given:
- identifier tuple variant `t` (bytes)
- key `k` (bytes)

Token:
- `HMAC_SHA256(k, t)` → hex-encoded lowercase string

Tokens are **not persistent** across rotations.

---

## Input fields (minimum)

EMTP v1 defines the following canonical fields:
- `full_name` (string)
- `dob` (YYYY-MM-DD)
- `phone` (E.164 or normalized digits)
- `address` (string normalized)

Implementations MAY include additional fields, but must not break compatibility.

---

## Canonicalization (v1)

- trim whitespace
- lowercase
- normalize punctuation
- phone: digits only, preserve country code if present
- address: normalize common abbreviations (e.g., "st" → "street") where feasible

See `schemas/emtp_v1.md` for exact rules.

---

## Tuple variant expansion

To improve match recall, clients generate a set of variants, e.g.:
- name: first/last swaps, middle initial optional, nickname list
- phone: with/without country code, last-10 digits
- address: unit stripped vs included, common abbreviations expanded

Variants MUST be deterministic given the same input.

---

## Token set construction

For each tuple variant `t` and each active key `k`:
- compute `HMAC_SHA256(k, t)`
- collect into a set
- deduplicate

Clients SHOULD publish/post tokens in arbitrary order.

---

## Key overlap window

Key Server returns:
- `current` key
- `prior` key (at minimum)

This ensures matching continuity during rotation boundaries.

---

## Security circuit breaker

Key Server MUST be able to revoke key access for misuse by:
- denying requests from revoked certificate serials
- rotating keys early if required

See `docs/key-server.md`.

