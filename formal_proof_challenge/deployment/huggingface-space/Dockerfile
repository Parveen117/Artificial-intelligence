FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FPG_PUBLIC_MODE=1 \
    FPG_HOST=0.0.0.0 \
    FPG_PORT=7860 \
    FPG_LEDGER_PATH=/data/formal_proof_public_receipts.jsonl \
    FPG_PERSISTENCE_MODE=container-volume-or-ephemeral

WORKDIR /app
RUN useradd --create-home --uid 1000 fpg && mkdir -p /data && chown -R fpg:fpg /data /app
COPY --chown=fpg:fpg formal_proof_challenge /app/formal_proof_challenge
USER fpg
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/healthz', timeout=3).read()"
CMD ["python", "-m", "formal_proof_challenge.app"]
