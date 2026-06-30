.PHONY: test run demo batch docker-build docker-run

test:
	python ai_trust_enablement/run_enablement_tests.py
	python -m compileall ai_trust_enablement

run:
	python ai_trust_enablement/server.py

demo:
	python ai_trust_enablement/ai_hallucination_recognition_engine.py --demo --out demo_certificate.json

batch:
	python ai_trust_enablement/batch_evaluator.py --input ai_trust_enablement/sample_cases.jsonl --output ai_trust_enablement/batch_certificates.jsonl --summary ai_trust_enablement/batch_summary.json

docker-build:
	docker build -t ai-trust-enable:latest .

docker-run:
	docker run --rm -p 8080:8080 ai-trust-enable:latest
