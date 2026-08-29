"""Pydantic schemas for machine credibility response contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class IncidentCredibilityData(BaseModel):
    """Machine-assessed credibility breakdown and drivers."""

    model_config = ConfigDict(from_attributes=True)

    incident_id: uuid.UUID
    score: float = Field(..., ge=0.0, le=1.0, description="Machine-assessed credibility score.")
    is_machine_assessed: bool = Field(
        default=True,
        description="True indicating statistical/algorithmic score, not human truth.",
    )
    label: str = Field(
        default="MODERATE_CREDIBILITY",
        description="Categorical credibility label (LOW, MODERATE, HIGH, VERY_HIGH).",
    )
    base_trust_prior: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Source institutional trust baseline prior score.",
    )
    engine_version: str = Field(default="v1", description="Credibility engine version identifier.")
    policy_version: str = Field(default="v1", description="Scoring policy version identifier.")
    explanation_text: str = Field(..., description="Explainable natural-language summary.")
    positive_drivers: List[str] = Field(
        default_factory=list,
        description="Contributing corroboration factors increasing credibility.",
    )
    negative_drivers: List[str] = Field(
        default_factory=list,
        description="Contradicting or penalized factors reducing credibility.",
    )
    uncertainty_flags: List[str] = Field(
        default_factory=list,
        description="Neutral uncertainty indicators and data gaps.",
    )
    last_calculated_at: datetime = Field(..., description="Timestamp of latest scoring evaluation.")


class IncidentCredibilityResponse(BaseModel):
    """Standard API envelope for machine credibility breakdown."""

    success: bool = True
    data: IncidentCredibilityData
    meta: dict = Field(default_factory=dict)
