import { api, session } from "./api.js";

/* ==========================================================================
   State + tiny helpers
   ========================================================================== */

const state = { user: null, categories: null };
const app = document.getElementById("app");

const ICONS = {
  home: '<path d="M3 10.7 12 3l9 7.7V20a1 1 0 0 1-1 1h-5.5v-6.5h-5V21H4a1 1 0 0 1-1-1z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  clipboard: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4.5V3h6v1.5M9 10h6M9 14h6"/>',
  shield: '<path d="M12 3 5 6v5c0 4.4 3 8 7 10 4-2 7-5.6 7-10V6z"/><path d="m9 12 2 2 4-4"/>',
  logout: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 17l5-5-5-5M15 12H4"/>',
  sparkles: '<path d="m12 3 1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6z"/><path d="M18.5 15.5 19.3 18l2.5.8-2.5.8-.8 2.4-.8-2.4-2.4-.8 2.4-.8z"/>',
  pin: '<path d="M12 21s7-6.1 7-11a7 7 0 1 0-14 0c0 4.9 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/>',
  calendar: '<rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 3v4M16 3v4M4 10h16"/>',
  camera: '<path d="M4 8h3l2-2h6l2 2h3v11H4z"/><circle cx="12" cy="13.5" r="3.4"/>',
  back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  check: '<path d="m5 12 4.5 4.5L19 7"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  alert: '<path d="M12 4 3 20h18z"/><path d="M12 10v4M12 17.2v.1"/>',
  box: '<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/><path d="M10 11v5M14 11v5"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/>',
  inbox: '<path d="M4 4h16v16H4z"/><path d="M4 13h4l2 3h4l2-3h4"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  refresh: '<path d="M20 12a8 8 0 1 1-2.3-5.7"/><path d="M20 4v5h-5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M5 20h14"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
};

function icon(name, size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function initials(name) {
  return String(name || "?").split(/\s+/).slice(0, 2).map((part) => part[0] || "").join("").toUpperCase();
}

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fmtDay(value) {
  if (!value) return "";
  const [year, month, day] = String(value).slice(0, 10).split("-").map(Number);
  if (!year) return "";
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    month: "short", day: "numeric", year: "numeric",
  });
}

