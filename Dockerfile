FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AI_TRUST_HOST=0.0.0.0 \
    AI_TRUST_PORT=8080 \
    AI_TRUST_RATE_LIMIT_PER_MIN=120 \
    AI_TRUST_MAX_BODY_BYTES=1000000

WORKDIR /app
COPY . /app

RUN python -m compileall ai_trust_enablement

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import json,urllib.request; print(json.loads(urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3).read())['ok'])"

CMD ["python", "ai_trust_enablement/server.py"]
