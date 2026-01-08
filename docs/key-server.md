# EMTP Key Server Protocol

## Purpose

The Key Server distributes a rotating set of shared HMAC keys to **credentialed participants**.
Restricted access is a **privacy circuit breaker**: the Key Server can revoke access for misuse.

The Key Server MUST NOT accept or store demographics.

---

## Endpoint

```
GET /keys?schema=emtp_v1
Accept: application/emtp+json
(mTLS required)
```

### Response (example)

```json
{
  "schema": "emtp_v1",
  "keys": [
    {"kid":"2026-01","not_before":"2026-01-01T00:00:00Z","not_after":"2026-02-01T00:00:00Z","key_b64":"..."},
    {"kid":"2025-12","not_before":"2025-12-01T00:00:00Z","not_after":"2026-01-01T00:00:00Z","key_b64":"..."}
  ]
}
```

- Key material MUST be base64 encoded bytes (`key_b64`)
- Key order is not meaningful
- Key Server MAY return more than two keys (e.g., for longer overlap windows)

---

## Authentication

- **mTLS required**
- participant authorization determined by certificate Policy OID and/or enrollment registry
- Key Server SHOULD publish a CRL/denylist mechanism (serial numbers)

---

## Rotation

- cadence: monthly (recommended default), daily for higher-risk ecosystems
- overlap: at least one prior period, recommended two for resiliency

---

## Caching

- responses SHOULD be cacheable by the client, but never by public intermediaries
- Key Server SHOULD set:
  - `Cache-Control: private, max-age=<...>`
  - `ETag` for efficient refresh

---

## Revocation behavior

On revocation:
- Key Server denies future key fetches for the revoked participant
- optional: rotate keys early + widen overlap window

---

## Non-goals

The Key Server is not a global identity provider.
It is only a key distribution service under governance.

