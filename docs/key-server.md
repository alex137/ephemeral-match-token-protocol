# EMTP key distribution using STP

EMTP relies on short-lived keys so match tokens cannot become durable identifiers.

This repo assumes keys (and the code that generates canonical match strings) are distributed via **STP** streams.

## Streams

### 1) Code SURL
An STP table mapping language names to code manifest SURLs.

- **PrimaryKey:** `language` (e.g., `go`, `python`, `js`)
- **Record:** `code_manifest_surl`

A code manifest includes:
- `source_url`
- `source_hash` (verification)
- `version`

The referenced source code MUST only generate canonical match strings.

### 2) Key distribution SURL
An STP table listing active key manifest SURLs.

- **PrimaryKey:** `key_manifest_surl`
- **Record:** `expires_at` (RFC3339 UTC)

Keys are revoked by deleting the row:
- Action: `-`
- PrimaryKey: the key manifest SURL

### 3) Key manifest
A key manifest MUST include:
- the actual key material (base64)
- the algorithm identifier (e.g., `hmac-sha256`)
- any token derivation instructions (prepend/append, separators)
- validity / expiration

## Client behavior

Clients generate canonical strings using the current code for their language.

For each member, they compute the full token set: every canonical string hashed using every unexpired key.

## Server behavior

Key distribution streams are control-plane state and SHOULD be treated as sensitive:
- do not log row contents
- require appropriate access controls for who can read the key distribution stream
