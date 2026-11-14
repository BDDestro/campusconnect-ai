# CampusConnect AI — Presentation Outline

**Suggested length:** 10–12 minutes + 3–5 minutes of demo and questions
**Audience:** Course instructor / project panel
**Deck:** 11 slides. Each slide below lists the message, the visual to show, and speaker notes.

---

## Slide 1 — Title

**On screen**

> **CampusConnect AI**
> Intelligent lost & found and complaint management for universities
>
> Student name · Course · Date

**Visual:** App icon and the mobile dashboard screenshot (`docs/screenshots/mobile-dashboard.png`).

**Say:** "CampusConnect AI is a working MVP that helps students recover lost items and route campus complaints, using AI to suggest matches and priorities while keeping humans in control."

---

## Slide 2 — The problem

**On screen**

- Lost & found is fragmented: separate desks, group chats, notice boards.
- Owners and finders rarely see each other's reports.
- Complaints arrive with no category, department, or priority.
- Contact details get exposed in public posts.

**Visual:** Two-column "Today" sketch: *Lost item → nowhere to post* | *Complaint → wrong inbox*.

**Say:** "A missing phone is reported in one place while the finder hands it in somewhere else. Complaints get misrouted and urgent safety issues can sit behind routine maintenance requests."

---

## Slide 3 — Goals and scope

**On screen**

| In scope | Out of scope (per roadmap) |
|---|---|
| Student register/login | Real-time chat |
| Lost/found reports + photos | Push notifications |
| AI match suggestions | Payments |
| Complaint AI triage | Maps |
| Student and admin dashboards | Facial recognition |
| Role-based privacy | Complex analytics |

**Say:** "The roadmap deliberately limits the first version. Every item here is implemented except the native APK, which I'll explain later."

---

## Slide 4 — Architecture

**On screen**

```text
Mobile-first PWA (installable)
        │  JSON + multipart over HTTPS
        ▼
FastAPI  ── auth (scrypt + JWT)
         ── reports / uploads / matching
         ── complaints / triage
         ── admin stats / match review
        │
        ▼
SQLAlchemy → SQLite now, PostgreSQL/Supabase by changing DATABASE_URL
```

**Visual:** The architecture diagram from `README.md`.

**Say:** "One versioned API serves the web client today and a Flutter client later. The browser never holds a secret — only a short-lived user token."

---

## Slide 5 — Student experience

**On screen**

1. Register or sign in.
2. Post a lost or found report with photo, category, location, date.
3. Browse and filter all public listings.
4. See AI-suggested matches with score and reasons.
5. Submit a complaint with a live AI preview.
6. Track status with a reference: `CC-2026-0007`.

**Visual:** Mobile screenshots — login, browse, report matches, complaint AI (2 × 2 grid).

**Say:** "Students see only their own records and matches. Public listings never show another student's name or contact details."

---

## Slide 6 — AI matching

**On screen**

- Text → TF-IDF vectors → cosine similarity.
- Title weighted 3×, category 2×; location included.
- Small boosts: same category, same/nearby location.
- Top 5 above `0.15`, each with human-readable reasons.

**Demo numbers**

| Pair | Score |
|---|---|
| iPhone lost ↔ iPhone found | 77% |
| ID card lost ↔ ID card found | 73% |
| Water bottle lost ↔ found | 62% |
| Backpack lost ↔ found | 51% |
| Glasses lost ↔ iPhone found | 29% (weak — shows why review matters) |

**Say:** "It's lexical, not a black box: no model download, runs offline, deterministic, and fast. The interface is small enough to swap in sentence-transformers embeddings without touching the API."

---

## Slide 7 — AI complaint triage

**On screen**

- Keyword rules → category, department, priority.
- Safety-critical words weighted 3× (fire, harassment, assault, injury, threat, weapon, gas leak).
- Priority: Critical / High / Medium / Low.
- Optional Gemini behind the backend; falls back to local rules on any error.
- Admin can override every field.

**Example**

> "Someone was harassing students near the east parking lot after dark and the lights are broken."
> → **Safety & Security · Campus Security · Critical**

**Say:** "This example matters: a naive keyword count sent it to Facilities because of 'broken lights'. Weighting safety words fixed a real bug, and there's a regression test for it."

---

## Slide 8 — Administrator experience

**On screen**

- Dashboard: users, reports, complaints, pending matches, top categories.
- Match queue: approve or reject every AI suggestion.
- Approving marks both reports as **matched**.
- Complaint queue: edit category, department, priority, status, admin note.
- Moderation: remove reports and complaints.
- Admin accounts are owner-created; never offered at sign-up.

**Visual:** `docs/screenshots/desktop-admin-dashboard.png` and `desktop-admin-matches.png`.

**Say:** "Approval is explicit. AI never returns an item on its own, and every complaint field stays editable."

---

## Slide 9 — Security and privacy

**On screen**

