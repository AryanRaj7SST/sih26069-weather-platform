"""Pydantic schemas for duplicate clustering response contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ClusterMemberSummary(BaseModel):
    """Summary of an incident report belonging to a duplicate cluster."""

    model_config = ConfigDict(from_attributes=True)

    report_id: uuid.UUID
    tracking_id: str
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score to primary.")
    occurred_at: datetime
    title: str
    is_representative: bool = Field(
        default=False,
        description="True if this report is the cluster primary anchor.",
    )


class IncidentClusterDetailData(BaseModel):
    """Duplicate cluster topology and member reports."""

    model_config = ConfigDict(from_attributes=True)

    cluster_id: uuid.UUID
    cluster_code: str
    total_member_count: int = Field(..., ge=1, description="Total reports in cluster.")
    is_representative: bool = Field(
        default=False,
        description="True if the queried incident is the primary anchor.",
    )
    representative_report_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Primary anchor incident ID.",
    )
    temporal_span_hours: Optional[float] = Field(
        default=None,
        description="Time span between earliest and latest reports in cluster.",
    )
    members: List[ClusterMemberSummary] = Field(default_factory=list)


class IncidentClusterDetailResponse(BaseModel):
    """Standard API envelope for duplicate cluster details."""

    success: bool = True
    data: IncidentClusterDetailData
    meta: dict = Field(default_factory=dict)
