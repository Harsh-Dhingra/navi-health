# Security

## Reporting a vulnerability

Email **security@[your-domain]** (update this before launch) with details. Do not
open a public GitHub issue for a vulnerability report.

## What's implemented

| Safeguard | Where |
|---|---|
| Field-level encryption for PHI columns (Fernet/AES-128) | [`app/core/crypto.py`](backend/app/core/crypto.py) |
| Password hashing (bcrypt, 72-byte limit enforced) | [`app/core/security.py`](backend/app/core/security.py) |
| Short-lived access tokens + rotating, revocable refresh tokens | [`app/api/routes/auth.py`](backend/app/api/routes/auth.py) |
| httpOnly, Secure, SameSite session cookies (not localStorage) | [`app/api/routes/auth.py`](backend/app/api/routes/auth.py), [`frontend/lib/api.ts`](frontend/lib/api.ts) |
| Account lockout after repeated failed logins | [`app/models/user.py`](backend/app/models/user.py) |
| Rate limiting (per-IP, stricter on auth/chat/upload) | [`app/core/rate_limit.py`](backend/app/core/rate_limit.py) |
| Ownership checks on every resource fetch (no IDOR) | `app/api/routes/*.py` |
| Upload validation: extension/MIME allowlist, size cap, filename sanitization | [`app/api/routes/documents.py`](backend/app/api/routes/documents.py) |
| Structured logging with automatic PHI-field redaction | [`app/core/logging.py`](backend/app/core/logging.py) |
| Append-only audit log of auth, PHI access, escalations, deletions | [`app/core/audit.py`](backend/app/core/audit.py), [`app/models/audit.py`](backend/app/models/audit.py) |
| Security headers (HSTS, X-Frame-Options, nosniff, etc.) | [`app/main.py`](backend/app/main.py) |
| No stack traces / internal errors leaked to clients | [`app/main.py`](backend/app/main.py) |
| Right-to-deletion endpoint (cascades all PHI) | [`app/api/routes/account.py`](backend/app/api/routes/account.py) |
| CI: lint, compile check, automated tests on every push | [`.github/workflows/backend-ci.yml`](.github/workflows/backend-ci.yml) |

## Key management

`FIELD_ENCRYPTION_KEYS` is a comma-separated list of Fernet keys, newest first.
To rotate:

1. Generate a new key, prepend it to `FIELD_ENCRYPTION_KEYS` (keep the old one after it).
2. Deploy — new writes use the new key; existing rows still decrypt with the old one.
3. Run a background job that reads and re-saves every encrypted row (forces re-encryption
   under the new key) — not included in this repo; write one before relying on rotation.
4. Once complete, drop the old key from the list.

Losing every key in `FIELD_ENCRYPTION_KEYS` makes the corresponding data permanently
unrecoverable — back the key up in your secrets manager's own backup mechanism.

## A known trade-off: `COOKIE_SAMESITE=none` and CSRF

The default Render deployment (backend and frontend on separate `*.onrender.com`
subdomains, no shared custom domain) requires `COOKIE_SAMESITE=none` for the auth
cookie to be sent cross-site at all (see `DEPLOYMENT.md` §5b). That weakens the
SameSite cookie's built-in CSRF protection. Two things currently limit the exposure:

1. Every state-changing endpoint requires a JSON body, which forces a CORS
   preflight; the preflight is rejected for any origin not in `CORS_ORIGINS`, so a
   plain cross-site `<form>` POST (which skips preflight) fails FastAPI's JSON
   parsing rather than mutating data.
2. The one endpoint with a real bypass path (`DELETE /api/account`) requires the
   user's current password in the body, which a CSRF attacker cannot supply.

This is **not** a substitute for explicit CSRF protection (e.g. a double-submit
token via `fastapi-csrf-protect`). Add that — or migrate to a shared custom domain
with `COOKIE_SAMESITE=lax` — before this handles PHI for real customers at scale.

## What's explicitly out of scope of this codebase

- **Penetration testing / third-party security audit** — get one before handling real
  PHI at scale. Nothing here substitutes for it.
- **Multi-factor authentication** — not yet implemented. Add before general availability.
- **DDoS protection beyond app-level rate limiting** — rely on your hosting platform's edge protections.
- **Malware/virus scanning of uploaded documents** — not implemented. Add (e.g. ClamAV) before
  accepting uploads from untrusted users at scale.
- **Formal HIPAA risk assessment, workforce training, incident response plan** — see
  [`COMPLIANCE_CHECKLIST.md`](COMPLIANCE_CHECKLIST.md). These are organizational, not
  code, artifacts.
