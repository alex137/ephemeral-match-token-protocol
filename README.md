# EMTP: Ephemeral Match Token Protocol

EMTP is a privacy-preserving protocol for organizations to discover that they refer to the **same person** without sharing demographics in cleartext and without creating durable identifiers.

## How It Works

Each organization:

1. **Normalizes** local identifiers (name, DOB, phone, address) using deterministic rules
2. **Generates tuples** combining normalized fields in standard formats
3. **Computes tokens** by applying HMAC-SHA256 with short-lived shared keys
4. **Matches** by comparing token sets with other organizations

Tokens are **ephemeral** because:
- Token generation depends on short-lived keys (monthly rotation recommended)
- Keys can be rotated and revoked
- Without the key, tokens cannot be reversed to identifiers

## Quick Start

```python
from reference.python.emtp import process_record, decode_key_hex

# Example (use real keys from key server in production)
test_key = decode_key_hex(
    "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
)

result = process_record(
    full_name="John R. Tolkien",
    dob="1892-01-03",
    phones=["(212) 555-0100"],
    keys=[test_key],
)

print(f"Generated {result['tuple_count']} tuples")
print(f"Generated {result['token_count']} tokens")
```

## Repository Structure

```
emtp/
├── spec.md                    # Normative specification (start here)
├── schemas/
│   └── emtp.schema.json       # JSON Schema for input validation
├── reference/
│   └── python/
│       └── emtp.py            # Reference implementation
├── test_vectors/
│   └── emtp_v1_vectors.json   # Conformance test vectors
├── docs/
│   ├── normalization.md       # Normalization examples and guidance
│   └── key-server.md          # Key distribution guidance
└── examples/
    └── example-input.json     # Example input record
```

## Specification

The complete specification is in [`spec.md`](spec.md). Key sections:

| Section | Description |
|---------|-------------|
| 3. Inputs | Required and optional identifier fields |
| 4. Normalization | Deterministic normalization rules |
| 5. Tuple Construction | How to build matchable tuples |
| 6. Token Generation | HMAC computation with domain separation |
| 7. Key Distribution | Key server requirements and rotation |

## Key Concepts

### Normalization (Section 4)

All inputs are normalized to ensure matching despite data variations:

| Input | Normalized |
|-------|------------|
| `MR. JRR Tolkien` | `jrr tolkien` |
| `J. R. R. Tolkien` | `j r r tolkien` |
| `(212) 555-0100` | `2125550100` |

### Tuple Format (Section 5)

Tuples are labeled, pipe-delimited strings:

```
name=jrr tolkien|dob=1892-01-03|phone=2125550100
```

### Token Generation (Section 6)

Tokens include domain separation for security:

```
message = "emtp|v1|" + tuple
token = HMAC-SHA256(key, message)
```

## Key Distribution

EMTP requires a key distribution mechanism. Options include:

- **STP streams** (State Transfer Protocol) for real-time distribution
- **REST API** with authentication
- **Static files** for testing

See [`docs/key-server.md`](docs/key-server.md) for details.

## Conformance

Implementations must pass the test vectors in [`test_vectors/emtp_v1_vectors.json`](test_vectors/emtp_v1_vectors.json).

A conforming implementation:
1. Produces identical normalized outputs for test inputs
2. Generates the same tuples for test records
3. Computes matching tokens with the test key

## Security Properties

- **No raw demographics shared**: Only tokens are exchanged
- **Ephemeral tokens**: Key rotation prevents persistent identifiers
- **Dictionary attack mitigation**: Keys restricted to authenticated participants
- **Revocation support**: Misbehaving participants can be excluded

## License

MIT (see `LICENSE`).
