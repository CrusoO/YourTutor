# ADR-013: Sign-in (D13): a way in for everyone that never fails

**Status:** Accepted (founder default, revised 5 Nov 2026 for "everyone")
**Date:** 2026-11-05
**Decision ID:** D13

## Context

The founder asked for sign-in for everyone. Students are often minors without their own email. Login failures were a Phase 0 problem (storage, SMTP, OTP lockout).

## Decision

- **Phase 1:** email OTP (fixed), Google sign-in (adults and guardians), teacher class code (students join a class; no child email needed), and family PIN.
- **Phase 2:** phone or WhatsApp OTP. This needs Indian SMS DLT registration or WhatsApp Business templates [From memory, to verify]. Ask the founder before signing up for any provider.
- **Phase 3:** company SSO.
- Every path falls back to a guest session that cannot fail (`safeStorage`, which never throws).

| Who | How they get in |
|---|---|
| Anyone, first visit | Guest plus a neutral age question |
| Students (Board Sprint, school pilot) | Teacher class code or guardian sign-up |
| Guardians | Email OTP or Google |
| Adults | Google or email OTP |

## Consequences

- Self-declared age is never treated as verified consent.
- Tiers never add actions (see the action registry rule in `docs/PRODUCT.md`).
- Class codes and consent records link to the school-mode design in v1.2.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D13, prompt section 1 D13, section J (parent folder, not in this repo).

## Revisions

- 2026-11-05: revised to "sign-in for everyone" with class codes and Google.
