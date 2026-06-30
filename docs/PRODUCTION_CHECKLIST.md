# Production Checklist

Use this checklist before calling the AI Trust Enablement service production-ready in an actual environment.

## Required

- [ ] Run `python ai_trust_enablement/run_enablement_tests.py` successfully.
- [ ] Build Docker image successfully.
- [ ] Confirm `/healthz`, `/version`, `/schema`, `/v1/evaluate`, and `/v1/batch` work.
- [ ] Set `AI_TRUST_API_TOKEN` before exposing the service.
- [ ] Put the service behind TLS.
- [ ] Configure request body limit and batch limit.
- [ ] Confirm prompt/answer logging is disabled or compliant with policy.
- [ ] Create regression cases for your own domain.
- [ ] Validate threshold behavior on grounded, unsupported, contradictory, and paraphrased answers.
- [ ] Monitor false positives and false negatives before using it to block user-visible output.

## Recommended

- [ ] Put service behind a reverse proxy such as NGINX, Caddy, or platform ingress.
- [ ] Add external observability: latency, error count, classification count, open residue histogram.
- [ ] Store certificates in an append-only audit store.
- [ ] Rotate API tokens.
- [ ] Version model IDs and prompt templates.
- [ ] Use staged rollout: shadow mode, review mode, then gating mode.

## Operating modes

| Mode | Action |
|---|---|
| Shadow | Generate certificates but do not alter output |
| Review | Flag suspicious answers for human review |
| Gating | Block, defer, retrieve, or regenerate when `ACTIONABLE_RESIDUE` occurs |
| Audit | Store all certificates for post-run review |

## Non-goals

This service is not a final truth oracle, not a substitute for retrieval, not a legal or medical authority, and not a magical hallucination exorcist. It is a practical certificate and gating layer. Annoyingly, reality still requires validation.
