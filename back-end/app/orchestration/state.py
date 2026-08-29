"""State management, transition logic, and readiness derivation for intelligence orchestration.

Stores durable stage telemetry inside WeatherReport.raw_payload['orchestration']
while enforcing failure-isolation and partial-success guarantees.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.models.report import WeatherReport
from app.orchestration.events import (
    OverallReadiness,
    StageName,
    StageOutcome,
)
from app.orchestration.models import (
    PipelineOrchestrationState,
    StageStateModel,
)

SUCCESS_OUTCOMES = {
    StageOutcome.SUCCESS_WITH_RESULTS,
    StageOutcome.SUCCESS_WITH_NO_MATCH,
    StageOutcome.SUCCESS_WITH_INSUFFICIENT_DATA,
    StageOutcome.SKIPPED_NOT_APPLICABLE,
    StageOutcome.SKIPPED_STALE,
}


def derive_overall_readiness(
    stages: Dict[StageName, StageStateModel],
) -> OverallReadiness:
    """Compute overall intelligence readiness based on per-stage state invariants.

    Invariants:
    1. If CREDIBILITY is successful (with any signals) -> READY or PARTIAL.
    2. If any optional stage is in RETRY_WAIT or PERMANENT_FAILURE -> PARTIAL (never FAILED).
    3. If CREDIBILITY failed permanently and no prior score exists -> FAILED.
    4. Default during in-flight evaluation -> PENDING.
    """
    if not stages:
        return OverallReadiness.INTELLIGENCE_PENDING

    cred_state = stages.get(StageName.CREDIBILITY)
    has_retry_or_failed_enrichment = any(
        s.status in (StageOutcome.RETRYABLE_FAILURE, StageOutcome.PERMANENT_FAILURE)
        for name, s in stages.items()
        if name != StageName.CREDIBILITY
    )

    if cred_state and cred_state.status in SUCCESS_OUTCOMES:
        if has_retry_or_failed_enrichment:
            return OverallReadiness.INTELLIGENCE_PARTIAL
        return OverallReadiness.INTELLIGENCE_READY

    if cred_state and cred_state.status == StageOutcome.PERMANENT_FAILURE:
        return OverallReadiness.INTELLIGENCE_FAILED

    return OverallReadiness.INTELLIGENCE_PENDING


def load_orchestration_state(report: WeatherReport) -> PipelineOrchestrationState:
    """Deserialize PipelineOrchestrationState from WeatherReport.raw_payload or initialize fresh."""
    raw = report.raw_payload or {}
    orch_data = raw.get("orchestration")

    if isinstance(orch_data, dict):
        try:
            # Parse dict keys into StageName enums
            stages_dict: Dict[StageName, StageStateModel] = {}
            for k, v in orch_data.get("stages", {}).items():
                try:
                    s_name = StageName(k)
                    stages_dict[s_name] = StageStateModel.model_validate(v)
                except (ValueError, TypeError):
                    continue

            return PipelineOrchestrationState(
                version=orch_data.get("version", "v1"),
                overall_readiness=OverallReadiness(
                    orch_data.get("overall_readiness", OverallReadiness.INTELLIGENCE_PENDING.value)
                ),
                last_successful_stage=(
                    StageName(orch_data["last_successful_stage"])
                    if orch_data.get("last_successful_stage")
                    else None
                ),
                last_updated_at=datetime.fromisoformat(
                    orch_data.get("last_updated_at", datetime.now(timezone.utc).isoformat())
                ),
                stages=stages_dict,
            )
        except Exception:
            pass

    # Fresh state template
    fresh_stages: Dict[StageName, StageStateModel] = {}
    for stg in StageName:
        fresh_stages[stg] = StageStateModel(status=StageOutcome.SUCCESS_WITH_NO_MATCH, attempt=0)

    return PipelineOrchestrationState(
        version="v1",
        overall_readiness=OverallReadiness.INTELLIGENCE_PENDING,
        last_successful_stage=None,
        last_updated_at=datetime.now(timezone.utc),
        stages=fresh_stages,
    )


def update_stage_state(
    report: WeatherReport,
    stage_name: StageName,
    outcome: StageOutcome,
    attempt: int,
    fingerprint: Optional[str] = None,
    duration_ms: Optional[float] = None,
    error_class: Optional[Any] = None,
    error_message: Optional[str] = None,
    summary: Optional[Dict[str, Any]] = None,
    next_retry_at: Optional[datetime] = None,
) -> PipelineOrchestrationState:
    """Atomically update a specific stage outcome and recompute overall readiness."""
    state = load_orchestration_state(report)
    now = datetime.now(timezone.utc)

    stage_model = state.stages.get(
        stage_name, StageStateModel(status=StageOutcome.SUCCESS_WITH_NO_MATCH, attempt=0)
    )

    stage_model.status = outcome
    stage_model.attempt = attempt
    stage_model.fingerprint = fingerprint
    stage_model.duration_ms = duration_ms
    stage_model.completed_at = now if outcome in SUCCESS_OUTCOMES else None
    stage_model.error_message = error_message
    stage_model.next_retry_at = next_retry_at
    if summary:
        stage_model.summary = summary

    state.stages[stage_name] = stage_model
    state.last_updated_at = now

    if outcome in SUCCESS_OUTCOMES and outcome != StageOutcome.SKIPPED_STALE:
        state.last_successful_stage = stage_name

    state.overall_readiness = derive_overall_readiness(state.stages)

    # Persist back into raw_payload
    current_raw = dict(report.raw_payload) if isinstance(report.raw_payload, dict) else {}
    current_raw["orchestration"] = state.model_dump(mode="json")
    report.raw_payload = current_raw

    # Keep processing_status synced for backwards compatibility
    if state.overall_readiness == OverallReadiness.INTELLIGENCE_READY:
        report.processing_status = "COMPLETED"
    elif state.overall_readiness == OverallReadiness.INTELLIGENCE_PARTIAL:
        report.processing_status = "PARTIAL_INTELLIGENCE"
    elif state.overall_readiness == OverallReadiness.INTELLIGENCE_FAILED:
        report.processing_status = "FAILED"
    else:
        report.processing_status = "PROCESSING"

    return state