- Passwords: `hashlib.scrypt`, random salt, constant-time compare.
- Sessions: signed HS256 JWT, 12-hour default.
- Public sign-up hard-codes `student`; a `role` field is rejected with `422`.
- Non-owners get `owner_name: null` and no matches.
- Uploads: MIME + magic-byte checks, 5 MB cap, UUID filenames.
- Secrets only in backend `.env`.

**Say:** "Privacy is enforced in serializers, not just hidden in the UI. I verified with two student accounts that the other owner's name and matches are absent from the API response."

---

## Slide 10 — Testing and results

**On screen**

- **21 / 21 API tests pass** (isolated temporary database).
- **75 / 75 responsive checks pass** — 5 widths × 15 route/role combinations.
- 0 horizontal overflow, 0 console errors, 0 failed requests.
- Bugs found and fixed during QA: classifier safety weighting, stretched status pills, stretched match badges, muted admin avatar, grid blowout, mobile filter truncation.

**Visual:** Small table of test categories (auth, privacy, validation, AI, admin).

**Say:** "The QA pass wasn't cosmetic — it caught a real classification bug and four layout defects."

---

## Slide 11 — Limitations and next steps

**On screen**

| Limitation | Next step |
|---|---|
| PWA, not a native APK | Flutter client against the same API → release APK |
| SQLite + local uploads | Supabase PostgreSQL + Storage, Alembic migrations |
| TF-IDF matching | sentence-transformers + pgvector |
| No email verification/reset | Add verification, reset, rate limiting, audit log |
| Synchronous matching | Background jobs + notifications |

**Say:** "The API is already Flutter-ready. The remaining work is client tooling and production hardening, not a redesign."

---

## Slide 12 — Conclusion / Q&A

**On screen**

> **CampusConnect AI**
> Students report. AI suggests. People decide.
>
> Demo: `http://127.0.0.1:8080` · Docs: `/docs`

**Say:** "The core loop from the roadmap works end to end: report, match, review, resolve, moderate — with privacy and human verification built in. Thank you — questions?"

---

## Live demo script (3–5 minutes)

Run `.\run.ps1` beforehand and keep two browser windows open: one normal, one incognito.

| # | Window | Action | What to point out |
|---|---|---|---|
| 1 | Normal | Open `http://127.0.0.1:8080` | Mobile-first login, installable PWA |
| 2 | Normal | Sign in as `maya@campus.edu` / `Student123!` | Student dashboard stats |
| 3 | Normal | Browse → search "iPhone" | 12 seeded items, filters |
| 4 | Normal | Open **Black iPhone 13 with blue case** | 77% match, reasons, "not proof of ownership" notice |
| 5 | Normal | Complaints → New | Type the harassment example, show **Safety & Security / Critical** live |
| 6 | Normal | Submit | Reference `CC-2026-0007`, Received → In Progress → Resolved |
| 7 | Incognito | Sign in as `leo@campus.edu` / `Student123!` | Open Maya's report: no owner name, no matches |
| 8 | Incognito | Sign in as `admin@campus.edu` / `Admin123!` | Dashboard counts, pending match queue |
| 9 | Incognito | Approve the iPhone match | Both reports become **matched** |
| 10 | Incognito | Complaints → open `CC-2026-0007` | Change status to In Progress, add note, save |
| 11 | Either | Resize to phone width | Bottom navigation, single-column cards, no overflow |

**Reset before presenting:** delete `backend/data/campusconnect.db` and restart to restore the pristine demo (12 open reports, 6 complaints, 5 pending matches).

**If the demo fails:** the screenshots in `docs/screenshots/` and `docs/PROJECT_REPORT.md` cover every screen and flow.

---

## Likely questions and short answers

**Why not sentence-transformers?**
The build machine had ~4 GB free and the torch download is ~2.5 GB. TF-IDF is deterministic, offline, and adequate for a campus-sized dataset. The matcher has a one-function interface, and the swap is documented in the README.

**Why not Supabase?**
SQLite keeps the MVP self-contained and reproducible. All access goes through SQLAlchemy, so `DATABASE_URL` moves it to Supabase PostgreSQL; uploads are isolated in `storage.py`.

**Why no APK?**
Flutter, Dart, and the Android SDK were not installed, and disk space was insufficient for the toolchain. The delivered client is an installable PWA using the same API; Flutter migration notes are included.

**Can AI approve a match automatically?**
No. Scores are suggestions. An administrator approves or rejects each pair, and approval is what marks items matched.

**What happens if Gemini is down?**
The backend catches any failure and silently falls back to local keyword rules, so complaint submission never depends on the external service.

**How is privacy enforced?**
In the serializers and dependencies, not the UI: non-owners receive `owner_name: null` and no match list. This is covered by API tests.

**What would you build next?**
The Flutter Android client, Supabase Storage/PostgreSQL, embedding-based matching, and background notifications for new matches.
