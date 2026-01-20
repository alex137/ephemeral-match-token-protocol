# Key Server (v0.3)

The Key Server distributes rotating HMAC keys to credentialed participants.

## Requirements
- Authenticate participants (e.g., mTLS / OAuth)
- Issue current + prior keys
- Rotate on fixed cadence (e.g., monthly)
- Support revocation (deny key access)

## Suggested endpoints

### GET /keys
Returns JSON:

```json
{
  "schema": "emtp_keys",
  "version": 1,
  "rotation": "monthly",
  "current": { "key_id": "2026-01", "key_b64": "<base64>" },
  "prior":   { "key_id": "2025-12", "key_b64": "<base64>" }
}
```

Participants MUST compute tokens for both keys.

## Revocation
Key Server MUST deny access to revoked participants.
Key Server SHOULD maintain audit logs of key fetches.
