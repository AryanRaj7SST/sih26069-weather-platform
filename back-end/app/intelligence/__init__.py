"""AI, classification, entity resolution, deduplication, and intelligence engine package."""

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
from app.intelligence.extractor import EntityExtractor, entity_extractor
from app.intelligence.resolver import LocationResolver, location_resolver
from app.intelligence.schemas import (
    CandidateQueryResult,
    ClusterAssignmentResult,
    DuplicateAssessment,
    DuplicateDecision,
    DuplicateSignalBreakdown,
    ExtractedEntity,
    LocationCandidate,
    LocationResolutionResult,
    ResolutionMethod,
    ResolutionStatus,
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
]
