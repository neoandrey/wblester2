"""Branded system-status page rendered by the API.

GET /logs serves this shell. The JavaScript inside authenticates against
/cpanel/jwt/diagnostics using the JWT stored by the login page and renders:

- a service card per dependent service (API / MongoDB / Redis) coloured by
  status (green up, amber not-configured, red down),
- warning/error counters,
- the most recent log lines with WARNING highlighted amber and ERROR red,
  plus All / Warnings / Errors filters and an auto-refresh toggle.
"""

from .branding import LOGO_SVG

LOGS_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>System status · WBLester &amp; O</title>
<style>
  :root { --ink:#0f1c17; --green:#2fa36b; --green-dark:#1b7a4f; --gold:#d9a441;
          --paper:#f4f8f6; --amber:#b7791f; --red:#c0392b; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:'Segoe UI',system-ui,-apple-system,Arial,sans-serif;
         background:
           radial-gradient(1100px 480px at 90% -10%, rgba(47,163,107,.14), transparent 60%),
           radial-gradient(900px 420px at -10% 110%, rgba(217,164,65,.12), transparent 55%),
           var(--paper);
         color:var(--ink); min-height:100vh; padding:26px 16px 60px; }
  .wrap { max-width:1060px; margin:0 auto; }
  header.bar { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:20px; }
  .logo { width:44px; height:44px; flex:none; }
  h1 { font-size:1.3rem; } h1 span { color:var(--gold); }
  .sub { font-size:.85rem; color:#5f6f67; margin-top:2px; }
  .spacer { flex:1; }
  button.chip { border:1.5px solid #d7e2dc; background:#fff; color:#41534a;
                padding:7px 14px; border-radius:999px; cursor:pointer;
                font-size:.82rem; font-weight:600; }
  button.chip.active { border-color:var(--green); color:var(--green-dark); background:#e9f7ef; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
           gap:14px; margin-bottom:18px; }
  .svc { background:#fff; border-radius:14px; padding:16px 18px;
         border:1px solid rgba(15,28,23,.07); box-shadow:0 12px 28px -18px rgba(15,28,23,.35); }
  .svc .name { font-weight:700; font-size:.95rem; display:flex; align-items:center; gap:8px; }
  .dot { width:10px; height:10px; border-radius:50%; background:#9aa8a1; flex:none; }
  .svc.up .dot { background:#22a55e; box-shadow:0 0 0 4px rgba(34,165,94,.15); }
  .svc.down .dot { background:#e04a3a; box-shadow:0 0 0 4px rgba(224,74,58,.15); }
  .svc.not-configured .dot { background:var(--gold); box-shadow:0 0 0 4px rgba(217,164,65,.15); }
  .svc .detail { margin-top:6px; font-size:.8rem; color:#66756d; word-break:break-word; }
  .counts { display:flex; gap:10px; align-items:center; margin-bottom:14px; flex-wrap:wrap; }
  .pill { font-size:.78rem; font-weight:700; padding:5px 12px; border-radius:999px; }
  .pill.err { background:#fdecea; color:var(--red); }
  .pill.warn { background:#fdf6e3; color:var(--amber); }
  .pill.ok { background:#e9f7ef; color:var(--green-dark); }
  table { width:100%; border-collapse:collapse; background:#fff; border-radius:14px;
          overflow:hidden; border:1px solid rgba(15,28,23,.07);
          box-shadow:0 14px 30px -22px rgba(15,28,23,.4); }
  th { text-align:left; font-size:.72rem; text-transform:uppercase; letter-spacing:.08em;
       color:#69786f; padding:11px 14px; background:#f0f5f2; }
  td { padding:8px 14px; font-size:.8rem; border-top:1px solid #eef3f0;
       vertical-align:top; font-family:Consolas,Menlo,monospace; word-break:break-word; }
  td.lvl { font-weight:800; white-space:nowrap; }
  tr.ERROR td { background:#fdf1ef; } tr.ERROR td.lvl { color:var(--red); }
  tr.WARNING td { background:#fffaf0; } tr.WARNING td.lvl { color:var(--amber); }
  tr.CRITICAL td { background:#fdf1ef; } tr.CRITICAL td.lvl { color:var(--red); }
  .empty { padding:26px; text-align:center; color:#7b897f; font-size:.9rem; }
  #gate { max-width:430px; margin:12vh auto; background:#fff; padding:28px;
          border-radius:14px; text-align:center; border:1px solid rgba(15,28,23,.07); }
  #gate a { color:var(--green-dark); font-weight:700; }
</style>
</head>
<body>
<div class="wrap">
  <header class="bar">
    {logo}
    <div><h1>WBLester <span>&amp;</span> O — System status</h1>
      <div class="sub" id="generated">Loading…</div></div>
    <div class="spacer"></div>
    <button class="chip active" data-filter="all">All</button>
    <button class="chip" data-filter="WARNING">Warnings</button>
    <button class="chip" data-filter="ERROR">Errors</button>
    <button class="chip" id="refresh">Auto ✓</button>
  </header>

  <div class="cards" id="services"></div>
  <div class="counts" id="counts"></div>
  <table id="logtable">
    <thead><tr><th style="width:150px">Time</th><th style="width:84px">Level</th>
      <th>Message</th></tr></thead>
    <tbody id="rows"></tbody>
  </table>
  <div class="empty" id="empty" hidden>No log lines match this filter.</div>
</div>

<div id="gate" hidden>
  <p><strong>Administrator sign-in required.</strong></p>
  <p style="margin-top:10px;font-size:.88rem;color:#66756d">
    This console exposes application logs and service health.
    Sign in with an administrator account to continue.</p>
  <p style="margin-top:16px"><a href="/login">Go to sign-in →</a></p>
</div>

<script>
let filter = 'all', auto = true, timer = null;

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function load() {
  const token = localStorage.getItem('wblester_access');
  if (!token) { gate(true); return; }
  let data;
  try {
    const r = await fetch('/cpanel/jwt/diagnostics', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (r.status === 401) { gate(true); return; }
    if (!r.ok) throw new Error('HTTP ' + r.status);
    data = await r.json();
  } catch (err) {
    document.getElementById('generated').textContent = 'Failed to load diagnostics: ' + err.message;
    return;
  }
  gate(false);
  render(data);
}

function gate(showLogin) {
  document.getElementById('gate').hidden = !showLogin;
  document.querySelector('.bar').style.display = showLogin ? 'none' : '';
  document.getElementById('services').style.display = showLogin ? 'none' : '';
  document.getElementById('logtable').style.display = showLogin ? 'none' : '';
}

function render(d) {
  document.getElementById('generated').textContent =
    'Last checked ' + (d.generated_at || '').replace('T', ' ') + 'Z · overall: ' + d.overall;

  document.getElementById('services').innerHTML = (d.services || []).map(s =>
    '<div class="svc ' + esc(s.status) + '"><div class="name"><span class="dot"></span>' +
    esc(s.name) + '</div><div class="detail">' + esc(s.detail) + '</div></div>'
  ).join('');

  const counts = d.counts || {};
  document.getElementById('counts').innerHTML =
    '<span class="pill ok">' + ((d.logs || []).length) + ' lines</span>' +
    '<span class="pill warn">' + (counts.warning || 0) + ' warnings</span>' +
    '<span class="pill err">' + (counts.error || 0) + ' errors</span>';

  const rows = (d.logs || []).filter(r =>
    filter === 'all' ? true :
    filter === 'WARNING' ? r.level === 'WARNING' :
    (r.level === 'ERROR' || r.level === 'CRITICAL'));

  document.getElementById('rows').innerHTML = rows.map(r =>
    '<tr class="' + esc(r.level) + '"><td>' + esc(r.ts) + '</td>' +
    '<td class="lvl">' + esc(r.level) + '</td>' +
    '<td>' + esc((r.logger ? '[' + r.logger + '] ' : '') + r.message) + '</td></tr>'
  ).join('');
  document.getElementById('empty').hidden = rows.length > 0;
}

document.querySelectorAll('button.chip[data-filter]').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('button.chip[data-filter]').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    filter = b.dataset.filter;
    load();
  });
});

document.getElementById('refresh').addEventListener('click', function () {
  auto = !auto;
  this.textContent = auto ? 'Auto ✓' : 'Auto ✗';
  this.classList.toggle('active', auto);
  if (auto) start(); else clearInterval(timer);
});

function start() { timer = setInterval(load, 10000); }

load();
start();
</script>
</body>
</html>
""".replace("{logo}", LOGO_SVG)
