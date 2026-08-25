> **DRAFT — NOT LEGAL ADVICE.** This is a starting point for your attorney, not a
> finished document. A real privacy policy for a product handling health data needs
> review for HIPAA, state health-data laws (e.g. Washington's My Health My Data Act,
> CMPA, CCPA/CPRA if you have California users), and — if you ever have EU/UK users —
> GDPR/UK GDPR. Do not publish until reviewed. Replace every `[bracketed]` placeholder.

# Privacy Policy

**Effective date:** `[date]` **Entity:** `[Legal business name]`, a `[state]` `[entity type]` ("NAVI," "we," "us")

## What we collect

- **Account information**: email, name, hashed password.
- **Health and insurance information you provide or upload**: insurance policy details,
  claims, explanations of benefits, medications, visit history, and any documents you
  upload (insurance cards, EOBs, etc.).
- **Usage data**: chat requests you send NAVI, and the agent workflow's resulting
  records (which we call "care journeys"), retained so you can see your history.
- **Technical data**: IP address and request metadata, retained briefly for security
  (rate limiting, abuse prevention) and audit logging.

## How we use it

- To operate the service: answering your requests, retrieving only the data each
  step of that request needs (see "Data minimization" below), and storing the result
  as your care journey history.
- To improve safety: our safety-review step logs when it flags a response for human
  review; we use these logs to improve the product, not to make decisions about you
  outside the product.
- We do **not** sell your data. We do **not** use your health data to train general-purpose
  AI models unless we tell you specifically and get your opt-in consent first.

## Who we share it with

- **Anthropic** (our AI provider), to process your requests. `[Confirm current status:
  are you operating under an Anthropic BAA? If yes, state that here and describe
  Anthropic's data retention terms as disclosed in that agreement — as of this
  drafting, BAA-covered API usage requires 30-day retention on Anthropic's side.]`
- `[Your hosting provider]`, which stores the underlying (encrypted) data.
- `[Any embeddings provider, e.g. Voyage AI, if enabled]`.
- `[Any payer/clearinghouse integration you enable, e.g. Availity]`, only for the
  specific coverage/cost/authorization check you request.
- We do not share your data with any other third party except as required by law, or
  with your explicit consent.

## Data minimization

Each of NAVI's specialist agents is scoped to only the category of your data it needs
for the task at hand (e.g. the cost-estimate agent does not read your medication
list). See `app/rag/retriever.py` in our public repository for the enforced technical
implementation of this policy, not just a promise.

## Your rights

- **Access**: you can view your stored data through the product.
- **Deletion**: you can permanently delete your account and all associated data at
  any time via account settings (technically: `DELETE /api/account`). This is
  irreversible.
- `[State-specific rights: California (CCPA/CPRA), Washington (MHMDA — note MHMDA's
  private right of action and specific "consumer health data" consent requirements),
  and any other state where you have users, need explicit sections here.]`

## Security

We encrypt health-related data fields at rest and encrypt all data in transit. See
our [Security page](../SECURITY.md) for detail. No system is perfectly secure; see
"Breach notification" below for what happens if something goes wrong.

## Breach notification

`[Describe your process and legally-required timelines — under HIPAA, affected
individuals must generally be notified within 60 days of discovery of a breach of
unsecured PHI, with additional requirements depending on breach size. Confirm exact
obligations with counsel.]`

## Retention

`[Define exactly how long you keep data after account deletion, backup retention
windows, and audit log retention — get this reviewed against your specific BAAs,
since some vendor BAAs impose their own minimum/maximum retention windows.]`

## Contact

`[support email]` · `[mailing address, if required in your jurisdiction]`
