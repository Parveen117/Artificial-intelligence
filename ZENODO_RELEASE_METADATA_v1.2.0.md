# Zenodo release metadata: v1.2.0

Use this as the copy/paste release record for the audited Challenge Engine snapshot.

## Title

Artificial Intelligence Trust Enablement v1.2.0: Challenge Engine and Foundational Verification

## Version

1.2.0

## Publication date

2026-08-07

## Creator

Monty Dabas  
Independent Researcher  
ORCID: 0009-0005-6948-209X

## Resource type

Software

## Description

Artificial Intelligence Trust Enablement v1.2.0 adds a connector-ready, fail-closed Challenge Engine to the existing AI trust-enablement repository. The Challenge Engine evaluates declared claim-to-evidence closure contracts rather than unrestricted natural-language truth. It supports exploratory, adversarial, and certified modes; defaults to a mathematics package; includes logic, code, and authorization-gated security-audit packages; separates non-formal evidence from formal promotion; publishes machine-readable threat-model break classes; emits SHA-256 Challenge Genesis records that freeze the rules of engagement with zero accepted claims; supports observer-flow probes, burden/reserve checks, and finite-to-limit completion gates; and exposes a stable JSON stdin/stdout connector contract.

The final hostile pre-release audit added 35 dedicated attack tests and the Challenge Engine workflow completed 57 unit/adversarial tests successfully. Separately, the foundational mathematics/audit layer records 236,456 exact/random/exhaustive adversarial cases. These counts are reported separately because they represent different forms of verification evidence.

Final release audit status: PASS_FINAL_CHALLENGE_RELEASE_AUDIT.

The release does not claim unrestricted English-language understanding, universal semantic truth, universal correctness, or automatic authentication of participant-supplied evidence. Natural-language text is payload-only by default unless an explicitly declared semantic adapter closes. Non-formal evidence may participate in exploratory/adversarial evaluation but does not become a formal certificate without the formal-promotion requirements of the selected package.

Repository use remains governed by the repository LICENSE, PATENT_NOTICE.md, COPYRIGHT_NOTICE.md, and any separately declared challenge authorization/scope. The Challenge protocol itself grants no additional copyright, patent, deployment, benchmarking, or derivative-work rights.

## Keywords

- artificial intelligence
- AI safety
- hallucination detection
- challenge engine
- adversarial testing
- red teaming
- formal verification
- fail-closed evaluation
- machine-readable certificates
- challenge genesis
- persistent records
- trustworthy AI

## Important release files

- `challenge_engine/README.md`
- `challenge_engine/RED_TEAM_RULES.md`
- `challenge_engine/CONNECTOR_CONTRACT.md`
- `challenge_engine/FINAL_ADVERSARIAL_RELEASE_AUDIT.md`
- `RELEASE_NOTES_v1.2.0.md`
- `foundational_mathematics/invariant_gated_state_transitions/`

## DOI handling

The repository currently carries `10.5281/zenodo.21300179` in `CITATION.cff` and the README badge. Before publishing the new Zenodo version, verify in the Zenodo UI whether this is the concept DOI or an older version DOI. After Zenodo mints the v1.2.0 version DOI, use the newly minted DOI for that immutable version while retaining the Zenodo concept DOI as the stable all-versions reference when appropriate.
