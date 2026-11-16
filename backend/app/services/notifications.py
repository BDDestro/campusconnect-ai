"""Create in-app notifications and deliver them by email when SMTP is configured."""

from __future__ import annotations

import hashlib
import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..database import SessionLocal
from ..models import Complaint, Match, Notification, Report, User

logger = logging.getLogger("campusconnect.notifications")


def create_notification(
    db: Session,
    user: User,
    *,
    kind: str,
    title: str,
    body: str,
    link: str,
    dedupe_key: str,
) -> Notification | None:
    """Add one notification unless this exact event was already recorded."""
    exists = db.scalar(select(Notification).where(Notification.dedupe_key == dedupe_key))
    if exists is not None:
        return None

    notification = Notification(
        user_id=user.id,
        kind=kind,
        title=title,
        body=body,
        link=link,
        dedupe_key=dedupe_key,
    )
    db.add(notification)
    db.flush()
    return notification


def notify_new_matches(db: Session, matches: list[Match]) -> list[Notification]:
    """Tell each lost-item owner about new possible matches.

    Multiple matches for the same lost report are grouped into one notification
    so a single report does not flood the student's inbox.
    """
    if not matches:
        return []

    grouped: dict[int, list[Match]] = {}
    for match in matches:
        grouped.setdefault(match.lost_report_id, []).append(match)

    created: list[Notification] = []
    for lost_id, group in grouped.items():
        lost: Report = group[0].lost_report
        best = max(group, key=lambda item: item.score)
        found: Report = best.found_report
        count = len(group)
        match_word = "match" if count == 1 else "matches"
        notification = create_notification(
            db,
            lost.owner,
            kind="match_found",
            title=f'Possible match for "{lost.title}"',
            body=(
                f"We found {count} possible {match_word} for your lost item. "
                f'Best: "{found.title}" ({round(best.score * 100)}% similarity). '
                "An administrator will review it before any handover."
            ),
            link=f"/reports/{lost.id}",
            dedupe_key=(
                f"match-found:{lost_id}:"
                + ",".join(str(item.id) for item in sorted(group, key=lambda row: row.id))
            ),
        )
        if notification is not None:
            created.append(notification)
    return created


def notify_match_approved(db: Session, match: Match) -> list[Notification]:
    """Tell both owners that an administrator approved their match."""
    lost = match.lost_report
    found = match.found_report
    created: list[Notification] = []

    for report, other in ((lost, found), (found, lost)):
        role = "lost" if report.id == lost.id else "found"
        notification = create_notification(
            db,
            report.owner,
            kind="match_approved",
            title=f"Match approved for your {role} item",
            body=(
                f'An administrator approved the match between "{lost.title}" and '
                f'"{found.title}". Please coordinate the handover through the campus '
                "lost & found desk."
            ),
            link=f"/reports/{report.id}",
            dedupe_key=f"match-approved:{match.id}:{report.user_id}",
        )
        if notification is not None:
            created.append(notification)
    return created


def notify_report_status(
    db: Session, report: Report, old_status: str, actor: User
) -> list[Notification]:
    """Notify an owner when an administrator changes their report status."""
    if actor.role != "admin" or report.user_id == actor.id or old_status == report.status:
        return []

    label = report.status.capitalize()
    notification = create_notification(
        db,
        report.owner,
        kind="report_status",
        title=f'Your report is now {label}',
        body=(
            f'An administrator changed the status of "{report.title}" '
            f"from {old_status.capitalize()} to {label}."
        ),
        link=f"/reports/{report.id}",
        dedupe_key=f"report-status:{report.id}:{report.status}",
    )
    return [notification] if notification is not None else []


