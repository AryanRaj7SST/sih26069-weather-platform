import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report import (
    CitizenReportCreate,
    ReportSubmitData,
    ReportSubmitResponse,
    SeverityType,
)
from app.services.report_service import report_service

router = APIRouter()


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
