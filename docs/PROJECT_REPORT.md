# CampusConnect AI — Short Project Report

**Project:** Intelligent University Lost & Found and Complaint Management  
**Stack:** FastAPI · SQLite/PostgreSQL · Python AI services · Mobile-first PWA · Docker/Compose · GitHub Actions/GHCR  
**Deliverable:** Working academic MVP with API tests and responsive UI verification

---

## Abstract

CampusConnect AI is a university platform where students report lost or found belongings and submit campus-related complaints. The system uses AI to rank possible lost/found matches and to suggest a complaint category, department, and priority. Students and administrators use separate dashboards with role-based access. In-app notifications and optional SMTP email keep owners and administrators informed when matches, approvals, or complaint updates occur. The MVP was implemented as a FastAPI backend with a mobile-first installable web client, backed by a relational database and packaged as a non-root Docker image with Compose. AI outputs are deliberately treated as suggestions: an administrator approves matches and can override every complaint field.

---

## 1. Introduction

University lost-and-found desks and complaint channels are often disconnected. A student may report a missing phone in one place, while the finder hands it in somewhere else. Complaints may be sent to the wrong department or arrive without a priority. CampusConnect AI addresses both problems in one platform:

- structured lost/found reports with photos and locations;
- semantic-style matching between opposite-type reports;
- complaint triage into category, department, and priority;
- notifications and optional email for matches, approvals, and complaint updates;
- a human-reviewed administration workflow.

The project follows the supplied roadmap's scope boundaries: no real-time chat, browser push notifications, payments, maps, facial recognition, or complex analytics in the first version. In-app notifications and optional email are included.

---

## 2. Objectives

1. Let students register, sign in, and submit lost/found reports with optional photos.
2. Let students browse and filter public listings without exposing private contact details.
3. Rank possible matches and explain each suggestion with a score and reasons.
4. Let students submit complaints and track their status with a reference number.
5. Give administrators a dashboard to review matches, assign complaints, update statuses, and moderate content.
6. Enforce role-based privacy: students see their own private records; admins see management data.
7. Keep administrator accounts owner-created, never selectable at public sign-up.
8. Notify students about new matches, approved matches, and complaint updates, and alert administrators about new complaints, with optional email delivery.
9. Provide a testable, documented MVP that can later move to Supabase, sentence-transformers, Gemini, and Flutter.

---

## 3. System design

### 3.1 Architecture

The client is a single-page web application (HTML, CSS, ES modules) with hash routing. It calls a FastAPI backend over JSON and multipart form data. The backend contains six routers:

- **auth** — registration, login, current user;
- **reports** — lost/found CRUD, uploads, matching, status updates;
- **complaints** — submission, AI triage, owner/admin access, admin updates;
- **notifications** — list own alerts, unread count, mark read;
- **admin** — statistics, match queue, approve/reject;
- **ai** — live classification preview and form options.

SQLAlchemy maps five tables: `profiles`, `reports`, `matches`, `complaints`, and `notifications`. SQLite is used for local development. The same models can target PostgreSQL/Supabase by changing `DATABASE_URL`.

Notification events are created in the same transaction as the record they describe. Email delivery is queued as a FastAPI background task after the commit, so an SMTP failure or an unconfigured mail server never blocks report or complaint submission. The notification row records `email_status` as `pending`, `sent`, `skipped`, or `failed`.

Deployment uses one Docker image containing the FastAPI backend and the PWA. The image runs as an unprivileged user, exposes a `/api/health` healthcheck, and is started with Docker Compose. SQLite and uploaded images live in the named `campusconnect-data` volume, so data survives container restarts. Compose publishes host port 8081 by default to avoid Docker Desktop's own use of host port 8080; the container listens on 8080 internally. A GitHub Actions workflow builds the image for `linux/amd64` and `linux/arm64` and publishes it to GitHub Container Registry as `ghcr.io/bddestro/campusconnect-ai`, so the same artifact can run on a laptop or an amd64/arm64 server.

### 3.2 Student workflow

1. Register or sign in.
2. Create a lost or found report with title, category, description, location, date, and optional image.
3. The backend stores the report, compares it with opposite-type open reports, and stores new matches above the threshold.
4. The student sees ranked matches with a similarity percentage and reasons such as shared keywords, same category, or same location.
5. The student can mark their own item as returned.
6. Complaints are submitted with a live AI preview; the saved complaint receives a reference such as `CC-2026-0007`.
7. The student tracks complaint status: Received → In Progress → Resolved.
8. The notification bell shows unread alerts. The student is notified when a new match is found, when an admin approves a match, and when an admin updates a complaint. If SMTP is configured, the same events are emailed.

### 3.3 Administrator workflow

