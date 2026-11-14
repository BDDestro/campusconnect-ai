"""Lost & found reports: create, browse, detail, status and moderation."""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ..constants import ITEM_CATEGORIES, REPORT_STATUSES, REPORT_TYPES
from ..database import get_db
from ..deps import get_current_user
from ..models import Report, User
from ..schemas import ReportStatusIn
from ..serializers import report_card, report_detail, match_out
from ..services.matching import ensure_matches
from ..services.storage import delete_image, save_image

router = APIRouter(prefix="/api/reports", tags=["reports"])

_EAGER = (
    selectinload(Report.owner),
    selectinload(Report.matches_as_lost),
    selectinload(Report.matches_as_found),
)


def _get_or_404(db: Session, report_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


def _clean(value: str, field: str, minimum: int, maximum: int) -> str:
    value = (value or "").strip()
    if len(value) < minimum:
        raise HTTPException(
            status_code=422, detail=f"{field} must be at least {minimum} characters."
        )
    if len(value) > maximum:
        raise HTTPException(
            status_code=422, detail=f"{field} must be at most {maximum} characters."
        )
    return value


@router.get("")
def list_reports(
    report_type: str | None = Query(None, alias="type"),
    category: str | None = Query(None),
    report_status: str | None = Query(None, alias="status"),
    q: str | None = Query(None, max_length=100),
    mine: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    if report_type and report_type not in REPORT_TYPES:
        raise HTTPException(status_code=422, detail="type must be 'lost' or 'found'.")
    if report_status and report_status not in REPORT_STATUSES:
        raise HTTPException(status_code=422, detail="Unknown report status.")

    stmt = select(Report).options(*_EAGER)
    if report_type:
        stmt = stmt.where(Report.type == report_type)
    if category:
        stmt = stmt.where(Report.category == category)
    if report_status:
        stmt = stmt.where(Report.status == report_status)
    if mine:
        stmt = stmt.where(Report.user_id == user.id)
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Report.title.ilike(needle),
                Report.description.ilike(needle),
                Report.location.ilike(needle),
            )
        )

    stmt = stmt.order_by(Report.created_at.desc()).limit(limit)
    reports = db.scalars(stmt).unique().all()
    return [report_card(report, user) for report in reports]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_report(
    type: str = Form(...),
    title: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    date: str | None = Form(None),
    image: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if type not in REPORT_TYPES:
        raise HTTPException(status_code=422, detail="type must be 'lost' or 'found'.")
    if category not in ITEM_CATEGORIES:
        raise HTTPException(status_code=422, detail="Unknown item category.")

    title = _clean(title, "Title", 3, 160)
    description = _clean(description, "Description", 10, 2000)
    location = _clean(location, "Location", 2, 160)

    try:
        event_date = date_type.fromisoformat(date) if date else date_type.today()
    except ValueError:
        raise HTTPException(status_code=422, detail="Date must be in YYYY-MM-DD format.") from None
    if event_date > date_type.today():
        raise HTTPException(status_code=422, detail="The date cannot be in the future.")

    image_url = save_image(image)
    report = Report(
        user_id=user.id,
        type=type,
        title=title,
        category=category,
        description=description,
        location=location,
        event_date=event_date,
        image_url=image_url,
    )
    try:
        db.add(report)
        db.commit()
        db.refresh(report)
        ensure_matches(db, report)
        db.commit()
    except Exception:
        db.rollback()
        delete_image(image_url)
        raise

    db.refresh(report)
    return report_detail(report, user)


@router.get("/{report_id}")
def get_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return report_detail(_get_or_404(db, report_id), user)


@router.patch("/{report_id}")
def update_report(
    report_id: int,
    data: ReportStatusIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = _get_or_404(db, report_id)
    is_owner = report.user_id == user.id
    is_admin = user.role == "admin"

    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="You can only update your own reports.")
    if not is_admin and data.status not in {"returned", "closed"}:
        raise HTTPException(
            status_code=403,
            detail="Students can only mark their own item as returned or closed.",
        )

    report.status = data.status
    db.commit()
    db.refresh(report)
    return report_detail(report, user)


@router.get("/{report_id}/matches")
def get_matches(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    report = _get_or_404(db, report_id)
    if report.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the owner or an administrator can view matches.")

    matches = list(report.matches_as_lost) + list(report.matches_as_found)
    if user.role != "admin":
        matches = [m for m in matches if m.status != "rejected"]
    matches.sort(key=lambda m: m.score, reverse=True)
    return [match_out(m, user) for m in matches]


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    admin: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    report = _get_or_404(db, report_id)
    delete_image(report.image_url)
    db.delete(report)
    db.commit()
    return {"ok": True}
