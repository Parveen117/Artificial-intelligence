# FPG3 public launch and external anchor

FPG3 converts the local FPG1/FPG2 demonstration into a hosted red-team surface with an independently publishable ledger checkpoint.

## Hosted service

The app supports hosted defaults through environment variables:

```text
FPG_PUBLIC_MODE=1
FPG_HOST=0.0.0.0
FPG_PORT=7860
FPG_LEDGER_PATH=/data/formal_proof_public_receipts.jsonl
FPG_MAX_LEDGER_ENTRIES=10000
FPG_ALLOW_SEAL=1
FPG_PUBLIC_APP_URL=https://example-space.hf.space
FPG_PUBLIC_ANCHOR_URL=https://example.github.io/Artificial-intelligence/
FPG_SOURCE_REVISION=<exact git commit>
```

Public endpoints:

```text
/healthz       service and ledger health
/api/config    public deployment settings
/api/stats     action counts and ledger head
/api/anchor    externally publishable checkpoint
```

In public mode, local filesystem paths are removed from API responses.

## Docker Space bundle

Build a self-contained Hugging Face Docker Space directory:

```bash
python formal_proof_challenge/deployment/build_hf_space_bundle.py \
  --output dist/formal-proof-gate-space \
  --source-revision "$(git rev-parse HEAD)"
```

The bundle includes a Space metadata README, Dockerfile, source package, fixtures, schemas, threat model, and a SHA-256 manifest. Docker Spaces use port `7860`.

The workflow `.github/workflows/fpg3-deploy-space.yml` can create or update a Space after these repository settings exist:

```text
Secret   HF_TOKEN
Variable HF_SPACE_REPO     example: MontyDabas/formal-proof-gate
```

Run **FPG3 Deploy Public Space** manually from GitHub Actions.

## External anchor

Build a local checkpoint:

```bash
python -m formal_proof_challenge.anchor \
  --ledger formal_proof_challenge/outputs/formal_proof_public_receipts.jsonl \
  --output latest-anchor.json \
  --source-revision "$(git rev-parse HEAD)"

python -m formal_proof_challenge.anchor --verify latest-anchor.json
```

The anchor binds:

```text
rule-set id and hash
ECL policy id and hash
IEL information invariant
receipt count
COMMIT / REJECT totals
receipt Merkle root
final IEL state
last ledger-entry hash
source revision
public app URL
```

`anchor_hash` is stable while the ledger state is unchanged. `document_hash` also binds the observation timestamp.

The workflow `.github/workflows/fpg3-anchor-pages.yml` can fetch `/api/anchor`, verify it, upload an immutable Actions artifact, and optionally publish the checkpoint through GitHub Pages.

Repository variables:

```text
FPG_PUBLIC_APP_URL     example: https://owner-space.hf.space
FPG_PAGES_ENABLED     set to true only after Pages uses GitHub Actions
```

GitHub Pages must be enabled with **Settings → Pages → Source: GitHub Actions** before `FPG_PAGES_ENABLED=true` is set.

## Public break submissions

The repository contains `.github/ISSUE_TEMPLATE/formal-proof-gate-break.yml`. Enable GitHub Issues under **Settings → General → Features** before launch.

A submitted case should include:

```text
minimal admitted proof JSON
why the derivation is invalid
observed certificate or receipt
exact source revision
receipt, anchor, or ledger-head hash
clean reproduction steps
```

Unknown syntax returning `PARSE_NOT_ADMITTED` is not a proof-gate break.

## Persistence boundary

A container filesystem may be ephemeral. Without a persistent volume or external evidence store, receipts can disappear after a restart. The public anchor makes replacement detectable only after somebody independently retains the anchor hash, Pages commit, workflow artifact, or another published checkpoint.

The public receipt and anchor remain tamper-evident research objects. They are not digital signatures, signer identities, trusted timestamps, distributed consensus, cryptocurrencies, or legal notarization.

## Launch order

1. Merge the reviewed PR and tag an immutable release.
2. Enable Issues and GitHub Pages.
3. Configure `HF_TOKEN` and `HF_SPACE_REPO`.
4. Run the Space deployment workflow.
5. Set `FPG_PUBLIC_APP_URL` to the resulting public app endpoint.
6. Run the external-anchor workflow and retain the first anchor hash.
7. Publish the challenge with the exact rule-set hash, release tag, app URL, anchor URL, and break criterion.