function timeAgo(value) {
  if (!value) return "";
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.round(diff / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return fmtDay(value);
}

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" || value === false) return;
    search.set(key, value);
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

const REPORT_STATUS = { open: "Open", matched: "Matched", returned: "Returned", closed: "Closed" };
const MATCH_STATUS = { pending: "Awaiting review", approved: "Approved", rejected: "Rejected" };
const COMPLAINT_STATUS = { Received: "Received", "In Progress": "In Progress", Resolved: "Resolved" };

const ITEM_META = {
  Electronics: ["📱", "cat-electronics"],
  Documents: ["🪪", "cat-documents"],
  Bags: ["🎒", "cat-bags"],
  "Personal Items": ["🧴", "cat-personal"],
  Clothing: ["👕", "cat-clothing"],
  Keys: ["🔑", "cat-keys"],
  Books: ["📚", "cat-books"],
  Other: ["📦", "cat-other"],
};

const COMPLAINT_META = {
  Facilities: "🛠️",
  "IT & Network": "🌐",
  "Safety & Security": "🛡️",
  Hostel: "🏠",
  Academics: "🎓",
  Transport: "🚌",
  Cleanliness: "🧹",
  Other: "📋",
};

function itemMeta(category) {
  return ITEM_META[category] || ITEM_META.Other;
}

function complaintEmoji(category) {
  return COMPLAINT_META[category] || "📋";
}

function statusBadge(status) {
  return `<span class="badge ${esc(status)}">${REPORT_STATUS[status] || esc(status)}</span>`;
}

function priorityBadge(priority) {
  return `<span class="badge ${String(priority).toLowerCase()}">${esc(priority)}</span>`;
}

function complaintStatusBadge(status) {
  const cls = status === "In Progress" ? "in-progress" : status.toLowerCase();
  return `<span class="badge ${cls}">${esc(status)}</span>`;
}

function matchStatusBadge(status) {
  return `<span class="badge ${esc(status)}">${MATCH_STATUS[status] || esc(status)}</span>`;
}

function options(list, selected) {
  return list.map((value) => `<option value="${esc(value)}"${value === selected ? " selected" : ""}>${esc(value)}</option>`).join("");
}

function toast(message, tone = "success") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = message;
  el.className = `toast show ${tone}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { el.className = "toast"; }, 3400);
}

function firstName() {
  return String(state.user?.name || "").split(" ")[0];
}

function isAdmin() {
  return state.user?.role === "admin";
}

async function ensureCategories() {
  if (!state.categories) state.categories = await api.categories();
  return state.categories;
}

/* ==========================================================================
   Auth screens
   ========================================================================== */

function renderAuth(mode) {
  const login = mode === "login";
  app.innerHTML = `
  <div class="auth">
    <aside class="auth-brand">
      <div class="auth-logo"><span class="logo-mark">C</span> CampusConnect AI</div>
      <div class="auth-hero">
        <span class="eyebrow">University lost &amp; found + complaints</span>
        <h1>Lost something?<br>Found something?<br>Say something.</h1>
        <p>One campus platform for missing belongings and the issues that need fixing — with AI that connects the dots.</p>
        <div class="auth-features">
          <div class="auth-feature">
            <span class="ficon">${icon("search", 19)}</span>
            <div><strong>AI-assisted matching</strong><span>Similar descriptions are ranked so nothing stays lost for long.</span></div>
          </div>
          <div class="auth-feature">
            <span class="ficon">${icon("sparkles", 19)}</span>
            <div><strong>Smart complaint triage</strong><span>Category, department and priority suggested in seconds.</span></div>
          </div>
          <div class="auth-feature">
            <span class="ficon">${icon("shield", 19)}</span>
            <div><strong>Human verification</strong><span>Every match is reviewed before an item is returned.</span></div>
          </div>
        </div>
      </div>
      <div class="auth-foot">CampusConnect AI · Academic prototype · AI suggestions are never final decisions.</div>
    </aside>

    <main class="auth-panel">
      <div class="auth-card">
        <div class="auth-mobile-brand"><span class="logo-mark sm">C</span> CampusConnect AI</div>
        <h2>${login ? "Welcome back" : "Create your account"}</h2>
        <p>${login ? "Sign in to report items, track complaints and review AI matches." : "Student accounts are free. Administrator accounts are created by the campus team."}</p>

        <form data-form="${login ? "login" : "register"}" novalidate>
          ${login ? "" : `
          <div class="field">
            <label for="reg-name">Full name</label>
            <input class="input" id="reg-name" name="name" autocomplete="name" required minlength="2" maxlength="80" placeholder="Maya Patel">
          </div>`}
          <div class="field">
            <label for="auth-email">Campus email</label>
            <input class="input" id="auth-email" name="email" type="email" autocomplete="email" required placeholder="you@campus.edu">
          </div>
          <div class="field">
            <label for="auth-password">Password</label>
            <input class="input" id="auth-password" name="password" type="password" autocomplete="${login ? "current-password" : "new-password"}" required minlength="8" placeholder="At least 8 characters">
          </div>
          ${login ? "" : `
          <div class="field">
            <label for="reg-confirm">Confirm password</label>
            <input class="input" id="reg-confirm" name="confirm" type="password" autocomplete="new-password" required minlength="8" placeholder="Repeat your password">
          </div>
          <div class="role-note">${icon("lock", 15)} Public sign-up only creates student accounts. Ask the project owner for administrator access.</div>`}
          <button class="btn primary block" type="submit">${login ? "Sign in" : "Create student account"}</button>
        </form>

        <p class="auth-switch">${login ? 'New here? <a href="#/register">Create a student account</a>' : 'Already registered? <a href="#/login">Sign in</a>'}</p>

        ${login ? `
        <div class="demo-box">
          <div class="demo-label">Try the demo</div>
          <div class="demo-btns">
            <button class="btn ghost" type="button" data-action="fill-demo" data-email="maya@campus.edu" data-password="Student123!">Student demo</button>
            <button class="btn ghost" type="button" data-action="fill-demo" data-email="admin@campus.edu" data-password="Admin123!">Admin demo</button>
          </div>
        </div>` : ""}
      </div>
    </main>
  </div>`;
  window.scrollTo(0, 0);
}

/* ==========================================================================
   Shell
   ========================================================================== */

function navItem(href, iconName, label, active) {
  return `<a class="nav-item ${active ? "active" : ""}" href="${href}"${active ? ' aria-current="page"' : ""}>${icon(iconName, 19)}<span>${label}</span></a>`;
}

function bottomItem(href, iconName, label, active, fab = false) {
  if (fab) {
    return `<a class="${active ? "active" : ""} fab" href="${href}"><span class="fab-circle">${icon("plus", 22)}</span><span>${label}</span></a>`;
  }
  return `<a class="${active ? "active" : ""}" href="${href}">${icon(iconName, 20)}<span>${label}</span></a>`;
}

function shell(content, active) {
  const admin = isAdmin();
  const user = state.user;
  return `
  <div class="shell">
    <aside class="sidebar">
      <a class="brand" href="#/">
        <span class="logo-mark">C</span>
        <span>CampusConnect AI<small>${admin ? "Administration" : "Student portal"}</small></span>
      </a>
      <nav class="nav">
        <div class="nav-label">Workspace</div>
        ${navItem("#/", "home", "Dashboard", active === "home")}
        ${navItem("#/browse", "search", "Lost &amp; Found", active === "browse")}
        ${admin ? "" : navItem("#/my-reports", "inbox", "My Reports", active === "my")}
        ${admin ? `
          <div class="nav-label">Administration</div>
          ${navItem("#/admin/matches", "sparkles", "AI Matches", active === "admin-matches")}
          ${navItem("#/admin/complaints", "clipboard", "Complaints", active === "admin-complaints")}
          ${navItem("#/admin/reports", "box", "All Reports", active === "admin-reports")}
        ` : `
          ${navItem("#/complaints", "clipboard", "Complaints", active === "complaints")}
        `}
      </nav>
      <a class="btn primary block" href="${admin ? "#/admin/matches" : "#/reports/new"}">
        ${icon(admin ? "sparkles" : "plus", 17)} ${admin ? "Review matches" : "Report an item"}
      </a>
      <div class="sidebar-foot">
        <div class="user-chip">
          <span class="avatar">${initials(user.name)}</span>
          <div class="who"><strong>${esc(user.name)}</strong><span>${admin ? "Administrator" : "Student"}</span></div>
        </div>
        <button class="logout" type="button" data-action="logout">${icon("logout", 17)} Sign out</button>
      </div>
    </aside>

    <div class="main-wrap">
      <header class="topbar">
        <a class="brand" href="#/"><span class="logo-mark sm">C</span> CampusConnect</a>
        <div class="row">
          <span class="avatar">${initials(user.name)}</span>
        </div>
      </header>
      <main class="content">${content}</main>
      <nav class="bottom-nav" aria-label="Primary">
        ${admin ? `
          ${bottomItem("#/", "home", "Home", active === "home")}
          ${bottomItem("#/browse", "search", "Browse", active === "browse")}
          ${bottomItem("#/admin/matches", "sparkles", "Matches", active === "admin-matches")}
          ${bottomItem("#/admin/complaints", "clipboard", "Complaints", active === "admin-complaints")}
          ${bottomItem("#/admin/reports", "box", "Reports", active === "admin-reports")}
        ` : `
          ${bottomItem("#/", "home", "Home", active === "home")}
          ${bottomItem("#/browse", "search", "Browse", active === "browse")}
          ${bottomItem("#/reports/new", "plus", "Report", active === "report", true)}
          ${bottomItem("#/complaints", "clipboard", "Complaints", active === "complaints")}
          ${bottomItem("#/my-reports", "inbox", "Mine", active === "my")}
        `}
      </nav>
    </div>
  </div>`;
}

function pageHead(eyebrow, title, subtitle, actions = "") {
  return `
  <div class="page-head">
    <div>
      <div class="eyebrow">${eyebrow}</div>
      <h1 class="page-title">${title}</h1>
      ${subtitle ? `<p class="page-sub">${subtitle}</p>` : ""}
    </div>
    ${actions ? `<div class="head-actions">${actions}</div>` : ""}
  </div>`;
}

function statCard(iconName, tone, value, label) {
  return `<div class="card stat"><span class="stat-icon ${tone}">${icon(iconName, 21)}</span><div><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div></div>`;
}

function emptyState(iconName, title, text, cta = "") {
  return `<div class="empty"><span class="eicon">${icon(iconName, 26)}</span><h3>${title}</h3><p>${text}</p>${cta}</div>`;
}

function loadingView() {
  return `<div class="page-loading">
    <div class="skeleton bar" style="width:42%"></div>
    <div class="grid"><div class="skeleton tile"></div><div class="skeleton tile"></div><div class="skeleton tile"></div></div>
  </div>`;
}

function errorView(message) {
  return `${pageHead("Something went wrong", "We couldn't load this page", "")}
    ${emptyState("alert", "Request failed", esc(message), `<button class="btn primary" type="button" data-action="retry">${icon("refresh", 16)} Try again</button>`)}`;
}

/* ==========================================================================
   Dashboard
   ========================================================================== */

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function miniReport(report) {
  const [emoji, cls] = itemMeta(report.category);
  return `<a class="mini-row" href="#/reports/${report.id}">
    <span class="thumb ${cls}">${report.image_url ? `<img src="${esc(report.image_url)}" alt="">` : emoji}</span>
    <span class="info"><strong>${esc(report.title)}</strong><span>${esc(report.type)} · ${esc(report.location)} · ${timeAgo(report.created_at)}</span></span>
    ${statusBadge(report.status)}
  </a>`;
}

function miniComplaint(complaint) {
  return `<a class="mini-row" href="#/complaints/${complaint.id}">
    <span class="thumb" style="background:#eef2ff">${complaintEmoji(complaint.category)}</span>
    <span class="info"><strong>${esc(complaint.description)}</strong><span>${esc(complaint.reference)} · ${timeAgo(complaint.created_at)}</span></span>
    ${complaintStatusBadge(complaint.status)}
  </a>`;
}

async function dashboard() {
  if (isAdmin()) return adminDashboard();

  const [reports, complaints] = await Promise.all([
    api.listReports({ mine: true }),
    api.listComplaints(),
  ]);

  const openReports = reports.filter((r) => ["open", "matched"].includes(r.status)).length;
  const matches = reports.reduce((total, r) => total + (r.match_count || 0), 0);
  const activeComplaints = complaints.filter((c) => c.status !== "Resolved").length;
  const resolved = complaints.filter((c) => c.status === "Resolved").length;

  return `
    ${pageHead(
      new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" }),
      `${greeting()}, ${esc(firstName())}`,
      "Here is what is happening with your reports and complaints.",
      `<a class="btn ghost" href="#/complaints/new">${icon("clipboard", 16)} New complaint</a>
       <a class="btn primary" href="#/reports/new">${icon("plus", 16)} Report an item</a>`
    )}

    <div class="stat-grid">
      ${statCard("inbox", "indigo", openReports, "Open reports")}
      ${statCard("sparkles", "amber", matches, "AI matches found")}
      ${statCard("clock", "rose", activeComplaints, "Complaints in progress")}
      ${statCard("check", "green", resolved, "Complaints resolved")}
    </div>

    <div class="dash-grid">
      <section class="card card-pad">
        <div class="card-head"><h2>Your recent reports</h2><a class="link" href="#/my-reports">View all ${icon("chevron", 14)}</a></div>
        <div class="mini-list">
          ${reports.length ? reports.slice(0, 4).map(miniReport).join("") : emptyState("box", "Nothing reported yet", "Lost or found something on campus? Create your first report.", `<a class="btn primary sm" href="#/reports/new">${icon("plus", 15)} Report an item</a>`)}
        </div>
      </section>

      <div class="stack">
        <section class="card card-pad">
          <div class="card-head"><h2>Quick actions</h2></div>
          <div class="quick-grid">
            <a class="quick" href="#/reports/new">
              <span class="qicon">${icon("plus", 19)}</span>
              <span><strong>Report an item</strong><span>Lost or found, in under a minute</span></span>
              <span class="chev">${icon("chevron", 16)}</span>
            </a>
            <a class="quick" href="#/browse?type=found">
              <span class="qicon">${icon("search", 19)}</span>
              <span><strong>Browse found items</strong><span>See what students have handed in</span></span>
              <span class="chev">${icon("chevron", 16)}</span>
            </a>
            <a class="quick" href="#/complaints/new">
              <span class="qicon">${icon("clipboard", 19)}</span>
              <span><strong>Submit a complaint</strong><span>Get an AI category and priority</span></span>
              <span class="chev">${icon("chevron", 16)}</span>
            </a>
          </div>
        </section>
        <div class="ai-tip">
          <div class="row">${icon("sparkles", 17)} AI is a helper, not a judge</div>
          <p>Matches and complaint priorities are suggestions. A student or administrator always verifies before an item is returned or a complaint is escalated.</p>
        </div>
      </div>
    </div>

    <section class="card card-pad mt-24">
      <div class="card-head"><h2>Your complaints</h2><a class="link" href="#/complaints">View all ${icon("chevron", 14)}</a></div>
      <div class="mini-list">
        ${complaints.length ? complaints.slice(0, 3).map(miniComplaint).join("") : emptyState("clipboard", "No complaints yet", "Something broken or unsafe on campus? Tell the right department.", `<a class="btn primary sm" href="#/complaints/new">${icon("plus", 15)} Submit a complaint</a>`)}
      </div>
    </section>`;
}

function miniMatch(match) {
  const [emoji, cls] = itemMeta(match.lost.category);
  return `<a class="mini-row" href="#/admin/matches">
    <span class="thumb ${cls}">${emoji}</span>
    <span class="info"><strong>${esc(match.lost.title)} ↔ ${esc(match.found.title)}</strong><span>${esc(match.lost.location)} · ${match.score}% similarity</span></span>
    <span class="score">${match.score}%</span>
  </a>`;
}

async function adminDashboard() {
  const stats = await api.adminStats();
  const maxCategory = Math.max(1, ...stats.top_categories.map((row) => row.count));

  return `
    ${pageHead(
      "Administrator overview",
      `${greeting()}, ${esc(firstName())}`,
      "Review AI matches, assign complaints and keep the campus moving.",
      `<a class="btn ghost" href="#/admin/reports">${icon("box", 16)} All reports</a>
       <a class="btn primary" href="#/admin/matches">${icon("sparkles", 16)} Review matches</a>`
    )}

    <div class="stat-grid">
      ${statCard("sparkles", "amber", stats.matches.pending, "Pending AI matches")}
      ${statCard("box", "indigo", stats.reports.open, "Open reports")}
      ${statCard("clipboard", "rose", stats.complaints.received, "New complaints")}
      ${statCard("user", "green", stats.users.students, "Students")}
    </div>

    <div class="admin-grid">
      <section class="card card-pad">
        <div class="card-head"><h2>Matches needing review</h2><a class="link" href="#/admin/matches">Open queue ${icon("chevron", 14)}</a></div>
        <div class="mini-list">
          ${stats.pending_matches.length ? stats.pending_matches.map(miniMatch).join("") : emptyState("check", "Queue is clear", "No AI matches are waiting for review right now.")}
        </div>
      </section>

      <section class="card card-pad">
        <div class="card-head"><h2>Reports by category</h2></div>
        <div class="bars">
          ${stats.top_categories.length ? stats.top_categories.map((row) => `
            <div class="bar-row">
              <div class="bar-label"><span>${esc(row.category)}</span><span>${row.count}</span></div>
              <div class="bar-track"><i style="width:${Math.round((row.count / maxCategory) * 100)}%"></i></div>
            </div>`).join("") : `<p class="muted small">No reports yet.</p>`}
        </div>
        <div class="notice brand mt-16">${icon("sparkles", 16)}<span>AI suggestions are reviewed by a person before any item is returned.</span></div>
      </section>
    </div>

    <section class="card card-pad mt-24">
      <div class="card-head"><h2>Recent complaints</h2><a class="link" href="#/admin/complaints">Manage complaints ${icon("chevron", 14)}</a></div>
      <div class="mini-list">
        ${stats.recent_complaints.length ? stats.recent_complaints.map(miniComplaint).join("") : emptyState("clipboard", "No complaints yet", "Student complaints will appear here.")}
      </div>
    </section>`;
}

/* ==========================================================================
   Lost & found
   ========================================================================== */

function browseHref(params, overrides = {}) {
  const merged = {
    type: params.get("type") || "",
    category: params.get("category") || "",
    status: params.get("status") || "",
    q: params.get("q") || "",
    ...overrides,
  };
  return `#/browse${buildQuery(merged)}`;
}

