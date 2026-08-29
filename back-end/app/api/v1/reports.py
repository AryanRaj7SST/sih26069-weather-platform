import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.report import WeatherReport
from app.schemas.credibility import IncidentCredibilityResponse
from app.schemas.duplicate import IncidentClusterDetailResponse
from app.schemas.evidence import IncidentEvidenceListResponse
from app.schemas.intelligence import IncidentIntelligenceStatusResponse
from app.schemas.observation import IncidentObservationListResponse
from app.schemas.report import (
    CategoryDetail,
    CitizenReportCreate,
    LocationDetail,
    MediaDetail,
    PaginationMeta,
    ReportDetailData,
    ReportDetailResponse,
    ReportDuplicateRequest,
    ReportListResponse,
    ReportRejectRequest,
    ReportReviewRequest,
    ReportSubmitData,
    ReportSubmitResponse,
    ReportVerifyRequest,
    SeverityType,
    VerificationEventDetail,
)
from app.services.incident_query_service import incident_query_service
from app.services.report_service import report_service
from app.services.storage import storage_service

router = APIRouter()

ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


def _serialize_report(report: WeatherReport) -> ReportDetailData:
    """Serialize a WeatherReport model to a public ReportDetailData schema."""
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

    history_items: List[VerificationEventDetail] = []
    if getattr(report, "verification_events", None):
        sorted_events = sorted(
            report.verification_events,
            key=lambda e: e.created_at,
            reverse=True,
        )
        for ev in sorted_events:
            history_items.append(
                VerificationEventDetail(
                    id=ev.id,
                    previous_status=ev.previous_status,
                    new_status=ev.new_status,
                    notes=ev.notes,
                    action_metadata=ev.action_metadata,
                    created_at=ev.created_at,
                    reviewer_name="Authorized Reviewer",
                )
            )

    return ReportDetailData(
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
        verification_history=history_items,
        created_at=report.created_at,
    )


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
    "",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Incident Reports",
    description="Paginated list of incident reports with multi-criteria and geospatial filtering.",
)
async def list_reports(
    page: int = Query(default=1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(default=20, ge=1, le=100, description="Records per page (max 100)"),
    category: Optional[str] = Query(None, description="Event category code"),
    severity: Optional[SeverityType] = Query(None, description="Severity level"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Verification status or comma-separated statuses"
    ),
    from_date: Optional[datetime] = Query(None, description="Start date (ISO8601)"),
    to_date: Optional[datetime] = Query(None, description="End date (ISO8601)"),
    min_credibility: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="Minimum credibility score"
    ),
    bbox: Optional[str] = Query(
        None,
        description="Bounding box in min_lon,min_lat,max_lon,max_lat format",
    ),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    """List and filter weather incident reports for map explorer and public lists."""
    # 1. Validate date bounds
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Parameter 'from_date' cannot be later than 'to_date'.",
            },
        )

    # 2. Parse and validate bbox if provided
    parsed_bbox: Optional[Tuple[float, float, float, float]] = None
    if bbox:
        parts = bbox.split(",")
        if len(parts) != 4:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid bbox format. Expected 'min_lon,min_lat,max_lon,max_lat'.",
                },
            )
        try:
            min_lon, min_lat, max_lon, max_lat = (float(p.strip()) for p in parts)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid bbox coordinates. Values must be numeric floats.",
                },
            )

        valid_lon = -180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0
        valid_lat = -90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0
        if not (valid_lon and valid_lat):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "VALIDATION_ERROR",
                    "message": "Bounding box coordinates out of valid geographic ranges.",
                },
            )

        if min_lon > max_lon or min_lat > max_lat:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid bbox range: min values must be <= max values.",
                },
            )

        parsed_bbox = (min_lon, min_lat, max_lon, max_lat)

    # 3. Query database
    (
        reports,
        total_records,
        total_pages,
        has_next,
        has_prev,
    ) = await report_service.list_reports(
        session=db,
        page=page,
        page_size=page_size,
        category=category,
        severity=severity,
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        min_credibility=min_credibility,
        bbox=parsed_bbox,
    )

    # 4. Serialize data
    items = [_serialize_report(r) for r in reports]

    return ReportListResponse(
        success=True,
        data=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
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

    return ReportDetailResponse(
        success=True,
        data=_serialize_report(report),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.post(
    "/{id}/verify",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Authorize and Verify Weather Report",
    description="Updates verification status to VERIFIED and records audit event.",
)
async def verify_report(
    id: str = Path(..., min_length=3, max_length=64, description="Report UUID or Tracking ID"),
    payload: Optional[ReportVerifyRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    """Authorize a weather report as verified ground truth."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Malformed identifier: {id}",
                "details": [],
            },
        )

    try:
        updated = await report_service.update_verification_status(
            session=db,
            report_id_or_tracking=clean_id,
            new_status="VERIFIED",
            notes=payload.notes if payload else None,
            action_metadata={"broadcast_alert": payload.broadcast_alert} if payload else None,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": f"Report not found: {clean_id}",
                "details": [],
            },
        )

    return ReportDetailResponse(
        success=True,
        data=_serialize_report(updated),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.post(
    "/{id}/reject",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Weather Report as False / Hoax / Inaccurate",
    description="Updates verification status to REJECTED and records audit event.",
)
async def reject_report(
    id: str = Path(..., min_length=3, max_length=64, description="Report UUID or Tracking ID"),
    payload: Optional[ReportRejectRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    """Reject false or inaccurate report."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Malformed identifier: {id}",
                "details": [],
            },
        )

    try:
        updated = await report_service.update_verification_status(
            session=db,
            report_id_or_tracking=clean_id,
            new_status="REJECTED",
            notes=payload.notes if payload else None,
            action_metadata={"rejection_reason": payload.rejection_reason} if payload else None,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": f"Report not found: {clean_id}",
                "details": [],
            },
        )

    return ReportDetailResponse(
        success=True,
        data=_serialize_report(updated),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.post(
    "/{id}/mark-duplicate",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Weather Report as Duplicate",
    description="Updates verification status to DUPLICATE and records audit event.",
)
async def mark_duplicate_report(
    id: str = Path(..., min_length=3, max_length=64, description="Report UUID or Tracking ID"),
    payload: Optional[ReportDuplicateRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    """Mark a redundant report as duplicate."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Malformed identifier: {id}",
                "details": [],
            },
        )

    try:
        updated = await report_service.update_verification_status(
            session=db,
            report_id_or_tracking=clean_id,
            new_status="DUPLICATE",
            notes=payload.notes if payload else None,
            action_metadata={"primary_report_id": payload.primary_report_id} if payload else None,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": f"Report not found: {clean_id}",
                "details": [],
            },
        )

    return ReportDetailResponse(
        success=True,
        data=_serialize_report(updated),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.post(
    "/{id}/review",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Weather Report Under Review",
    description="Updates verification status to UNDER_REVIEW and records audit event.",
)
async def place_report_under_review(
    id: str = Path(..., min_length=3, max_length=64, description="Report UUID or Tracking ID"),
    payload: Optional[ReportReviewRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    """Mark report as actively under review by an operator."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Malformed identifier: {id}",
                "details": [],
            },
        )

    try:
        updated = await report_service.update_verification_status(
            session=db,
            report_id_or_tracking=clean_id,
            new_status="UNDER_REVIEW",
            notes=payload.notes if payload else None,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": f"Report not found: {clean_id}",
                "details": [],
            },
        )

    return ReportDetailResponse(
        success=True,
        data=_serialize_report(updated),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.get(
    "/{id}/credibility",
    response_model=IncidentCredibilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Report Credibility Breakdown",
)
async def get_report_credibility(
    id: str = Path(..., min_length=3, max_length=64, description="Report UUID or Tracking ID"),
    db: AsyncSession = Depends(get_db),
) -> IncidentCredibilityResponse:
    """Retrieve credibility evaluation breakdown for report."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Malformed identifier"
        )

    data = await incident_query_service.get_incident_credibility(session=db, identifier=clean_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return IncidentCredibilityResponse(
        success=True,
        data=data,
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.get(
    "/{id}/intelligence",
    response_model=IncidentIntelligenceStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Report Intelligence Readiness Status",
)
async def get_report_intelligence(
    id: str = Path(..., min_length=3, max_length=64, description="Report UUID or Tracking ID"),
    db: AsyncSession = Depends(get_db),
) -> IncidentIntelligenceStatusResponse:
    """Retrieve intelligence orchestration readiness for report."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Malformed identifier"
        )

    data = await incident_query_service.get_incident_intelligence_status(
        session=db, identifier=clean_id
    )
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return IncidentIntelligenceStatusResponse(
        success=True,
        data=data,
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.get(
    "/{id}/evidence",
    response_model=IncidentEvidenceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Report Linked Digital Evidence",
)
async def get_report_evidence(
    id: str = Path(..., min_length=3, max_length=64, description="Report UUID or Tracking ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> IncidentEvidenceListResponse:
    """Retrieve paginated linked evidence for report."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Malformed identifier"
        )

    (
        items,
        total_records,
        total_pages,
        has_next,
        has_prev,
    ) = await incident_query_service.get_incident_evidence(
        session=db, identifier=clean_id, page=page, page_size=page_size
    )
    if items is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return IncidentEvidenceListResponse(
        success=True,
        data=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        ),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.get(
    "/{id}/observations",
    response_model=IncidentObservationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Report Corroborating Physical Observations",
)
async def get_report_observations(
    id: str = Path(..., min_length=3, max_length=64, description="Report UUID or Tracking ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> IncidentObservationListResponse:
    """Retrieve paginated observations corroborating report."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Malformed identifier"
        )

    (
        items,
        total_records,
        total_pages,
        has_next,
        has_prev,
    ) = await incident_query_service.get_incident_observations(
        session=db, identifier=clean_id, page=page, page_size=page_size
    )
    if items is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return IncidentObservationListResponse(
        success=True,
        data=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        ),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )


@router.get(
    "/{id}/cluster",
    response_model=IncidentClusterDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Report Duplicate Cluster Details",
)
async def get_report_cluster(
    id: str = Path(..., min_length=3, max_length=64, description="Report UUID or Tracking ID"),
    db: AsyncSession = Depends(get_db),
) -> IncidentClusterDetailResponse:
    """Retrieve duplicate cluster topology for report."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Malformed identifier"
        )

    data = await incident_query_service.get_incident_cluster(session=db, identifier=clean_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return IncidentClusterDetailResponse(
        success=True,
        data=data,
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
        },
    )
