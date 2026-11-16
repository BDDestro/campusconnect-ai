# CampusConnect AI

[![Publish Docker image](https://github.com/BDDestro/campusconnect-ai/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/BDDestro/campusconnect-ai/actions/workflows/docker-publish.yml)
[![GHCR](https://img.shields.io/badge/GHCR-ghcr.io%2Fbddestro%2Fcampusconnect--ai-2496ED?logo=docker&logoColor=white)](https://github.com/BDDestro/campusconnect-ai/pkgs/container/campusconnect-ai)

**University lost & found + complaint management, with AI-assisted matching and triage.**

CampusConnect AI is a working academic MVP built from the *CampusConnect AI Project Roadmap*. Students report lost or found belongings and submit campus complaints. A FastAPI backend runs the AI features, enforces role-based privacy, and serves a mobile-first installable web client. Administrators review AI matches, triage complaints, and moderate reports.

> **AI is a helper, not a judge.** A similarity score is not proof of ownership, and an AI complaint priority is a recommendation. A student or administrator verifies every match and can override every complaint field.

---

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@campus.edu` | `Admin123!` |
| Student | `maya@campus.edu` | `Student123!` |
| Student | `leo@campus.edu` | `Student123!` |

Administrator accounts are created only from backend environment variables on first start. Public sign-up **always** creates a student account and cannot submit a `role` field.

---

## Quick start (Docker)

Requires Docker Desktop (Windows/macOS) or Docker Engine with Compose v2.

```powershell
Copy-Item .env.docker.example .env   # first run only
docker compose up -d --build
```

Then open:

- App: **http://127.0.0.1:8081**
- API docs (Swagger): **http://127.0.0.1:8081/docs**
- Health check: **http://127.0.0.1:8081/api/health**

The container listens on 8080 internally. Compose publishes **8081** because Docker Desktop on Windows also binds host port 8080. Change `PORT` in the project-root `.env` if 8081 is taken. The SQLite database and uploaded images persist in the `campusconnect-data` volume.

| Command | Purpose |
|---|---|
| `docker compose logs -f` | Follow application logs |
| `docker compose ps` | Show container and health status |
| `docker compose down` | Stop the container, keep data |
| `docker compose down -v` | Stop and delete the database + uploads |
| `docker compose up -d --build` | Rebuild after code changes |

Before exposing the app beyond your machine, set a strong `SECRET_KEY` and `ADMIN_PASSWORD` in `.env`. For public hosting, put the container behind an HTTPS reverse proxy (Caddy or nginx). The root `.env` is gitignored and is never baked into the image.

### Published image (GHCR)

Every push to `main` builds a multi-arch image for `linux/amd64` and `linux/arm64` and publishes it to GitHub Container Registry:

```powershell
docker run -d --name campusconnect-ai -p 8081:8080 `
  -e SECRET_KEY="replace-with-a-long-random-string" `
  -v campusconnect-data:/app/backend/data `
  ghcr.io/bddestro/campusconnect-ai:latest
```

- Package: [ghcr.io/bddestro/campusconnect-ai](https://github.com/BDDestro/campusconnect-ai/pkgs/container/campusconnect-ai)
- Workflow: [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) — builds and pushes on every push to `main`, on `v*` tags, and on manual dispatch.
- Tags: `latest` for `main`, the branch or tag name, and `sha-<commit>`.
- This is the same non-root container used by Compose. Mount a volume at `/app/backend/data` to keep SQLite and uploads across restarts.

### Local development (without Docker)

```powershell
cd campusconnect
.\setup.ps1
.\run.ps1
```

Then open **http://127.0.0.1:8080**. The first start creates the SQLite database, bootstraps the administrator, and seeds demo students, reports, complaints, and AI matches.

To start the backend manually instead:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env

cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

### Reseed the demo

The seed only runs when the database has no reports or complaints.

**Docker:**

```powershell
docker compose down -v
docker compose up -d
```

**Local:**

```powershell
Remove-Item backend\data\campusconnect.db
.\run.ps1
```

This deletes demo data, not source code. Local uploads live in `backend/data/uploads/`; Docker uploads live in the `campusconnect-data` volume.

### Ports

Windows on the development machine reserves port 8000 (`WinError 10013`), so the local launcher uses **8080**. Docker Compose publishes the app on **8081** because Docker Desktop also binds host port 8080; the container still listens on 8080 internally. If a port is busy, change it in `run.ps1` or in the project-root `.env` (`PORT=...`).

---

## Screenshots

Captured with headless Chrome at **390 × 844** (mobile) and **1440 × 900** (desktop).

<table>
<tr>
<td align="center"><img src="docs/screenshots/mobile-login.png" width="240" alt="Mobile login"><br><sub>Student login</sub></td>
<td align="center"><img src="docs/screenshots/mobile-dashboard.png" width="240" alt="Student dashboard"><br><sub>Student dashboard</sub></td>
<td align="center"><img src="docs/screenshots/mobile-browse.png" width="240" alt="Browse lost and found"><br><sub>Browse &amp; filter</sub></td>
</tr>
<tr>
<td align="center"><img src="docs/screenshots/mobile-report-matches.png" width="240" alt="AI match card"><br><sub>AI-suggested match</sub></td>
<td align="center"><img src="docs/screenshots/mobile-complaint-ai.png" width="240" alt="Complaint AI triage"><br><sub>Live complaint triage</sub></td>
<td align="center"><img src="docs/screenshots/desktop-admin-matches.png" width="240" alt="Admin match review"><br><sub>Admin match review</sub></td>
</tr>
</table>

More: [admin dashboard](docs/screenshots/desktop-admin-dashboard.png) · [admin complaint queue](docs/screenshots/desktop-admin-complaints.png).

**Documentation:** [Project report](docs/PROJECT_REPORT.md) · [Presentation outline and demo script](docs/PRESENTATION_OUTLINE.md)

---

## What is implemented

### Student

- Register and sign in with email + password.
- Create **lost** or **found** reports with title, category, description, location, date, and optional photo.
- Browse all public item listings with search, type, category, and status filters.
- View a report detail page with an AI-ranked list of possible matches, similarity score, and human-readable reasons.
- View only their own reports and complaints; other students' private records and matches are hidden.
- Mark their own item as **returned**.
- Submit a complaint and see a **live AI preview** of category, department, and priority before submitting.
- Receive a complaint reference such as `CC-2026-0007` and track status: Received → In Progress → Resolved.
- Get in-app notifications when a found item matches a lost report, when an admin approves a match, and when an admin updates a complaint; optional email delivery uses the same events.
- Install the web app to a phone home screen (PWA).

### Administrator

- Owner-created admin account only; no admin option at public sign-up.
- Dashboard with user, report, complaint, and match counts plus top report categories.
- Review the AI match queue; approve or reject each suggestion.
- Approving a match marks both reports as **matched**.
- Complaint queue with editable category, department, priority, status, and an admin note visible to the student.
- Get an in-app and optional email alert for every new student complaint.
- Student owners are notified when an admin changes a complaint's status, department, priority, category, or note.
- View all reports and all complaints.
- Remove inappropriate or duplicate reports and complaints (moderation).
- Student accounts cannot access admin endpoints or admin routes.

### AI features

- **Lost/found matching:** TF-IDF text vectors + cosine similarity, with category and location boosts. Returns a ranked list with a score and reasons. Threshold: `0.15`; top 5 candidates per report.
- **Complaint triage:** transparent keyword rules assign a category, department, and priority. Safety-critical keywords are weighted more heavily than incidental facilities words.
- **Optional Gemini:** if `GEMINI_API_KEY` is set, complaint triage tries Gemini first and silently falls back to the local rules on any failure. The key never reaches the browser.
- **Human verification:** match approval/rejection and every complaint field remain under human control.

### PWA

- Web app manifest, service worker, SVG + PNG icons, and a favicon.
- Network-first caching for the app shell; API and uploads are never cached.
- Installable from Chrome/Edge on desktop and Android.

### Notifications and email

- A bell in the sidebar/top bar shows the unread count; `#/notifications` lists every update.
- **Match events:** the lost-item owner is alerted when new AI matches are stored, and both owners are alerted when an admin approves a match.
- **Complaint events:** every admin is alerted when a student submits a complaint, and the student is alerted when an admin changes the status, department, priority, category, or note.
- Notifications are private: the API only lists and marks the signed-in user's own rows.
- Email is optional. If `SMTP_HOST` is set, each notification is also emailed in a background task; otherwise its `email_status` is `skipped` and the UI shows "Email not configured". Failed sends are recorded as `failed` and never break the request.
- Gmail example: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_TLS=true`, `SMTP_USER=you@gmail.com`, and an App Password in `SMTP_PASSWORD`.

### Deployment

- One Docker image contains the FastAPI backend and the PWA.
- Runs as an unprivileged user with a `/api/health` healthcheck.
- Docker Compose publishes the app and keeps SQLite + uploads in the `campusconnect-data` volume.
- Data survives restarts; `docker compose down -v` resets the demo.

---

## Architecture

```text
┌─────────────────────────────────────────────┐
│  Web client / installable PWA               │
│  frontend/ · vanilla ES modules · hash SPA  │
│  Mobile-first, responsive, offline shell    │
└──────────────────────┬──────────────────────┘
                       │ HTTPS JSON + multipart
┌──────────────────────▼──────────────────────┐
│  FastAPI backend · backend/app              │
│  ┌────────────┬─────────────┬─────────────┐ │
│  │ auth       │ reports     │ complaints  │ │
│  │ scrypt+JWT │ uploads     │ triage      │ │
│  ├────────────┼─────────────┼─────────────┤ │
│  │ admin      │ AI services │ notifications│ │
│  │ stats      │ TF-IDF/rules│ in-app/email│ │
│  └────────────┴─────────────┴─────────────┘ │
│  SQLAlchemy ORM · Pydantic validation       │
└──────────────────────┬──────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │ SQLite (development)        │
        │ PostgreSQL / Supabase (prod)│
        │ local uploads → object store│
        └─────────────────────────────┘
```

The web client is a single-page app with hash routing. It calls the same versioned JSON API a Flutter client would use. There is no server-side HTML templating and no client-side secret. The backend and web client are packaged in one non-root Docker image; Compose publishes it and mounts the persistent data volume.

### Project structure

```text
campusconnect/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entry point, static mounts, lifespan
│   │   ├── config.py            .env settings and paths
│   │   ├── database.py          engine, session, table creation
│   │   ├── models.py            profiles, reports, matches, complaints, notifications
│   │   ├── schemas.py           Pydantic request/response models
│   │   ├── security.py          scrypt password hashing + JWT
│   │   ├── deps.py              current-user and admin dependencies
│   │   ├── serializers.py       privacy-aware API serializers
│   │   ├── seed.py              admin bootstrap + demo dataset
│   │   ├── constants.py         categories, departments, statuses
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── reports.py
│   │   │   ├── complaints.py
│   │   │   ├── notifications.py
│   │   │   ├── admin.py
│   │   │   └── ai.py
│   │   └── services/
│   │       ├── matching.py      TF-IDF + cosine ranking
│   │       ├── classify.py      rules + optional Gemini
│   │       ├── notifications.py in-app alerts + optional SMTP email
│   │       └── storage.py       validated image uploads
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_api.py          27 API tests
│   ├── requirements.txt
│   ├── .env.example
│   └── data/                    gitignored SQLite DB + uploads
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   ├── js/api.js
│   ├── js/app.js
│   ├── manifest.webmanifest
│   ├── sw.js
│   ├── favicon.ico
│   └── icons/
├── docs/
│   ├── PROJECT_REPORT.md        short academic report
│   ├── PRESENTATION_OUTLINE.md  slide outline + demo script
│   └── screenshots/
├── Dockerfile                   non-root image with healthcheck
├── compose.yaml                 app service + persistent data volume
├── .dockerignore
├── .env.docker.example          Docker/Compose settings template
├── .github/
│   └── workflows/
│       └── docker-publish.yml   multi-arch build + push to GHCR
├── setup.ps1
├── run.ps1
├── .gitignore
└── README.md
```

---

## API overview

All private endpoints require `Authorization: Bearer <token>`. Request validation errors return `422`; permission failures return `403`; missing records return `404`.

| Method | Path | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/health` | Public | Service status |
| `POST` | `/api/auth/register` | Public | Create a **student** account |
| `POST` | `/api/auth/login` | Public | Email/password login, returns JWT |
| `GET` | `/api/auth/me` | Signed in | Current profile |
| `GET` | `/api/ai/categories` | Signed in | Item categories, complaint categories, departments, priorities |
| `POST` | `/api/ai/classify` | Signed in | Live complaint triage preview |
| `GET` | `/api/reports` | Signed in | Browse/search reports (`type`, `category`, `status`, `q`, `mine`, `limit`) |
| `POST` | `/api/reports` | Signed in | Create report (multipart form + optional `image`) |
| `GET` | `/api/reports/{id}` | Signed in | Report detail; matches only for owner/admin |
| `PATCH` | `/api/reports/{id}` | Owner/admin | Update status (`returned`/`closed` for students) |
| `GET` | `/api/reports/{id}/matches` | Owner/admin | Ranked matches |
| `DELETE` | `/api/reports/{id}` | Admin | Moderate/remove report |
| `GET` | `/api/complaints` | Signed in | Own complaints; all for admin |
| `POST` | `/api/complaints` | Signed in | Submit complaint (multipart + optional `image`) |
| `GET` | `/api/complaints/{id}` | Owner/admin | Complaint detail |
| `PATCH` | `/api/complaints/{id}` | Admin | Edit category, department, priority, status, note |
| `DELETE` | `/api/complaints/{id}` | Admin | Moderate/remove complaint |
| `GET` | `/api/notifications` | Signed in | Own notifications + unread count |
| `PATCH` | `/api/notifications/{id}/read` | Signed in | Mark one own notification as read |
| `POST` | `/api/notifications/read-all` | Signed in | Mark all own notifications as read |
| `GET` | `/api/admin/stats` | Admin | Dashboard statistics |
| `GET` | `/api/admin/matches` | Admin | Match queue (`status=pending/approved/rejected`) |
| `PATCH` | `/api/admin/matches/{id}` | Admin | Approve/reject match |

### Example: login and create a report

```powershell
$base = "http://127.0.0.1:8081"   # Docker; use 8080 for a local Python run

$login = Invoke-RestMethod -Method Post -Uri "$base/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"email":"maya@campus.edu","password":"Student123!"}'

$headers = @{ Authorization = "Bearer $($login.access_token)" }

Invoke-RestMethod -Method Post -Uri "$base/api/reports" `
  -Headers $headers `
  -Form @{
    type = "lost"
    title = "Black iPhone 13 with blue case"
    category = "Electronics"
    description = "Black iPhone with a dark blue case and a dog photo on the lock screen."
    location = "Main Library"
    date = (Get-Date -Format "yyyy-MM-dd")
  }
```

---

## Database schema

| Table | Key fields | Notes |
|---|---|---|
| `profiles` | `id`, `name`, `email`, `password_hash`, `role`, `created_at` | `role` is `student` or `admin`; email unique |
| `reports` | `id`, `user_id`, `type`, `title`, `category`, `description`, `location`, `date`, `image_url`, `status`, `created_at` | `type` is `lost`/`found`; status `open`/`matched`/`returned`/`closed` |
| `matches` | `id`, `lost_report_id`, `found_report_id`, `score`, `reasons`, `status`, `created_at` | Unique lost/found pair; status `pending`/`approved`/`rejected` |
| `complaints` | `id`, `user_id`, `reference`, `description`, `category`, `department`, `priority`, `status`, `admin_note`, `image_url`, `ai_source`, `created_at`, `updated_at` | Reference format `CC-YYYY-NNNN`; status `Received`/`In Progress`/`Resolved` |
| `notifications` | `id`, `user_id`, `kind`, `title`, `body`, `link`, `dedupe_key`, `is_read`, `email_status`, `created_at` | Private to one user; `kind` is `match_found`, `match_approved`, `report_status`, `complaint_new`, or `complaint_update`; `email_status` is `pending`/`sent`/`skipped`/`failed` |

Foreign keys cascade on user/report deletion. `matches` has a unique constraint on `(lost_report_id, found_report_id)` to prevent duplicates.

---

## Security and privacy

- **Passwords:** stdlib `hashlib.scrypt` with a random 16-byte salt and constant-time comparison. No plaintext passwords.
- **Sessions:** signed HS256 JWT with `sub`, `iat`, and `exp`; default lifetime 12 hours.
- **Admin control:** the administrator is bootstrapped from `ADMIN_EMAIL` / `ADMIN_PASSWORD` on startup. `RegisterIn` uses `extra="forbid"`, so a public sign-up that tries to send `role` is rejected with `422`. Registration hard-codes `role="student"`.
- **Role-based access:** admin routes require `role == "admin"`. Students can only read their own complaints and only see matches on their own reports. Admins can see all records needed for management.
- **Public listings:** item cards and public report detail never include the reporter's name, email, or contact details. `owner_name` is `null` unless the viewer is that report's owner or an admin. Matches are hidden from non-owners.
- **Notification privacy:** every notification query and read update is scoped to `user_id == current_user.id`; another student cannot read or mark someone else's alerts.
- **Contact details:** the UI explicitly warns students not to put phone numbers or ID numbers in public descriptions. There is no phone field.
- **Uploads:** MIME allowlist (JPEG/PNG/WebP), magic-byte validation, 5 MB limit, UUID filenames, and path-traversal-safe deletion.
- **Secrets:** `.env` is gitignored. API keys and the JWT secret stay on the backend; the browser only receives a short-lived user token.
- **CORS:** configurable via `CORS_ORIGINS`; same-origin web app needs nothing.
- **Moderation:** admins can remove reports and complaints, with cascading cleanup of related matches.

For a production deployment, add HTTPS, a strong random `SECRET_KEY`, PostgreSQL, object storage, rate limiting, email verification, password reset, audit logging, and backups. The MVP intentionally does not include those.

---

## Testing

### API tests

```powershell
cd backend
..\.venv\Scripts\python.exe -X utf8 -m pytest -q
```

**Result: 27 passed.**

Covered behavior includes:

- health check and admin bootstrap login;
- student registration, duplicate email, wrong password;
- public registration cannot choose the admin role;
- private endpoints reject anonymous requests;
- report creation, validation (future date, bad category, short text, bad type);
- AI matching between a lost and found report, with score/reasons;
- privacy: another student sees no owner name and no matches;
- image upload accepts a valid PNG and rejects an executable;
- owner can mark returned; other students cannot update/delete;
- complaint classification, reference format, live preview endpoint;
- safety wording beats incidental facilities keywords;
- complaints are private to owner and admin;
- admin can update complaint fields; students cannot;
- admin stats shape; students blocked from admin;
- approving a match marks both reports as matched;
- match creation and approval notifications go to the right owner(s);
- new complaints notify admins only; admin updates notify the student owner;
- notifications are private and can be marked read;
- admin moderation delete.

Tests use an isolated temporary SQLite database and do not touch demo data.

### Responsive/UI sweep

A headless Chrome sweep checked **75 combinations** of route × viewport width:

- widths: 360, 390, 768, 1024, 1440 px;
- student routes: dashboard, browse, new report, own report, another student's report, my reports, complaints, new complaint, complaint detail;
- admin routes: dashboard, match queue, complaint queue, all reports, report detail, complaint detail.

Result: **0 horizontal-overflow problems, 0 console errors, 0 failed requests**. The sweep also caught and fixed four CSS issues during development: stretched status pills, stretched match badges, muted admin avatar text, and grid blowout from long nowrap text.

### Docker smoke test

`docker compose up -d --build` starts the image as unprivileged UID `10001`, passes its `/api/health` healthcheck, and serves the seeded demo through the published port: 12 reports, 6 complaints, 5 pending matches, 2 students. The database and uploads persist in the `campusconnect-data` volume across restarts.

The published `ghcr.io/bddestro/campusconnect-ai:latest` image was also pulled and run in a disposable container. It reported healthy, served the PWA and manifest, returned the same seeded counts, and ran as UID `10001`. A second disposable container verified the complaint notification flow end to end: a student submission created an admin alert, an admin update created a student alert, both showed `email_status=skipped` without SMTP, and a third student received neither the complaint nor its notification.

---

## Configuration

Copy `backend/.env.example` to `backend/.env` and adjust:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | empty → SQLite in `backend/data/` | SQLAlchemy URL; set a Postgres URL for Supabase |
| `SECRET_KEY` | dev key in example | JWT signing key; **replace in production** |
| `TOKEN_MINUTES` | `720` | Login token lifetime |
| `ADMIN_NAME` | `Campus Administrator` | Bootstrap admin display name |
| `ADMIN_EMAIL` | `admin@campus.edu` | Bootstrap admin email |
| `ADMIN_PASSWORD` | `Admin123!` | Bootstrap admin password (first start only) |
| `AUTO_SEED` | `true` | Seed demo data when the database is empty |
| `MAX_UPLOAD_MB` | `5` | Image upload limit |
| `GEMINI_API_KEY` | empty | Optional Gemini triage; empty uses local rules |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `SMTP_HOST` | empty | SMTP server; empty keeps notifications in-app only |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | empty | SMTP login user |
| `SMTP_PASSWORD` | empty | SMTP password or app password |
| `SMTP_FROM` | empty → `SMTP_USER` | From address on notification emails |
| `SMTP_TLS` | `true` | STARTTLS for port 587 |
| `SMTP_SSL` | `false` | Implicit TLS, usually port 465 |
| `APP_BASE_URL` | `http://127.0.0.1:8080` | Public URL used in email links |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins for separate clients |
| `DATA_DIR` | `backend/data` | SQLite/uploads location override |

`ensure_admin` never overwrites an existing admin password. If you change `ADMIN_PASSWORD` after the first start, the existing account keeps its old password.

**Docker:** Compose reads the project-root `.env` (created from `.env.docker.example`) with the same variable names plus `PORT` (host port, default `8081`). It does not read `backend/.env`; the container receives these values as environment variables.

---

## Migration paths

### SQLite → Supabase PostgreSQL

1. Create a Supabase project and copy the Postgres connection string.
2. Install a driver: `pip install "psycopg[binary]"`.
3. Set in `backend/.env`:

   ```env
   DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
   ```

4. Restart the backend. `init_db()` creates the four tables on first run.
5. For production, replace `create_all` with Alembic migrations and enable backups.

The SQLAlchemy models map directly to the roadmap's suggested tables. If you later expose Supabase directly to clients, add Row Level Security policies; the current design keeps all access behind FastAPI, so RLS is not required for this architecture.

### Local uploads → Supabase Storage

Replace the two functions in `backend/app/services/storage.py`:

- `save_image()` → upload bytes to a Supabase Storage bucket, return a public or signed URL.
- `delete_image()` → remove the object by path.

The rest of the API stores only `image_url`, so no router changes are needed. Keep the MIME/magic-byte/size checks in the backend.

### TF-IDF → sentence-transformers

The matching interface is deliberately small. In `backend/app/services/matching.py`, replace the TF-IDF vectorization inside `rank()` with embeddings:

```python
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")  # load once at startup

def rank(query, candidates):
    texts = [_document(query)] + [_document(c) for c in candidates]
    vectors = model.encode(texts, normalize_embeddings=True)
    scores = util.cos_sim(vectors[0], vectors[1:])[0]
    # keep the same (candidate, score, reasons) return shape
```

Keep `ensure_matches()` and the API unchanged. Add category/location boosts if desired. For a production system, store embeddings in a vector column (pgvector on Supabase) and index them. The current TF-IDF approach is deterministic, has no model download, and is fast for a campus-sized dataset.

### Gemini complaint triage

Set `GEMINI_API_KEY` in `backend/.env` and restart. The classifier calls Gemini with a constrained JSON prompt, validates the returned category/department/priority against allowlists, and falls back to local rules on any error. The key is used only server-side.

**Privacy note:** complaint text can contain personal details. Before enabling an external LLM, add redaction or a consent notice, and avoid sending private student information to third-party services.

### Flutter web / Android client

The API is framework-agnostic and ready for Flutter:

- Use `dio` or `http` for JSON and `MultipartRequest` for report/complaint images.
- Store the JWT in `flutter_secure_storage` (mobile) or secure storage for web; send `Authorization: Bearer <token>`.
- Map screens directly: login/register, dashboard, browse, report form/detail, my reports, complaint form/detail, admin dashboard/matches/complaints/reports.
- Android emulator base URL: `http://10.0.2.2:8081` for Docker (or `http://10.0.2.2:8080` for a local Python run); physical device: your machine's LAN IP and published port.
- Set `CORS_ORIGINS` for a separately hosted Flutter web build.

An APK is **not included** in this repository because Flutter, Dart, and the Android SDK were not installed on the build machine and the available disk space was insufficient for the toolchain. The delivered client is a mobile-first installable PWA that exercises the same backend. With Flutter installed:

```bash
flutter create campusconnect_app
# add screens/services using the API table above
flutter build apk --release
```

---

## Roadmap mapping

| Roadmap module | Status |
|---|---|
| Student registration/login | Done |
| Lost/found reports with photos | Done |
| Browse/search/filter listings | Done |
| AI-suggested lost/found matches | Done (TF-IDF + cosine; sentence-transformers swap documented) |
| Mark item returned | Done |
| Complaints with AI category/department/priority | Done (rules + optional Gemini) |
| Complaint reference and status tracking | Done |
| Admin dashboard and statistics | Done |
| Admin match approve/reject | Done |
| Admin complaint assignment/status/note | Done |
| Admin moderation | Done |
| Role-based privacy | Done and tested |
| Owner-created admin accounts | Done |
| Website | Done (installable PWA; Docker image published to GHCR) |
| Android APK | Not built — toolchain/disk constraint; Flutter-ready API and migration notes provided |
| Source code, schema, AI demo, test results | Done |
| Short report/presentation | [Project report](docs/PROJECT_REPORT.md) + [presentation outline](docs/PRESENTATION_OUTLINE.md) + screenshots |

### Scope boundaries

Per the roadmap, the MVP intentionally skips real-time chat, browser push notifications, payments, maps, facial recognition, and complex analytics. In-app notifications and optional email are included. AI output is always a suggestion, never an automatic decision.

Known MVP limitations:

- SQLite and local disk uploads are single-node development choices.
- No email verification, password reset, rate limiting, or audit log yet.
- No background job queue; matching runs synchronously when a report is created.
- The PWA is not a native Android APK.
- Demo data is fictional and for presentation only.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `WinError 10013` / port blocked | Use port 8080 (local) or 8081 (Docker), or choose another free port |
| `ModuleNotFoundError` | Run `.\setup.ps1` or install `backend\requirements.txt` into `.venv` |
| Admin login fails | Check `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env` (local) or the project-root `.env` (Docker); the password is only applied when the admin is first created |
| Images return 404 | Confirm the file exists in `backend/data/uploads/` and the `/uploads` mount is active |
| Old CSS/JS after an update | Hard reload; the service worker is network-first, but bump `CACHE` in `frontend/sw.js` if needed |
| Flutter web CORS error | Set `CORS_ORIGINS` to the Flutter dev origin |
| Tests fail on Windows console encoding | Run with `python -X utf8 -m pytest -q` |
| Want a clean local demo | Delete `backend/data/campusconnect.db` and restart |
| Docker: port already allocated | Set `PORT` in the project-root `.env` to a free port, then `docker compose up -d` |
| Docker: reset the demo | `docker compose down -v` then `docker compose up -d` |
| Docker: code changes not visible | `docker compose up -d --build` |

---

## Tech stack

- **Backend:** Python 3.14, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2, PyJWT, stdlib `scrypt`.
- **Database:** SQLite for development; PostgreSQL/Supabase via `DATABASE_URL`.
- **AI:** pure-Python TF-IDF + cosine similarity; keyword triage with optional Gemini.
- **Frontend:** vanilla ES modules, hash SPA, hand-written CSS design system, PWA manifest + service worker.
- **Container:** Dockerfile (non-root user, healthcheck) + Compose v2 with a named data volume.
- **CI/registry:** GitHub Actions builds multi-arch images (`linux/amd64`, `linux/arm64`) and publishes them to GitHub Container Registry (`ghcr.io/bddestro/campusconnect-ai`).
- **Testing:** pytest + FastAPI TestClient; headless Chrome responsive sweep.
- **Images:** Pillow used only to generate PWA icons/favicon (not a runtime dependency).

---

## Credits

Built as an academic prototype from the *CampusConnect AI Project Roadmap* (website + Android plan). Demo names, reports, and complaints are fictional. AI suggestions must be verified by a person before any item is returned or complaint escalated.
