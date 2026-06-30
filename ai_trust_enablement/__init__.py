"""AI Trust Enablement package."""

from .ai_hallucination_recognition_engine import (
    AIHallucinationRecognitionEngine,
    DetectorConfig,
    RecognitionCertificate,
    RecognitionMetrics,
    StateSignature,
    build_signature,
    entropy_capacity_from_logits,
)
from .panini_nyaya_claim_verifier import (
    PaniniNyayaClaimVerifier,
    ClaimVerificationReport,
    PramanaResult,
    DerivationState,
)
from .paninian_meta_engine import (
    derive,
    derive_many,
    compact_trace,
    DerivedRule,
    RuleMetadata,
)
from .paninian_certificate_adapter import enrich_report
from .claim_frame_kernel import (
    ClaimFrameKernel,
    ClaimFrame,
    FrameMatch,
    FrameClosureReport,
)

__all__ = [
    "AIHallucinationRecognitionEngine",
    "DetectorConfig",
    "RecognitionCertificate",
    "RecognitionMetrics",
    "StateSignature",
    "build_signature",
    "entropy_capacity_from_logits",
    "PaniniNyayaClaimVerifier",
    "ClaimVerificationReport",
    "PramanaResult",
    "DerivationState",
    "derive",
    "derive_many",
    "compact_trace",
    "DerivedRule",
    "RuleMetadata",
    "enrich_report",
    "ClaimFrameKernel",
    "ClaimFrame",
    "FrameMatch",
    "FrameClosureReport",
]
