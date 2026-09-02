/* AJAX layer — fetch-based with JWT access/refresh handling for admin calls. */

const TOKENS_KEY = 'wb_tokens';
let memTokens = null;

export function getTokens() {
  if (memTokens) return memTokens;
  try {
    memTokens = JSON.parse(localStorage.getItem(TOKENS_KEY) || 'null');
  } catch {
    memTokens = null;
  }
  return memTokens;
}

export function setTokens(tokens) {
  memTokens = tokens;
  if (tokens) localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
  else localStorage.removeItem(TOKENS_KEY);
}

async function parseBody(res) {
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return text;
  }
}

/** Low-level request. Returns {ok, status, data}. */
export async function request(url, options = {}, retried = false) {
  const headers = { ...(options.headers || {}) };
  const tokens = getTokens();
  if (tokens?.accessToken && !options.anon) {
    headers.Authorization = `Bearer ${tokens.accessToken}`;
  }
  let body = options.body;
  if (body !== undefined && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, { ...options, headers, body });
  } catch (err) {
    return { ok: false, status: 0, data: { message: String(err) } };
  }
  const data = await parseBody(res);

  // Access token expired: try one silent refresh, then replay the call.
  if (res.status === 401 && !retried && !options.anon && tokens?.refreshToken) {
    const refreshed = await refreshTokens();
    if (refreshed) return request(url, options, true);
    setTokens(null);
  }
  return { ok: res.ok, status: res.status, data };
}

async function refreshTokens() {
  const tokens = getTokens();
  if (!tokens?.refreshToken) return false;
  let res;
  try {
    res = await fetch('/auth/refresh', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${tokens.refreshToken}`,
        'Content-Type': 'application/json',
      },
    });
  } catch {
    return false;
  }
  if (!res.ok) return false;
  const next = await parseBody(res);
  if (!next?.access_token) return false;
  setTokens({
    accessToken: next.access_token,
    refreshToken: next.refresh_token || tokens.refreshToken,
  });
  return true;
}

export async function login(username, password) {
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const data = await parseBody(res);
  if (res.ok && data?.access_token) {
    setTokens({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    });
    return { ok: true };
  }
  return { ok: false, message: data?.message || 'Login failed' };
}

export function logout() {
  setTokens(null);
}

/* Convenience wrappers ---------------------------------------------------- */
export const GET = (url, opts) => request(url, { method: 'GET', ...opts });
export const POST = (url, body, opts) =>
  request(url, { method: 'POST', body, ...opts });
export const PUT = (url, body, opts) =>
  request(url, { method: 'PUT', body, ...opts });
export const DEL = (url, opts) => request(url, { method: 'DELETE', ...opts });

/* Generic CRUD against /cpanel/jwt/data/<table> ---------------------------- */

/* The data endpoints serialise documents snake_case; the admin UI speaks
   camelCase (mirroring /public/content). Normalise top-level keys only —
   nested values such as content_json.blocks keep their own key style. */
function camelizeKey(key) {
  if (key.startsWith('_')) return key;
  return key.replace(/_([a-z0-9])/g, (_, c) => c.toUpperCase());
}

function camelizeRow(row) {
  if (!row || typeof row !== 'object' || Array.isArray(row)) return row;
  const out = {};
  for (const [k, v] of Object.entries(row)) {
    const key = camelizeKey(k);
    if (!key.startsWith('_')) out[key] = v;
  }
  return out;
}

export const dataTable = {
  list: async (table) => {
    const res = await GET(`/cpanel/jwt/data/${table}`);
    const rows = res.ok ? res.data?.[table] : null;
    if (Array.isArray(rows)) res.data = { [table]: rows.map(camelizeRow) };
    return res;
  },
  upsert: (table, record) => POST(`/cpanel/jwt/data/${table}`, record),
  remove: (table, id) => DEL(`/cpanel/jwt/data/${table}/${id}`),
};

export function postContactForm(payload) {
  return POST('/public/contact', payload, { anon: true });
}
