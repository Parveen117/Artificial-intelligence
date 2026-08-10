# RNKE Public Red-Team Challenge — Limited Participation Authorization v1

## Effective boundary

This limited authorization becomes effective only when this file is present on the repository's default branch or an official release tag published by the repository owner.

Subject to the conditions below, the repository rights holder grants participants a limited, revocable, non-exclusive, non-transferable permission to:

- clone or download this repository for the purpose of participating in the RNKE public red-team challenge;
- execute the included Challenge Engine locally against the included synthetic fixtures;
- modify challenge candidate fields within the published challenge scope;
- create good-faith reproductions, test cases, reports, issues, and pull requests for submission to this repository;
- quote the minimum repository material reasonably necessary to explain a submitted finding.

## Authorized target

The authorized target is limited to:

```text
Parveen117/Artificial-intelligence
challenge_engine/
red_team_challenge/
included synthetic challenge fixtures
```

and only for the challenge purpose described in `red_team_challenge/README.md`.

## Not authorized

This challenge does **not** authorize participants to:

- test, access, scan, exploit, impair, or interfere with any third-party system;
- test production CELEXTRIX services, live user accounts, real mailboxes, cloud resources, payment systems, domains, hosting accounts, devices, networks, or infrastructure;
- obtain, use, disclose, or attempt to obtain passwords, tokens, private keys, personal data, confidential information, or trade secrets;
- bypass account controls, rate limits, authentication, authorization, billing, or platform restrictions;
- deploy the repository, commercialize it, train competing systems on it, create derivative products, or use it outside the narrow challenge permission;
- create real-world side effects through email, financial, cloud, filesystem, social, hardware, or other external actions.

The Challenge protocol itself grants no authority beyond this file.

## Safety requirements

Participants must:

1. use synthetic data and local/disposable environments;
2. avoid real credentials, secrets, personal data, and private links in submissions;
3. stop immediately if an experiment unexpectedly reaches a real service or creates a real-world side effect;
4. report high-impact findings privately first when public disclosure could create material risk;
5. provide a minimal reproducible case and accurately distinguish observed facts from speculation;
6. comply with applicable law and platform terms.

## Submission and disclosure

A pull request or issue is the normal submission channel. Do not publish secrets, personal information, live exploit credentials, or sensitive operational details.

Maintainers may ask that a high-impact report be moved to a private channel before technical details are discussed publicly. Public credit may be provided with the participant's consent after reproduction and remediation decisions.

## No bounty, employment, or warranty

This authorization does not promise payment, prize, employment, partnership, acceptance, response time, or public credit. No monetary bounty is announced for v1.

The materials are provided as-is and without warranty. Participation is at the participant's own risk.

## Relationship to repository rights

The repository's general `LICENSE`, `PATENT_NOTICE.md`, and `COPYRIGHT_NOTICE.md` continue to apply. This document grants only the narrow permission expressly stated here. No patent license, commercial license, deployment license, or general derivative-work license is granted.

The repository owner may amend, suspend, or withdraw this challenge authorization for future activity. Withdrawal does not retroactively authorize activity that was outside scope.

## Interpretation

When scope is uncertain, treat the activity as unauthorized until the repository owner gives written clarification.