function reportCard(report) {
  const [emoji, cls] = itemMeta(report.category);
  const label = REPORT_STATUS[report.status] || report.status;
  return `<a class="item-card" href="#/reports/${report.id}" data-item
      data-text="${esc(`${report.title} ${report.description} ${report.location} ${report.category}`.toLowerCase())}">
    <div class="item-media ${cls}">
      ${report.image_url ? `<img src="${esc(report.image_url)}" alt="${esc(report.title)}">` : `<span>${emoji}</span>`}
      <span class="badge ${esc(report.type)}">${esc(report.type)}</span>
      <span class="status-pill badge ${esc(report.status)}">${esc(label)}</span>
    </div>
    <div class="item-body">
      <h3>${esc(report.title)}</h3>
      <div class="item-meta">${icon("pin", 13)} ${esc(report.location)} · ${fmtDay(report.date)}</div>
      <div class="item-foot">
        <span class="chip">${esc(report.category)}</span>
        ${report.match_count ? `<span class="match-pill">${icon("sparkles", 12)} ${report.match_count} match${report.match_count > 1 ? "es" : ""}</span>` : ""}
      </div>
    </div>
  </a>`;
}

async function browse(params) {
  const type = params.get("type") || "";
  const category = params.get("category") || "";
  const reportStatus = params.get("status") || "";
  const q = params.get("q") || "";
  const cats = await ensureCategories();
  const reports = await api.listReports({ type, category, status: reportStatus, q });

  return `
    ${pageHead(
      "Campus lost &amp; found",
      "Lost &amp; Found",
      "Browse what students have lost or handed in. AI highlights likely matches; a human confirms ownership.",
      `<a class="btn primary" href="#/reports/new">${icon("plus", 16)} Report an item</a>`
    )}

    <div class="filter-bar">
      <div class="search">${icon("search", 17)}<input class="input" type="search" placeholder="Search items, descriptions, locations…" data-filter-search value="${esc(q)}"></div>
      <div class="segmented">
        <a class="${!type ? "active" : ""}" href="${browseHref(params, { type: "" })}">All</a>
        <a class="${type === "lost" ? "active" : ""}" href="${browseHref(params, { type: "lost" })}">Lost</a>
        <a class="${type === "found" ? "active" : ""}" href="${browseHref(params, { type: "found" })}">Found</a>
      </div>
      <select class="select" data-filter="category" aria-label="Filter by category">
        <option value="">All categories</option>
        ${options(cats.item_categories, category)}
      </select>
      <select class="select" data-filter="status" aria-label="Filter by status">
        <option value="">Any status</option>
        ${options(["open", "matched", "returned", "closed"], reportStatus)}
      </select>
    </div>

    ${reports.length ? `
      <div class="item-grid">${reports.map(reportCard).join("")}</div>
      <div class="empty hidden" data-no-results>${icon("search", 26)}<h3>No items match your search</h3><p>Try a different word or clear the search box.</p></div>
    ` : emptyState(
      "box",
      "No items to show",
      type || category || reportStatus ? "No reports match these filters yet." : "Be the first to report a lost or found item on campus.",
      `<a class="btn primary" href="#/reports/new">${icon("plus", 16)} Report an item</a>`
    )}`;
}