def notify_new_complaint(db: Session, complaint: Complaint) -> list[Notification]:
    """Alert every administrator when a student submits a complaint."""
    admins = db.scalars(select(User).where(User.role == "admin")).all()
    description = complaint.description
    excerpt = description if len(description) <= 160 else f"{description[:157]}..."
    created: list[Notification] = []

    for admin in admins:
        if admin.id == complaint.user_id:
            continue
        notification = create_notification(
            db,
            admin,
            kind="complaint_new",
            title=f"New {complaint.priority.lower()}-priority complaint {complaint.reference}",
            body=(
                f"{complaint.owner.name} submitted a {complaint.category} complaint for "
                f"{complaint.department} ({complaint.priority} priority): \"{excerpt}\""
            ),
            link=f"/complaints/{complaint.id}",
            dedupe_key=f"complaint-new:{complaint.id}:{admin.id}",
        )
        if notification is not None:
            created.append(notification)
    return created


def notify_complaint_update(
    db: Session,
    complaint: Complaint,
    changes: dict[str, tuple[str, str]],
    actor: User,
) -> list[Notification]:
    """Tell a complaint owner when an administrator changes its handling.

    `changes` maps field name -> (old value, new value). Only fields an
    administrator can edit are included; no contact details are ever exposed.
    """
    if actor.role != "admin" or complaint.user_id == actor.id or not changes:
        return []

    labels = {
        "category": "Category",
        "department": "Department",
        "priority": "Priority",
        "status": "Status",
        "admin_note": "Administrator note",
    }
    parts = []
    for field, (old, new) in changes.items():
        label = labels.get(field, field.replace("_", " ").capitalize())
        if field == "admin_note":
            parts.append("Administrator note updated")
        else:
            parts.append(f"{label}: {old or '—'} → {new or '—'}")

    digest = hashlib.sha1(
        repr(sorted((field, old, new) for field, (old, new) in changes.items())).encode()
    ).hexdigest()[:16]
    notification = create_notification(
        db,
        complaint.owner,
        kind="complaint_update",
        title=f"Update on complaint {complaint.reference}",
        body=(
            f"An administrator updated your {complaint.category} complaint. "
            + "; ".join(parts)
            + "."
        ),
        link=f"/complaints/{complaint.id}",
        dedupe_key=f"complaint-update:{complaint.id}:{digest}",
    )
    return [notification] if notification is not None else []


def _send_email(to_email: str, subject: str, body: str, link: str) -> str:
    """Send one email, returning sent / skipped / failed. Never raises."""
    if not config.SMTP_HOST:
        logger.info(
            "SMTP is not configured; email to %s was not sent (%s).", to_email, subject
        )
        return "skipped"

    url = f"{config.APP_BASE_URL}/#{link}" if link else config.APP_BASE_URL
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.SMTP_FROM
    message["To"] = to_email
    message.set_content(
        f"{body}\n\n"
        f"Open CampusConnect AI: {url}\n\n"
        "This is an automated message from CampusConnect AI. Please do not reply."
    )

    try:
        if config.SMTP_SSL:
            with smtplib.SMTP_SSL(
                config.SMTP_HOST, config.SMTP_PORT, timeout=15
            ) as server:
                if config.SMTP_USER:
                    server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(
                config.SMTP_HOST, config.SMTP_PORT, timeout=15
            ) as server:
                server.ehlo()
                if config.SMTP_TLS:
                    server.starttls()
                    server.ehlo()
                if config.SMTP_USER:
                    server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.send_message(message)
    except Exception:
        logger.exception("Failed to send notification email to %s", to_email)
        return "failed"

    logger.info("Sent notification email to %s (%s).", to_email, subject)
    return "sent"


def send_notification_email(notification_id: int) -> None:
    """Background-task entry point: send and record the email status."""
    with SessionLocal() as db:
        notification = db.get(Notification, notification_id)
        if notification is None:
            return
        user = db.get(User, notification.user_id)
        if user is None:
            notification.email_status = "failed"
            db.commit()
            return

        notification.email_status = _send_email(
            user.email, notification.title, notification.body, notification.link
        )
        db.commit()
