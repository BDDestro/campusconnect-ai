# CampusConnect AI — Short Project Report

**Project:** Intelligent University Lost & Found and Complaint Management  
**Stack:** FastAPI · SQLite/PostgreSQL · Python AI services · Mobile-first PWA  
**Deliverable:** Working academic MVP with API tests and responsive UI verification

---

## Abstract

CampusConnect AI is a university platform where students report lost or found belongings and submit campus-related complaints. The system uses AI to rank possible lost/found matches and to suggest a complaint category, department, and priority. Students and administrators use separate dashboards with role-based access. The MVP was implemented as a FastAPI backend with a mobile-first installable web client, backed by a relational database. AI outputs are deliberately treated as suggestions: an administrator approves matches and can override every complaint field.

---

## 1. Introduction

University lost-and-found desks and complaint channels are often disconnected. A student may report a missing phone in one place, while the finder hands it in somewhere else. Complaints may be sent to the wrong department or arrive without a priority. CampusConnect AI addresses both problems in one platform:

- structured lost/found reports with photos and locations;
- semantic-style matching between opposite-type reports;
- complaint triage into category, department, and priority;
- a human-reviewed administration workflow.

The project follows the supplied roadmap's scope boundaries: no real-time chat, push notifications, payments, maps, facial recognition, or complex analytics in the first version.

---

## 2. Objectives

1. Let students register, sign in, and submit lost/found reports with optional photos.
2. Let students browse and filter public listings without exposing private contact details.
3. Rank possible matches and explain each suggestion with a score and reasons.
4. Let students submit complaints and track their status with a reference number.
5. Give administrators a dashboard to review matches, assign complaints, update statuses, and moderate content.
6. Enforce role-based privacy: students see their own private records; admins see management data.
7. Keep administrator accounts owner-created, never selectable at public sign-up.
8. Provide a testable, documented MVP that can later move to Supabase, sentence-transformers, Gemini, and Flutter.

---

## 3. System design

### 3.1 Architecture

The client is a single-page web application (HTML, CSS, ES modules) with hash routing. It calls a FastAPI backend over JSON and multipart form data. The backend contains five routers:

- **auth** — registration, login, current user;
- **reports** — lost/found CRUD, uploads, matching, status updates;
- **complaints** — submission, AI triage, owner/admin access, admin updates;
- **admin** — statistics, match queue, approve/reject;
- **ai** — live classification preview and form options.

SQLAlchemy maps four tables: `profiles`, `reports`, `matches`, and `complaints`. SQLite is used for local development. The same models can target PostgreSQL/Supabase by changing `DATABASE_URL`.

### 3.2 Student workflow

1. Register or sign in.
2. Create a lost or found report with title, category, description, location, date, and optional image.
3. The backend stores the report, compares it with opposite-type open reports, and stores new matches above the threshold.
4. The student sees ranked matches with a similarity percentage and reasons such as shared keywords, same category, or same location.
5. The student can mark their own item as returned.
6. Complaints are submitted with a live AI preview; the saved complaint receives a reference such as `CC-2026-0007`.
7. The student tracks complaint status: Received → In Progress → Resolved.

### 3.3 Administrator workflow

1. Sign in with the owner-created admin account.
2. Review dashboard statistics: users, reports, complaints, pending matches, top categories.
3. Open the AI match queue and approve or reject each suggestion.
4. Approving a match marks both reports as matched.
5. Open the complaint queue, edit category/department/priority/status, and add a note visible to the student.
6. View all reports and remove inappropriate or duplicate submissions.

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

---

## 5. Security and privacy

- **Passwords:** `hashlib.scrypt` with a random salt and constant-time comparison.
- **Sessions:** signed HS256 JWT with an expiry (default 12 hours).
- **Admin bootstrap:** the admin is created from backend environment variables. Public registration uses a Pydantic model with `extra="forbid"` and hard-codes the student role, so a `role` field is rejected with `422`.
- **Role checks:** FastAPI dependencies enforce signed-in and admin access. Students cannot read another student's complaints or matches.
- **Privacy-aware serialization:** public listings and non-owner report detail omit `owner_name`; matches are returned only to the owner or an admin. The frontend also hides match sections from non-owners.
- **Uploads:** MIME allowlist, magic-byte checks, 5 MB limit, UUID filenames, safe deletion.
- **Secrets:** `.env` is gitignored; API keys and JWT secrets stay on the server.
- **Moderation:** admins can delete reports and complaints; cascading foreign keys clean up related matches.

Production hardening would add HTTPS, a strong random secret, PostgreSQL, object storage, rate limiting, email verification, password reset, audit logs, and backups.

---

## 6. Testing and results

### 6.1 API tests

`pytest` runs 21 tests against an isolated temporary SQLite database. All 21 pass.

The suite covers authentication, admin bootstrap, role-escalation rejection, duplicate email, wrong password, private endpoint protection, report validation, image validation, AI matching, privacy, owner status updates, complaint classification and references, live triage preview, safety-weighted classification, complaint privacy, admin updates, statistics shape, student/admin separation, match approval, and moderation deletion.

### 6.2 Responsive UI verification

A headless Chrome sweep checked 75 combinations of route and viewport width (360, 390, 768, 1024, 1440 px) for student and admin routes. It checked:

- horizontal overflow;
- console errors;
- failed HTTP requests;
- presence of the page heading and expected layout mode.

Final result: **0 problems**. The sweep found and prompted fixes for four CSS issues: stretched status pills, stretched match-side badges, muted admin avatar text, and grid blowout from long nowrap text.

### 6.3 Manual demonstration

The following flows were exercised in a browser:

- student login and dashboard;
- browse with 12 seeded items;
- own report detail with a 77% match and reasons;
- live complaint triage, submission, reference, and status steps;
- admin login and dashboard;
- match approval (both reports became matched) and rejection;
- admin complaint update (status, department, priority, note);
- admin deletion of a disposable report pair and complaint;
- mobile and desktop screenshots.

---

## 7. Limitations

- The client is an installable PWA, not a native Android APK. Flutter/Dart and the Android SDK were unavailable on the build machine, and disk space was insufficient for the toolchain.
- SQLite and local disk uploads are development choices, not a production deployment.
- Matching runs synchronously at report creation; there is no background job queue.
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
5. Add background matching jobs and notifications for new matches.
6. Add redaction/consent before sending complaint text to an external LLM.
7. Add richer analytics only after the core workflows are stable.

---

## 9. Conclusion

CampusConnect AI demonstrates the complete core loop from the roadmap: students report items and complaints, AI produces ranked matches and triage suggestions, and administrators verify matches, assign complaints, update statuses, and moderate content. The implementation prioritizes privacy, explicit human control, testability, and a clean migration path to Supabase, sentence-transformers, Gemini, and Flutter. The delivered PWA is usable on desktop and mobile today, while the API remains ready for the planned Android client.

---

## Appendix — Demo accounts

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@campus.edu` | `Admin123!` |
| Student | `maya@campus.edu` | `Student123!` |
| Student | `leo@campus.edu` | `Student123!` |

Run:

```powershell
cd campusconnect
.\setup.ps1
.\run.ps1
```

Open http://127.0.0.1:8080. API docs: http://127.0.0.1:8080/docs.