function matchSide(report) {
  const [emoji, cls] = itemMeta(report.category);
  return `<a class="match-side" href="#/reports/${report.id}">
    <span class="badge ${esc(report.type)}">${esc(report.type)}</span>
    <span class="thumb ${cls}">${report.image_url ? `<img src="${esc(report.image_url)}" alt="">` : emoji}</span>
    <h4>${esc(report.title)}</h4>
    <p>${esc(report.location)} · ${fmtDay(report.date)}</p>
    ${report.owner_name ? `<p>Reported by ${esc(report.owner_name)}</p>` : ""}
  </a>`;
}

function matchCard(match, admin = false) {
  return `<article class="card match-card">
    <div class="match-top">
      <span class="score-badge"><b>${match.score}%</b><span>similarity</span></span>
      ${matchStatusBadge(match.status)}
    </div>
    <div class="score-bar"><i style="width:${match.score}%"></i></div>
    <div class="match-pair">
      ${matchSide(match.lost)}
      <div class="match-arrow">${icon("arrow", 18)}</div>
      ${matchSide(match.found)}
    </div>
    <div class="reasons">${match.reasons.map((reason) => `<span class="reason">${esc(reason)}</span>`).join("")}</div>
    ${admin && match.status === "pending" ? `
      <div class="match-actions">
        <button class="btn primary sm" type="button" data-action="approve-match" data-id="${match.id}">${icon("check", 15)} Approve match</button>
        <button class="btn danger sm" type="button" data-action="reject-match" data-id="${match.id}">${icon("x", 15)} Reject</button>
      </div>` : ""}
  </article>`;
}

async function reportDetail(id, params) {
  const report = await api.getReport(id);
  const created = params.get("created") === "1";
  const [emoji, cls] = itemMeta(report.category);
  const canSeeMatches = report.is_mine || isAdmin();
  const label = REPORT_STATUS[report.status] || report.status;

  return `
    <a class="back-link" href="#/browse">${icon("back", 16)} Back to Lost &amp; Found</a>
    ${created ? `<div class="notice success mt-8" style="margin-bottom:18px">${icon("check", 17)}<span><strong>Report saved.</strong> ${report.matches.length ? `We found ${report.matches.length} possible match${report.matches.length > 1 ? "es" : ""} below.` : "We will keep comparing it with new reports."}</span></div>` : ""}

    <div class="detail-grid">
      <div class="detail-media ${cls}">
        ${report.image_url ? `<img src="${esc(report.image_url)}" alt="${esc(report.title)}">` : `<span>${emoji}</span>`}
        <span class="badge ${esc(report.type)}">${esc(report.type)}</span>
      </div>

      <section class="card detail-card">
        <div class="row">${statusBadge(report.status)}<span class="chip">${esc(report.category)}</span></div>
        <h1>${esc(report.title)}</h1>
        <p class="detail-desc">${esc(report.description)}</p>

        <div class="detail-meta">
          <div class="meta-row">${icon("pin", 17)} <span>Location</span> <strong>${esc(report.location)}</strong></div>
          <div class="meta-row">${icon("calendar", 17)} <span>Date</span> <strong>${fmtDay(report.date)}</strong></div>
          <div class="meta-row">${icon("clock", 17)} <span>Reported</span> <strong>${timeAgo(report.created_at)}</strong></div>
          ${report.owner_name ? `<div class="meta-row">${icon("user", 17)} <span>Reporter</span> <strong>${esc(report.owner_name)}</strong></div>` : ""}
        </div>

        ${report.is_mine ? `<div class="notice brand">${icon("shield", 17)}<span>This is your report. Mark it as returned once you have the item back.</span></div>` : `<div class="notice">${icon("lock", 17)}<span>Reporter details and AI matches are private. An administrator verifies ownership before an item is returned.</span></div>`}

        <div class="detail-actions">
          ${report.is_mine && ["open", "matched"].includes(report.status) ? `<button class="btn primary" type="button" data-action="mark-returned" data-id="${report.id}">${icon("check", 16)} Mark as returned</button>` : ""}
          ${isAdmin() ? `<button class="btn danger" type="button" data-action="delete-report" data-id="${report.id}">${icon("trash", 16)} Remove report</button>` : ""}
          <a class="btn ghost" href="${isAdmin() ? "#/admin/reports" : "#/my-reports"}">Back to list</a>
        </div>
      </section>
    </div>

    ${canSeeMatches ? `
      <div class="section-head">
        <h2>${icon("sparkles", 19)} AI-suggested matches <span class="count">${report.matches.length}</span></h2>
      </div>
      <div class="notice warn" style="margin-bottom:16px">${icon("alert", 17)}<span>A similarity score is not proof of ownership. Verify the details, then approve the match as an administrator.</span></div>
      <div class="match-list">
        ${report.matches.length
          ? report.matches.map((match) => matchCard(match, isAdmin())).join("")
          : emptyState("search", "No matches yet", "This report is now being compared against new items. Check back soon.")}
      </div>` : ""}`;
}

/* ==========================================================================
   New report
   ========================================================================== */

