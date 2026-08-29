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
