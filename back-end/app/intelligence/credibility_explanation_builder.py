"""Deterministic structured explanation builder for incident credibility assessments.

Converts mathematical credibility signal breakdowns and provenance summaries
into auditable, human-readable explanations, positive drivers, negative drivers,
and uncertainty flags without using LLMs.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Set

from app.core.config import settings
from app.intelligence.schemas import (
    CredibilityAssessment,
    CredibilityProvenanceSummary,
    CredibilitySignalBreakdown,
    IncidentCredibilityInputs,
    SourceFamily,
)


class CredibilityExplanationBuilder:
    """Builds explainable and auditable assessment envelopes."""

    def build_assessment(
        self,
        incident_id: uuid.UUID,
        inputs: IncidentCredibilityInputs,
        signals: CredibilitySignalBreakdown,
        engine_version: str = settings.CREDIBILITY_ENGINE_VERSION,
        policy_version: str = settings.CREDIBILITY_POLICY_VERSION,
        assessed_at: datetime | None = None,
        is_stale: bool = False,
        is_failure_fallback: bool = False,
    ) -> CredibilityAssessment:
        """Construct full structured CredibilityAssessment from scorer outputs."""
        now = assessed_at or datetime.now(timezone.utc)

        # 1. Provenance Summary
        participating_families: Set[SourceFamily] = {inputs.origin_family}
        has_cross_quoted = False
        for grp in inputs.evidence_groups:
            if grp.is_derived_lineage:
                has_cross_quoted = True
            elif (grp.max_confidence * grp.role_weight) > 0.10:
                participating_families.add(grp.source_family)

        for stn in inputs.observation_stations:
            if (stn.corroboration_score * stn.relationship_weight) > 0.10:
                participating_families.add(stn.source_family)

        provenance = CredibilityProvenanceSummary(
            originating_source_family=inputs.origin_family,
            independent_family_count=len(participating_families),
            participating_families=sorted(list(participating_families)),
            cluster_member_count=inputs.cluster_member_count,
            digital_provenance_groups_count=len(inputs.evidence_groups),
            physical_stations_count=len(inputs.observation_stations),
            has_cross_quoted_lineage=has_cross_quoted,
        )

        # 2. Positive Drivers
        positive_drivers: List[str] = []
        if signals.source_prior >= 0.80:
            positive_drivers.append(
                f"High institutional source trust ({signals.source_prior:.2f}) "
                f"from {inputs.source_code}."
            )
        elif signals.source_prior >= 0.50:
            positive_drivers.append(
                f"Moderate baseline source trust ({signals.source_prior:.2f}) "
                f"from {inputs.source_code}."
            )

        if signals.crowd_cluster_score > 0.20:
            positive_drivers.append(
                f"Crowd corroboration from {inputs.cluster_member_count} duplicate incident "
                f"reports (score: {signals.crowd_cluster_score:.2f})."
            )

        if signals.digital_evidence_score > 0.20:
            positive_drivers.append(
                f"Digital evidence corroboration across {len(inputs.evidence_groups)} "
                f"distinct provenance groups (score: {signals.digital_evidence_score:.2f})."
            )

        if signals.physical_observation_score > 0.20:
            positive_drivers.append(
                f"Physical sensor telemetry confirmation across "
                f"{len(inputs.observation_stations)} monitoring stations "
                f"(score: {signals.physical_observation_score:.2f})."
            )

        if provenance.independent_family_count >= 2:
            fam_names = ", ".join(f.value for f in provenance.participating_families)
            positive_drivers.append(
                f"Multi-source diversity boost (×{signals.diversity_multiplier:.2f}) from "
                f"{provenance.independent_family_count} independent families ({fam_names})."
            )

        # 3. Negative Drivers
        negative_drivers: List[str] = []
        if signals.negative_penalty > 0.01:
            negative_drivers.append(
                f"Diagnostic negative penalty of -{signals.negative_penalty:.4f} applied "
                "due to contradictory physical telemetry or debunking evidence."
            )

        if signals.applied_cap < 0.98 and signals.penalized_score > signals.applied_cap:
            negative_drivers.append(
                f"Score capped at {signals.applied_cap:.2f} per policy (isolated source "
                "or single-provenance boundary)."
            )

        # 4. Uncertainty Flags
        uncertainty_flags: List[str] = []
        if not inputs.has_coordinates:
            uncertainty_flags.append("Missing structured geographic coordinates.")
        if not inputs.has_timestamp:
            uncertainty_flags.append("Missing exact incident occurrence timestamp.")
        if not inputs.has_description:
            uncertainty_flags.append("Missing detailed incident description.")
        if not inputs.has_location_name:
            uncertainty_flags.append("Unresolved administrative location name.")

        if (
            signals.crowd_cluster_score == 0.0
            and signals.digital_evidence_score == 0.0
            and signals.physical_observation_score == 0.0
        ):
            uncertainty_flags.append(
                "Isolated incident: No external news, crowd, or sensor corroboration available."
            )

        if has_cross_quoted:
            uncertainty_flags.append(
                "Cross-quoted media detected; deduplicated to prevent double-counting."
            )

        if is_stale:
            uncertainty_flags.append(
                "Assessment is marked stale due to an incomplete recomputation."
            )
        if is_failure_fallback:
            uncertainty_flags.append(
                "Preserved historical score due to transient collector failure."
            )

        # 5. Composite Explanation Text
        explanation_lines = [
            f"Machine Credibility Score: {signals.final_credibility_score:.4f} (Ceiling: 0.9800).",
            (
                f"Base incident anchor: {signals.incident_baseline:.4f} "
                f"(Prior {signals.source_prior:.2f}, Quality {signals.report_quality_score:.2f})."
            ),
        ]
        if signals.support_delta > 0.0:
            explanation_lines.append(
                f"Corroboration lift: +{signals.support_delta:.4f} "
                f"(Support {signals.synthesized_support:.4f}, "
                f"Diversity ×{signals.diversity_multiplier:.2f})."
            )
        if signals.negative_penalty > 0.0:
            explanation_lines.append(f"Contradiction penalty: -{signals.negative_penalty:.4f}.")
        if signals.applied_cap < 0.98:
            explanation_lines.append(f"Policy upper bound: {signals.applied_cap:.2f}.")

        explanation_text = "\n".join(explanation_lines)

        return CredibilityAssessment(
            incident_id=incident_id,
            credibility_score=signals.final_credibility_score,
            signals=signals,
            provenance=provenance,
            positive_drivers=positive_drivers,
            negative_drivers=negative_drivers,
            uncertainty_flags=uncertainty_flags,
            explanation=explanation_text,
            engine_version=engine_version,
            policy_version=policy_version,
            assessed_at=now,
            is_stale=is_stale,
            is_failure_fallback=is_failure_fallback,
        )


credibility_explanation_builder = CredibilityExplanationBuilder()