async function newReport() {
  const cats = await ensureCategories();
  return `
    ${pageHead("Lost &amp; found", "Report an item", "A clear description helps the AI find a match — but a human always confirms ownership.")}

    <div class="dash-grid">
      <form data-form="report" enctype="multipart/form-data" novalidate>
        <div class="card form-card">
          <div class="form-section">
            <div>
              <div class="form-section-title">What happened?</div>
              <div class="form-section-sub">Choose one, then describe the item.</div>
            </div>

            <div class="type-picker">
              <div class="type-option lost">
                <input type="radio" id="type-lost" name="type" value="lost" checked>
                <label for="type-lost">
                  <span class="ticon">${icon("search", 19)}</span>
                  <span><strong>I lost something</strong><span>Report a missing item</span></span>
                </label>
              </div>
              <div class="type-option found">
                <input type="radio" id="type-found" name="type" value="found">
                <label for="type-found">
                  <span class="ticon">${icon("box", 19)}</span>
                  <span><strong>I found something</strong><span>Help return it to its owner</span></span>
                </label>
              </div>
            </div>

            <div class="form-grid">
              <div class="field span-2">
                <label for="report-title">Item title</label>
                <input class="input" id="report-title" name="title" required minlength="3" maxlength="160" placeholder="e.g. Black iPhone 13 with blue case">
              </div>
              <div class="field">
                <label for="report-category">Category</label>
                <select class="select" id="report-category" name="category">${options(cats.item_categories, "Electronics")}</select>
              </div>
              <div class="field">
                <label for="report-date">Date</label>
                <input class="input" id="report-date" name="date" type="date" value="${todayISO()}" max="${todayISO()}" required>
              </div>
              <div class="field span-2">
                <label for="report-location">Location</label>
                <input class="input" id="report-location" name="location" required minlength="2" maxlength="160" placeholder="e.g. Main Library, second floor">
              </div>
              <div class="field span-2">
                <label for="report-description">Description <span class="hint" data-report-count>0 / 2000</span></label>
                <textarea class="textarea" id="report-description" name="description" required minlength="10" maxlength="2000" placeholder="Colour, brand, distinguishing marks, what was inside…"></textarea>
                <span class="hint">Never include phone numbers, ID numbers or other private contact details.</span>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div>
              <div class="form-section-title">Photo (optional)</div>
              <div class="form-section-sub">A photo helps other students recognise the item.</div>
            </div>
            <div class="photo-field">
              <input type="file" id="report-photo" name="image" accept="image/png,image/jpeg,image/webp" data-photo-input hidden>
              <label class="dropzone" for="report-photo" data-photo-preview>
                <span class="dz-icon">${icon("camera", 21)}</span>
                <strong>Add a photo</strong>
                <span>JPG, PNG or WebP · up to 5 MB</span>
              </label>
            </div>
          </div>

          <div class="form-actions">
            <a class="btn ghost" href="#/browse">Cancel</a>
            <button class="btn primary" type="submit">${icon("sparkles", 16)} Submit report</button>
          </div>
        </div>
      </form>

      <div class="side-tips">
        <section class="card tip-card">
          <h3>${icon("sparkles", 17)} Better descriptions, better matches</h3>
          <ul>
            <li>Include colour, brand and any unique marks.</li>
            <li>Mention what was inside bags or cases.</li>
            <li>Use the exact place: “Main Library entrance”, not “campus”.</li>
          </ul>
        </section>
        <section class="card tip-card">
          <h3>${icon("shield", 17)} How matching works</h3>
          <p>Your report is compared with opposite-type reports using text similarity, category and location. You will see a ranked list with reasons, and an administrator approves any match before handover.</p>
        </section>
        <div class="notice warn">${icon("alert", 16)}<span>Do not share phone numbers or personal contact details in public item descriptions.</span></div>
      </div>
    </div>`;
}

/* ==========================================================================
   Complaints
   ========================================================================== */

function complaintCard(complaint) {
  return `<a class="card complaint-card" href="#/complaints/${complaint.id}">
    <div class="complaint-top">
      <span class="complaint-ref">${esc(complaint.reference)}</span>
      <div class="row">${priorityBadge(complaint.priority)}${complaintStatusBadge(complaint.status)}</div>
    </div>
    <h3>${esc(complaint.description)}</h3>
    <div class="complaint-meta">
      <span class="chip">${complaintEmoji(complaint.category)} ${esc(complaint.category)}</span>
      <span class="chip">${esc(complaint.department)}</span>
    </div>
    <div class="complaint-foot">
      <span class="tiny muted">${timeAgo(complaint.created_at)}</span>
      <span class="link">View details ${icon("chevron", 14)}</span>
    </div>
  </a>`;
}

function statusSteps(status) {
  const order = ["Received", "In Progress", "Resolved"];
  const index = order.indexOf(status);
  return `<div class="steps">${order.map((step, i) => `
    <div class="step ${i < index ? "done" : i === index ? "current" : ""}">${step}</div>`).join("")}</div>`;
}

async function complaints(params) {
  const status = params.get("status") || "";
  const items = await api.listComplaints({ status });

  return `
    ${pageHead(
      "Complaint management",
      "Your complaints",
      "Report campus issues and follow them from received to resolved.",
      `<a class="btn primary" href="#/complaints/new">${icon("plus", 16)} New complaint</a>`
    )}

    <div class="filter-bar">
      <div class="segmented">
        <a class="${!status ? "active" : ""}" href="#/complaints">All</a>
        ${["Received", "In Progress", "Resolved"].map((value) => `<a class="${status === value ? "active" : ""}" href="#/complaints${buildQuery({ status: value })}">${value}</a>`).join("")}
      </div>
      <span class="tiny muted" style="margin-left:auto">${items.length} complaint${items.length === 1 ? "" : "s"}</span>
    </div>

    ${items.length
      ? `<div class="complaint-list">${items.map(complaintCard).join("")}</div>`
      : emptyState("clipboard", "No complaints here", status ? "No complaints with this status." : "Seen something broken, unsafe or unfair? Submit a complaint and the right department will be notified.", `<a class="btn primary" href="#/complaints/new">${icon("plus", 16)} Submit a complaint</a>`)}`;
}

function aiPanelIdle() {
  return `<div class="ai-panel">
    <div class="ai-head"><span class="ai-title">${icon("sparkles", 16)} AI triage</span><span class="ai-live">live</span></div>
    <p class="ai-empty">Describe the issue and we will suggest a category, department and priority. An administrator reviews every complaint.</p>
  </div>`;
}

function aiPanelResult(suggestion) {
  return `<div class="ai-panel">
    <div class="ai-head"><span class="ai-title">${icon("sparkles", 16)} AI triage</span><span class="ai-live">${esc(suggestion.source)}</span></div>
    <div class="ai-grid">
      <div class="ai-cell"><span>Category</span><strong>${esc(suggestion.category)}</strong></div>
      <div class="ai-cell"><span>Department</span><strong>${esc(suggestion.department)}</strong></div>
      <div class="ai-cell"><span>Priority</span><strong>${esc(suggestion.priority)}</strong></div>
    </div>
    <div class="confidence"><div class="bar"><i style="width:${Math.round(suggestion.confidence * 100)}%"></i></div><span>${Math.round(suggestion.confidence * 100)}% confidence</span></div>
    <p class="ai-reason">${esc(suggestion.reason)}</p>
    <p class="ai-reason">Suggestion only — an administrator can change it.</p>
  </div>`;
}

