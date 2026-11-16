"""Admin dashboard statistics and AI match review."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import require_admin
from ..models import Complaint, Match, Report, User
from ..schemas import MatchReviewIn
from ..serializers import complaint_out, match_out
from ..services.notifications import notify_match_approved, send_notification_email
from .reports import _EAGER as REPORT_EAGER

router = APIRouter(prefix="/api/admin", tags=["admin"])

_MATCH_EAGER = (
    selectinload(Match.lost_report).selectinload(Report.owner),
    selectinload(Match.found_report).selectinload(Report.owner),
)


def _count(db: Session, model, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


@router.get("/stats")
def stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    top_categories = db.execute(
        select(Report.category, func.count(Report.id))
        .group_by(Report.category)
        .order_by(func.count(Report.id).desc())
        .limit(5)
    ).all()

    pending = db.scalars(
        select(Match)
        .options(*_MATCH_EAGER)
        .where(Match.status == "pending")
        .order_by(Match.score.desc())
        .limit(3)
    ).all()

    recent = db.scalars(
        select(Complaint)
        .options(selectinload(Complaint.owner))
        .order_by(Complaint.created_at.desc())
        .limit(5)
    ).all()

    return {
        "users": {
            "total": _count(db, User),
            "students": _count(db, User, User.role == "student"),
            "admins": _count(db, User, User.role == "admin"),
        },
        "reports": {
            "total": _count(db, Report),
            "lost": _count(db, Report, Report.type == "lost"),
            "found": _count(db, Report, Report.type == "found"),
            "open": _count(db, Report, Report.status == "open"),
            "matched": _count(db, Report, Report.status == "matched"),
            "returned": _count(db, Report, Report.status == "returned"),
        },
        "complaints": {
            "total": _count(db, Complaint),
            "received": _count(db, Complaint, Complaint.status == "Received"),
            "in_progress": _count(db, Complaint, Complaint.status == "In Progress"),
            "resolved": _count(db, Complaint, Complaint.status == "Resolved"),
        },
        "matches": {
            "pending": _count(db, Match, Match.status == "pending"),
            "approved": _count(db, Match, Match.status == "approved"),
            "rejected": _count(db, Match, Match.status == "rejected"),
        },
        "top_categories": [
            {"category": category, "count": count} for category, count in top_categories
        ],
        "pending_matches": [match_out(m, admin) for m in pending],
        "recent_complaints": [complaint_out(c, admin) for c in recent],
    }


@router.get("/matches")
def list_matches(
    match_status: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=300),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(Match).options(*_MATCH_EAGER)
    if match_status:
        if match_status not in {"pending", "approved", "rejected"}:
            raise HTTPException(status_code=422, detail="Unknown match status.")
        stmt = stmt.where(Match.status == match_status)
    stmt = stmt.order_by(Match.score.desc()).limit(limit)
    return [match_out(m, admin) for m in db.scalars(stmt).all()]


@router.patch("/matches/{match_id}")
def review_match(
    match_id: int,
    data: MatchReviewIn,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found.")

    match.status = data.status
    created_notifications = []
    if data.status == "approved":
        for report in (match.lost_report, match.found_report):
            if report.status in {"open", "matched"}:
                report.status = "matched"
        created_notifications = notify_match_approved(db, match)

    db.commit()
    db.refresh(match)

    for notification in created_notifications:
        background_tasks.add_task(send_notification_email, notification.id)

    return match_out(match, admin)
