"""End-to-end API tests for CampusConnect AI."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def create_report(client, headers, **overrides):
    payload = {
        "type": "lost",
        "title": "Black iPhone 13 with blue case",
        "category": "Electronics",
        "description": "Black iPhone 13 with a dark blue silicone case and a dog photo on the lock screen.",
        "location": "Main Library",
        "date": date.today().isoformat(),
    }
    payload.update(overrides)
    return client.post("/api/reports", data=payload, headers=headers)


# --------------------------------------------------------------------------- #
# meta / auth
# --------------------------------------------------------------------------- #

def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_admin_bootstrap_login(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.edu", "password": "AdminPass123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "admin"
    assert body["access_token"]


def test_register_returns_student_and_token(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "New Student",
            "email": f"new-{uuid4().hex[:8]}@test.edu",
            "password": "Password123!",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "student"
    assert body["access_token"]


def test_public_registration_cannot_choose_admin(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Sneaky Student",
            "email": f"sneaky-{uuid4().hex[:8]}@test.edu",
            "password": "Password123!",
            "role": "admin",
        },
    )
    assert response.status_code == 422


def test_duplicate_email_rejected(client, student):
    response = client.post(
        "/api/auth/register",
        json={"name": "Copycat", "email": student["email"], "password": "Password123!"},
    )
    assert response.status_code == 409


def test_wrong_password_rejected(client, student):
    response = client.post(
        "/api/auth/login",
        json={"email": student["email"], "password": "WrongPassword1!"},
    )
    assert response.status_code == 401


def test_private_endpoints_require_login(client):
    assert client.get("/api/reports").status_code == 401
    assert client.get("/api/complaints").status_code == 401
    assert client.get("/api/admin/stats").status_code == 401


# --------------------------------------------------------------------------- #
# lost & found
# --------------------------------------------------------------------------- #

def test_create_report_and_ai_match(client, student, other_student):
    lost = create_report(client, student["headers"])
    assert lost.status_code == 201, lost.text
    lost_body = lost.json()
    assert lost_body["type"] == "lost"
    assert lost_body["status"] == "open"
    assert lost_body["is_mine"] is True
    assert lost_body["matches"] == []

    found = create_report(
        client,
        other_student["headers"],
        type="found",
        title="iPhone found on a library bench",
        description="Found a black iPhone with a blue case on a bench outside the main library. Dog photo on screen.",
        location="Main Library",
    )
    assert found.status_code == 201, found.text
    assert found.json()["matches"], "the found report should match the lost one"

    detail = client.get(f"/api/reports/{lost_body['id']}", headers=student["headers"])
    assert detail.status_code == 200
    body = detail.json()
    assert body["match_count"] >= 1
    assert body["matches"][0]["score"] > 0
    assert body["matches"][0]["status"] == "pending"
    assert body["matches"][0]["reasons"]
    assert body["matches"][0]["lost"]["id"] == lost_body["id"]
    assert body["matches"][0]["found"]["id"] == found.json()["id"]


def test_report_privacy_hides_owner_and_matches(client, student, other_student):
    lost = create_report(client, student["headers"], title="Grey umbrella", category="Other",
                         description="Grey folding umbrella with a wooden handle left in the cafeteria.")
    create_report(client, other_student["headers"], type="found", title="Umbrella found",
                  category="Other", location="Cafeteria",
                  description="Found a grey folding umbrella with a wooden handle at the cafeteria.")

    response = client.get(f"/api/reports/{lost.json()['id']}", headers=other_student["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["owner_name"] is None
    assert body["matches"] == []
    assert body["match_count"] == 0


def test_report_validation(client, student):
    future = (date.today() + timedelta(days=3)).isoformat()
    assert create_report(client, student["headers"], date=future).status_code == 422
    assert create_report(client, student["headers"], category="Spaceships").status_code == 422
    assert create_report(client, student["headers"], description="short").status_code == 422
    assert create_report(client, student["headers"], type="borrowed").status_code == 422


def test_image_upload_accepts_png_and_rejects_executables(client, student):
    ok = client.post(
        "/api/reports",
        data={
            "type": "found",
            "title": "Blue notebook with stickers",
            "category": "Books",
            "description": "Found a blue spiral notebook covered in stickers in the library.",
            "location": "Main Library",
            "date": date.today().isoformat(),
        },
        files={"image": ("photo.png", PNG, "image/png")},
        headers=student["headers"],
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["image_url"].startswith("/uploads/")

    bad = client.post(
        "/api/reports",
        data={
            "type": "found",
            "title": "Suspicious file",
            "category": "Other",
            "description": "This upload should be rejected by the server.",
            "location": "Main Library",
            "date": date.today().isoformat(),
        },
        files={"image": ("virus.exe", b"MZ" + b"0" * 64, "application/octet-stream")},
        headers=student["headers"],
    )
    assert bad.status_code == 400


def test_owner_can_mark_returned_but_not_others_reports(client, student, other_student):
    report = create_report(client, student["headers"], title="Green water bottle",
                           category="Personal Items",
                           description="Green metal water bottle with a black lid and a small dent.")
    report_id = report.json()["id"]

    forbidden = client.patch(
        f"/api/reports/{report_id}",
        json={"status": "returned"},
        headers=other_student["headers"],
    )
    assert forbidden.status_code == 403

    ok = client.patch(
        f"/api/reports/{report_id}",
        json={"status": "returned"},
        headers=student["headers"],
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "returned"

    assert client.delete(f"/api/reports/{report_id}", headers=student["headers"]).status_code == 403
    assert client.delete(f"/api/reports/{report_id}", headers=other_student["headers"]).status_code == 403


# --------------------------------------------------------------------------- #
# complaints
# --------------------------------------------------------------------------- #

def test_complaint_classification_and_reference(client, student):
    response = client.post(
        "/api/complaints",
        data={"description": "Someone is harassing students near the east parking lot after dark and there are no lights."},
        headers=student["headers"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["category"] == "Safety & Security"
    assert body["priority"] == "Critical"
    assert body["department"] == "Campus Security"
    assert body["status"] == "Received"
    assert body["reference"].startswith("CC-")
    assert body["ai_source"] in {"rules", "gemini"}


def test_classify_preview_endpoint(client, student):
    response = client.post(
        "/api/ai/classify",
        json={"description": "The hostel Wi-Fi keeps disconnecting during online classes."},
        headers=student["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "IT & Network"
    assert body["department"] == "IT Services"
    assert 0 <= body["confidence"] <= 1


def test_safety_wording_beats_incidental_facilities_keywords(client, student):
    response = client.post(
        "/api/ai/classify",
        json={
            "description": "Someone was harassing students near the east parking lot after dark "
            "and the lights are broken."
        },
        headers=student["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "Safety & Security"
    assert body["department"] == "Campus Security"
    assert body["priority"] == "Critical"


def test_complaints_are_private_to_owner_and_admin(client, student, other_student, admin_headers):
    created = client.post(
        "/api/complaints",
        data={"description": "The library air conditioning is broken and the room is very hot."},
        headers=student["headers"],
    )
    assert created.status_code == 201, created.text
    complaint_id = created.json()["id"]

    assert client.get(f"/api/complaints/{complaint_id}", headers=other_student["headers"]).status_code == 403
    assert client.get(f"/api/complaints/{complaint_id}", headers=admin_headers).status_code == 200

    mine = client.get("/api/complaints", headers=student["headers"]).json()
    assert any(item["id"] == complaint_id for item in mine)
    assert all(item["is_mine"] for item in mine)

    everyone = client.get("/api/complaints", headers=admin_headers).json()
    assert any(item["id"] == complaint_id for item in everyone)


def test_admin_updates_complaint(client, student, admin_headers):
    created = client.post(
        "/api/complaints",
        data={"description": "The projector in lecture hall E2 does not turn on and lectures are delayed."},
        headers=student["headers"],
    )
    complaint_id = created.json()["id"]

    assert client.patch(
        f"/api/complaints/{complaint_id}",
        json={"status": "Resolved"},
        headers=student["headers"],
    ).status_code == 403

    updated = client.patch(
        f"/api/complaints/{complaint_id}",
        json={
            "status": "In Progress",
            "department": "IT Services",
            "priority": "High",
            "admin_note": "Technician assigned.",
        },
        headers=admin_headers,
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["status"] == "In Progress"
    assert body["priority"] == "High"
    assert body["admin_note"] == "Technician assigned."


# --------------------------------------------------------------------------- #
# admin
# --------------------------------------------------------------------------- #

def test_admin_stats_shape(client, admin_headers):
    response = client.get("/api/admin/stats", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    for key in ("users", "reports", "complaints", "matches", "top_categories"):
        assert key in body
    assert body["reports"]["total"] >= 1


def test_student_cannot_access_admin(client, student):
    assert client.get("/api/admin/stats", headers=student["headers"]).status_code == 403
    assert client.get("/api/admin/matches", headers=student["headers"]).status_code == 403


def test_admin_approves_match_and_reports_become_matched(client, student, other_student, admin_headers):
    lost = create_report(client, student["headers"], title="Red umbrella with black handle",
                         category="Other",
                         description="Lost a red umbrella with a black curved handle near the cafeteria.")
    create_report(client, other_student["headers"], type="found", title="Umbrella left at cafeteria",
                  category="Other", location="Cafeteria",
                  description="Found a red umbrella with a black curved handle at the cafeteria.")

    matches = client.get("/api/admin/matches?status=pending", headers=admin_headers).json()
    target = next(m for m in matches if m["lost"]["id"] == lost.json()["id"])
    assert target["score"] > 0

    approved = client.patch(
        f"/api/admin/matches/{target['id']}",
        json={"status": "approved"},
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    lost_after = client.get(f"/api/reports/{lost.json()['id']}", headers=student["headers"]).json()
    found_id = target["found"]["id"]
    found_after = client.get(f"/api/reports/{found_id}", headers=other_student["headers"]).json()
    assert lost_after["status"] == "matched"
    assert found_after["status"] == "matched"


def test_admin_can_moderate_delete(client, student, admin_headers):
    created = create_report(client, student["headers"], title="Spam report",
                            category="Other", description="This is an inappropriate test report that should be removed.")
    report_id = created.json()["id"]
    deleted = client.delete(f"/api/reports/{report_id}", headers=admin_headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/reports/{report_id}", headers=admin_headers).status_code == 404