async function newComplaint() {
  return `
    ${pageHead("Complaints", "Submit a complaint", "Describe the issue once. We route it to the right department and show you the priority.")}

    <div class="dash-grid">
      <form data-form="complaint" enctype="multipart/form-data" novalidate>
        <div class="card form-card">
          <div class="form-section">
            <div>
              <div class="form-section-title">What needs attention?</div>
              <div class="form-section-sub">Be specific about the place and the problem.</div>
            </div>
            <div class="field">
              <label for="complaint-description">Description <span class="hint" data-char-count>0 / 4000</span></label>
              <textarea class="textarea" id="complaint-description" name="description" required minlength="10" maxlength="4000" placeholder="e.g. The water fountain on the second floor of the science building has been leaking for three days and the floor is slippery."></textarea>
            </div>
            <div id="ai-suggestion">${aiPanelIdle()}</div>
          </div>

          <div class="form-section">
            <div>
              <div class="form-section-title">Photo (optional)</div>
              <div class="form-section-sub">A photo helps the department understand the issue.</div>
            </div>
            <div class="photo-field">
              <input type="file" id="complaint-photo" name="image" accept="image/png,image/jpeg,image/webp" data-photo-input hidden>
              <label class="dropzone" for="complaint-photo" data-photo-preview>
                <span class="dz-icon">${icon("camera", 21)}</span>
                <strong>Add a photo</strong>
                <span>JPG, PNG or WebP · up to 5 MB</span>
              </label>
            </div>
          </div>

          <div class="form-actions">
            <a class="btn ghost" href="#/complaints">Cancel</a>
            <button class="btn primary" type="submit">${icon("clipboard", 16)} Submit complaint</button>
          </div>
        </div>
      </form>

      <div class="side-tips">
        <section class="card tip-card">
          <h3>${icon("sparkles", 17)} How AI triage works</h3>
          <p>A text classifier reads your description and suggests a category, a department and a priority. The suggestion is saved with the complaint so the administrator can accept or edit it.</p>
        </section>
        <section class="card tip-card">
          <h3>${icon("alert", 17)} Emergencies</h3>
          <p>This is not an emergency service. For immediate danger, fire or medical help, contact campus security or local emergency services first.</p>
        </section>
        <div class="notice">${icon("lock", 16)}<span>Complaints are private. Only you and administrators can see them.</span></div>
      </div>
    </div>`;
}

function adminComplaintForm(complaint, cats) {
  return `<form class="admin-complaint-form" data-form="admin-complaint" data-id="${complaint.id}">
    <label class="field"><span class="label">Category</span><select class="select" name="category">${options(cats.complaint_categories, complaint.category)}</select></label>
    <label class="field"><span class="label">Department</span><select class="select" name="department">${options(cats.departments, complaint.department)}</select></label>
    <label class="field"><span class="label">Priority</span><select class="select" name="priority">${options(cats.priorities, complaint.priority)}</select></label>
    <label class="field"><span class="label">Status</span><select class="select" name="status">${options(["Received", "In Progress", "Resolved"], complaint.status)}</select></label>
    <label class="field span-2"><span class="label">Admin note</span><textarea class="textarea" name="admin_note" maxlength="2000" placeholder="Visible to the student">${esc(complaint.admin_note || "")}</textarea></label>
    <div class="form-actions">
      <button class="btn primary sm" type="submit">Save changes</button>
      <button class="btn danger sm" type="button" data-action="delete-complaint" data-id="${complaint.id}">${icon("trash", 14)} Delete</button>
    </div>
  </form>`;
}

async function complaintDetail(id, params) {
  const [complaint, cats] = await Promise.all([api.getComplaint(id), ensureCategories()]);
  const created = params.get("created") === "1";

  return `
    <a class="back-link" href="${isAdmin() ? "#/admin/complaints" : "#/complaints"}">${icon("back", 16)} Back to complaints</a>
    ${created ? `<div class="notice success" style="margin-bottom:18px">${icon("check", 17)}<span><strong>Complaint submitted.</strong> Your reference is ${esc(complaint.reference)}. Keep it for follow-up.</span></div>` : ""}

    <div class="complaint-detail">
      <section class="card complaint-main">
        <div class="between">
          <span class="complaint-ref">${esc(complaint.reference)}</span>
          <div class="row">${priorityBadge(complaint.priority)}${complaintStatusBadge(complaint.status)}</div>
        </div>
        <h1>${esc(complaint.category)} complaint</h1>
        ${statusSteps(complaint.status)}
        <p class="complaint-body">${esc(complaint.description)}</p>
        ${complaint.image_url ? `<img src="${esc(complaint.image_url)}" alt="Complaint photo" style="border-radius:14px;max-height:340px;object-fit:cover;width:100%">` : ""}
        ${complaint.admin_note ? `<div class="admin-note mt-16"><strong>Administrator note</strong>${esc(complaint.admin_note)}</div>` : ""}
        <div class="detail-meta">
          <div class="meta-row">${icon("clipboard", 17)} <span>Department</span> <strong>${esc(complaint.department)}</strong></div>
          <div class="meta-row">${icon("clock", 17)} <span>Submitted</span> <strong>${timeAgo(complaint.created_at)}</strong></div>
          <div class="meta-row">${icon("refresh", 17)} <span>Last update</span> <strong>${timeAgo(complaint.updated_at)}</strong></div>
          ${complaint.owner_name ? `<div class="meta-row">${icon("user", 17)} <span>Student</span> <strong>${esc(complaint.owner_name)}</strong></div>` : ""}
        </div>
        ${isAdmin() ? adminComplaintForm(complaint, cats) : `<div class="notice">${icon("shield", 16)}<span>AI priority is a recommendation, not an emergency response. Contact campus security directly for immediate danger.</span></div>`}
      </section>

      <aside class="side-tips">
        <div class="ai-panel">
          <div class="ai-head"><span class="ai-title">${icon("sparkles", 16)} AI triage</span><span class="ai-live">${esc(complaint.ai_source)}</span></div>
          <div class="ai-grid">
            <div class="ai-cell"><span>Category</span><strong>${esc(complaint.category)}</strong></div>
            <div class="ai-cell"><span>Department</span><strong>${esc(complaint.department)}</strong></div>
            <div class="ai-cell"><span>Priority</span><strong>${esc(complaint.priority)}</strong></div>
          </div>
          <p class="ai-reason">Generated when the complaint was submitted. Administrators can override every field.</p>
        </div>
        <div class="notice">${icon("lock", 16)}<span>Only you and campus administrators can see this complaint.</span></div>
      </aside>
    </div>`;
}

/* ==========================================================================
   My reports
   ========================================================================== */

async function myReports() {
  const reports = await api.listReports({ mine: true });
  return `
    ${pageHead(
      "Your activity",
      "My reports",
      "Everything you have reported, with AI matches and current status.",
      `<a class="btn primary" href="#/reports/new">${icon("plus", 16)} Report an item</a>`
    )}
    ${reports.length
      ? `<div class="item-grid">${reports.map(reportCard).join("")}</div>`
      : emptyState("box", "No reports yet", "Report a lost or found item and we will start looking for matches.", `<a class="btn primary" href="#/reports/new">${icon("plus", 16)} Report an item</a>`)}`;
}

