const TOKEN_KEY = "cc_token";

export const session = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  set token(value) {
    if (value) localStorage.setItem(TOKEN_KEY, value);
    else localStorage.removeItem(TOKEN_KEY);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
  },
};

async function request(path, { method = "GET", json, form, auth = true } = {}) {
  const headers = {};
  if (auth && session.token) headers.Authorization = `Bearer ${session.token}`;

  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = form;
  }

  let response;
  try {
    response = await fetch(path, { method, headers, body });
  } catch {
    throw new Error("Cannot reach the server. Make sure it is running.");
  }

  if (response.status === 401 && auth) {
    session.clear();
    window.dispatchEvent(new CustomEvent("cc:unauthorized"));
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    const detail = data && data.detail;
    if (typeof detail === "string") message = detail;
    else if (Array.isArray(detail)) {
      message = detail.map((item) => item.msg || "").filter(Boolean).join("; ") || message;
    }
    throw new Error(message);
  }
  return data;
}

function query(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" || value === false) return;
    search.set(key, value);
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const api = {
  register: (payload) => request("/api/auth/register", { method: "POST", json: payload, auth: false }),
  login: (payload) => request("/api/auth/login", { method: "POST", json: payload, auth: false }),
  me: () => request("/api/auth/me"),

  categories: () => request("/api/ai/categories"),
  classify: (description) => request("/api/ai/classify", { method: "POST", json: { description } }),

  listReports: (params) => request(`/api/reports${query(params)}`),
  getReport: (id) => request(`/api/reports/${id}`),
  createReport: (form) => request("/api/reports", { method: "POST", form }),
  updateReport: (id, payload) => request(`/api/reports/${id}`, { method: "PATCH", json: payload }),
  deleteReport: (id) => request(`/api/reports/${id}`, { method: "DELETE" }),

  listComplaints: (params) => request(`/api/complaints${query(params)}`),
  getComplaint: (id) => request(`/api/complaints/${id}`),
  createComplaint: (form) => request("/api/complaints", { method: "POST", form }),
  updateComplaint: (id, payload) => request(`/api/complaints/${id}`, { method: "PATCH", json: payload }),
  deleteComplaint: (id) => request(`/api/complaints/${id}`, { method: "DELETE" }),

  adminStats: () => request("/api/admin/stats"),
  adminMatches: (status) => request(`/api/admin/matches${query({ status })}`),
  reviewMatch: (id, status) => request(`/api/admin/matches/${id}`, { method: "PATCH", json: { status } }),
};
