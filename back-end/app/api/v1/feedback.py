"""Community Feedback Loop API Router."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.feedback import IncidentFeedback
from app.models.report import WeatherReport
from app.schemas.feedback import (
    FeedbackSummaryData,
    FeedbackVoteRequest,
    FeedbackVoteResponse,
)
from app.services.incident_query_service import ID_PATTERN

router = APIRouter()


@router.post(
    "/{id}/feedback",
    response_model=FeedbackVoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Community 'Still Accurate?' Vote",
    description="Records a citizen confirm/dispute vote on an active incident report.",
)
async def submit_incident_feedback(
    request: Request,
    id: str = Path(..., min_length=3, max_length=64, description="Incident UUID or Tracking ID"),
    payload: FeedbackVoteRequest = ...,
    db: AsyncSession = Depends(get_db),
) -> FeedbackVoteResponse:
    """Submit confirm or dispute vote for incident."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": f"Malformed identifier: {id}"},
        )

    vote_kind = payload.vote_type.upper()
    if vote_kind not in ("CONFIRM", "DISPUTE"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "vote_type must be CONFIRM or DISPUTE"},
        )

    # Resolve report
    stmt = select(WeatherReport).where(
        (WeatherReport.id.cast(String) == clean_id) | (WeatherReport.tracking_id == clean_id)
    )
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"Incident not found: {clean_id}"},
        )

    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")[:255]

    vote = IncidentFeedback(
        report_id=report.id,
        vote_type=vote_kind,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    db.add(vote)
    await db.commit()

    # Aggregate counts
    confirm_stmt = select(func.count(IncidentFeedback.id)).where(
        IncidentFeedback.report_id == report.id,
        IncidentFeedback.vote_type == "CONFIRM",
    )
    dispute_stmt = select(func.count(IncidentFeedback.id)).where(
        IncidentFeedback.report_id == report.id,
        IncidentFeedback.vote_type == "DISPUTE",
    )

    conf_res = await db.execute(confirm_stmt)
    disp_res = await db.execute(dispute_stmt)

    conf_cnt = conf_res.scalar() or 0
    disp_cnt = disp_res.scalar() or 0

    return FeedbackVoteResponse(
        success=True,
        data=FeedbackSummaryData(
            report_id=report.id,
            confirm_count=conf_cnt,
            dispute_count=disp_cnt,
            user_voted=True,
            voted_type=vote_kind,
            last_voted_at=datetime.now(timezone.utc),
        ),
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.get(
    "/{id}/feedback",
    response_model=FeedbackVoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Community Feedback Summary",
    description="Returns aggregate confirm/dispute vote counts for an incident.",
)
async def get_incident_feedback_summary(
    id: str = Path(..., min_length=3, max_length=64, description="Incident UUID or Tracking ID"),
    db: AsyncSession = Depends(get_db),
) -> FeedbackVoteResponse:
    """Get feedback summary counts for incident."""
    clean_id = id.strip()
    if not ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": f"Malformed identifier: {id}"},
        )

    stmt = select(WeatherReport).where(
        (WeatherReport.id.cast(String) == clean_id) | (WeatherReport.tracking_id == clean_id)
    )
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"Incident not found: {clean_id}"},
        )

    confirm_stmt = select(func.count(IncidentFeedback.id)).where(
        IncidentFeedback.report_id == report.id,
        IncidentFeedback.vote_type == "CONFIRM",
    )
    dispute_stmt = select(func.count(IncidentFeedback.id)).where(
        IncidentFeedback.report_id == report.id,
        IncidentFeedback.vote_type == "DISPUTE",
    )

    conf_res = await db.execute(confirm_stmt)
    disp_res = await db.execute(dispute_stmt)

    conf_cnt = conf_res.scalar() or 0
    disp_cnt = disp_res.scalar() or 0

    return FeedbackVoteResponse(
        success=True,
        data=FeedbackSummaryData(
            report_id=report.id,
            confirm_count=conf_cnt,
            dispute_count=disp_cnt,
            user_voted=False,
            voted_type="",
            last_voted_at=datetime.now(timezone.utc),
        ),
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )
