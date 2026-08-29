"""Incident Credibility Engine — orchestrator and persistence service.

Safety Guarantees:
- Never modifies WeatherReport.verification_status.
- Machine credibility score is strictly clamped in [0.0000, 0.9800].
- Atomic updates: credibility_score and credibility_explanation in single transaction.
- On failure: preserves historical score, marks is_stale=True, never sets score=0.
- Targeted incremental recomputation for evidence link, observation, and cluster changes.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.credibility_collector import (
    CredibilityCollector,
    credibility_collector,
)
from app.intelligence.credibility_explanation_builder import (
    CredibilityExplanationBuilder,
    credibility_explanation_builder,
)
from app.intelligence.credibility_scorer import (
    CredibilityScorer,
    credibility_scorer,
)
from app.intelligence.schemas import (
    CredibilityResult,
)
from app.models.corroboration import IncidentObservationCorroboration
from app.models.duplicate import DuplicateCluster, DuplicateMember
from app.models.evidence import IncidentEvidenceLink
from app.models.report import WeatherReport

logger = logging.getLogger(__name__)


class CredibilityEngine:
    """Production orchestrator for incident credibility scoring and explanation persistence."""

    def __init__(
        self,
        collector: Optional[CredibilityCollector] = None,
        scorer: Optional[CredibilityScorer] = None,
        explanation_builder: Optional[CredibilityExplanationBuilder] = None,
    ) -> None:
        self.collector = collector or credibility_collector
        self.scorer = scorer or credibility_scorer
        self.explanation_builder = explanation_builder or credibility_explanation_builder

    async def evaluate_incident_credibility(
        self,
        db: AsyncSession,
        incident_id: uuid.UUID,
        commit: bool = True,
    ) -> Optional[CredibilityResult]:
        """Collect signals, compute score, build structured explanation, and persist."""
        try:
            # 1. Collect normalized inputs
            inputs = await self.collector.collect_inputs(db=db, incident_id=incident_id)
            if not inputs:
                logger.warning("Could not collect inputs for incident %s", incident_id)
                return None

            # 2. Pure mathematical scoring
            signals = self.scorer.score_incident(inputs=inputs)

            # 3. Build structured explanation
            assessment = self.explanation_builder.build_assessment(
                incident_id=incident_id,
                inputs=inputs,
                signals=signals,
            )

            # 4. Atomic persistence into WeatherReport
            stmt = select(WeatherReport).where(WeatherReport.id == incident_id)
            res = await db.execute(stmt)
            report = res.scalar_one_or_none()

            if report:
                report.credibility_score = signals.final_credibility_score
                report.credibility_explanation = assessment.model_dump(mode="json")
                report.updated_at = datetime.now(timezone.utc)
                if commit:
                    await db.commit()

            return CredibilityResult(
                incident_id=incident_id,
                credibility_score=signals.final_credibility_score,
                is_persisted=report is not None,
                assessment=assessment,
            )

        except Exception as exc:
            logger.error(
                "Credibility evaluation failed for incident %s: %s. Preserving historical score.",
                incident_id,
                exc,
                exc_info=True,
            )
            # Safe failure fallback: rollback broken transaction first, preserve score, mark stale
            try:
                await db.rollback()
                stmt = select(WeatherReport).where(WeatherReport.id == incident_id)
                res = await db.execute(stmt)
                report = res.scalar_one_or_none()

                if report:
                    prev_explanation: Dict[str, Any] = (
                        dict(report.credibility_explanation)
                        if isinstance(report.credibility_explanation, dict)
                        else {}
                    )
                    prev_explanation["is_stale"] = True
                    prev_explanation["is_failure_fallback"] = True
                    prev_explanation["last_error"] = str(exc)
                    prev_explanation["failed_at"] = datetime.now(timezone.utc).isoformat()
                    report.credibility_explanation = prev_explanation
                    if commit:
                        await db.commit()
            except Exception as fallback_exc:
                logger.error(
                    "Failed to record failure fallback metadata for incident %s: %s",
                    incident_id,
                    fallback_exc,
                    exc_info=True,
                )

            return None

    async def recompute_for_evidence_link(
        self,
        db: AsyncSession,
        link_id: uuid.UUID,
    ) -> Optional[CredibilityResult]:
        """Targeted recomputation triggered by a new or modified IncidentEvidenceLink."""
        stmt = select(IncidentEvidenceLink).where(IncidentEvidenceLink.id == link_id)
        res = await db.execute(stmt)
        link = res.scalar_one_or_none()
        if not link:
            logger.warning("Evidence link %s not found for credibility recomputation.", link_id)
            return None
        return await self.evaluate_incident_credibility(db=db, incident_id=link.report_id)

    async def recompute_for_observation_corroboration(
        self,
        db: AsyncSession,
        corroboration_id: uuid.UUID,
    ) -> Optional[CredibilityResult]:
        """Targeted recomputation on modified IncidentObservationCorroboration."""
        stmt = select(IncidentObservationCorroboration).where(
            IncidentObservationCorroboration.id == corroboration_id
        )
        res = await db.execute(stmt)
        corr = res.scalar_one_or_none()
        if not corr:
            logger.warning(
                "Observation corroboration %s not found for credibility recomputation.",
                corroboration_id,
            )
            return None
        return await self.evaluate_incident_credibility(db=db, incident_id=corr.report_id)

    async def recompute_for_cluster(
        self,
        db: AsyncSession,
        cluster_id: uuid.UUID,
    ) -> List[CredibilityResult]:
        """Targeted recomputation for all member reports in an affected DuplicateCluster."""
        # Find primary report and all members
        cluster_stmt = select(DuplicateCluster).where(DuplicateCluster.id == cluster_id)
        cluster_res = await db.execute(cluster_stmt)
        cluster = cluster_res.scalar_one_or_none()

        if not cluster:
            logger.warning(
                "DuplicateCluster %s not found for credibility recomputation.", cluster_id
            )
            return []

        members_stmt = select(DuplicateMember).where(DuplicateMember.cluster_id == cluster_id)
        members_res = await db.execute(members_stmt)
        members = list(members_res.scalars().all())

        affected_ids = {cluster.primary_report_id}
        for m in members:
            affected_ids.add(m.report_id)

        results: List[CredibilityResult] = []
        for r_id in affected_ids:
            res = await self.evaluate_incident_credibility(db=db, incident_id=r_id, commit=False)
            if res:
                results.append(res)

        await db.commit()
        return results

    async def recompute_incident_batch(
        self,
        db: AsyncSession,
        incident_ids: List[uuid.UUID],
    ) -> List[CredibilityResult]:
        """Batch recomputation of multiple target incidents."""
        results: List[CredibilityResult] = []
        for r_id in incident_ids:
            res = await self.evaluate_incident_credibility(db=db, incident_id=r_id, commit=False)
            if res:
                results.append(res)
        await db.commit()
        return results


credibility_engine = CredibilityEngine()
