# Key Distribution Guide

This document provides additional guidance on EMTP key distribution. For the normative specification, see [spec.md](../spec.md) Section 7.

## Overview

EMTP tokens are made ephemeral through short-lived keys. The key distribution system must:

1. **Authenticate participants** before providing keys
2. **Rotate keys regularly** (monthly recommended)
3. **Support overlap** between key epochs for continuity
4. **Enable revocation** for compromised or misbehaving participants

## Key Manifest Format

Each key is described by a manifest:

```json
{
  "kid": "2026-01",
  "key": "base64-encoded-32-byte-key",
  "algorithm": "hmac-sha256",
  "not_before": "2026-01-01T00:00:00Z",
  "not_after": "2026-02-01T00:00:00Z"
}
```

| Field | Description |
|-------|-------------|
| `kid` | Unique key identifier, typically epoch-based (e.g., `2026-01`) |
| `key` | 256-bit key material, base64 encoded |
| `algorithm` | Always `hmac-sha256` for EMTP v1 |
| `not_before` | Start of validity window (RFC3339 UTC) |
| `not_after` | End of validity window (RFC3339 UTC) |

## Distribution Options

### Option 1: STP-Based Distribution

Keys can be distributed via STP (State Transfer Protocol) streams:

**Code Distribution Stream**
- Maps languages to code manifest SURLs
- Primary key: `language` (e.g., `python`, `go`, `js`)
- Record: `code_manifest_surl`

**Key Distribution Stream**
- Lists active key manifest SURLs
- Primary key: `key_manifest_surl`
- Record: `expires_at` (RFC3339)
- Revocation: Delete row (action `-`)

### Option 2: REST API

A simple HTTPS API endpoint:

```
GET /keys
Authorization: Bearer <token>

Response:
{
  "keys": [
    { "kid": "2026-01", "key": "...", ... },
    { "kid": "2025-12", "key": "...", ... }
  ]
}
```

### Option 3: Static Distribution

For testing or low-volume deployments, keys can be distributed as static files with access controls.

## Client Behavior

1. **Fetch keys** from the key server (with authentication)
2. **Cache keys** locally with their validity windows
3. **Generate tokens** using all non-expired keys
4. **Refresh keys** before current epoch ends

Token generation uses all currently valid keys:

```python
tokens = set()
for key in active_keys:
    for tuple in tuples:
        tokens.add(compute_token(key, tuple))
```

## Server Behavior

The key server MUST:

1. **Authenticate all requests** (mTLS, OIDC, API key, etc.)
2. **Log access** for audit purposes (without logging key material)
3. **Serve at least 2 epochs** (current + previous)
4. **Support revocation** by removing keys from distribution
5. **Protect key material** as highly sensitive data

## Rotation Timeline

Recommended monthly rotation with overlap:

```
January:
  - Active keys: 2025-12, 2026-01
  - Participants compute tokens with both keys

February:
  - Active keys: 2026-01, 2026-02
  - 2025-12 tokens naturally expire from matching
```

## Security Considerations

1. **Key secrecy**: Keys must never be logged, embedded in code, or transmitted insecurely
2. **Access control**: Only authenticated, authorized participants receive keys
3. **Revocation**: Support immediate revocation for compromised participants
4. **Audit logging**: Log who accessed keys and when (but not the keys themselves)
5. **Key generation**: Use cryptographically secure random number generators

## Example: Testing Without Key Server

For development/testing, use a fixed test key:

```python
# DO NOT USE IN PRODUCTION
TEST_KEY = bytes.fromhex(
    "000102030405060708090a0b0c0d0e0f"
    "101112131415161718191a1b1c1d1e1f"
)
```

This key is used in test vectors and reference implementation examples.
