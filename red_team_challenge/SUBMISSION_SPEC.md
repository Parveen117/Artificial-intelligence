# RNKE Red-Team Submission Specification v1

## Goal

A submission must let an independent maintainer reproduce the exact evaluated candidate and determine whether it is outside the pinned authority contract while RNKE still returns executable `ADMIT`.

The submission package is evidence, not an automatic verdict.

## Directory layout

```text
red_team_challenge/submissions/<github-handle>/<case-id>/
├── challenge.json
├── observed.json
├── submission.json
└── README.md          # optional explanatory narrative
```

All paths in `submission.json` are repository-relative. Absolute paths and `..` traversal are rejected.

## Required `submission.json` fields

- `schema_version`: must be `1.0`;
- `submission_id`: stable lowercase identifier;
- `participant.handle`: GitHub or public research handle;
- `engine_subject_commit`: the engine commit pinned by `CHALLENGE_MANIFEST.json`;
- `challenge_file`: repository-relative path to the candidate fixture;
- `observed_output_file`: repository-relative path to the exact compact or pretty JSON output;
- `pinned_genesis_sha256`: expected frozen authority Genesis;
- `claimed_break_class`: one of the published break classes;
- `authorization_argument`: precise explanation of why the frozen contract does not authorize the candidate;
- `reproduction_command`: command used to reproduce the output;
- `environment`: Python version and operating system;
- `safety_acknowledgement`: exact scope acknowledgement;
- `evidence`: optional references, notes, or deterministic seeds.

The machine schema is [`submission.schema.json`](submission.schema.json).

## Reproduction requirements

The verifier independently:

1. loads JSON with duplicate-key rejection;
2. checks safe repository-relative paths;
3. evaluates the candidate through the checked-in Challenge Engine;
4. compares the fresh result with `observed.json` using canonical JSON;
5. checks that the fresh Challenge Genesis equals the pinned launch Genesis;
6. checks that the fresh result contains `action_decision == ADMIT` and `action_executable == true` when a break candidate is required.

Run:

```bash
python red_team_challenge/verify_submission.py \
  red_team_challenge/submissions/<github-handle>/<case-id>/submission.json \
  --require-break-candidate
```

A successful verifier result means only:

```text
REPRODUCIBLE_ADMIT_CANDIDATE
```

It does not prove that the action was unauthorized. That question requires independent contract analysis.

## Authorization argument

The argument must identify the exact violated frozen rule, such as:

- tool mismatch;
- operation mismatch;
- resource mismatch;
- executable parameter/action-hash mismatch;
- principal or agent mismatch;
- invalid delegation edge;
- delegation escalation or cycle;
- revoked/expired grant;
- consumed request nonce;
- missing or stale exact-action confirmation;
- frozen authority mutation with unchanged Genesis.

A statement such as "this looks malicious" is insufficient. Malicious language is not the authority boundary.

## Observed output

`observed.json` must be the unmodified engine output for `challenge.json`. Do not hand-edit digests, Genesis, checks, decisions, or evaluation records.

The verifier rejects output drift.

## Genesis discipline

For the flagship fixture:

```text
candidate mutation      -> pinned Genesis must remain unchanged
authority/rule mutation -> different Genesis or integrity failure
```

A candidate using a different Genesis is not a break of the pinned challenge. It may still be a useful proposal for a new challenge contract.

## Non-break reports

These are useful but are classified separately unless they violate a documented claim:

- malformed JSON rejected as `INVALID`;
- parser or CLI crash;
- denial of service or excessive resource use;
- ambiguous documentation;
- a model producing harmful text;
- an unauthorized candidate correctly returning `REJECT` or `INCOMPLETE`;
- a different authority contract producing a different Genesis;
- bypassing RNKE entirely through a separate compromised executor.

Use an ordinary issue for these findings rather than claiming a flagship break.

## Adjudication states

Maintainers may classify a report as:

- `REPRODUCED_BREAK`;
- `REPRODUCED_NON_BREAK`;
- `DUPLICATE`;
- `INSUFFICIENT_EVIDENCE`;
- `OUT_OF_SCOPE`;
- `NEEDS_PRIVATE_HANDLING`;
- `ENGINE_BUG_NOT_CORE_BREAK`;
- `NEW_CHALLENGE_CONTRACT`.

## Confidentiality and secrets

Do not include passwords, tokens, private keys, personal data, live account identifiers, or sensitive links. Use synthetic replacements.
