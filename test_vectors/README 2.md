# EMTP Test Vectors

This folder contains deterministic test vectors for **Ephemeral Match Token Protocol (EMTP)**.

- `emtp_vectors_v0.3.json` includes:
  - a fixed test key (HMAC-SHA256) and
  - a small set of inputs (names, DOB, phone, address, id numbers)
  - derived canonical forms + selected tuple strings
  - expected HMAC outputs for those tuples

## How to use

1. Implement EMTP canonicalization and tuple expansion per `docs/spec.md`.
2. For each vector, generate the same tuple strings.
3. Compute `HMAC-SHA256(key, tuple_string)` and compare to expected outputs.

> Note: Production deployments **must not** use the fixed test key. Test vectors exist only for interoperability.