1. Sign in with the owner-created admin account.
2. Review dashboard statistics: users, reports, complaints, pending matches, top categories.
3. Open the AI match queue and approve or reject each suggestion.
4. Approving a match marks both reports as matched.
5. Open the complaint queue, edit category/department/priority/status, and add a note visible to the student.
6. Receive an in-app and optional email alert for every new student complaint.
7. View all reports and remove inappropriate or duplicate submissions.

---

## 4. AI approach

### 4.1 Lost/found matching

The MVP uses **TF-IDF vectors and cosine similarity** in pure Python:

- text is lowercased, tokenized, stop-word filtered, and lightly stemmed (trailing `s`);
- title terms are repeated three times and category twice to weight them;
- location is included;
- cosine similarity is computed between the query report and opposite-type candidates;
- small boosts are added for same category (`+0.06`) and same/nearby location (`+0.05`/`+0.02`);
- scores are capped at `0.99`; the threshold is `0.15`; the top five candidates are stored;
- each match stores human-readable reasons.

This approach requires no model download and runs offline. The interface is intentionally small so it can be replaced by sentence-transformers embeddings without changing the API. Demo results include an iPhone match at 77%, an ID card at 73%, a water bottle at 62%, a backpack at 51%, and a weaker glasses/iPhone suggestion at 29%. The last example is useful for demonstrating why human review matters.

### 4.2 Complaint triage

The default classifier uses transparent keyword rules:

- each category has an associated department and keyword list;
- the category with the highest weighted keyword score wins;
- safety-critical words (fire, harassment, assault, injury, threat, weapon, gas leak, collapse, etc.) receive weight 3, so they are not overridden by incidental facilities words such as "broken" or "light";
- priority is Critical for safety-critical wording, High for urgent wording, Low for minor wording, otherwise Medium;
- confidence is derived from the number of matched keywords;
- a fallback routes unmatched complaints to Student Affairs for manual review.

If `GEMINI_API_KEY` is configured, the backend asks Gemini for structured JSON and validates the returned category, department, and priority against allowlists. Any error falls back to the local rules. The key never leaves the backend. Because complaint text may contain personal details, external LLM use should be preceded by redaction or a consent notice.

### 4.3 Human verification

The UI and API both state that a similarity score is not proof of ownership and that AI priority is not an emergency response. Match approval is an explicit administrator action. Complaint fields remain editable by administrators. This satisfies the roadmap's requirement that people review important decisions.

### 4.4 Notifications and email

Notifications are stored in the `notifications` table and exposed through three authenticated endpoints. Events are:

- `match_found` — the lost-item owner is told that one or more possible matches were stored; multiple matches for the same report are grouped into one alert;
- `match_approved` — both owners are told that an administrator approved the pair;
- `report_status` — a report owner is told when an administrator changes the report status;
- `complaint_new` — every administrator is told when a student submits a complaint;
- `complaint_update` — the complaint owner is told when an administrator changes the status, department, priority, category, or note.

Each event has a deduplication key, so retries and repeated updates do not create duplicate rows. The notification API scopes all reads and writes to the signed-in user. Emails are optional: when `SMTP_HOST` is empty, the row is marked `skipped` and the UI displays "Email not configured"; when SMTP is configured, a background task sends the message and records `sent` or `failed`. Email links use `APP_BASE_URL` and never include another user's private data.

---

## 5. Security and privacy

- **Passwords:** `hashlib.scrypt` with a random salt and constant-time comparison.
- **Sessions:** signed HS256 JWT with an expiry (default 12 hours).
- **Admin bootstrap:** the admin is created from backend environment variables. Public registration uses a Pydantic model with `extra="forbid"` and hard-codes the student role, so a `role` field is rejected with `422`.
- **Role checks:** FastAPI dependencies enforce signed-in and admin access. Students cannot read another student's complaints or matches.
- **Privacy-aware serialization:** public listings and non-owner report detail omit `owner_name`; matches are returned only to the owner or an admin. The frontend also hides match sections from non-owners.
- **Notification privacy:** every notification read is scoped to the signed-in user; another student cannot list or mark someone else's alerts.
- **Uploads:** MIME allowlist, magic-byte checks, 5 MB limit, UUID filenames, safe deletion.
- **Secrets:** `.env` is gitignored; API keys, JWT secrets, and SMTP credentials stay on the server.
- **Moderation:** admins can delete reports and complaints; cascading foreign keys clean up related matches.

Production hardening would add HTTPS, a strong random secret, PostgreSQL, object storage, rate limiting, email verification, password reset, audit logs, and backups.

---

## 6. Testing and results

### 6.1 API tests

`pytest` runs 27 tests against an isolated temporary SQLite database. All 27 pass.

