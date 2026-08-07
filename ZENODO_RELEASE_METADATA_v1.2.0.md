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

Artificial Intelligence Trust Enablement v1.2.0 adds a connector-ready, fail-closed Challenge Engine to the existing AI trust-enablement repository. The Challenge Engine evaluates declared claim-to-evidence closure contracts rather than unrestricted natural-language truth. It supports exploratory, adversarial, and certified modes; defaults to a mathematics package; includes logic, code, and authorization-gated security-audit packages; separates non-formal evidence from formal promotion; publishes machine-readable threat-model break classes; emits SHA-256 Challenge Genesis records that freeze the rules of engagement with zero accepted claims; supports observer-flow probes, burden/reserve checks, finite-to-limit completion gates, strict JSON connector parsing, package-manifest commitment, scoped target-of-evaluation binding, and hash-bound Challenge Evaluation records with optional parent links.

Two hostile release passes were performed. The final seal specifically tested parser differentials, duplicate JSON keys, NaN/Infinity tokens, malformed package/mode fallback, package path abuse, exact threshold boundaries, scoped TOE mismatch, package-manifest mutation, Genesis integrity, and evaluation-result chaining. A real binary floating-point boundary issue was found and fixed: the mathematical equality `0.1 + 0.7 = 0.8` could previously be represented by Python as `0.7999999999999999`, incorrectly creating a strict reserve. Threshold decisions now use decimal-intent arithmetic for the declared numeric values.

The final Challenge Engine workflow completed 84 unit/adversarial tests successfully. Separately, the foundational mathematics/audit layer records 236,456 exact/random/exhaustive adversarial cases. These counts are reported separately because they represent different forms of verification evidence.

Final release audit status: PASS_FINAL_CHALLENGE_SEAL_AUDIT.

The release does not claim unrestricted English-language understanding, universal semantic truth, universal correctness, automatic authentication of participant-supplied evidence, or stateless replay detection. Natural-language text is payload-only by default unless an explicitly declared semantic adapter closes. Non-formal evidence may participate in exploratory/adversarial evaluation but does not become a formal certificate without the formal-promotion requirements of the selected package. Challenge Evaluation hashes make individual outcomes reproducible, while detecting reuse of an old valid evaluation as a new request remains a persistent connector/ledger responsibility.

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
- challenge evaluation
- persistent records
- trustworthy AI

## Important release files

- `challenge_engine/README.md`
- `challenge_engine/RED_TEAM_RULES.md`
- `challenge_engine/CONNECTOR_CONTRACT.md`
- `challenge_engine/FINAL_ADVERSARIAL_RELEASE_AUDIT.md`
- `challenge_engine/FINAL_SEAL_AUDIT.md`
- `RELEASE_NOTES_v1.2.0.md`
- `foundational_mathematics/invariant_gated_state_transitions/`

## DOI handling

The repository currently carries `10.5281/zenodo.21300179` in `CITATION.cff` and the README badge. Before publishing the new Zenodo version, verify in the Zenodo UI whether this is the concept DOI or an older version DOI. After Zenodo mints the v1.2.0 version DOI, use the newly minted DOI for that immutable version while retaining the Zenodo concept DOI as the stable all-versions reference when appropriate.
