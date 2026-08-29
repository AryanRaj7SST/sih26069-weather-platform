import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.schemas import NormalizedEvidenceEvent
from app.models.evidence import EvidenceItem
from app.models.source import Source

logger = logging.getLogger(__name__)


class EvidenceService:
    """Service handling persistence, idempotency, and retrieval of secondary evidence items."""

    async def get_or_create_source(
        self,
        session: AsyncSession,
        source_code: str = "GDELT_DOC",
        name: str = "GDELT DOC 2.0 Web News",
        source_type: str = "RSS",
        base_trust_score: float = 0.70,
    ) -> Source:
        """Fetch existing evidence source or register a new one idempotently."""
        normalized_code = source_code.strip().upper()
        stmt = select(Source).where(Source.source_code == normalized_code)
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()

        if not source:
            source = Source(
                source_code=normalized_code,
                name=name,
                source_type=source_type,
                base_trust_score=base_trust_score,
                is_active=True,
            )
            session.add(source)
            await session.flush()
            logger.info(f"Registered evidence source: {normalized_code}")

        return source

    async def ingest_normalized_evidence(
        self,
        session: AsyncSession,
        event: NormalizedEvidenceEvent,
    ) -> EvidenceItem:
        """Persist or update an external evidence item idempotently via (source_id, external_id)."""
        source = await self.get_or_create_source(
            session=session,
            source_code=event.source_code,
        )

        stmt = select(EvidenceItem).where(
            EvidenceItem.source_id == source.id,
            EvidenceItem.external_id == event.external_id,
        )
        result = await session.execute(stmt)
        existing: Optional[EvidenceItem] = result.scalar_one_or_none()

        if existing:
            existing.title = event.title
            existing.url = event.url
            existing.publisher_domain = event.publisher_domain
            existing.language = event.language
            existing.published_at = event.published_at
            existing.text_snippet = event.text_snippet
            existing.sha256_hash = event.sha256_hash
            existing.raw_payload = event.raw_payload
            await session.commit()
            await session.refresh(existing)
            logger.debug(
                f"Updated existing evidence item '{existing.external_id}' "
                f"({existing.publisher_domain})"
            )
            return existing

        evidence = EvidenceItem(
            source_id=source.id,
            external_id=event.external_id,
            evidence_type=event.evidence_type,
            title=event.title,
            url=event.url,
            publisher_domain=event.publisher_domain,
            language=event.language,
            published_at=event.published_at,
            captured_at=event.captured_at,
            text_snippet=event.text_snippet,
            sha256_hash=event.sha256_hash,
            raw_payload=event.raw_payload,
        )
        session.add(evidence)
        await session.commit()
        await session.refresh(evidence)
        logger.info(
            f"Persisted new evidence item '{evidence.external_id}' ({evidence.publisher_domain})"
        )
        return evidence


evidence_service = EvidenceService()
