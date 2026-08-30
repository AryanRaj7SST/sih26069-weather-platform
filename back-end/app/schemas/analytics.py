"""Pydantic schemas for Dashboard and Analytics aggregation contracts."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class VerificationBreakdown(BaseModel):
    """Breakdown of verification statuses."""

    model_config = ConfigDict(from_attributes=True)

    verified_count: int = Field(default=0, description="Count of authority-verified incidents.")
    verified_rate: int = Field(
        default=0, description="Percentage of total incidents that are verified (0-100)."
    )
    pending_count: int = Field(default=0, description="Count of pending or under-review incidents.")
    under_review_count: int = Field(
        default=0, description="Count of incidents actively under review."
    )
    rejected_count: int = Field(default=0, description="Count of rejected reports.")
    duplicate_count: int = Field(default=0, description="Count of duplicate reports.")


class SeverityBreakdown(BaseModel):
    """Breakdown of severity levels."""

    model_config = ConfigDict(from_attributes=True)

    severe_high_count: int = Field(default=0, description="Combined severe and high urgency count.")
    severe_count: int = Field(default=0, description="Count of SEVERE urgency incidents.")
    high_count: int = Field(default=0, description="Count of HIGH urgency incidents.")
    moderate_count: int = Field(default=0, description="Count of MODERATE urgency incidents.")
    low_count: int = Field(default=0, description="Count of LOW urgency incidents.")


class CategoryDistributionItem(BaseModel):
    """Single item in hazard category distribution."""

    model_config = ConfigDict(from_attributes=True)

    category_code: str = Field(..., description="Canonical category code or OTHER.")
    category_name: str = Field(..., description="Human-readable hazard name.")
    count: int = Field(default=0, description="Total reports in this category.")
    percentage: int = Field(default=0, description="Percentage of total reports (0-100).")


class DiurnalDistributionItem(BaseModel):
    """Single item in 6-hour diurnal activity distribution."""

    model_config = ConfigDict(from_attributes=True)

    window: str = Field(..., description="Window start key e.g. 00:00, 06:00, 12:00, 18:00.")
    label: str = Field(..., description="Human-readable window range e.g. 00:00 - 06:00.")
    count: int = Field(default=0, description="Total reports occurring in this diurnal window.")


class DashboardSummaryData(BaseModel):
    """Structured situational aggregate metrics for Dashboard and Analytics KPI cards."""

    model_config = ConfigDict(from_attributes=True)

    total_count: int = Field(
        default=0, description="Total records matching active filters and time window."
    )
    period_count: int = Field(
        default=0,
        description="Total records matching active filters and time window (compatibility alias).",
    )
    count_24h: int = Field(
        default=0,
        description="Count of incidents occurring in the last 24 hours within the filtered scope.",
    )
    last_24h_pct: int = Field(
        default=0,
        description="Percentage of filtered records occurring in the last 24 hours (0-100).",
    )
    verification: VerificationBreakdown
    severity: SeverityBreakdown
    category_distribution: List[CategoryDistributionItem] = Field(default_factory=list)
    diurnal_distribution: List[DiurnalDistributionItem] = Field(default_factory=list)


class DashboardSummaryResponse(BaseModel):
    """Standard envelope for dashboard summary aggregate endpoint."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    data: DashboardSummaryData
    meta: dict = Field(default_factory=dict)


class AnalyticsTrendBucket(BaseModel):
    """Single time-series bucket in analytics trend progression."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket identifier or ISO timestamp.")
    label: str = Field(..., description="Display label e.g. '00:00 - 04:00' or 'Sun 23'.")
    total: int = Field(default=0, description="Total reports in this time window.")
    verified: int = Field(default=0, description="Verified reports in this time window.")


class AnalyticsTrendData(BaseModel):
    """Structured time-series activity trend dataset."""

    model_config = ConfigDict(from_attributes=True)

    time_range: str = Field(..., description="Requested time range e.g. 24h, 7d, 30d, all.")
    interval: str = Field(..., description="Bucket granularity e.g. hour, day.")
    buckets: List[AnalyticsTrendBucket] = Field(default_factory=list)


class AnalyticsTrendResponse(BaseModel):
    """Standard envelope for analytics time-series trend endpoint."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    data: AnalyticsTrendData
    meta: dict = Field(default_factory=dict)


class RegionalDistributionItem(BaseModel):
    """Regional aggregation bucket item."""

    model_config = ConfigDict(from_attributes=True)

    region_code: str = Field(..., description="Two-letter region code or OTHER")
    region_name: str = Field(..., description="Display name of the region")
    count: int = Field(default=0, ge=0, description="Total incident count in region")
    percentage: int = Field(
        default=0, ge=0, le=100, description="Percentage of total classified reports"
    )


class AnalyticsRegionalData(BaseModel):
    """Payload data for regional analytics distribution."""

    model_config = ConfigDict(from_attributes=True)

    time_range: str = Field(..., description="Requested time range filter")
    total_classified: int = Field(
        default=0, ge=0, description="Total reports classified across regions"
    )
    regions: List[RegionalDistributionItem] = Field(
        default_factory=list, description="Ranked regional breakdown"
    )


class AnalyticsRegionalResponse(BaseModel):
    """Standard envelope response for regional analytics API."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    data: AnalyticsRegionalData
    meta: dict = Field(default_factory=dict)
