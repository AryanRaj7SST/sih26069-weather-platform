"""Incident Lifecycle Pipeline Executor.

Orchestrates sequential and dependency-checked execution of all intelligence stages
for an incident, enforcing failure isolation, per-stage state tracking, and atomic persistence.
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import WeatherReport
from app.orchestration.dependency_graph import DependencyGraph
from app.orchestration.events import (
    FailureClass,
    StageExecutionResult,
    StageName,
    StageOutcome,
)
from app.orchestration.handlers import (
    CredibilityStageHandler,
    DuplicateStageHandler,
    EvidenceStageHandler,
    LocationStageHandler,
    ObservationStageHandler,
    StageHandler,
    credibility_stage_handler,
    duplicate_stage_handler,
    evidence_stage_handler,
    location_stage_handler,
    observation_stage_handler,
)
from app.orchestration.models import PipelineOrchestrationState
from app.orchestration.retry_policy import retry_policy
from app.orchestration.state import (
    load_orchestration_state,
    update_stage_state,
)

logger = logging.getLogger(__name__)


class IncidentPipeline:
    """Production orchestrator executing the full intelligence lifecycle for an incident."""

    def __init__(
        self,
        location_handler: Optional[LocationStageHandler] = None,
        duplicate_handler: Optional[DuplicateStageHandler] = None,
        evidence_handler: Optional[EvidenceStageHandler] = None,
        observation_handler: Optional[ObservationStageHandler] = None,
        credibility_handler: Optional[CredibilityStageHandler] = None,
    ) -> None:
        self.handlers: Dict[StageName, StageHandler] = {
            StageName.LOCATION: location_handler or location_stage_handler,
            StageName.DUPLICATE: duplicate_handler or duplicate_stage_handler,
            StageName.EVIDENCE: evidence_handler or evidence_stage_handler,
            StageName.OBSERVATION: observation_handler or observation_stage_handler,
            StageName.CREDIBILITY: credibility_handler or credibility_stage_handler,
        }

    async def execute_pipeline(
        self,
        db: AsyncSession,
        incident_id: uuid.UUID,
        commit: bool = True,
    ) -> PipelineOrchestrationState:
        """Run all eligible intelligence stages for target incident with failure isolation."""
        # 1. Fetch target incident
        stmt = select(WeatherReport).where(WeatherReport.id == incident_id)
        res = await db.execute(stmt)
        report = res.scalar_one_or_none()

        if not report:
            logger.warning("Incident %s not found for pipeline execution.", incident_id)
            raise ValueError(f"Incident {incident_id} not found")

        state = load_orchestration_state(report)
        stages_order = DependencyGraph.get_pipeline_execution_order()

        for stage_name in stages_order:
            # Check prerequisites
            if not DependencyGraph.can_execute_stage(stage_name, state.stages):
                logger.info(
                    "Skipping stage %s for incident %s; prerequisites not met.",
                    stage_name.value,
                    incident_id,
                )
                continue

            handler = self.handlers.get(stage_name)
            if not handler:
                continue

            current_stage_model = state.stages.get(stage_name)
            current_attempt = (
                current_stage_model.attempt + 1 if current_stage_model is not None else 1
            )

            # Execute stage with strict failure isolation
            try:
                result = await handler.execute(db=db, report=report)
            except Exception as e:
                logger.error(
                    "Unhandled exception in stage %s for incident %s: %s",
                    stage_name.value,
                    incident_id,
                    e,
                )
                err_class = retry_policy.classify_error(e)
                result = StageExecutionResult(
                    stage_name=stage_name,
                    outcome=(
                        StageOutcome.RETRYABLE_FAILURE
                        if err_class == FailureClass.TRANSIENT
                        else StageOutcome.PERMANENT_FAILURE
                    ),
                    error_class=err_class,
                    error_message=str(e),
                )

            # Re-select locked row to ensure fresh JSONB snapshot before updating
            lock_stmt = (
                select(WeatherReport).where(WeatherReport.id == incident_id).with_for_update()
            )
            lock_res = await db.execute(lock_stmt)
            locked_report = lock_res.scalar_one_or_none() or report

            # Update per-stage state on locked row
            state = update_stage_state(
                report=locked_report,
                stage_name=stage_name,
                outcome=result.outcome,
                attempt=current_attempt,
                fingerprint=result.fingerprint,
                duration_ms=result.duration_ms,
                error_class=result.error_class,
                error_message=result.error_message,
                summary=result.results_summary,
            )

            # Flush stage state changes
            await db.flush()

        if commit:
            await db.commit()

        logger.info(
            "Completed intelligence pipeline for incident %s -> readiness: %s",
            incident_id,
            state.overall_readiness.value,
        )
        return state

    async def execute_single_stage(
        self,
        db: AsyncSession,
        incident_id: uuid.UUID,
        stage_name: StageName,
        commit: bool = True,
    ) -> StageExecutionResult:
        """Execute a single targeted stage for an incident and persist its state."""
        stmt = select(WeatherReport).where(WeatherReport.id == incident_id)
        res = await db.execute(stmt)
        report = res.scalar_one_or_none()

        if not report:
            raise ValueError(f"Incident {incident_id} not found")

        state = load_orchestration_state(report)
        handler = self.handlers.get(stage_name)
        if not handler:
            raise ValueError(f"No handler configured for stage {stage_name}")

        current_stage_model = state.stages.get(stage_name)
        current_attempt = current_stage_model.attempt + 1 if current_stage_model is not None else 1

        try:
            result = await handler.execute(db=db, report=report)
        except Exception as e:
            logger.error(
                "Unhandled exception in stage %s for incident %s: %s",
                stage_name.value,
                incident_id,
                e,
            )
            err_class = retry_policy.classify_error(e)
            result = StageExecutionResult(
                stage_name=stage_name,
                outcome=(
                    StageOutcome.RETRYABLE_FAILURE
                    if err_class == FailureClass.TRANSIENT
                    else StageOutcome.PERMANENT_FAILURE
                ),
                error_class=err_class,
                error_message=str(e),
            )

        # Acquire narrow row-level lock on latest DB state to prevent JSONB race overwrites
        lock_stmt = select(WeatherReport).where(WeatherReport.id == incident_id).with_for_update()
        lock_res = await db.execute(lock_stmt)
        locked_report = lock_res.scalar_one_or_none() or report

        update_stage_state(
            report=locked_report,
            stage_name=stage_name,
            outcome=result.outcome,
            attempt=current_attempt,
            fingerprint=result.fingerprint,
            duration_ms=result.duration_ms,
            error_class=result.error_class,
            error_message=result.error_message,
            summary=result.results_summary,
        )

        if commit:
            await db.commit()

        return result


incident_pipeline = IncidentPipeline()
