import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import UploadFile
from geoalchemy2.elements import WKTElement
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.category import EventCategory
from app.models.media import ReportMedia
from app.models.report import WeatherReport
from app.models.source import Source
from app.schemas.report import CitizenReportCreate
from app.services.storage import StorageService, storage_service


class ReportService:
    """Business logic service for citizen weather reports."""

    def __init__(self, storage: Optional[StorageService] = None) -> None:
        self.storage = storage or storage_service

    @staticmethod
    def generate_tracking_id() -> str:
        """Generate human-readable and safe tracking identifier.

        Format: RPT-YYYYMMDD-XXXX (e.g., RPT-20260829-B4F8)
        """
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_suffix = secrets.token_hex(2).upper()
        return f"RPT-{date_str}-{random_suffix}"

    async def get_or_create_citizen_source(self, session: AsyncSession) -> Source:
        """Ensure standard CITIZEN_WEB data source exists in the database."""
        stmt = select(Source).where(Source.source_code == "CITIZEN_WEB")
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()

        if source is None:
            source = Source(
                source_code="CITIZEN_WEB",
                name="Citizen Web Portal",
                source_type="CITIZEN_REPORT",
                base_trust_score=0.6,
                is_active=True,
            )
            session.add(source)
            await session.flush()

        return source

    async def resolve_category(
        self, session: AsyncSession, category_code: str
    ) -> Tuple[Optional[uuid.UUID], Optional[str]]:
        """Resolve category UUID and reported category title."""
        stmt = select(EventCategory).where(EventCategory.category_code == category_code.upper())
        result = await session.execute(stmt)
        category = result.scalar_one_or_none()

        if category is not None:
            return category.id, category.title
        return None, category_code

    async def create_citizen_report(
        self,
        session: AsyncSession,
        payload: CitizenReportCreate,
        media_files: Optional[List[UploadFile]] = None,
    ) -> Tuple[WeatherReport, int]:
        """Process and persist a citizen weather report with optional media uploads."""
        uploaded_keys: List[str] = []
        report_id = uuid.uuid4()
        tracking_id = self.generate_tracking_id()

        try:
            # 1. Resolve source and category
            source = await self.get_or_create_citizen_source(session)
            category_id, reported_category = await self.resolve_category(
                session, payload.category_code
            )

            # 2. Upload media files if present
            media_records: List[ReportMedia] = []
            if media_files:
                if len(media_files) > 3:
                    raise ValueError("Maximum of 3 media files can be attached per report")

                for upload_file in media_files:
                    if upload_file.filename:
                        content_type = upload_file.content_type or "application/octet-stream"
                        file_bytes = await upload_file.read()

                        if len(file_bytes) == 0:
                            continue

                        (
                            storage_key,
                            sha256_hash,
                            file_size,
                            media_type,
                        ) = self.storage.upload_media_file(
                            file_bytes=file_bytes,
                            filename=upload_file.filename,
                            content_type=content_type,
                            bucket_name=settings.S3_BUCKET_NAME,
                            report_id=report_id,
                        )
                        uploaded_keys.append(storage_key)

                        media_records.append(
                            ReportMedia(
                                report_id=report_id,
                                media_type=media_type,
                                storage_bucket=settings.S3_BUCKET_NAME,
                                storage_key=storage_key,
                                mime_type=content_type,
                                file_size_bytes=file_size,
                                sha256_hash=sha256_hash,
                            )
                        )

            # 3. Construct spatial PostGIS Point
            point_wkt = f"POINT({payload.longitude} {payload.latitude})"
            geom = WKTElement(point_wkt, srid=4326)

            occurred_time = payload.occurred_at or datetime.now(timezone.utc)

            # 4. Instantiate WeatherReport entity
            report = WeatherReport(
                id=report_id,
                tracking_id=tracking_id,
                source_id=source.id,
                category_id=category_id,
                reported_category=reported_category,
                severity=payload.severity,
                title=payload.title,
                description=payload.description,
                location_name=payload.location_name,
                geom=geom,
                latitude=payload.latitude,
                longitude=payload.longitude,
                occurred_at=occurred_time,
                processing_status="QUEUED",
                verification_status="PENDING",
                credibility_score=0.0,
            )

            session.add(report)
            for media in media_records:
                session.add(media)

            await session.commit()
            await session.refresh(report)

            return report, len(media_records)

        except Exception:
            await session.rollback()
            # Clean up uploaded media in storage if database commit fails
            for key in uploaded_keys:
                self.storage.delete_media_file(key, bucket_name=settings.S3_BUCKET_NAME)
            raise

    async def get_report_by_id_or_tracking(
        self, session: AsyncSession, identifier: str
    ) -> Optional[WeatherReport]:
        """Fetch a single report by tracking ID or UUID primary key."""
        clean_id = identifier.strip()
        if not clean_id:
            return None

        # Check if identifier can be parsed as a UUID
        parsed_uuid: Optional[uuid.UUID] = None
        try:
            parsed_uuid = uuid.UUID(clean_id)
        except ValueError:
            parsed_uuid = None

        stmt = select(WeatherReport).options(
            selectinload(WeatherReport.category),
            selectinload(WeatherReport.media),
        )

        if parsed_uuid is not None:
            stmt = stmt.where(
                or_(
                    WeatherReport.id == parsed_uuid,
                    WeatherReport.tracking_id == clean_id,
                )
            )
        else:
            stmt = stmt.where(WeatherReport.tracking_id == clean_id)

        result = await session.execute(stmt)
        return result.scalar_one_or_none()


report_service = ReportService()
