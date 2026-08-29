"""Pydantic schemas for digital evidence linking response contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.intelligence.schemas import EvidenceRelationship
from app.schemas.report import PaginationMeta


class IncidentEvidenceItemData(BaseModel):
    """Digital evidence item linked to an incident."""

    model_config = ConfigDict(from_attributes=True)

    link_id: uuid.UUID = Field(..., description="Unique link relationship ID.")
    evidence_id: uuid.UUID = Field(..., description="Unique evidence item ID.")
    evidence_type: str = Field(..., description="Source type (NEWS_ARTICLE, SOCIAL_POST, etc.).")
    publisher_domain: Optional[str] = Field(
        default=None, description="Publishing news/social domain."
    )
    title: str = Field(..., description="Headline or post title.")
    text_snippet: str = Field(..., description="Concise text snippet.")
    published_at: datetime = Field(..., description="Publication timestamp.")
    relationship: EvidenceRelationship = Field(
        ...,
        description="Canonical link role (e.g. SUPPORTING, RELATED, CONTRADICTORY).",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Assessed link confidence score.",
    )
    provenance_group: Optional[str] = Field(
        default=None,
        description="Source provenance grouping key.",
    )
    url: Optional[str] = Field(default=None, description="Public article or post URL.")
    is_human_override: bool = Field(
        default=False,
        description="True if an operator manually confirmed this link.",
    )


class IncidentEvidenceListResponse(BaseModel):
    """Standard API envelope for paginated incident evidence items."""

    success: bool = True
    data: List[IncidentEvidenceItemData] = Field(default_factory=list)
    pagination: PaginationMeta
    meta: dict = Field(default_factory=dict)
