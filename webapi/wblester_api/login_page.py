"""Branded HTML login page served by the API for browser traffic.

The page validates every textbox as the user types (yellow = warning,
red = error), shows inline suggestions, and on submit presents a summary
dialog listing all validation problems with correction hints before any
request is made. On success the JWT pair is stored in localStorage so the
/logs status console can reuse it.
"""

from .branding import LOGO_SVG

LOGIN_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in · WBLester &amp; O</title>
<style>
  :root { --ink:#0f1c17; --green:#2fa36b; --green-dark:#1b7a4f; --gold:#d9a441; --paper:#f4f8f6;
          --warn:#b7791f; --warn-bg:#fffaf0; --err:#c0392b; --err-bg:#fdf1ef; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:'Segoe UI',system-ui,-apple-system,Arial,sans-serif;
         min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:
           radial-gradient(1100px 500px at 85% -10%, rgba(47,163,107,.16), transparent 60%),
           radial-gradient(900px 420px at -10% 110%, rgba(217,164,65,.14), transparent 55%),
           var(--paper);
         color:var(--ink); padding:24px 12px; }
  .card { width:min(560px, 100%); background:#fff; border-radius:20px;
          box-shadow:0 24px 60px -24px rgba(15,28,23,.35); overflow:hidden;
          border:1px solid rgba(15,28,23,.06); }
  .brand { background:linear-gradient(135deg, var(--green) 0%, #14563c 100%);
           padding:34px 34px 26px; color:#fff; }
  .mark { display:flex; align-items:center; gap:14px; }
  .logo { width:52px; height:52px; flex:none; }
  h1 { font-size:1.45rem; letter-spacing:.2px; }
  h1 span { color:var(--gold); }
  .tag { margin-top:10px; font-size:.86rem; opacity:.85; }
  form { padding:30px 34px 32px; display:grid; gap:16px; }
  label { font-size:.78rem; font-weight:600; text-transform:uppercase;
          letter-spacing:.08em; color:#5b6b64; display:block; margin-bottom:6px; }
  input { width:100%; padding:13px 15px; border:1.5px solid #dde5e1; border-radius:11px;
          font-size:.97rem; outline:none; transition:border-color .15s, background .15s; }
  input:focus { border-color:var(--green); box-shadow:0 0 0 3px rgba(47,163,107,.14); }
  input.warn { border-color:var(--warn); background:var(--warn-bg); }
  input.err  { border-color:var(--err); background:var(--err-bg); }
  .hint { font-size:.78rem; min-height:1.05em; margin-top:5px; }
  .hint.warn { color:var(--warn); } .hint.err { color:var(--err); }
  button { margin-top:4px; padding:14px; border:0; border-radius:11px; cursor:pointer;
           font-size:1rem; font-weight:700; color:#fff;
           background:linear-gradient(135deg, var(--green), var(--green-dark));
           box-shadow:0 10px 22px -10px rgba(27,122,79,.75); transition:transform .12s; }
  button:hover { transform:translateY(-1px); }
  button:disabled { opacity:.6; transform:none; cursor:wait; }
  #msg { font-size:.88rem; min-height:1.3em; text-align:center; }
  .ok { color:var(--green-dark); } .err { color:var(--err); }
  footer { padding:0 34px 26px; text-align:center; font-size:.78rem; color:#8a968f; }
  footer a { color:var(--green-dark); font-weight:600; text-decoration:none; }
  code { background:#eef3f1; padding:2px 6px; border-radius:6px; }

  /* Summary dialog */
  #overlay { position:fixed; inset:0; background:rgba(15,28,23,.45);
             display:flex; align-items:center; justify-content:center; z-index:50;
             opacity:0; pointer-events:none; transition:opacity .18s; }
  #overlay.show { opacity:1; pointer-events:auto; }
  .dialog { width:min(480px, calc(100vw - 40px)); background:#fff; border-radius:16px;
            box-shadow:0 30px 70px -20px rgba(15,28,23,.5); overflow:hidden;
            transform:translateY(10px); transition:transform .18s; }
  #overlay.show .dialog { transform:translateY(0); }
  .dialog header { background:linear-gradient(135deg,var(--err),#a93226);
                   color:#fff; padding:16px 20px; font-weight:700; }
  .dialog header.warn-only { background:linear-gradient(135deg,var(--warn),#9c6b1a); }
  .dialog ul { list-style:none; padding:18px 20px; max-height:46vh; overflow:auto; }
  .dialog li { font-size:.86rem; padding:9px 12px; border-radius:9px; margin-bottom:8px; }
  .dialog li b { display:block; margin-bottom:2px; }
  .dialog li.err { background:var(--err-bg); color:#7c2d22; }
  .dialog li.warn { background:var(--warn-bg); color:#7a5518; }
  .dialog .actions { display:flex; gap:10px; padding:0 20px 20px; }
  .dialog .actions button { flex:1; margin-top:0; }
  .btn-ghost { background:#eef3f1 !important; color:#41534a !important;
               box-shadow:none !important; }
</style>
</head>
<body>
  <main class="card">
    <div class="brand">
      <div class="mark">{logo}
        <h1>WBLester <span>&amp;</span> O</h1></div>
      <p class="tag">Agriculture &middot; Real Estate &middot; Natural Resources &amp; Energy</p>
    </div>
    <form id="f" autocomplete="off" novalidate>
      <div>
        <label for="u">Username</label>
        <input id="u" placeholder="e.g. wblester" spellcheck="false">
        <div class="hint" id="uh"></div>
      </div>
      <div>
        <label for="p">Password</label>
        <input id="p" type="password" placeholder="••••••••">
        <div class="hint" id="ph"></div>
      </div>
      <button type="submit">Sign in</button>
      <div id="msg"></div>
    </form>
    <footer>Manage content from the WBLESTER console at <code>/admin</code>
      &middot; <a href="/logs">System status</a></footer>
  </main>

  <div id="overlay" role="dialog" aria-modal="true">
    <div class="dialog">
      <header id="dlg-title">Please fix these issues</header>
      <ul id="dlg-list"></ul>
      <div class="actions">
        <button type="button" class="btn-ghost" id="dlg-cancel">Close</button>
        <button type="button" id="dlg-proceed" hidden>Continue anyway</button>
      </div>
    </div>
  </div>

<script>
const f = document.getElementById('f'), msg = document.getElementById('msg');
const u = document.getElementById('u'), p = document.getElementById('p');
const uh = document.getElementById('uh'), ph = document.getElementById('ph');
const overlay = document.getElementById('overlay');

/* ---------- per-field validation ---------- */
const RULES = {
  u: {
    validate(v) {
      if (!v.trim()) return ['error', 'Username is required.',
                             'Enter the username assigned to you (e.g. wblester).'];
      if (v.trim().length < 3) return ['error', 'Username is too short.',
                             'Usernames have at least 3 characters.'];
      if (/\\s/.test(v)) return ['error', 'Username cannot contain spaces.', 'Remove the spaces.'];
      if (v !== v.toLowerCase()) return ['warning', 'Unusual capitalisation.',
                             'Usernames are normally lowercase — double-check yours.'];
      return null;
    }
  },
  p: {
    validate(v) {
      if (!v) return ['error', 'Password is required.', 'Type your password to continue.'];
      if (v.length < 8) return ['error', 'Password is too short.',
                            'Passwords must be at least 8 characters long.'];
      const weakBits = [];
      if (!/[0-9]/.test(v)) weakBits.push('a number');
      if (!/[^A-Za-z0-9]/.test(v)) weakBits.push('a symbol');
      if (!/[A-Z]/.test(v)) weakBits.push('an uppercase letter');
      if (weakBits.length) return ['warning', 'This password could be stronger.',
        'Consider adding ' + weakBits.join(', ') + '.'];
      return null;
    }
  }
};

let capsWarned = false;
function checkField(input, hint) {
  const result = RULES[input.id].validate(input.value);
  input.classList.remove('warn', 'err');
  hint.classList.remove('warn', 'err');
  if (!result) { hint.textContent = ''; return null; }
  const [kind, title, tip] = result;
  input.classList.add(kind === 'error' ? 'err' : 'warn');
  hint.classList.add(kind);
  hint.textContent = kind === 'error' ? title : title + ' ' + tip;
  return result;
}

function attach(input, hint) {
  input.addEventListener('input', () => checkField(input, hint));
  input.addEventListener('blur', () => checkField(input, hint));
  input.addEventListener('keyup', e => {
    const on = e.getModifierState && e.getModifierState('CapsLock');
    if (on && !capsWarned) {
      capsWarned = true;
      hint.classList.add('warn'); hint.textContent =
        'Caps Lock is on — passwords are case-sensitive.';
    } else if (!on && capsWarned && input === p &&
               !p.classList.contains('err')) {
      capsWarned = false; hint.textContent = ''; hint.classList.remove('warn');
    }
  });
}
attach(u, uh); attach(p, ph);

/* ---------- summary dialog ---------- */
function showSummary(entries) {
  const errors = entries.filter(e => e.kind === 'error');
  const warnings = entries.filter(e => e.kind === 'warning');
  const title = document.getElementById('dlg-title');
  title.textContent = errors.length ? 'Fix ' + errors.length + ' issue' +
    (errors.length > 1 ? 's' : '') + ' to sign in'
    : 'Review ' + warnings.length + ' suggestion' + (warnings.length > 1 ? 's' : '');
  title.classList.toggle('warn-only', errors.length === 0);

  document.getElementById('dlg-list').innerHTML = entries.map(e =>
    '<li class="' + e.kind + '"><b>' + esc(e.title) + '</b>' + esc(e.tip) +
    '</li>').join('');

  const proceed = document.getElementById('dlg-proceed');
  proceed.hidden = errors.length > 0;   /* warnings may be overridden */
  overlay.classList.add('show');
  return new Promise(resolve => {
    document.getElementById('dlg-cancel').onclick = () => {
      overlay.classList.remove('show'); resolve(false);
    };
    proceed.onclick = () => { overlay.classList.remove('show'); resolve(true); };
    overlay.onclick = e => {
      if (e.target === overlay) { overlay.classList.remove('show'); resolve(false); }
    };
  });
}

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function doLogin() {
  const btn = f.querySelector('button[type=submit]');
  btn.disabled = true; msg.className = ''; msg.textContent = '';
  try {
    const r = await fetch('/auth/login', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: u.value.trim(), password: p.value }) });
    const d = await r.json();
    if (r.ok && d.user) {
      try {
        localStorage.setItem('wblester_access', d.access_token || '');
        localStorage.setItem('wblester_refresh', d.refresh_token || '');
        localStorage.setItem('wblester_user', JSON.stringify(d.user || {}));
      } catch (e) { /* storage unavailable — session-only use */ }
      const superuser = d.user.role_name === 'superuser';
      msg.className = 'ok';
      msg.innerHTML = 'Welcome, ' + esc(d.user.username || 'user') +
        ' (' + esc(d.user.role_name || 'member') + ').<br>' +
        (superuser
          ? '<a href="/logs" style="color:#1b7a4f;font-weight:700">Open system status →</a>'
          : 'Open the console app at /admin to continue.');
      setTimeout(() => { if (superuser) location.href = '/logs'; }, 900);
    } else {
      msg.className = 'err';
      msg.textContent = d.message || 'Sign-in failed';
    }
  } catch (err) { msg.className = 'err'; msg.textContent = 'Network error'; }
  finally { btn.disabled = false; }
}

f.addEventListener('submit', async (e) => {
  e.preventDefault();
  const results = [
    { field: 'Username', ...pack(checkField(u, uh)) },
    { field: 'Password', ...pack(checkField(p, ph)) },
  ].filter(x => x.kind);
  if (results.length) {
    const ok = await showSummary(results.map(r => ({
      kind: r.kind,
      title: r.field + ': ' + r.title,
      tip: r.tip,
    })));
    if (!ok) return;
  }
  doLogin();
});

function pack(result) {
  if (!result) return {};
  return { kind: result[0], title: result[1], tip: result[2] };
}
</script>
</body>
</html>
""".replace("{logo}", LOGO_SVG)