The suite covers authentication, admin bootstrap, role-escalation rejection, duplicate email, wrong password, private endpoint protection, report validation, image validation, AI matching, privacy, owner status updates, complaint classification and references, live triage preview, safety-weighted classification, complaint privacy, admin updates, statistics shape, student/admin separation, match approval, match notifications, complaint notifications, notification privacy, and moderation deletion.

### 6.2 Responsive UI verification

A headless Chrome sweep checked 75 combinations of route and viewport width (360, 390, 768, 1024, 1440 px) for student and admin routes. It checked:

- horizontal overflow;
- console errors;
- failed HTTP requests;
- presence of the page heading and expected layout mode.

Final result: **0 problems**. The sweep found and prompted fixes for four CSS issues: stretched status pills, stretched match-side badges, muted admin avatar text, and grid blowout from long nowrap text.

### 6.3 Docker smoke test

The Compose stack was built and started from a clean volume. The container reported healthy, ran as UID `10001`, and served the seeded dataset through the published port: 12 reports, 6 complaints, 5 pending matches, and 2 students. The same counts remained after a container restart, confirming that the named volume preserves the database and uploads. The published `ghcr.io/bddestro/campusconnect-ai:latest` image was then pulled and run in a disposable container; it reported healthy, served the PWA and manifest, returned the same seeded counts, and also ran as UID `10001`.

### 6.4 Manual demonstration

The following flows were exercised in a browser:

- student login and dashboard;
- browse with 12 seeded items;
- own report detail with a 77% match and reasons;
- live complaint triage, submission, reference, and status steps;
- admin login and dashboard;
- match approval (both reports became matched) and rejection;
- admin complaint update (status, department, priority, note);
- notification bell, unread badge, mark-read, and complaint update alert as the student;
- admin new-complaint alert in the notification page;
- admin deletion of a disposable report pair and complaint;
- mobile and desktop screenshots.

---

## 7. Limitations

- The client is an installable PWA, not a native Android APK. Flutter/Dart and the Android SDK were unavailable on the build machine, and disk space was insufficient for the toolchain.
- SQLite and local disk uploads are development choices, not a production deployment.
- The Docker setup is a single container with a local volume; orchestration, horizontal scaling, and managed backups are out of scope.
- Matching runs synchronously at report creation; there is no background job queue.
- Email is optional and requires SMTP settings; without them, notifications stay in-app and are marked `skipped`. There is no durable email queue or retry worker yet.
- Notifications are in-app (with 30-second polling), not browser push notifications.
- No email verification, password reset, rate limiting, or audit logging yet.
- The TF-IDF matcher is lexical, not deeply semantic; it performs well on the demo data but should be replaced by embeddings for broader vocabulary.
- External Gemini triage is optional and disabled by default; privacy review is required before enabling it.
- Demo data is fictional.

---

## 8. Future work

1. Build the Flutter web/Android client against the existing API and produce a release APK.
2. Move to Supabase PostgreSQL and Storage; add Alembic migrations and RLS if direct client access is introduced.
3. Replace TF-IDF with sentence-transformers (`all-MiniLM-L6-v2`) and optionally pgvector indexing.
4. Add email verification, password reset, rate limiting, audit logs, and admin action history.
5. Add background matching jobs, a durable email queue with retry, and browser push notifications.
6. Add redaction/consent before sending complaint text to an external LLM.
7. Add managed container hosting with an HTTPS reverse proxy, automated backups, and monitoring; the multi-arch GHCR image pipeline is already in place.
8. Add richer analytics only after the core workflows are stable.

---

## 9. Conclusion

CampusConnect AI demonstrates the complete core loop from the roadmap: students report items and complaints, AI produces ranked matches and triage suggestions, administrators verify matches, assign complaints, update statuses, and moderate content, and notifications keep both sides informed. The implementation prioritizes privacy, explicit human control, testability, and a clean migration path to Supabase, sentence-transformers, Gemini, and Flutter. The delivered PWA is usable on desktop and mobile today, while the API remains ready for the planned Android client.

---

## Appendix — Demo accounts

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@campus.edu` | `Admin123!` |
| Student | `maya@campus.edu` | `Student123!` |
| Student | `leo@campus.edu` | `Student123!` |

Run the published image (no clone or build):

```powershell
docker run -d --name campusconnect-ai -p 8081:8080 `
  -e SECRET_KEY="replace-with-a-long-random-string" `
  -v campusconnect-data:/app/backend/data `
  ghcr.io/bddestro/campusconnect-ai:latest
```

Or build from source with Docker Compose (recommended for development):

```powershell
Copy-Item .env.docker.example .env
docker compose up -d --build
```

Open http://127.0.0.1:8081. API docs: http://127.0.0.1:8081/docs.

Or run locally:

```powershell
cd campusconnect
.\setup.ps1
.\run.ps1
```

Open http://127.0.0.1:8080. API docs: http://127.0.0.1:8080/docs.
