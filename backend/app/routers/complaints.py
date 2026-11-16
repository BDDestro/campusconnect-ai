"""Complaints: submit with AI triage, track status, admin assignment."""

from __future__ import annotations

from datetime import date as date_type

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ..constants import COMPLAINT_CATEGORIES, COMPLAINT_STATUSES, DEPARTMENTS, PRIORITIES
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import Complaint, User
from ..schemas import ComplaintUpdate
from ..serializers import complaint_out
from ..services.classify import classify_text
from ..services.notifications import (
    notify_complaint_update,
    notify_new_complaint,
    send_notification_email,
)
from ..services.storage import delete_image, save_image

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


def _get_or_404(db: Session, complaint_id: int) -> Complaint:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return complaint


def _can_view(user: User, complaint: Complaint) -> bool:
    return user.role == "admin" or complaint.user_id == user.id


@router.get("")
def list_complaints(
    complaint_status: str | None = Query(None, alias="status"),
    q: str | None = Query(None, max_length=100),
    limit: int = Query(200, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    if complaint_status and complaint_status not in COMPLAINT_STATUSES:
        raise HTTPException(status_code=422, detail="Unknown complaint status.")

    stmt = select(Complaint).options(selectinload(Complaint.owner))
    if user.role != "admin":
        stmt = stmt.where(Complaint.user_id == user.id)
    if complaint_status:
        stmt = stmt.where(Complaint.status == complaint_status)
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Complaint.description.ilike(needle),
                Complaint.reference.ilike(needle),
                Complaint.category.ilike(needle),
            )
        )

    stmt = stmt.order_by(Complaint.created_at.desc()).limit(limit)
    return [complaint_out(item, user) for item in db.scalars(stmt).all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_complaint(
    background_tasks: BackgroundTasks,
    description: str = Form(...),
    image: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    description = (description or "").strip()
    if len(description) < 10:
        raise HTTPException(status_code=422, detail="Please describe the issue in at least 10 characters.")
    if len(description) > 4000:
        raise HTTPException(status_code=422, detail="Description must be at most 4000 characters.")

    suggestion = classify_text(description)
    image_url = save_image(image)

    complaint = Complaint(
        user_id=user.id,
        description=description,
        category=suggestion["category"],
        department=suggestion["department"],
        priority=suggestion["priority"],
        status="Received",
        image_url=image_url,
        ai_source=suggestion["source"],
    )
    try:
        db.add(complaint)
        db.flush()
        complaint.reference = f"CC-{date_type.today().year}-{complaint.id:04d}"
        created_notifications = notify_new_complaint(db, complaint)
        db.commit()
    except Exception:
        db.rollback()
        delete_image(image_url)
        raise

    for notification in created_notifications:
        background_tasks.add_task(send_notification_email, notification.id)

    db.refresh(complaint)
    return complaint_out(complaint, user)


@router.get("/{complaint_id}")
def get_complaint(
    complaint_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    complaint = _get_or_404(db, complaint_id)
    if not _can_view(user, complaint):
        raise HTTPException(status_code=403, detail="You can only view your own complaints.")
    return complaint_out(complaint, user)


@router.patch("/{complaint_id}")
def update_complaint(
    complaint_id: int,
    data: ComplaintUpdate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    complaint = _get_or_404(db, complaint_id)
    updates = data.model_dump(exclude_unset=True, exclude_none=True)

    if "category" in updates and updates["category"] not in COMPLAINT_CATEGORIES:
        raise HTTPException(status_code=422, detail="Unknown complaint category.")
    if "department" in updates and updates["department"] not in DEPARTMENTS:
        raise HTTPException(status_code=422, detail="Unknown department.")
    if "priority" in updates and updates["priority"] not in PRIORITIES:
        raise HTTPException(status_code=422, detail="Unknown priority.")
    if "status" in updates and updates["status"] not in COMPLAINT_STATUSES:
        raise HTTPException(status_code=422, detail="Unknown complaint status.")

    tracked = ("category", "department", "priority", "status", "admin_note")
    before = {field: getattr(complaint, field) for field in tracked}

    for field, value in updates.items():
        setattr(complaint, field, value.strip() if isinstance(value, str) else value)

    changes = {
        field: (before[field], getattr(complaint, field))
        for field in tracked
        if before[field] != getattr(complaint, field)
    }
    created_notifications = notify_complaint_update(db, complaint, changes, admin)

    db.commit()
    db.refresh(complaint)

    for notification in created_notifications:
        background_tasks.add_task(send_notification_email, notification.id)

    return complaint_out(complaint, admin)


@router.delete("/{complaint_id}")
def delete_complaint(
    complaint_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    complaint = _get_or_404(db, complaint_id)
    delete_image(complaint.image_url)
    db.delete(complaint)
    db.commit()
    return {"ok": True}
