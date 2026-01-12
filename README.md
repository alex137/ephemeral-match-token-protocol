# EMTP: Ephemeral Match Token Protocol

EMTP is a way for independent organizations to discover that they likely refer to the **same person** (member/patient) without sharing demographics in cleartext and without creating durable identifiers.

At a high level, each organization:
1. turns local identifiers into one or more **canonical match strings**
2. applies one or more **short-lived keys** to those strings to generate **match tokens**
3. uses token overlap to route the right request to the right endpoint

EMTP is designed so that tokens are **not usable as durable identifiers**:
- token generation depends on short-lived keys
- keys can be rotated/expired and revoked

---

## EMTP + STP

EMTP assumes three STP state streams:

### 1) Code SURL (canonical string generators)
An STP table mapping programming languages to *source-code manifests*.

- **PrimaryKey:** `language` (e.g., `go`, `python`, `javascript`)
- **Record:** `code_manifest_surl`

Each code manifest points to source that deterministically generates canonical strings from local identifiers. The published code should generate canonical strings only (not tokens), so keying policy lives with the key distribution stream.

### 2) Key distribution SURL (active keys)
An STP table listing active key manifests.

- **PrimaryKey:** `key_manifest_surl`
- **Record:** `expires_at` (RFC3339 UTC)

Deleting a `key_manifest_surl` row revokes that key (even before `expires_at`).

### 3) Key manifest SURLs (per-key details)
Each key manifest is an STP stream (or a static document) that contains:
- the **key material** (as bytes / base64)
- the **key algorithm ID** and hashing details
- any canonical instructions (e.g., whether to prepend/append the key)
- the key’s effective period

---

## How to generate match tokens

1) Generate your canonical string set using the current code for your language.

2) Fetch the current key distribution SURL.

3) For each unexpired key manifest:
- load the manifest
- compute tokens for **each canonical string** using the manifest’s algorithm

**A complete match-token set** is: *every canonical string hashed with every unexpired key*.

---

## Why STP

Using STP for EMTP coordination makes the control plane:
- cacheable (poll or stream)
- replayable (gap recovery)
- auditable (ordered change log)

See:
- `docs/spec.md`
- `docs/key-server.md`

---

## License

MIT (see `LICENSE`).
