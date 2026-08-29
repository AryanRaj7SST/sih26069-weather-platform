import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResolutionStatus(str, Enum):
    """Status of geographic location resolution."""

    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class ResolutionMethod(str, Enum):
    """Method utilized for geographic location determination."""

    STRUCTURED_COORDINATES = "STRUCTURED_COORDINATES"
    EXACT_ADMIN_MATCH = "EXACT_ADMIN_MATCH"
    PLACE_DICTIONARY = "PLACE_DICTIONARY"
    GEOCODER = "GEOCODER"
    NLP_ENTITY_RESOLUTION = "NLP_ENTITY_RESOLUTION"
    HUMAN_CORRECTION = "HUMAN_CORRECTION"


class DuplicateDecision(str, Enum):
    """Outcome decision of semantic duplicate evaluation."""

    DUPLICATE = "DUPLICATE"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    DISTINCT = "DISTINCT"


class LocationCandidate(BaseModel):
    """A plausible candidate place for an extracted entity."""

    place_name: str = Field(..., description="Canonical place or administrative name.")
    locality: Optional[str] = Field(default=None, description="Sub-city locality.")
    city: Optional[str] = Field(default=None, description="City or municipal area.")
    district: Optional[str] = Field(default=None, description="Administrative district.")
    state: Optional[str] = Field(default=None, description="State or province.")
    country: str = Field(default="India", description="Country name.")
    latitude: float = Field(..., description="WGS84 decimal latitude.")
    longitude: float = Field(..., description="WGS84 decimal longitude.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence score.")
    match_type: str = Field(default="EXACT", description="Match precision type.")


class ExtractedEntity(BaseModel):
    """Geographic entity mention identified within unstructured text."""

    text: str = Field(..., description="The raw entity substring extracted from text.")
    normalized_text: str = Field(..., description="Cleaned, lowercased entity text.")
    entity_type: str = Field(
        default="LOCATION",
        description="Entity category ('CITY', 'STATE', 'LOCALITY', 'DISTRICT', 'COUNTRY').",
    )
    start_char: int = Field(..., ge=0, description="Character offset start.")
    end_char: int = Field(..., ge=0, description="Character offset end.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence.")


class LocationResolutionResult(BaseModel):
    """Standard contract representing the result of entity and location resolution."""

    original_text: Optional[str] = Field(default=None, description="Raw input text analyzed.")
    normalized_text: Optional[str] = Field(
        default=None, description="Cleaned text after normalization."
    )
    place_name: Optional[str] = Field(default=None, description="Resolved canonical place name.")
    locality: Optional[str] = Field(default=None, description="Sub-city locality if identified.")
    city: Optional[str] = Field(default=None, description="City or urban center.")
    district: Optional[str] = Field(default=None, description="Administrative district.")
    state: Optional[str] = Field(default=None, description="State or Union Territory.")
    country: Optional[str] = Field(default="India", description="Country name.")
    latitude: Optional[float] = Field(
        default=None, ge=-90.0, le=90.0, description="Resolved WGS84 latitude."
    )
    longitude: Optional[float] = Field(
        default=None, ge=-180.0, le=180.0, description="Resolved WGS84 longitude."
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Location resolution confidence score (0.0 - 1.0).",
    )
    resolution_status: ResolutionStatus = Field(
        default=ResolutionStatus.UNRESOLVED,
        description="Resolution status ('RESOLVED', 'AMBIGUOUS', 'UNRESOLVED').",
    )
    resolution_method: ResolutionMethod = Field(
        default=ResolutionMethod.NLP_ENTITY_RESOLUTION,
        description="Provenance of how the location was resolved.",
    )
    candidates: List[LocationCandidate] = Field(
        default_factory=list,
        description="Candidate places when resolution is ambiguous or multi-option.",
    )
    provider: str = Field(
        default="internal_gazetteer",
        description="Service or gazetteer database providing the resolution.",
    )
    is_human_corrected: bool = Field(
        default=False,
        description="Flag indicating manual operator intervention/override.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional audit, extraction context, or bounding box details.",
    )


class DuplicateSignalBreakdown(BaseModel):
    """Detailed multi-dimensional signal breakdown of duplicate comparison."""

    spatial_distance_meters: Optional[float] = Field(
        default=None, description="Physical distance between incident coordinates."
    )
    spatial_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Spatial proximity similarity (0.0 to 1.0)."
    )
    temporal_delta_seconds: Optional[float] = Field(
        default=None, description="Time delta between incident occurrences."
    )
    temporal_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Temporal proximity similarity (0.0 to 1.0)."
    )
    category_compatibility_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Hazard category compatibility (0.0 to 1.0)."
    )
    semantic_similarity: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Text vector semantic cosine similarity."
    )
    entity_compatibility_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Location entity match score."
    )
    source_relationship_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Contextual source cross-correlation score."
    )


class DuplicateAssessment(BaseModel):
    """Explainable evaluation output comparing two incident reports for duplication."""

    candidate_report_id: uuid.UUID = Field(..., description="ID of the incoming report.")
    reference_report_id: uuid.UUID = Field(..., description="ID of the existing comparison report.")
    decision: DuplicateDecision = Field(..., description="Classification decision.")
    overall_score: float = Field(
        ..., ge=0.0, le=1.0, description="Composite duplicate similarity score."
    )
    signals: DuplicateSignalBreakdown = Field(..., description="Signal breakdown.")
    explanation: str = Field(..., description="Human-readable decision explanation.")
    model_version: str = Field(..., description="Engine/model version identifier.")
    semantic_method: str = Field(
        default="sparse_tfidf_ngram_v1",
        description="Active semantic vectorization method utilized.",
    )
    assessed_at: datetime = Field(..., description="UTC assessment timestamp.")


class CandidateQueryResult(BaseModel):
    """Result of candidate retrieval with completeness and truncation diagnostics."""

    candidates: List[Any] = Field(default_factory=list, description="Candidate report objects.")
    total_found: int = Field(default=0, description="Total candidates matching criteria.")
    candidate_limit: int = Field(default=50, description="Max candidate limit configured.")
    is_truncated: bool = Field(
        default=False, description="True if candidate count reached the query limit cap."
    )


class ClusterAssignmentResult(BaseModel):
    """Result of evaluating a report against incident duplicate clusters."""

    report_id: uuid.UUID = Field(..., description="ID of the evaluated report.")
    decision: DuplicateDecision = Field(..., description="Clustering decision.")
    cluster_id: Optional[uuid.UUID] = Field(
        default=None, description="Assigned DuplicateCluster ID if confirmed duplicate."
    )
    is_primary: bool = Field(
        default=False, description="True if report is the primary anchor of the cluster."
    )
    matched_report_id: Optional[uuid.UUID] = Field(
        default=None, description="ID of the primary/reference report matched against."
    )
    candidate_count: int = Field(default=0, description="Number of candidates evaluated.")
    is_truncated: bool = Field(
        default=False, description="True if candidate retrieval reached configured cap."
    )
    assessment: Optional[DuplicateAssessment] = Field(
        default=None, description="Detailed assessment with the best candidate match."
    )
