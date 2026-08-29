import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report import (
    CategoryDetail,
    CitizenReportCreate,
    LocationDetail,
    MediaDetail,
    ReportDetailData,
    ReportDetailResponse,
    ReportSubmitData,
    ReportSubmitResponse,
    SeverityType,
)
from app.services.report_service import report_service
from app.services.storage import storage_service

router = APIRouter()

ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


@router.post(
    "",
    response_model=ReportSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Citizen Incident Report",
    description="Allows citizens to submit a geotagged weather report with optional media.",
)
async def submit_citizen_report(
    latitude: float = Form(..., description="Latitude coordinate between -90 and 90"),
    longitude: float = Form(..., description="Longitude coordinate between -180 and 180"),
    category_code: str = Form(..., description="Weather event category code"),
    severity: SeverityType = Form(default="MODERATE", description="Incident severity level"),
    title: str = Form(..., description="Brief title summarizing the incident"),
    description: Optional[str] = Form(None, description="Detailed text observation"),
    location_name: Optional[str] = Form(None, description="Landmark or locality name"),
    occurred_at: Optional[datetime] = Form(None, description="Observation timestamp"),
    media_files: Optional[List[UploadFile]] = File(
        None, description="Up to 3 attached photos or videos"
    ),
    db: AsyncSession = Depends(get_db),
) -> ReportSubmitResponse:
    """Intake and persist citizen weather incident reports."""
    # 1. Pydantic validation
    try:
        payload = CitizenReportCreate(
            latitude=latitude,
            longitude=longitude,
            category_code=category_code,
            severity=severity,
            title=title,
            description=description,
            location_name=location_name,
            occurred_at=occurred_at,
        )
    except (ValidationError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Invalid report submission parameters",
                "errors": e.errors() if isinstance(e, ValidationError) else [str(e)],
            },
        )

    # 2. Process and persist report
    try:
        report, media_count = await report_service.create_citizen_report(
            session=db,
            payload=payload,
            media_files=media_files,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BAD_REQUEST",
                "message": str(e),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Failed to persist citizen report",
                "details": str(e),
            },
        )

    return ReportSubmitResponse(
        success=True,
        data=ReportSubmitData(
            id=report.id,
            tracking_id=report.tracking_id,
            processing_status=report.processing_status,
            verification_status=report.verification_status,
            submitted_at=report.created_at,
            media_count=media_count,
        ),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.get(
    "/{id}",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Single Report by ID or Tracking Code",
    description="Fetch public tracking information for a report by tracking ID or UUID.",
)
async def get_report_by_id_or_tracking(
    id: str = Path(
        ...,
        min_length=3,
        max_length=64,
        description="Report UUID or Tracking ID (e.g., RPT-20260829-K8L9)",
    ),
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    """Retrieve public status and incident details for tracking."""
    # 1. Format validation
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": (
                    f"Malformed report identifier: '{id}'. "
                    "Identifier must be alphanumeric with hyphens."
                ),
                "details": [],
            },
        )

    # 2. Database lookup
    report = await report_service.get_report_by_id_or_tracking(
        session=db,
        identifier=clean_id,
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": f"Weather report with ID {clean_id} does not exist.",
                "details": [],
            },
        )

    # 3. Construct category detail
    category_code = (
        report.category.category_code
        if report.category is not None
        else (report.reported_category or "UNKNOWN")
    )
    category_title = (
        report.category.title
        if report.category is not None
        else (report.reported_category or "Weather Incident")
    )

    # 4. Construct media details with public URLs
    media_items: List[MediaDetail] = []
    if report.media:
        for m in report.media:
            media_items.append(
                MediaDetail(
                    id=m.id,
                    media_type=m.media_type,
                    url=storage_service.get_media_url(
                        storage_key=m.storage_key,
                        bucket_name=m.storage_bucket,
                    ),
                    sha256_hash=m.sha256_hash,
                )
            )

    return ReportDetailResponse(
        success=True,
        data=ReportDetailData(
            id=report.id,
            tracking_id=report.tracking_id,
            title=report.title,
            description=report.description,
            category=CategoryDetail(
                code=category_code,
                title=category_title,
            ),
            severity=report.severity,
            location=LocationDetail(
                name=report.location_name,
                latitude=report.latitude,
                longitude=report.longitude,
            ),
            occurred_at=report.occurred_at,
            processing_status=report.processing_status,
            verification_status=report.verification_status,
            credibility_score=report.credibility_score,
            media=media_items,
            created_at=report.created_at,
        ),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )
