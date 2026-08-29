"""Directed stage dependency graph and execution prerequisite evaluator.

Distinguishes hard dependencies from optional enrichment branches:
- Hard dependencies: LOCATION_RESOLUTION provides spatial bounds for candidate queries.
  If LOCATION completes with INSUFFICIENT_DATA, downstream stages run with text/category filters.
- Optional enrichment: DUPLICATE, EVIDENCE, and OBSERVATION provide supplementary signals.
  CREDIBILITY can run using whatever signals are currently available in PostgreSQL.
"""

from __future__ import annotations

from typing import Dict, List, Set

from app.orchestration.events import (
    StageName,
)
from app.orchestration.models import StageStateModel
from app.orchestration.state import SUCCESS_OUTCOMES


class DependencyGraph:
    """Evaluates stage execution prerequisites and downstream execution order."""

    # Explicit hard dependencies (prerequisites that must complete before starting)
    _HARD_DEPENDENCIES: Dict[StageName, Set[StageName]] = {
        StageName.LOCATION: set(),
        StageName.DUPLICATE: {StageName.LOCATION},
        StageName.EVIDENCE: {StageName.LOCATION},
        StageName.OBSERVATION: {StageName.LOCATION},
        StageName.CREDIBILITY: set(),  # Credibility runs on available state; does not block
    }

    # Optional enrichment relationships for downstream trigger routing
    _ENRICHMENT_STAGES: Set[StageName] = {
        StageName.DUPLICATE,
        StageName.EVIDENCE,
        StageName.OBSERVATION,
    }

    @classmethod
    def can_execute_stage(
        cls,
        stage: StageName,
        current_stages: Dict[StageName, StageStateModel],
    ) -> bool:
        """Determine whether a stage is eligible to execute given current stage states.

        Rules:
        1. LOCATION can always execute.
        2. DUPLICATE, EVIDENCE, OBSERVATION require LOCATION to have reached a terminal state
           (even SUCCESS_WITH_INSUFFICIENT_DATA is sufficient to unblock non-spatial matching).
        3. CREDIBILITY can execute whenever triggered; it consumes whatever DB signals exist.
        """
        prereqs = cls._HARD_DEPENDENCIES.get(stage, set())
        for p in prereqs:
            p_state = current_stages.get(p)
            if not p_state or p_state.status not in SUCCESS_OUTCOMES:
                return False
        return True

    @classmethod
    def get_pipeline_execution_order(cls) -> List[StageName]:
        """Return canonical execution sequence for full forward incident processing."""
        return [
            StageName.LOCATION,
            StageName.DUPLICATE,
            StageName.EVIDENCE,
            StageName.OBSERVATION,
            StageName.CREDIBILITY,
        ]

    @classmethod
    def is_enrichment_stage(cls, stage: StageName) -> bool:
        """Return True if stage represents an optional enrichment signal branch."""
        return stage in cls._ENRICHMENT_STAGES
