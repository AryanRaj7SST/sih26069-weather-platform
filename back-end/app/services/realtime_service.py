"""Realtime event publishing service over Redis Streams.

Provides an isolated, failure-resilient abstraction for emitting domain lifecycle events
(report creations, triage/verification transitions, intelligence readiness)
to the outbound Redis Stream for downstream SSE and real-time subscribers.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import AsyncRedisClient, redis_client
from app.models.outbox import RealtimeOutbox
from app.models.report import WeatherReport
from app.schemas.realtime import (
    ClusterUpdatedPayload,
    RealtimeEvent,
    RealtimeEventType,
    ReportCreatedPayload,
    ReportIntelligenceReadyPayload,
    ReportVerificationChangedPayload,
)

logger = logging.getLogger(__name__)


class RealtimeService:
    """Service boundary for emitting structured real-time events to Redis Streams and Outbox."""

    def __init__(
        self,
        client: Optional[AsyncRedisClient] = None,
        stream_name: Optional[str] = None,
        maxlen: Optional[int] = None,
    ) -> None:
        self.client = client or redis_client
        self.stream_name = stream_name or settings.REALTIME_STREAM_NAME
        self.maxlen = maxlen or settings.REALTIME_STREAM_MAXLEN

    def stage_event(
        self,
        session: AsyncSession,
        event: RealtimeEvent,
    ) -> RealtimeOutbox:
        """Stage a RealtimeOutbox row in the current database session.

        Guarantees transactional atomicity: The outbox row commits in the exact same
        PostgreSQL transaction as the domain entities.
        """
        outbox_row = RealtimeOutbox(
            event_id=event.event_id,
            event_type=event.event_type.value,
            entity_id=str(event.entity_id),
            tracking_id=event.tracking_id,
            occurred_at=event.occurred_at,
            payload=event.payload,
            status="PENDING",
            attempts=0,
            max_attempts=5,
        )
        session.add(outbox_row)
        return outbox_row

    def stage_report_created(
        self,
        session: AsyncSession,
        report: WeatherReport,
        category_code: Optional[str] = None,
        has_media: bool = False,
        event_id: Optional[uuid.UUID] = None,
    ) -> RealtimeOutbox:
        """Stage a report.created event in the active transaction session."""
        cat_code = (
            category_code
            or (
                report.reported_category
                if hasattr(report, "reported_category") and report.reported_category
                else None
            )
            or "OTHER"
        )
        has_attachments = has_media or bool("media" in report.__dict__ and report.__dict__["media"])

        payload = ReportCreatedPayload(
            tracking_id=report.tracking_id,
            category_code=cat_code,
            severity=report.severity,
            verification_status=report.verification_status or "PENDING",
            location_name=report.location_name,
            latitude=float(report.latitude),
            longitude=float(report.longitude),
            occurred_at=report.occurred_at or report.created_at or datetime.now(timezone.utc),
            has_media=has_attachments,
        )

        event = RealtimeEvent(
            event_id=event_id or uuid.uuid4(),
            event_type=RealtimeEventType.REPORT_CREATED,
            occurred_at=report.created_at or datetime.now(timezone.utc),
            entity_id=str(report.id),
            tracking_id=report.tracking_id,
            payload=payload.model_dump(mode="json"),
        )
        return self.stage_event(session, event)

    def stage_verification_changed(
        self,
        session: AsyncSession,
        report: WeatherReport,
        previous_status: str,
        new_status: str,
        category_code: Optional[str] = None,
        event_id: Optional[uuid.UUID] = None,
    ) -> RealtimeOutbox:
        """Stage a report.verification_changed event in the active transaction session."""
        cat_code = (
            category_code
            or (
                report.reported_category
                if hasattr(report, "reported_category") and report.reported_category
                else None
            )
            or "OTHER"
        )

        payload = ReportVerificationChangedPayload(
            tracking_id=report.tracking_id,
            previous_status=previous_status,
            new_status=new_status,
            category_code=cat_code,
            severity=report.severity,
            location_name=report.location_name,
            occurred_at=report.occurred_at,
        )

        event = RealtimeEvent(
            event_id=event_id or uuid.uuid4(),
            event_type=RealtimeEventType.REPORT_VERIFICATION_CHANGED,
            occurred_at=datetime.now(timezone.utc),
            entity_id=str(report.id),
            tracking_id=report.tracking_id,
            payload=payload.model_dump(mode="json"),
        )
        return self.stage_event(session, event)

    def stage_intelligence_ready(
        self,
        session: AsyncSession,
        report: WeatherReport,
        credibility_score: float,
        readiness: str = "INTELLIGENCE_READY",
        assessed_at: Optional[datetime] = None,
        event_id: Optional[uuid.UUID] = None,
    ) -> RealtimeOutbox:
        """Stage a report.intelligence_ready event in the active transaction session."""
        payload = ReportIntelligenceReadyPayload(
            tracking_id=report.tracking_id,
            credibility_score=float(credibility_score),
            readiness=readiness,
            assessed_at=assessed_at or datetime.now(timezone.utc),
        )

        event = RealtimeEvent(
            event_id=event_id or uuid.uuid4(),
            event_type=RealtimeEventType.REPORT_INTELLIGENCE_READY,
            occurred_at=datetime.now(timezone.utc),
            entity_id=str(report.id),
            tracking_id=report.tracking_id,
            payload=payload.model_dump(mode="json"),
        )
        return self.stage_event(session, event)

    def stage_cluster_updated(
        self,
        session: AsyncSession,
        cluster_id: str,
        primary_report_id: str,
        member_count: int,
        event_id: Optional[uuid.UUID] = None,
    ) -> RealtimeOutbox:
        """Stage a cluster.updated event in the active transaction session."""
        payload = ClusterUpdatedPayload(
            cluster_id=cluster_id,
            primary_report_id=primary_report_id,
            member_count=member_count,
            updated_at=datetime.now(timezone.utc),
        )

        event = RealtimeEvent(
            event_id=event_id or uuid.uuid4(),
            event_type=RealtimeEventType.CLUSTER_UPDATED,
            occurred_at=datetime.now(timezone.utc),
            entity_id=cluster_id,
            tracking_id=None,
            payload=payload.model_dump(mode="json"),
        )
        return self.stage_event(session, event)

    async def publish_staged_outbox(
        self,
        outbox: RealtimeOutbox,
    ) -> Optional[str]:
        """Publish a previously committed outbox event to Redis Streams (fast path)."""
        if outbox.event_type.startswith("orchestration."):
            target_stream = "stream:weather:orchestration"
            orch_dict = outbox.payload if isinstance(outbox.payload, dict) else {}
            payload_fields: Dict[str, Any] = {
                "event_id": str(orch_dict.get("event_id", outbox.event_id)),
                "event_type": orch_dict.get("event_type", outbox.event_type),
                "aggregate_type": orch_dict.get("aggregate_type", ""),
                "aggregate_id": str(orch_dict.get("aggregate_id", outbox.entity_id)),
                "correlation_id": orch_dict.get("correlation_id", ""),
                "attempt": str(orch_dict.get("attempt", outbox.attempts + 1)),
                "data": json.dumps(orch_dict),
            }
        else:
            target_stream = self.stream_name
            payload_fields = {
                "event_id": str(outbox.event_id),
                "event_type": outbox.event_type,
                "occurred_at": outbox.occurred_at.isoformat(),
                "entity_id": str(outbox.entity_id),
                "tracking_id": outbox.tracking_id or "",
                "payload": json.dumps(outbox.payload),
            }

        try:
            msg_id = await self.client.xadd(
                target_stream,
                payload_fields,
                max_len=self.maxlen,
                approximate=True,
            )
            logger.info(
                "Published staged outbox event '%s' (%s) to '%s': %s",
                outbox.event_id,
                outbox.event_type,
                target_stream,
                msg_id,
            )
            return msg_id
        except Exception as e:
            logger.warning(
                "Fast-path Redis publish failed for event '%s' to '%s'; worker will retry: %s",
                outbox.event_id,
                target_stream,
                e,
            )
            return None

    async def publish_event(self, event: RealtimeEvent) -> Optional[str]:
        """Serialize and append a RealtimeEvent to the outbound Redis Stream.

        Guarantees failure isolation: If Redis is temporarily unreachable, the error
        is logged but not raised, ensuring the primary database transaction is never aborted.
        """
        try:
            payload_fields: Dict[str, Any] = {
                "event_id": str(event.event_id),
                "event_type": event.event_type.value,
                "occurred_at": event.occurred_at.isoformat(),
                "entity_id": str(event.entity_id),
                "tracking_id": event.tracking_id or "",
                "payload": json.dumps(event.payload),
            }

            msg_id = await self.client.xadd(
                self.stream_name,
                payload_fields,
                max_len=self.maxlen,
                approximate=True,
            )
            logger.info(
                "Published realtime event '%s' (%s) for entity '%s' to '%s': %s",
                event.event_id,
                event.event_type.value,
                event.entity_id,
                self.stream_name,
                msg_id,
            )
            return msg_id
        except Exception as e:
            logger.error(
                "Failed to publish realtime event '%s' to Redis Stream '%s': %s",
                event.event_id,
                self.stream_name,
                e,
            )
            return None

    async def publish_report_created(
        self,
        report: WeatherReport,
        category_code: Optional[str] = None,
        has_media: bool = False,
    ) -> Optional[str]:
        """Construct and publish a privacy-safe report.created event."""
        try:
            cat_code = (
                category_code
                or (
                    report.reported_category
                    if hasattr(report, "reported_category") and report.reported_category
                    else None
                )
                or "OTHER"
            )
            has_attachments = has_media or bool(
                "media" in report.__dict__ and report.__dict__["media"]
            )

            payload = ReportCreatedPayload(
                tracking_id=report.tracking_id,
                category_code=cat_code,
                severity=report.severity,
                verification_status=report.verification_status or "PENDING",
                location_name=report.location_name,
                latitude=float(report.latitude),
                longitude=float(report.longitude),
                occurred_at=report.occurred_at or report.created_at or datetime.now(timezone.utc),
                has_media=has_attachments,
            )

            event = RealtimeEvent(
                event_id=uuid.uuid4(),
                event_type=RealtimeEventType.REPORT_CREATED,
                occurred_at=report.created_at or datetime.now(timezone.utc),
                entity_id=str(report.id),
                tracking_id=report.tracking_id,
                payload=payload.model_dump(mode="json"),
            )
            return await self.publish_event(event)
        except Exception as e:
            logger.error(
                "Failed to construct report.created realtime event for report '%s': %s",
                getattr(report, "id", "unknown"),
                e,
            )
            return None

    async def publish_verification_changed(
        self,
        report: WeatherReport,
        previous_status: str,
        new_status: str,
        category_code: Optional[str] = None,
    ) -> Optional[str]:
        """Construct and publish a report.verification_changed event."""
        try:
            cat_code = (
                category_code
                or (
                    report.reported_category
                    if hasattr(report, "reported_category") and report.reported_category
                    else None
                )
                or "OTHER"
            )

            payload = ReportVerificationChangedPayload(
                tracking_id=report.tracking_id,
                previous_status=previous_status,
                new_status=new_status,
                category_code=cat_code,
                severity=report.severity,
                location_name=report.location_name,
                occurred_at=report.occurred_at,
            )

            event = RealtimeEvent(
                event_id=uuid.uuid4(),
                event_type=RealtimeEventType.REPORT_VERIFICATION_CHANGED,
                occurred_at=datetime.now(timezone.utc),
                entity_id=str(report.id),
                tracking_id=report.tracking_id,
                payload=payload.model_dump(mode="json"),
            )
            return await self.publish_event(event)
        except Exception as e:
            logger.error(
                "Failed to construct report.verification_changed event for report '%s': %s",
                getattr(report, "id", "unknown"),
                e,
            )
            return None

    async def publish_intelligence_ready(
        self,
        report: WeatherReport,
        credibility_score: float,
        readiness: str = "INTELLIGENCE_READY",
        assessed_at: Optional[datetime] = None,
    ) -> Optional[str]:
        """Construct and publish a report.intelligence_ready event."""
        payload = ReportIntelligenceReadyPayload(
            tracking_id=report.tracking_id,
            credibility_score=float(credibility_score),
            readiness=readiness,
            assessed_at=assessed_at or datetime.now(timezone.utc),
        )

        event = RealtimeEvent(
            event_id=uuid.uuid4(),
            event_type=RealtimeEventType.REPORT_INTELLIGENCE_READY,
            occurred_at=datetime.now(timezone.utc),
            entity_id=str(report.id),
            tracking_id=report.tracking_id,
            payload=payload.model_dump(mode="json"),
        )
        return await self.publish_event(event)

    async def publish_cluster_updated(
        self,
        cluster_id: str,
        primary_report_id: str,
        member_count: int,
    ) -> Optional[str]:
        """Construct and publish a cluster.updated event."""
        payload = ClusterUpdatedPayload(
            cluster_id=cluster_id,
            primary_report_id=primary_report_id,
            member_count=member_count,
            updated_at=datetime.now(timezone.utc),
        )

        event = RealtimeEvent(
            event_id=uuid.uuid4(),
            event_type=RealtimeEventType.CLUSTER_UPDATED,
            occurred_at=datetime.now(timezone.utc),
            entity_id=cluster_id,
            tracking_id=None,
            payload=payload.model_dump(mode="json"),
        )
        return await self.publish_event(event)

    def stage_orchestration_trigger(
        self,
        session: AsyncSession,
        report: WeatherReport,
    ) -> RealtimeOutbox:
        """Stage an orchestration.incident_ingested event in the outbox table.

        This reuses the RealtimeOutbox table to guarantee transactional atomicity
        with the report creation, while ensuring independent retry semantics from the
        frontend SSE events.
        """
        from app.orchestration.events import (
            AggregateType,
            OrchestrationEvent,
            OrchestrationEventType,
        )

        orch_event = OrchestrationEvent(
            event_id=uuid.uuid4(),
            event_type=OrchestrationEventType.INCIDENT_INGESTED,
            aggregate_type=AggregateType.WEATHER_REPORT,
            aggregate_id=report.id,
            producer="rest_api",
            correlation_id=report.tracking_id or str(uuid.uuid4()),
            idempotency_key=f"ingest-{report.id}",
        )

        outbox_row = RealtimeOutbox(
            event_id=orch_event.event_id,
            event_type="orchestration.incident_ingested",
            entity_id=str(report.id),
            tracking_id=report.tracking_id,
            occurred_at=datetime.now(timezone.utc),
            payload=orch_event.model_dump(mode="json"),
            status="PENDING",
            attempts=0,
            max_attempts=5,
        )
        session.add(outbox_row)
        return outbox_row


realtime_service = RealtimeService()
