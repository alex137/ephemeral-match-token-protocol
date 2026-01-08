# Threat Model & Safety Constraints

## Primary risks

- **Linkability / tracking:** tokens could enable correlation across ecosystems
- **Token reversal attempts:** brute force or dictionary attacks over demographics
- **Key leakage:** compromise yields widespread linkage risk
- **Misuse by participants:** using tokens for prohibited purposes (ads, surveillance)

---

## Mitigations

### Ephemerality
- rotating keys + overlap windows prevent persistent identifiers

### Restricted access
- keys available only to credentialed participants
- revocation is a circuit breaker

### No demographics in the registry
- servers match only on tokens, never store identifiers

### Rate limiting + anomaly detection
- detect suspicious fetch patterns or brute-force attempts

---

## Explicit non-goals

EMTP is not designed to support:
- public identity graphs
- advertising tracking
- cross-site targeting
- persistent universal identifiers

---

## Recommended governance constraints

- audited participant enrollment
- signed acceptable-use policy
- enforcement penalties for misuse
- independent oversight for key server operations

