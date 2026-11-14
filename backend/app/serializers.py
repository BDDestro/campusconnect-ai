"""Turn ORM rows into API-safe dictionaries.

Privacy rule: names and owner details are only exposed to the owner and admins.
Public item listings show the item, never the reporter's identity.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import Complaint, Match, Report, User


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _can_see_owner(viewer: User, owner_id: int) -> bool:
    return viewer.role == "admin" or viewer.id == owner_id


def report_summary(report: Report, viewer: User) -> dict:
    return {
        "id": report.id,
        "type": report.type,
        "title": report.title,
        "category": report.category,
        "description": report.description,
        "location": report.location,
        "date": report.event_date.isoformat(),
        "status": report.status,
        "image_url": report.image_url,
        "created_at": iso(report.created_at),
        "owner_name": report.owner.name if _can_see_owner(viewer, report.user_id) else None,
        "is_mine": report.user_id == viewer.id,
    }


def _all_matches(report: Report) -> list[Match]:
    return list(report.matches_as_lost) + list(report.matches_as_found)


def report_card(report: Report, viewer: User) -> dict:
    data = report_summary(report, viewer)
    visible = _can_see_owner(viewer, report.user_id)
    active = [m for m in _all_matches(report) if m.status != "rejected"] if visible else []
    data["match_count"] = len(active)
    data["top_score"] = round(max((m.score for m in active), default=0.0) * 100)
    return data


def match_out(match: Match, viewer: User) -> dict:
    return {
        "id": match.id,
        "score": round(match.score * 100),
        "reasons": [part for part in match.reasons.split("; ") if part],
        "status": match.status,
        "created_at": iso(match.created_at),
        "lost": report_summary(match.lost_report, viewer),
        "found": report_summary(match.found_report, viewer),
    }


def report_detail(report: Report, viewer: User) -> dict:
    data = report_card(report, viewer)
    visible = _can_see_owner(viewer, report.user_id)
    matches = _all_matches(report) if visible else []
    if viewer.role != "admin":
        matches = [m for m in matches if m.status != "rejected"]
    data["matches"] = [
        match_out(m, viewer) for m in sorted(matches, key=lambda m: m.score, reverse=True)
    ]
    return data


def complaint_out(complaint: Complaint, viewer: User) -> dict:
    return {
        "id": complaint.id,
        "reference": complaint.reference,
        "description": complaint.description,
        "category": complaint.category,
        "department": complaint.department,
        "priority": complaint.priority,
        "status": complaint.status,
        "admin_note": complaint.admin_note,
        "image_url": complaint.image_url,
        "ai_source": complaint.ai_source,
        "created_at": iso(complaint.created_at),
        "updated_at": iso(complaint.updated_at),
        "owner_name": complaint.owner.name if _can_see_owner(viewer, complaint.user_id) else None,
        "is_mine": complaint.user_id == viewer.id,
    }
