import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.report import WeatherReport
from app.models.verification import VerificationEvent
from app.services.report_service import (
    ALLOWED_VERIFICATION_TRANSITIONS,
    InvalidStateTransitionError,
    report_service,
)


async def _create_test_report(
    db_session: AsyncSession,
    status: str = "PENDING",
    tracking_prefix: str = "RPT-SM",
) -> WeatherReport:
    """Helper to create a test report in a specific verification status."""
    uid = uuid.uuid4().hex[:8]
    source = await report_service.get_or_create_source(
        session=db_session,
        source_code=f"SRC_SM_{uid}",
        name="State Machine Test Source",
    )
    processing_st = (
        "PENDING" if status == "PENDING" else ("COMPLETED" if status == "VERIFIED" else "CLOSED")
    )
    report = WeatherReport(
        tracking_id=f"{tracking_prefix}-{uid}",
        source_id=source.id,
        title=f"State Machine Test Report {uid}",
        reported_category="HEAVY_RAINFALL",
        severity="HIGH",
        latitude=19.0760,
        longitude=72.8777,
        occurred_at=datetime.now(timezone.utc),
        geom="SRID=4326;POINT(72.8777 19.0760)",
        processing_status=processing_st,
        verification_status=status,
        credibility_score=0.6500,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    return report


@pytest.mark.asyncio
async def test_transition_matrix_definition() -> None:
    """Verify transition table completeness and isolation."""
    assert "PENDING" in ALLOWED_VERIFICATION_TRANSITIONS
    assert "UNDER_REVIEW" in ALLOWED_VERIFICATION_TRANSITIONS
    assert "VERIFIED" in ALLOWED_VERIFICATION_TRANSITIONS
    assert "REJECTED" in ALLOWED_VERIFICATION_TRANSITIONS
    assert "DUPLICATE" in ALLOWED_VERIFICATION_TRANSITIONS

    # PENDING can transition to all 4 states
    assert ALLOWED_VERIFICATION_TRANSITIONS["PENDING"] == {
        "UNDER_REVIEW",
        "VERIFIED",
        "REJECTED",
        "DUPLICATE",
    }
    # UNDER_REVIEW can transition to 3 terminal states
    assert ALLOWED_VERIFICATION_TRANSITIONS["UNDER_REVIEW"] == {
        "VERIFIED",
        "REJECTED",
        "DUPLICATE",
    }
    # Terminal states are strictly empty sets
    assert ALLOWED_VERIFICATION_TRANSITIONS["VERIFIED"] == set()
    assert ALLOWED_VERIFICATION_TRANSITIONS["REJECTED"] == set()
    assert ALLOWED_VERIFICATION_TRANSITIONS["DUPLICATE"] == set()


@pytest.mark.asyncio
async def test_valid_pending_to_under_review(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test Case A: Valid PENDING -> UNDER_REVIEW transition."""
    report = await _create_test_report(db_session, status="PENDING")
    res = await api_client.post(
        f"/api/v1/verification/{report.id}/review",
        json={"notes": "Operator started manual review."},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["verification"]["status"] == "UNDER_REVIEW"
    assert len(data["verification_history"]) == 1
    assert data["verification_history"][0]["previous_status"] == "PENDING"
    assert data["verification_history"][0]["new_status"] == "UNDER_REVIEW"


@pytest.mark.asyncio
async def test_valid_pending_to_verified(api_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test Case B: Valid PENDING -> VERIFIED transition."""
    report = await _create_test_report(db_session, status="PENDING")
    res = await api_client.post(
        f"/api/v1/verification/{report.id}/verify",
        json={"notes": "Direct verification from ground team."},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["verification"]["status"] == "VERIFIED"
    assert len(data["verification_history"]) == 1
    assert data["verification_history"][0]["previous_status"] == "PENDING"
    assert data["verification_history"][0]["new_status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_valid_pending_to_rejected(api_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test Case C: Valid PENDING -> REJECTED transition."""
    report = await _create_test_report(db_session, status="PENDING")
    res = await api_client.post(
        f"/api/v1/verification/{report.id}/reject",
        json={"rejection_reason": "INACCURATE_LOCATION", "notes": "Wrong coordinates."},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["verification"]["status"] == "REJECTED"
    assert len(data["verification_history"]) == 1
    assert data["verification_history"][0]["previous_status"] == "PENDING"
    assert data["verification_history"][0]["new_status"] == "REJECTED"


@pytest.mark.asyncio
async def test_valid_pending_to_duplicate(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test Case D: Valid PENDING -> DUPLICATE transition."""
    report = await _create_test_report(db_session, status="PENDING")
    res = await api_client.post(
        f"/api/v1/verification/{report.id}/mark-duplicate",
        json={"primary_report_id": "RPT-PRIMARY-99", "notes": "Duplicate of primary incident."},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["verification"]["status"] == "DUPLICATE"
    assert len(data["verification_history"]) == 1
    assert data["verification_history"][0]["previous_status"] == "PENDING"
    assert data["verification_history"][0]["new_status"] == "DUPLICATE"


@pytest.mark.asyncio
async def test_valid_under_review_to_terminal_states(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test Cases E, F, G: Valid UNDER_REVIEW -> VERIFIED, REJECTED, DUPLICATE."""
    # E: UNDER_REVIEW -> VERIFIED
    rep_e = await _create_test_report(db_session, status="PENDING")
    await api_client.post(f"/api/v1/verification/{rep_e.id}/review")
    res_e = await api_client.post(
        f"/api/v1/verification/{rep_e.id}/verify",
        json={"notes": "Verified post-review"},
    )
    assert res_e.status_code == 200
    assert res_e.json()["data"]["verification"]["status"] == "VERIFIED"
    assert len(res_e.json()["data"]["verification_history"]) == 2

    # F: UNDER_REVIEW -> REJECTED
    rep_f = await _create_test_report(db_session, status="PENDING")
    await api_client.post(f"/api/v1/verification/{rep_f.id}/review")
    res_f = await api_client.post(
        f"/api/v1/verification/{rep_f.id}/reject",
        json={"rejection_reason": "HOAX", "notes": "Confirmed hoax"},
    )
    assert res_f.status_code == 200
    assert res_f.json()["data"]["verification"]["status"] == "REJECTED"
    assert len(res_f.json()["data"]["verification_history"]) == 2

    # G: UNDER_REVIEW -> DUPLICATE
    rep_g = await _create_test_report(db_session, status="PENDING")
    await api_client.post(f"/api/v1/verification/{rep_g.id}/review")
    res_g = await api_client.post(
        f"/api/v1/verification/{rep_g.id}/mark-duplicate",
        json={"primary_report_id": "RPT-PRIMARY-01"},
    )
    assert res_g.status_code == 200
    assert res_g.json()["data"]["verification"]["status"] == "DUPLICATE"
    assert len(res_g.json()["data"]["verification_history"]) == 2


@pytest.mark.asyncio
async def test_terminal_verified_mutations_blocked(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test Case H: VERIFIED is terminal and cannot transition to any state."""
    report = await _create_test_report(db_session, status="VERIFIED")

    # VERIFIED -> UNDER_REVIEW (Blocked)
    res_review = await api_client.post(f"/api/v1/verification/{report.id}/review")
    assert res_review.status_code == 400
    assert res_review.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # VERIFIED -> REJECTED (Blocked)
    res_reject = await api_client.post(
        f"/api/v1/verification/{report.id}/reject",
        json={"rejection_reason": "OUTDATED_ARCHIVE"},
    )
    assert res_reject.status_code == 400
    assert res_reject.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # VERIFIED -> DUPLICATE (Blocked)
    res_dup = await api_client.post(
        f"/api/v1/verification/{report.id}/mark-duplicate",
        json={"primary_report_id": "RPT-01"},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # VERIFIED -> VERIFIED (Repeated terminal action blocked)
    res_verify = await api_client.post(
        f"/api/v1/verification/{report.id}/verify",
        json={"notes": "Duplicate verify"},
    )
    assert res_verify.status_code == 400
    assert res_verify.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_terminal_rejected_mutations_blocked(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test Case I: REJECTED is terminal and cannot transition to any state."""
    report = await _create_test_report(db_session, status="REJECTED")

    # REJECTED -> VERIFIED (Blocked)
    res_verify = await api_client.post(
        f"/api/v1/verification/{report.id}/verify",
        json={"notes": "Revive rejected"},
    )
    assert res_verify.status_code == 400
    assert res_verify.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # REJECTED -> UNDER_REVIEW (Blocked)
    res_review = await api_client.post(f"/api/v1/verification/{report.id}/review")
    assert res_review.status_code == 400
    assert res_review.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # REJECTED -> DUPLICATE (Blocked)
    res_dup = await api_client.post(
        f"/api/v1/verification/{report.id}/mark-duplicate",
        json={"primary_report_id": "RPT-01"},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # REJECTED -> REJECTED (Repeated terminal action blocked)
    res_reject = await api_client.post(
        f"/api/v1/verification/{report.id}/reject",
        json={"rejection_reason": "HOAX"},
    )
    assert res_reject.status_code == 400
    assert res_reject.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_terminal_duplicate_mutations_blocked(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test Case J: DUPLICATE is terminal and cannot transition to any state."""
    report = await _create_test_report(db_session, status="DUPLICATE")

    # DUPLICATE -> VERIFIED (Blocked)
    res_verify = await api_client.post(f"/api/v1/verification/{report.id}/verify")
    assert res_verify.status_code == 400
    assert res_verify.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # DUPLICATE -> UNDER_REVIEW (Blocked)
    res_review = await api_client.post(f"/api/v1/verification/{report.id}/review")
    assert res_review.status_code == 400
    assert res_review.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # DUPLICATE -> REJECTED (Blocked)
    res_reject = await api_client.post(
        f"/api/v1/verification/{report.id}/reject",
        json={"rejection_reason": "HOAX"},
    )
    assert res_reject.status_code == 400
    assert res_reject.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # DUPLICATE -> DUPLICATE (Repeated terminal action blocked)
    res_dup = await api_client.post(
        f"/api/v1/verification/{report.id}/mark-duplicate",
        json={"primary_report_id": "RPT-01"},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_invalid_transition_no_side_effects_on_db(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test Cases K, L, M: Invalid transitions return HTTP 400 and do not modify DB status."""
    report = await _create_test_report(db_session, status="REJECTED")

    # Count existing verification events
    count_stmt = select(VerificationEvent).where(VerificationEvent.report_id == report.id)
    initial_events = (await db_session.execute(count_stmt)).scalars().all()
    initial_count = len(initial_events)

    # Attempt illegal transition
    res = await api_client.post(
        f"/api/v1/reports/{report.tracking_id}/verify",
        json={"notes": "Illegal attempt"},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_STATE_TRANSITION"
    assert "Cannot transition report from terminal state 'REJECTED'" in body["error"]["message"]

    # Re-query report from DB directly (fresh session query)
    stmt = (
        select(WeatherReport)
        .where(WeatherReport.id == report.id)
        .options(selectinload(WeatherReport.verification_events))
        .execution_options(populate_existing=True)
    )
    refreshed = (await db_session.execute(stmt)).scalar_one()

    # Verify status is unchanged
    assert refreshed.verification_status == "REJECTED"
    # Verify no new audit event was persisted
    assert len(refreshed.verification_events) == initial_count


@pytest.mark.asyncio
async def test_service_level_exception_direct(db_session: AsyncSession) -> None:
    """Verify service-level direct call raises InvalidStateTransitionError."""
    report = await _create_test_report(db_session, status="VERIFIED")

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await report_service.update_verification_status(
            session=db_session,
            report_id_or_tracking=str(report.id),
            new_status="UNDER_REVIEW",
        )

    err = exc_info.value
    assert err.current_status == "VERIFIED"
    assert err.target_status == "UNDER_REVIEW"
    assert "Terminal verification states" in str(err)