/* ==========================================================================
   Admin views
   ========================================================================== */

async function adminMatches(params) {
  const status = params.get("status") || "pending";
  const matches = await api.adminMatches(status);
  const tabs = [
    ["pending", "Pending"],
    ["approved", "Approved"],
    ["rejected", "Rejected"],
    ["", "All"],
  ];

  return `
    ${pageHead(
      "Administration",
      "AI match review",
      "Compare lost and found reports, then approve or reject each suggestion. Approval marks both reports as matched.",
      `<a class="btn ghost" href="#/admin">${icon("chart", 16)} Overview</a>`
    )}

    <div class="tabs">
      ${tabs.map(([value, label]) => `<a class="tab ${status === value ? "active" : ""}" href="#/admin/matches${buildQuery({ status: value })}">${label}</a>`).join("")}
    </div>

    ${matches.length
      ? `<div class="match-list">${matches.map((match) => matchCard(match, true)).join("")}</div>`
      : emptyState("check", "Nothing in this queue", status === "pending" ? "No AI matches are waiting for review." : "No matches with this status.")}`;
}

async function adminComplaints(params) {
  const status = params.get("status") || "";
  const [items, cats] = await Promise.all([api.listComplaints({ status }), ensureCategories()]);

  return `
    ${pageHead(
      "Administration",
      "Complaint queue",
      "Assign departments, adjust AI suggestions and move complaints through to resolution.",
      `<a class="btn ghost" href="#/admin">${icon("chart", 16)} Overview</a>`
    )}

    <div class="tabs">
      <a class="tab ${!status ? "active" : ""}" href="#/admin/complaints">All</a>
      ${["Received", "In Progress", "Resolved"].map((value) => `<a class="tab ${status === value ? "active" : ""}" href="#/admin/complaints${buildQuery({ status: value })}">${value}</a>`).join("")}
    </div>

    ${items.length ? `<div class="stack">${items.map((complaint) => `
      <details class="admin-row">
        <summary>
          <span class="thumb" style="width:42px;height:42px;border-radius:11px;display:grid;place-items:center;background:#eef2ff;font-size:20px;flex:none">${complaintEmoji(complaint.category)}</span>
          <span class="info" style="flex:1;min-width:0">
            <strong style="display:block;font-size:13px">${esc(complaint.reference)} · ${esc(complaint.category)}</strong>
            <span style="display:block;font-size:11.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(complaint.description)}</span>
          </span>
          <span class="row">${priorityBadge(complaint.priority)}${complaintStatusBadge(complaint.status)}</span>
        </summary>
        <div class="details-body">
          <p class="small" style="color:#374151;line-height:1.6">${esc(complaint.description)}</p>
          <div class="row tiny muted">
            <span>${icon("user", 13)} ${esc(complaint.owner_name || "Student")}</span>
            <span>${icon("clock", 13)} ${timeAgo(complaint.created_at)}</span>
          </div>
          ${complaint.image_url ? `<img src="${esc(complaint.image_url)}" alt="" style="max-height:220px;border-radius:12px;object-fit:cover">` : ""}
          ${adminComplaintForm(complaint, cats)}
        </div>
      </details>`).join("")}</div>`
      : emptyState("clipboard", "No complaints here", "No complaints match this filter.")}`;
}

async function adminReports() {
  const reports = await api.listReports({ limit: 200 });
  return `
    ${pageHead(
      "Administration",
      "All reports",
      "Every lost and found report on campus. Remove inappropriate or duplicate submissions when needed.",
      `<a class="btn ghost" href="#/admin/matches">${icon("sparkles", 16)} Review matches</a>`
    )}

    ${reports.length ? `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Item</th><th>Type</th><th>Category</th><th>Reporter</th><th>Status</th><th>Date</th><th></th></tr></thead>
          <tbody>
            ${reports.map((report) => `
              <tr>
                <td><a class="t-title" href="#/reports/${report.id}">${esc(report.title)}</a><div class="t-sub">${esc(report.location)}</div></td>
                <td><span class="badge ${esc(report.type)}">${esc(report.type)}</span></td>
                <td>${esc(report.category)}</td>
                <td>${esc(report.owner_name || "—")}</td>
                <td>${statusBadge(report.status)}</td>
                <td class="muted">${fmtDay(report.date)}</td>
                <td><button class="btn danger sm" type="button" data-action="delete-report" data-id="${report.id}" title="Remove report" aria-label="Remove ${esc(report.title)}">${icon("trash", 14)}</button></td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>` : emptyState("box", "No reports", "No lost or found reports have been submitted.")}`;
}

/* ==========================================================================
   Routing
   ========================================================================== */

const ROUTES = [
  { pattern: /^\/$/, view: () => dashboard(), nav: "home" },
  { pattern: /^\/browse$/, view: (params) => browse(params), nav: "browse" },
  { pattern: /^\/reports\/new$/, view: () => newReport(), nav: "report" },
  { pattern: /^\/reports\/(\d+)$/, view: (params, id) => reportDetail(id, params), nav: "browse" },
  { pattern: /^\/my-reports$/, view: () => myReports(), nav: "my" },
  { pattern: /^\/complaints$/, view: (params) => complaints(params), nav: "complaints" },
  { pattern: /^\/complaints\/new$/, view: () => newComplaint(), nav: "complaints" },
  { pattern: /^\/complaints\/(\d+)$/, view: (params, id) => complaintDetail(id, params), nav: "complaints" },
  { pattern: /^\/admin$/, view: () => adminDashboard(), nav: "admin", admin: true },
  { pattern: /^\/admin\/matches$/, view: (params) => adminMatches(params), nav: "admin-matches", admin: true },
  { pattern: /^\/admin\/complaints$/, view: (params) => adminComplaints(params), nav: "admin-complaints", admin: true },
  { pattern: /^\/admin\/reports$/, view: () => adminReports(), nav: "admin-reports", admin: true },
];

function parseHash() {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  return { path: path || "/", params: new URLSearchParams(query) };
}

let renderToken = 0;

async function render() {
  const token = ++renderToken;
  const { path, params } = parseHash();

  if (!state.user) {
    renderAuth(path === "/register" ? "register" : "login");
    return;
  }
  if (path === "/login" || path === "/register") {
    location.hash = "#/";
    return;
  }

  const route = ROUTES.find((candidate) => candidate.pattern.test(path));
  if (!route) {
    app.innerHTML = shell(`${pageHead("404", "Page not found", "That link does not exist.")}${emptyState("search", "Nothing here", "Head back to your dashboard.", `<a class="btn primary" href="#/">Go home</a>`)}`, "");
    return;
  }
  if (route.admin && !isAdmin()) {
    toast("Administrator access required.", "error");
    location.hash = "#/";
    return;
  }

  app.innerHTML = shell(loadingView(), route.nav);
  try {
    const matches = path.match(route.pattern);
    const html = await route.view(params, ...matches.slice(1));
    if (token !== renderToken) return;
    app.innerHTML = shell(html, route.nav);
    window.scrollTo(0, 0);
  } catch (error) {
    if (token !== renderToken) return;
    app.innerHTML = shell(errorView(error.message), route.nav);
  }
}

/* ==========================================================================
   Forms + actions
   ========================================================================== */

function formError(form, message) {
  let el = form.querySelector(".form-error");
  if (!el) {
    el = document.createElement("div");
    el.className = "form-error";
    form.prepend(el);
  }
  el.textContent = message;
}

async function withBusy(form, task) {
  const button = form.querySelector('button[type="submit"]');
  const original = button ? button.innerHTML : "";
  if (button) {
    button.disabled = true;
    button.innerHTML = '<span class="spin"></span> Working…';
  }
  try {
    await task();
  } finally {
    if (button && document.body.contains(button)) {
      button.disabled = false;
      button.innerHTML = original;
    }
  }
}

document.addEventListener("submit", async (event) => {
  const form = event.target;
  const kind = form.dataset.form;
  if (!kind) return;
  event.preventDefault();
  form.querySelector(".form-error")?.remove();

  try {
    await withBusy(form, async () => {
      if (kind === "login" || kind === "register") {
        const data = Object.fromEntries(new FormData(form));
        if (kind === "register" && data.password !== data.confirm) {
          throw new Error("The two passwords do not match.");
        }
        const body = await api[kind]({
          name: data.name,
          email: data.email,
          password: data.password,
        });
        session.token = body.access_token;
        state.user = body.user;
        state.categories = null;
        toast(`Welcome, ${body.user.name.split(" ")[0]}.`);
        if (location.hash === "#/") render();
        else location.hash = "#/";
        return;
      }

      if (kind === "report") {
        const data = await api.createReport(new FormData(form));
        const count = data.matches.length;
        toast(count ? `Report saved — ${count} possible match${count > 1 ? "es" : ""} found.` : "Report saved.");
        location.hash = `#/reports/${data.id}?created=1`;
        return;
      }

      if (kind === "complaint") {
        const data = await api.createComplaint(new FormData(form));
        toast(`Complaint submitted · ${data.reference}`);
        location.hash = `#/complaints/${data.id}?created=1`;
        return;
      }

      if (kind === "admin-complaint") {
        const payload = Object.fromEntries(new FormData(form));
        await api.updateComplaint(form.dataset.id, payload);
        toast("Complaint updated.");
        render();
        return;
      }
    });
  } catch (error) {
    formError(form, error.message);
    toast(error.message, "error");
  }
});

