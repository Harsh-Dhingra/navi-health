# HIPAA Readiness Checklist

**This is not legal advice and is not a substitute for a formal risk assessment by
qualified counsel or a compliance consultant.** It exists so you can see, at a glance,
what engineering has covered and what remains — most of what remains cannot be done by
writing code.

Legend: ✅ implemented in this codebase · ⬜ requires action by you (the business)

## Technical safeguards (45 CFR § 164.312)

- ✅ Encryption of PHI at rest (field-level, `app/core/crypto.py`) and in transit (TLS, enforced by hosting platform + HSTS header)
- ✅ Unique user identification, access controls scoped per-user (no cross-account data access — see ownership checks in every route)
- ✅ Automatic session timeout (15-minute access tokens, 7-day refresh with rotation)
- ✅ Audit controls (`audit_logs` table — logs auth events, PHI access, escalations, deletions)
- ✅ Account lockout after repeated failed authentication attempts
- ⬜ Emergency access procedure (a documented "break glass" process for authorized emergency PHI access — not built; needed before production if any workforce member other than the account owner will need emergency access)
- ⬜ Automatic logoff policy documented for any admin tooling you build later
- ⬜ Integrity controls / mechanism to authenticate that PHI hasn't been improperly altered (audit log covers *access*, not a full tamper-evidence scheme — consider write-once storage or hash-chaining if this becomes a requirement)

## Administrative safeguards (45 CFR § 164.308)

- ⬜ **Designate a Privacy Officer and a Security Officer** (can be the same person pre-scale) — required, and not something an engineer or AI agent can designate on your behalf
- ⬜ **Conduct a formal Security Risk Assessment** — required before handling real PHI; hire a HIPAA compliance consultant or use a recognized SRA tool
- ⬜ **Workforce training** on PHI handling, even if "workforce" is currently just you
- ⬜ **Incident response / breach notification plan**, including the 60-day HHS breach notification deadline if a breach occurs
- ⬜ **Sanction policy** for workforce members who violate PHI policies
- ⬜ **Business Associate Agreements** signed with every vendor touching PHI — see [`DEPLOYMENT.md`](DEPLOYMENT.md) §2 for the specific ones this stack needs (hosting, Anthropic, embeddings, any payer/clearinghouse integration)
- ⬜ **Minimum necessary policy** — this codebase implements the technical half (`app/rag/retriever.py` scopes what each agent reads) but the organizational policy documenting *why* and *who reviews it* is still yours to write

## Physical safeguards (45 CFR § 164.310)

- ⬜ Largely inherited from your hosting provider once a BAA is signed (Render's BAA covers this) — confirm what's covered vs. what you're still responsible for (e.g. physical security of any device you use to access the admin database directly)

## Breach preparedness

- ⬜ Cyber liability / tech E&O insurance — strongly recommended, not built into a codebase
- ⬜ A tested process for the legally-required breach notification (affected individuals, HHS, and in some cases media) if PHI is ever exposed

## Before you flip "real customers, real PHI" on

At minimum: BAAs signed (all of them, not just hosting), a risk assessment completed,
a named Privacy/Security Officer, and an incident response plan written down. Consider
this checklist a map of the remaining work, not a certificate of compliance.
