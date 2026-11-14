"""Bootstrap the admin account and, on first run, a demo dataset."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import config
from .models import Complaint, Report, User
from .security import hash_password
from .services.classify import classify_text
from .services.matching import ensure_matches

DEMO_PASSWORD = "Student123!"

DEMO_STUDENTS = [
    ("Maya Patel", "maya@campus.edu"),
    ("Leo Chen", "leo@campus.edu"),
]

# (owner email, type, title, category, description, location, days ago)
DEMO_REPORTS = [
    (
        "maya@campus.edu", "lost", "Black iPhone 13 with blue case", "Electronics",
        "Lost my black iPhone 13 with a dark blue silicone case near the main library entrance. "
        "The lock screen shows a photo of a dog.",
        "Main Library", 2,
    ),
    (
        "leo@campus.edu", "found", "iPhone found on library bench", "Electronics",
        "Found a black iPhone with a blue case on a bench outside the main library. "
        "The lock screen has a dog photo.",
        "Main Library", 1,
    ),
    (
        "maya@campus.edu", "lost", "Blue Hydro Flask water bottle", "Personal Items",
        "Blue Hydro Flask with a dent near the bottom and a mountain sticker.",
        "Cafeteria", 3,
    ),
    (
        "leo@campus.edu", "found", "Water bottle left in the cafeteria", "Personal Items",
        "Found a blue metal water bottle with mountain stickers on a cafeteria table.",
        "Cafeteria", 1,
    ),
    (
        "maya@campus.edu", "lost", "Student ID card in clear holder", "Documents",
        "University student ID card in a clear plastic holder, lost between the science "
        "building and the bus stop.",
        "Science Building", 1,
    ),
    (
        "leo@campus.edu", "found", "ID card on the science building stairs", "Documents",
        "Found a university student ID card in a clear holder on the floor near the science "
        "building stairs.",
        "Science Building", 0,
    ),
    (
        "maya@campus.edu", "lost", "Black North Face backpack", "Bags",
        "Black North Face backpack with a laptop and a green notebook inside, lost in the "
        "engineering building.",
        "Engineering Building", 4,
    ),
    (
        "leo@campus.edu", "found", "Backpack in lecture hall E2", "Bags",
        "Found a black backpack with a laptop inside in lecture hall E2.",
        "Engineering Building", 2,
    ),
    (
        "leo@campus.edu", "found", "Silver Casio scientific calculator", "Electronics",
        "Found a silver Casio scientific calculator in room 204 after the math exam.",
        "Science Building", 0,
    ),
    (
        "maya@campus.edu", "lost", "Prescription glasses in red case", "Personal Items",
        "Black rectangular prescription glasses in a red case, left in a library study room.",
        "Main Library", 5,
    ),
    (
        "leo@campus.edu", "found", "Navy hoodie with white logo", "Clothing",
        "Found a navy blue hoodie with a small white logo on the back, left at the sports center.",
        "Sports Center", 0,
    ),
    (
        "maya@campus.edu", "lost", "Keys with red keychain", "Keys",
        "A set of keys with a red carabiner and a small torch keychain, lost near parking lot B.",
        "Parking Lot B", 2,
    ),
]

# (owner email, description, status, admin note)
DEMO_COMPLAINTS = [
    (
        "maya@campus.edu",
        "The water fountain on the second floor of the science building has been leaking for "
        "three days and the floor is slippery.",
        "Received", "",
    ),
    (
        "leo@campus.edu",
        "The Wi-Fi in the hostel keeps disconnecting every few minutes, especially at night. "
        "I cannot attend my online classes.",
        "In Progress", "Network team is checking the hostel access points.",
    ),
    (
        "maya@campus.edu",
        "Someone was harassing students near the east parking lot after dark. The area has no "
        "working lights.",
        "In Progress", "Campus security has increased patrols in the area.",
    ),
    (
        "leo@campus.edu",
        "The projector in lecture hall E2 does not turn on, so lectures are delayed.",
        "Resolved", "Projector cable replaced and tested.",
    ),
    (
        "maya@campus.edu",
        "Trash bins near the cafeteria are overflowing and smell bad.",
        "Resolved", "Bins emptied and the collection schedule was updated.",
    ),
    (
        "leo@campus.edu",
        "One of the chairs in the library study room is broken and unsafe to sit on.",
        "Resolved", "Chair replaced by facilities.",
    ),
]


def ensure_admin(db: Session) -> User:
    """Create the bootstrap admin from env if missing. Never overwrite a password."""
    user = db.scalar(select(User).where(User.email == config.ADMIN_EMAIL))
    if user is not None:
        if user.role != "admin":
            user.role = "admin"
            db.commit()
        return user

    user = User(
        name=config.ADMIN_NAME,
        email=config.ADMIN_EMAIL,
        password_hash=hash_password(config.ADMIN_PASSWORD),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_if_empty(db: Session) -> bool:
    """Populate demo data only when there are no reports or complaints yet."""
    if db.scalar(select(func.count(Report.id))) or db.scalar(select(func.count(Complaint.id))):
        return False

    existing = {user.email: user for user in db.scalars(select(User)).all()}
    students: dict[str, User] = {}
    for name, email in DEMO_STUDENTS:
        if email in existing:
            students[email] = existing[email]
            continue
        student = User(
            name=name,
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            role="student",
        )
        db.add(student)
        students[email] = student
    db.flush()

    reports: list[Report] = []
    for email, report_type, title, category, description, location, days_ago in DEMO_REPORTS:
        report = Report(
            user_id=students[email].id,
            type=report_type,
            title=title,
            category=category,
            description=description,
            location=location,
            event_date=date.today() - timedelta(days=days_ago),
        )
        db.add(report)
        reports.append(report)
    db.flush()

    for report in reports:
        ensure_matches(db, report)

    for email, description, complaint_status, note in DEMO_COMPLAINTS:
        suggestion = classify_text(description)
        complaint = Complaint(
            user_id=students[email].id,
            description=description,
            category=suggestion["category"],
            department=suggestion["department"],
            priority=suggestion["priority"],
            status=complaint_status,
            admin_note=note,
            ai_source=suggestion["source"],
        )
        db.add(complaint)
        db.flush()
        complaint.reference = f"CC-{date.today().year}-{complaint.id:04d}"

    db.commit()
    return True


if __name__ == "__main__":
    from .database import SessionLocal, init_db

    init_db()
    with SessionLocal() as session:
        ensure_admin(session)
        created = seed_if_empty(session)
    print("Demo data seeded." if created else "Database already has data; nothing to seed.")
