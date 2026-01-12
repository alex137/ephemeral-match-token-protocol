# EMTP Specification (Draft)

EMTP (Ephemeral Match Token Protocol) defines how organizations generate **match tokens** that enable probabilistic person matching without sharing demographics in cleartext and without creating durable IDs.

This repo specifies:
- how to generate canonical match strings
- how to combine those strings with short-lived keys to create tokens
- how to distribute code and keys via STP (State Transfer Protocol)

---

## 1. Canonical match strings

Implementations generate a set of canonical strings from local identifiers (e.g., name, DOB, address, phone). Canonicalization details are provided as source code referenced by the **Code SURL**.

**Important:** the canonical-string code SHOULD NOT embed keys or produce tokens. It outputs deterministic strings.

---

## 2. Keys and key manifests

Tokens are made short-lived by using short-lived keys.

A **key manifest** describes exactly how to turn a canonical string into a match token, including:
- key material (base64)
- algorithm ID (e.g., HMAC-SHA256)
- any canonical instructions (prepend/append, separators)
- validity window / expiration

---

## 3. Token generation

Given:
- `S`: the set of canonical strings
- `K`: the set of active keys from the key distribution stream

A complete match token set is:

```
T = { token(k, s)  for each k in K  for each s in S }
```

Where `token(k, s)` is defined by the key manifest.

---

## 4. STP streams

EMTP uses STP as its coordination/control plane.

### 4.1 Code SURL
An STP table mapping languages to code manifest SURLs.

- PrimaryKey: `language`
- Record: `code_manifest_surl`

A code manifest points to:
- source code (or a versioned archive)
- a verification hash
- optional build/run instructions

### 4.2 Key distribution SURL
An STP table listing active key manifests.

- PrimaryKey: `key_manifest_surl`
- Record: `expires_at` (RFC3339 UTC)

A key is active if it:
- is present in the key distribution table, and
- has not expired

Keys can be revoked early by a delete row (`-`) for the `key_manifest_surl`.

### 4.3 Key manifest SURLs
Key manifests contain the key material and token derivation instructions.

They may be STP streams (append-only) or static documents, but MUST be immutable by reference (versioned URL or content-addressed).

---

## 5. Security properties (informal)

- Tokens are not durable identifiers because they depend on short-lived keys.
- Organizations never need to send demographics to the matching service; they publish tokens.
- Revocation is immediate by deleting a key manifest from the distribution stream.
