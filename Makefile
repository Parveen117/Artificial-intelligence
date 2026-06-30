.PHONY: test run demo batch panini claims frames fusion docker-build docker-run

test:
	python ai_trust_enablement/run_enablement_tests.py
	python -m compileall ai_trust_enablement

run:
	python ai_trust_enablement/server.py

demo:
	python ai_trust_enablement/ai_hallucination_recognition_engine.py --demo --out demo_certificate.json

batch:
	python ai_trust_enablement/batch_evaluator.py --input ai_trust_enablement/sample_cases.jsonl --output ai_trust_enablement/batch_certificates.jsonl --summary ai_trust_enablement/batch_summary.json

panini:
	python ai_trust_enablement/paninian_meta_engine.py --rule 1.1.6 --rule 1.1.24

claims:
	python ai_trust_enablement/panini_nyaya_claim_verifier.py --demo --out panini_nyaya_report.json

frames:
	python ai_trust_enablement/claim_frame_kernel.py --demo --out claim_frame_report.json

fusion:
	python ai_trust_enablement/fusion_certificate_engine.py --demo --out fusion_certificate.json

docker-build:
	docker build -t ai-trust-enable:latest .

docker-run:
	docker run --rm -p 8080:8080 ai-trust-enable:latest