document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  const action = target.dataset.action;
  const id = target.dataset.id;

  if (action === "fill-demo") {
    const form = target.closest("form") || document.querySelector('form[data-form="login"]');
    if (!form) return;
    form.elements.email.value = target.dataset.email;
    form.elements.password.value = target.dataset.password;
    form.requestSubmit();
    return;
  }

  if (action === "logout") {
    session.clear();
    state.user = null;
    state.categories = null;
    if (location.hash === "#/login") render();
    else location.hash = "#/login";
    return;
  }

  if (action === "retry") {
    render();
    return;
  }

  try {
    if (action === "mark-returned") {
      await api.updateReport(id, { status: "returned" });
      toast("Marked as returned.");
      render();
    } else if (action === "approve-match" || action === "reject-match") {
      const status = action === "approve-match" ? "approved" : "rejected";
      await api.reviewMatch(id, status);
      toast(status === "approved" ? "Match approved — both reports marked as matched." : "Match rejected.");
      render();
    } else if (action === "delete-report") {
      if (!window.confirm("Remove this report? This cannot be undone.")) return;
      await api.deleteReport(id);
      toast("Report removed.");
      if (location.hash.startsWith("#/reports/")) location.hash = "#/admin/reports";
      else render();
    } else if (action === "delete-complaint") {
      if (!window.confirm("Remove this complaint? This cannot be undone.")) return;
      await api.deleteComplaint(id);
      toast("Complaint removed.");
      if (location.hash.startsWith("#/complaints/") && isAdmin()) location.hash = "#/admin/complaints";
      else render();
    } else if (action === "clear-photo") {
      const field = target.closest(".photo-field");
      const input = field.querySelector("[data-photo-input]");
      const label = field.querySelector("[data-photo-preview]");
      input.value = "";
      label.classList.remove("has-image");
      label.innerHTML = `<span class="dz-icon">${icon("camera", 21)}</span><strong>Add a photo</strong><span>JPG, PNG or WebP · up to 5 MB</span>`;
    }
  } catch (error) {
    toast(error.message, "error");
  }
});

document.addEventListener("change", (event) => {
  const input = event.target;
  if (input.matches("[data-photo-input]")) {
    const field = input.closest(".photo-field");
    const label = field.querySelector("[data-photo-preview]");
    const file = input.files && input.files[0];
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast("Use a JPG, PNG or WebP image.", "error");
      input.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast("Image must be under 5 MB.", "error");
      input.value = "";
      return;
    }
    label.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="Preview"><span class="hint">Click to replace</span>`;
    label.classList.add("has-image");
    return;
  }

  if (input.matches("[data-filter]")) {
    const params = new URLSearchParams(location.hash.split("?")[1] || "");
    if (input.value) params.set(input.dataset.filter, input.value);
    else params.delete(input.dataset.filter);
    const query = params.toString();
    location.hash = `#/browse${query ? `?${query}` : ""}`;
  }
});

document.addEventListener("input", (event) => {
  const input = event.target;

  if (input.matches("[data-filter-search]")) {
    const needle = input.value.trim().toLowerCase();
    let visible = 0;
    document.querySelectorAll("[data-item]").forEach((card) => {
      const match = !needle || card.dataset.text.includes(needle);
      card.classList.toggle("hidden", !match);
      if (match) visible += 1;
    });
    document.querySelector("[data-no-results]")?.classList.toggle("hidden", visible > 0);
    return;
  }

  if (input.id === "report-description") {
    const counter = document.querySelector("[data-report-count]");
    if (counter) counter.textContent = `${input.value.length} / 2000`;
    return;
  }

  if (input.id === "complaint-description") {
    const counter = document.querySelector("[data-char-count]");
    if (counter) counter.textContent = `${input.value.length} / 4000`;

    clearTimeout(liveClassify.timer);
    const text = input.value.trim();
    if (text.length < 12) {
      const box = document.getElementById("ai-suggestion");
      if (box) box.innerHTML = aiPanelIdle();
      return;
    }

    liveClassify.timer = setTimeout(async () => {
      const box = document.getElementById("ai-suggestion");
      if (!box) return;
      box.querySelector(".ai-panel")?.classList.add("loading");
      const sequence = ++liveClassify.sequence;
      try {
        const suggestion = await api.classify(text);
        if (sequence !== liveClassify.sequence) return;
        const current = document.getElementById("ai-suggestion");
        if (current) current.innerHTML = aiPanelResult(suggestion);
      } catch {
        const current = document.getElementById("ai-suggestion");
        current?.querySelector(".ai-panel")?.classList.remove("loading");
      }
    }, 650);
  }
});

const liveClassify = { timer: null, sequence: 0 };

/* ==========================================================================
   Boot
   ========================================================================== */

async function boot() {
  if (session.token) {
    try {
      state.user = await api.me();
    } catch {
      session.clear();
    }
  }

  window.addEventListener("hashchange", render);
  window.addEventListener("cc:unauthorized", () => {
    if (!state.user) return;
    state.user = null;
    state.categories = null;
    toast("Your session expired. Please sign in again.", "error");
    if (location.hash === "#/login") render();
    else location.hash = "#/login";
  });

  render();

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

boot();
