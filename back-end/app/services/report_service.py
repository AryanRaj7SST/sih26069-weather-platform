import math
import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import UploadFile
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, or_, select
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

    async def list_reports(
        self,
        session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        min_credibility: Optional[float] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Tuple[List[WeatherReport], int, int, bool, bool]:
        """Query and filter weather reports with PostGIS spatial bounds and pagination."""
        stmt = select(WeatherReport).options(
            selectinload(WeatherReport.category),
            selectinload(WeatherReport.media),
        )
        count_stmt = select(func.count(WeatherReport.id))

        filters = []

        if category:
            clean_cat = category.strip().upper()
            stmt = stmt.outerjoin(WeatherReport.category)
            count_stmt = count_stmt.outerjoin(WeatherReport.category)
            filters.append(
                or_(
                    EventCategory.category_code == clean_cat,
                    WeatherReport.reported_category.ilike(f"%{clean_cat}%"),
                )
            )

        if severity:
            clean_sev = severity.strip().upper()
            filters.append(WeatherReport.severity == clean_sev)

        if status:
            statuses = [s.strip().upper() for s in status.split(",") if s.strip()]
            if len(statuses) == 1:
                filters.append(WeatherReport.verification_status == statuses[0])
            elif len(statuses) > 1:
                filters.append(WeatherReport.verification_status.in_(statuses))

        if from_date:
            filters.append(WeatherReport.occurred_at >= from_date)

        if to_date:
            filters.append(WeatherReport.occurred_at <= to_date)

        if min_credibility is not None:
            filters.append(WeatherReport.credibility_score >= min_credibility)

        if bbox is not None:
            min_lon, min_lat, max_lon, max_lat = bbox
            envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
            filters.append(func.ST_Within(WeatherReport.geom, envelope))

        if filters:
            for f in filters:
                stmt = stmt.where(f)
                count_stmt = count_stmt.where(f)

        # 1. Total records count
        count_res = await session.execute(count_stmt)
        total_records = count_res.scalar() or 0

        # 2. Paginated data query
        stmt = stmt.order_by(WeatherReport.occurred_at.desc(), WeatherReport.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(stmt)
        reports = list(result.scalars().all())

        # 3. Calculate pagination metadata
        total_pages = max(1, math.ceil(total_records / page_size)) if total_records > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1

        return reports, total_records, total_pages, has_next, has_prev


report_service = ReportService()
