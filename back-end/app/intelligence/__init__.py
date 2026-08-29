"""AI, classification, deduplication, evidence linking, observation corroboration,
and intelligence package."""

from app.intelligence.candidate_generator import CandidateGenerator, candidate_generator
from app.intelligence.category_rules import (
    CATEGORY_COMPATIBILITY_MATRIX,
    get_category_compatibility,
)
from app.intelligence.clustering_engine import (
    IncidentClusteringEngine,
    clustering_engine,
)
from app.intelligence.duplicate_scorer import DuplicateScorer, duplicate_scorer
from app.intelligence.evaluation_dataset import (
    BENCHMARK_EVALUATION_PAIRS,
    evaluate_threshold_sensitivity,
    run_benchmark_evaluation,
)
from app.intelligence.evidence_candidate_generator import (
    EvidenceCandidateGenerator,
    evidence_candidate_generator,
)
from app.intelligence.evidence_evaluation_dataset import (
    EVIDENCE_BENCHMARK_PAIRS,
    run_evidence_benchmark_evaluation,
)
from app.intelligence.evidence_linking_engine import (
    EvidenceLinkingEngine,
    evidence_linking_engine,
)
from app.intelligence.evidence_scorer import EvidenceScorer, evidence_scorer
from app.intelligence.extractor import EntityExtractor, entity_extractor
from app.intelligence.observation_candidate_generator import (
    ObservationCandidateGenerator,
    observation_candidate_generator,
)
from app.intelligence.observation_corroboration_engine import (
    ObservationCorroborationEngine,
    observation_corroboration_engine,
)
from app.intelligence.observation_evaluation_dataset import (
    OBSERVATION_BENCHMARK_CASES,
    run_observation_benchmark,
)
from app.intelligence.observation_scorer import (
    ObservationScorer,
    WaterLevelPolicy,
    observation_scorer,
)
from app.intelligence.observation_trend_analyzer import (
    ObservationTrendAnalyzer,
    observation_trend_analyzer,
)
from app.intelligence.resolver import LocationResolver, location_resolver
from app.intelligence.schemas import (
    CandidateQueryResult,
    ClusterAssignmentResult,
    CorroborationAssessment,
    CorroborationResult,
    CorroborationSignalBreakdown,
    DuplicateAssessment,
    DuplicateDecision,
    DuplicateSignalBreakdown,
    EvidenceLinkAssessment,
    EvidenceLinkResult,
    EvidenceLinkSignalBreakdown,
    EvidenceRelationship,
    ExtractedEntity,
    LocationCandidate,
    LocationResolutionResult,
    ObservationDataQuality,
    ObservationRelationship,
    ResolutionMethod,
    ResolutionStatus,
    TrendAnalysisResult,
    TrendDirection,
)
from app.intelligence.semantic_similarity import (
    SemanticVectorizer,
    semantic_vectorizer,
)

__all__ = [
    "ResolutionStatus",
    "ResolutionMethod",
    "DuplicateDecision",
    "LocationCandidate",
    "ExtractedEntity",
    "LocationResolutionResult",
    "DuplicateSignalBreakdown",
    "DuplicateAssessment",
    "CandidateQueryResult",
    "ClusterAssignmentResult",
    "EvidenceRelationship",
    "EvidenceLinkSignalBreakdown",
    "EvidenceLinkAssessment",
    "EvidenceLinkResult",
    "ObservationRelationship",
    "ObservationDataQuality",
    "TrendDirection",
    "TrendAnalysisResult",
    "CorroborationSignalBreakdown",
    "CorroborationAssessment",
    "CorroborationResult",
    "EntityExtractor",
    "entity_extractor",
    "LocationResolver",
    "location_resolver",
    "CATEGORY_COMPATIBILITY_MATRIX",
    "get_category_compatibility",
    "SemanticVectorizer",
    "semantic_vectorizer",
    "DuplicateScorer",
    "duplicate_scorer",
    "CandidateGenerator",
    "candidate_generator",
    "IncidentClusteringEngine",
    "clustering_engine",
    "BENCHMARK_EVALUATION_PAIRS",
    "run_benchmark_evaluation",
    "evaluate_threshold_sensitivity",
    "EvidenceScorer",
    "evidence_scorer",
    "EvidenceCandidateGenerator",
    "evidence_candidate_generator",
    "EvidenceLinkingEngine",
    "evidence_linking_engine",
    "EVIDENCE_BENCHMARK_PAIRS",
    "run_evidence_benchmark_evaluation",
    "ObservationScorer",
    "WaterLevelPolicy",
    "observation_scorer",
    "ObservationTrendAnalyzer",
    "observation_trend_analyzer",
    "ObservationCandidateGenerator",
    "observation_candidate_generator",
    "ObservationCorroborationEngine",
    "observation_corroboration_engine",
    "OBSERVATION_BENCHMARK_CASES",
    "run_observation_benchmark",
]
