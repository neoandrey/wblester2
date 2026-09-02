# WBLester & O — Content Management System

A complete, self-hosted content-management platform for **WBLester & O**, a
single marketing website that covers three business verticals in one brand:

- **Agriculture**
- **Real Estate**
- **Natural Resources & Energy (production and sales)**

WBLester & O ships as three cooperating components on one origin:

| Component | What it is | Users |
| --- | --- | --- |
| **Frontend** | The public marketing website (`/`) | Visitors |
| **Backend** | The admin portal (`/admin`) | Administrators & superusers |
| **WebApi** | The Flask JSON API + worker | Automation (no UI) |

Every change an administrator makes — a new page, a hidden category, a hero
photo, a contact detail — is stored once in **MongoDB** through the WebApi and
reaches the public website automatically within one refresh cycle. No rebuilds,
no redeploys, no manual cache flushes.

---

## 1. About the application

WBLester & O is a **content-management system (CMS)** that lets a non-technical
team run a professional, marketing-grade website entirely from a browser.

- The **public site** presents the brand across the three verticals. Its menus,
  sub-menus, pages, banners, service cards, statistics, galleries,
  testimonials, partners strip and contact forms are all *content* stored in the
  database and rendered from structured blocks — nothing is hard-coded in the
  page markup.
- The **admin portal** is where editors manage that content: pages, the
  category/menu tree, the mailbox, outgoing mail, users, roles and permissions,
  uploaded images and files, site settings, scheduled events, background jobs,
  logs, and a full audit trail.
- The **WebApi** is the single bridge between the two browser applications and
  every backing service (database, cache, file storage, mail, scheduling).

The design language blends **green, gold and blue** with a leaf-and-vine emblem —
an identity that speaks to agriculture, energy and the created environment. The
public layout is fully responsive (desktop, tablet, mobile) and inspired by the
Garden-Hub style.

---

## 2. Features at a glance

**Public website**
- Responsive, CMS-driven layout with animated banners, service grids, feature
  boxes, process steps, parallax statistics, filterable galleries, testimonials
  and a partners strip.
- Dynamic menus and sub-menus driven by categories and pages.
- Breadcrumbs, nested sub-page navigation and per-page structured content.
- Contact / quote forms that post straight into the admin mailbox and notify the
  configured mailing list by email.
- Offline-first: content is cached in the browser (IndexedDB), shown instantly,
  and re-synchronised in the background.

**Admin portal**
- Dashboard with at-a-glance statistics (content, users, messages, service
  health, storage).
- Full **pages** editor with structured per-block forms, page hierarchy,
  show/hide toggles and a "set as home page" option.
- **Categories** manager (the menu tree), with show/hide and ordering.
- **Messages** mailbox: read, reply by email, mark read/replied/archived/trashed,
  and compose outgoing mail with templates and attachments.
- **Mail templates** library with create, edit, preview and search.
- **Site settings** (brand, contact details, map embed, mailing list, home page).
- **Users**, **Roles** and the **permissions matrix** (read / modify / create-delete).
- **Images** and **Files** libraries: upload (including drag-and-drop),
  thumbnails, copy URL, dependency-aware deletion.
- **Events** and **Jobs** (superuser): schedule and trigger mail campaigns,
  retry failed deliveries.
- **Logs** (superuser): a unified, SIEM-style view over frontend, backend and
  WebApi logs.
- **System** (superuser): live service diagnostics and log tail.
- **Audit trail**: every create / update / delete, with who did it, when, and
  the old versus new values.

**Security & account management**
- JWT authentication (access + refresh tokens) with silent session renewal.
- Role-based access control (RBAC) enforced **server-side**.
- Password strength rules, account lockout after failed attempts, unlock tool,
  mandatory password change on first login, and a welcome email when an account
  is created.

---

## 3. Tools used to build it

| Layer | Technology |
| --- | --- |
| Admin portal | **Flutter** / Dart (web), `go_router`, `provider`, `shared_preferences`, `flutter_svg`, `http`, `web` |
| Public site | **Vanilla JavaScript** (ES modules) + HTML5 + CSS3 — no framework, no build step |
| WebApi | **Python 3 + Flask**, `mongoengine`, `Flask-JWT-Extended`, `flask-cors`, `Pillow`, `gunicorn` |
| Job worker | **RQ** (Redis Queue) for scheduled events and email delivery |
| Database | **MongoDB 7** |
| Cache / queue | **Redis 7** |
| Asset storage | Docker volume (`uploads_data`), images auto-processed into responsive variants |
| Web server | **nginx** (serves the admin bundle, reverse-proxies the API) |
| Orchestration | **Docker Compose** (five services) |
| Testing | `pytest` (API, mongomock/fakeredis/mocked SMTP), `flutter test` (admin portal) |

---

## 4. Architecture

```
Browser
  │
  ├── /admin/*  ──► nginx (backend container) ──► /usr/share/nginx/html/admin  (Flutter admin SPA)
  │                    │
  │                    └── everything else ──► webapi:5454  (Flask, gunicorn)
  │
  ├── /          ──► webapi ──► frontend/ (public SPA, static)
  │                    │
  └── JSON API calls ──► webapi (all /cpanel/jwt/* and /public/* routes)
                           │
        ┌──────────────────┼─────────────────────┬────────────────────┐
        ▼                  ▼                     ▼                    ▼
     MongoDB            Redis              uploads volume          SMTP (mail)
     (all content)     (cache / RQ)       (images & files)     (contact, replies,
                                                                 campaigns)
```

### The five Docker services

| Service | Image | Role |
| --- | --- | --- |
| `mongo` | `mongo:7` | Persists every collection |
| `redis` | `redis:7-alpine` | Cache + RQ queue for the worker |
| `webapi` | build `./webapi` | Flask app: JSON API, serves the public SPA, `/login`, `/logs`, `/uploads`; seeds the database on first boot |
| `worker` | build `./webapi` | RQ worker + scheduler loop (delivers scheduled events / email, retries) |
| `backend` | build `./backend` | Compiles the Flutter admin SPA on first build, serves it at `/admin/*`, and nginx-reverse-proxies whatever remains to `webapi` |

The `backend` nginx container is the **only published port** — a single `PORT`
(default `5454`) drives the host mapping, the nginx upstream and the gunicorn
bind, so the whole application lives on **one origin** and needs no CORS setup.

---

## 5. How the backend (admin portal) and frontend (public site) are connected

Both browser applications are **static front-ends that never talk to MongoDB,
Redis, the uploads volume or SMTP directly**. The Flask **WebApi** is the only
process allowed to touch the backing services, and both UIs talk to it over
HTTP on the same origin.

### Admin portal → WebApi (JSON, authenticated)

1. An administrator signs in at `/admin`. The portal sends `POST /auth/login`
   and stores the returned **access + refresh JWTs** in `localStorage`.
2. Every screen then performs direct JSON calls with the access token:
   `GET/POST/PUT/DELETE /cpanel/jwt/data/<Table>` (generic CRUD for pages,
   categories, users, roles, messages, mail templates …), plus specialised
   endpoints (`/cpanel/jwt/pages/tree`, `/roles/matrix`,
   `/scheduler/events|jobs`, `/settings`, `/diagnostics`, `/stats`,
   `/system-logs`, `/uploads`, `/messages/compose|reply|unread-count`).
3. When an access token expires the portal silently calls `/auth/refresh` with
   the refresh token and retries — so a session stays alive across reloads until
   it genuinely expires.
4. Every successful write is versioned and logged to the **AuditTrail**, and the
   change is immediately available to the API.

### WebApi → public site (anonymous snapshot)

1. The public site fetches `GET /public/content` — an **anonymous, read-only
   snapshot** of visible categories, visible pages (including their content
   blocks) and a whitelisted subset of settings.
2. It stores that snapshot in its **IndexedDB cache**, paints the page from the
   cache instantly (offline-first), then revalidates in the background: a
   60-second timer plus a re-check whenever the tab regains focus
   (stale-while-revalidate).
3. If the API says the content changed, the site re-renders in place.
   **The net effect: an edit made in the admin portal appears on the website
   within one sync cycle — no rebuild or refresh required.**
4. Contact and quote forms `POST /public/contact`; the API stores a `Message`
   (which appears in the admin mailbox) and mails the configured mailing list.
5. All images/files on the public site are served anonymously from `/uploads/…`
   (with `?size=…` variants generated server-side by Pillow).

### Security boundary

Browsing to a protected URL without a token redirects HTML navigations to
`/login`; JSON API clients receive a clean `401`. Role-based permissions are
enforced **inside the WebApi** for every `/cpanel/**` route, so the admin portal
only ever *shows* the actions a user is allowed to take.

---

## 6. Repository layout

| Path | Purpose |
| --- | --- |
| `frontend/` | Public website SPA (vanilla JS, no build step). Served at `/`. |
| `frontend/index.html` | SPA shell (fonts, SVG icon sprite, mount points) |
| `frontend/css/gardenhub.css` + `admin.css` | Public theme + legacy admin styles |
| `frontend/js/` | `db.js` (IndexedDB), `api.js` (fetch + JWT), `store.js` (revalidate engine), `ui.js` (DOM helpers), `views/public.js` (chrome + block renderer), `views/admin.js` (legacy admin views) |
| `frontend/assets/` | `logo.svg`, `user.jpg` |
| `backend/` | Flutter admin portal (web-only). Served at `/admin`. |
| `backend/lib/core/` | API client, session/auth store, helpers, status maps, theme, shared UI |
| `backend/lib/screens/` | login + shell, dashboard, pages (+ block editor), categories, messages, mail templates, settings, users, roles, images, files, events, jobs, logs, system, audit |
| `backend/lib/routing/app_router.dart` | Client router; `kSectionOrder` lists the sidebar sections |
| `backend/nginx/default.conf.template` | Serves `/admin/*` and proxies all else to `webapi` |
| `backend/Dockerfile` | Multi-stage: compiles the Flutter bundle, packages it into nginx |
| `webapi/` | Flask application + tests. |
| `webapi/wblester_api/app.py` | App factory: routing, SPA serving, MongoDB wiring |
| `webapi/wblester_api/blueprints/` | `auth`, `data`, `sync`, `pages`, `categories`, `settings`, `users`, `roles`, `permissions`, `messages`, `uploads`, `public`, `scheduler_admin`, `system_logs`, `stats`, `diagnostics` |
| `webapi/wblester_api/models/` | MongoEngine documents mirroring every collection |
| `webapi/wblester_api/utils/` | RBAC (`auth.py`), helpers (`helpers.py`), images (`images.py`), mail + outbox (`mail.py`, `outbox.py`) |
| `webapi/wblester_api/worker/` | RQ job handlers and enqueue helpers |
| `webapi/wblester_api/seed.py` | Seeder: roles/matrix, superuser + admin accounts, settings, categories, 19 seed pages with photography |
| `webapi/tests/` | `pytest` suite (mongomock, fakeredis, mocked SMTP) |
| `docker-compose.yml` | The five services (mongo, redis, webapi, worker, backend) |
| `.env.example` | Template for environment/secrets configuration |
| `docs/` | Design reference images |
| `data/` | Local `mongodump` backups |
| `build_dependencies/` | Helper scripts for deployment + encrypted settings |

---

## 7. Getting started

### Prerequisites

- **Docker Desktop** (or a Docker engine + Compose plugin).
- Nothing else — the backend image compiles Flutter *inside* Docker, so a host
  Flutter/Python install is **not** required to run the stack.

### Run the whole stack

```bash
cp .env.example .env   # adjust secrets/credentials first (see §8)
docker compose up --build -d
```

On first boot the `webapi` container seeds the database automatically:
roles, permission matrix, superuser + default-admin accounts, site settings,
three categories, 19 pages of starter content and 23 curated photos.

Open (default `PORT=5454`; substitute your `PORT` if you changed it):

| URL | Purpose |
| --- | --- |
| `http://localhost:5454/` | Public website |
| `http://localhost:5454/admin` | Admin portal |
| `http://localhost:5454/health` | Liveness check |
| `http://localhost:5454/login` | Server-rendered sign-in page |
| `http://localhost:5454/logs` | System status console |

Stop with `docker compose down`. To wipe the database and reseed from scratch:
`docker compose down -v && docker compose up --build -d`.

> **Rebuilding the admin portal:** the `backend` image compiles the Flutter SPA
> during `docker compose build`. To ship an admin UI change, rebuild just that
> image: `docker compose build backend && docker compose up -d backend`.

### Run the WebApi without Docker (development only)

```bash
cd webapi
python -m venv .venv-api && .venv-api\Scripts\activate   # Windows (Linux: source .venv-api/bin/activate)
pip install -r requirements.txt
python -m wblester_api.seed                              # one-time seeding
python -m wblester_api.wsgi                              # serves :$PORT (default 5454)
```

The non-Docker route serves no admin portal and only serves the public SPA if
`SPA_DIR` points at `../frontend`.

---

## 8. Configuration

All configuration lives in `.env` (copy from `.env.example`). The most common
settings:

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `5454` | **Single web port for the whole stack** (host mapping, nginx upstream, gunicorn bind) |
| `SECRET_KEY`, `JWT_SECRET_KEY` | `change-me…` | Flask + JWT signing secrets — **must change in production** |
| `MONGODB_USERNAME/PASSWORD/DB` | `wblester_user` / `WBLester@123` / `wblester` | MongoDB credentials |
| `REDIS_HOST` | `localhost` | Redis host |
| `SMTP_HOST/PORT/USERNAME/PASSWORD` | Gmail defaults | Outgoing mail (contact form, replies, account emails, campaigns) |
| `MAIL_DEFAULT_SENDER` | `no-reply@wblester.local` | From-address for outgoing mail |
| `WBLESTER_ADMIN_*` | see §9 | Bootstrap superuser account |
| `WBLESTER_DEFAULT_ADMIN_*` | see §9 | Bootstrap admin account |
| `WBLESTER_API_USERNAME/PASSWORD` | `wblester_sync` / `WBLester@123` | Machine-to-machine account |
| `PUBLIC_BASE_URL` | `http://localhost:<PORT>` | Base URL used to build absolute media URLs |

---

## 9. Default accounts (development)

| Account | Username | Password | Role |
| --- | --- | --- | --- |
| Superuser | `wblester` | `WBLester@123` | Full access, incl. events/jobs/logs/system |
| Admin | `wblesteradmin` | `WbLester@123!` | Full content management |
| Sync (M2M) | `wblester_sync` | `WBLester@123` | Automated API access |

> **Change every default password before going live.** The superuser and admin
> credentials come from the `WBLESTER_ADMIN_*` / `WBLESTER_DEFAULT_ADMIN_*`
> environment variables, so they can be rotated centrally and re-applied on a
> fresh seed.

---

## 10. Administrator user manual

This section is a walkthrough for a newly onboarded administrator. It covers
sign-in, every admin section, and the operational habits that keep the site
healthy.

### 10.1 Signing in

1. Open `http://<your-host>/admin`.
2. Enter your username and password. Passwords must be at least 8 characters
   and pass a strength check; the form gives live warnings as you type.
3. On your **very first login** you will be required to choose a new password
   before entering the portal. Do this now — nothing else is reachable until
   you do.
4. After success you land on the **Dashboard**. Your session stays alive
   across page reloads until the tokens genuinely expire; if a token expires
   mid-use the portal renews it silently.

The exact sections you see depend on your role. Superuser-only areas
(Events, Jobs, Logs, System) are hidden for other roles.

### 10.2 Dashboard

A clickable statistics overview: pages, categories, new messages, users,
images, documents, media storage, active users, running jobs and audit entries.
Every card jumps to its section, so the dashboard also works as a navigation
hub.

Superusers additionally see **Frontend errors** and **Must change password**
cards. If a number looks wrong, drill into the section to investigate — service
health itself lives in §10.11 (System), with detail in §10.14 (Logs).

### 10.3 Pages — the heart of the site

The **Pages** screen is a searchable table (filter by title or slug), ordered
by **sort order** and then row ID. Each row shows the category, whether the
page is the current **home** page, and a **Visible** switch.

**Page fields** (in the *New page* / *Edit page* dialog):

| Field | Meaning |
| --- | --- |
| Title | Displayed heading (required) |
| Slug | URL tail, lowercase-hyphenated, e.g. `about-us` (required) |
| Category | Which menu the page belongs to; empty keeps it outside the menus |
| Sort order | Numeric; lower values list first |
| Visible on the website | Off = hidden from menus and the public site |
| SEO title / description | Meta data for search engines |
| Content blocks | The page's building blocks — see below |

**Create a page:**

1. Press **New page** (top-right).
2. Fill in Title, Slug, Category, Sort order and visibility.
3. Press **N block(s)…** to add content blocks — or leave it empty and add them
   when editing.
4. Press **Save page** (a "Page created." toast confirms; Title and Slug are
   mandatory).

**Edit a page / update its content:**

1. Click the pencil icon on the row.
2. Change any field. Press **N block(s)…** to edit the content blocks.
3. Press **Save page**. The API writes the page, bumps its version and logs the
   change to the audit trail; the public site picks it up within one sync
   cycle.

**The block editor:**

- Opened from the **N block(s)…** button; the header has an **+ Add block…**
  dropdown with every block type.
- Each block row offers **move up / move down**, **edit** and **remove**.
- Editing a block opens a form with that type's fields. Blocks that hold a
  collection show an **Add `item`** button — every item (slide, card, photo,
  quote, counter, chip …) can be added, edited and removed individually.
- Image fields always show an **Image library…** button: pick an asset already
  uploaded (§10.10), or upload a new file right from that dialog.

| Block | Renders on the site | Fields you fill in |
| --- | --- | --- |
| `jumbotron` | Full-width banner carousel | **Slides**: image URL, kicker, title, subtitle (words in `[brackets]` highlighted in gold) |
| `hero` | Page header image band | Background image URL |
| `richText` | Rich-text / HTML passage | HTML content |
| `cards` | Services grid | Section title + intro; **Cards**: image, title, text, links-to-slug |
| `features` | Feature / trust boxes | Section title + intro; **Features**: title, text |
| `steps` | Numbered process band | Section title + intro; **Steps**: title, text |
| `stats` | Parallax counters band | Background image; **Counters**: value (e.g. `30+`), label |
| `gallery` | Filterable photo gallery | Section title + intro; **Photos**: image, caption, filter tag |
| `about` | About split with image collage | Title, green lead line, body HTML; photo URLs as a simple list |
| `testimonials` | Auto-advancing quote cards | **Quotes**: headline, quote, author, location/role |
| `partners` | Partner chips strip | **Chips**: label |
| `cta` | Gradient call-to-action band | Title, text, button label |
| `contactForm` | Quote / contact form | Title, intro |

**Other row actions:** **home** — set the page as the home page shown at `/`;
**open-in-new-tab** — view the live page; **delete** — permanent, always
confirmed, no undo. Prefer hiding over deleting (§11). Hide/show is done with
the **Visible** switch or the visibility checkbox in the dialog — a hidden page
leaves menus and the public site but stays in the database.

### 10.4 Categories — the menu tree

Categories become the top-level **menus** on the public site; pages are
assigned to them in the page dialog (§10.3) and become sub-menus beneath them.

- **Create**: press **New category**; enter **Name** and **Slug** (both
  required), a **Sort order**, tick **Visible on the website**, then **Save
  category**.
- **Rename / reorganise**: open the row with the pencil icon and edit the same
  fields. The **Parent** column is informational (set by the category
  hierarchy); ordering follows the sort order number.
- **Hide / show**: untick **Visible on the website** — the whole menu branch
  disappears from the public site without touching its content.
- **Delete**: confirmed first; **pages in the category are not removed**, only
  the menu entry.

> If a category has no visible pages of its own, navigation automatically
> resolves to its top-most visible page so menu clicks always land somewhere.

### 10.5 Messages — the mailbox

Every contact/quote form submission from the website lands here. Filter the
list with the status chips **All / New / Read / Replied / Archived / Trashed**.

- **Read**: click a row to open the message — a **New** message is automatically
  marked **Read**. The dialog shows subject, sender, received time and body.
- **Reply**: press **Reply**, type the answer and **Send reply**. The outgoing
  mail is recorded back on the message, which turns **Replied**.
- **Archive / Trash**: buttons in the open message keep the inbox tidy;
  Trashed messages survive until you delete them.
- **Delete** (row icon): removes a message **permanently** after confirmation —
  prefer Trash if you may need it later.

**Compose outgoing mail:**

1. Tick **Mailing list (N)** to include every address from Site Settings
   (§10.7), and/or type recipient addresses in **To** (comma or newline
   separated).
2. Fill in **Subject**.
3. Optionally pick a saved **Template** (from §10.6) — the dialog lists the
   `{{placeholders}}` the template expects.
4. Provide the **Name placeholder** when the template uses one.
5. Write the **Message**, or rely on the template body alone.
6. Press **Attach media** to embed images inline and/or add documents as
   attachments from the media libraries (§10.10).
7. Press **Send** — a "Mail sent." confirmation appears.

### 10.6 Mail templates

Reusable HTML bodies for replies and campaigns, sorted by name.

- **Create**: press **New template**; give it a **Template name** (required), an
  optional **Description**, and the **Contents** — `{{placeholders}}` in double
  braces are filled from the message context (e.g. `{{name}}`, `{{body}}`,
  `{{message}}`), then **Save template**.
- **Preview** a template with the eye icon to review its raw contents; **edit**
  with the pencil icon; **delete** removes it permanently after confirmation.
- Templates are picked from the **Template** dropdown when composing mail
  (§10.5).

### 10.7 Settings

Site-wide configuration. Press **Edit settings**, change a group, then **Save
settings**. The groups are:

- **Identity** — site name, site title, site description, keywords and the
  startup message.
- **Contact** — address, email, phone number, contact message, and the Google
  map embed.
- **Home & accounts** — home page id (which page renders at `/`), default
  mailing account, sync mode (0 online / 1 local) and session timeout.
- **Structured data (JSON)** — the **mailing list** (JSON array of addresses;
  also feeds Compose's "Mailing list" option), **social media** links, and
  **overrides**.

Site name and site title are required; the JSON fields are validated. Saves are
stored, versioned and revalidated by the public site like any other content
change.

### 10.8 Users

Manage administrator accounts. The table shows **ID, Username, Email, Role,
State** (ACTIVE / INACTIVE / LOCKED), **Logins** and row actions.

- **Create a user**: press **New user**; enter username, email, role and a
  password **typed twice to confirm**. On creation an email notification is
  sent (username, role and portal URL — never the password), and the new user
  must choose their own password at first login.
- **Edit a user**: change the **Role**, the **Active** state, tick **Unlock
  this account** when a locked account appears, and optionally set a **New
  password** (the user is then forced to change it at next login).
- **Delete**: after confirmation, removes the account.

### 10.9 Roles & permissions

The **permissions matrix** grants each role a level for every permission. The
CMS defines four levels:

| Level | Meaning |
| --- | --- |
| `Deny` | No access |
| `Read` | View content |
| `Modify` | Edit existing content |
| `Full` | Create and delete records |

- Each role is a card; every permission is a dropdown showing its current level.
- Change a value, then press that card's **Save** (it stays disabled until
  something changed).
- **New role** creates a fresh role (name + description) that you can then grant
  levels to.
- **Delete role** removes it after confirmation (the superuser role cannot be
  deleted; users keep their records).

Because levels are enforced **server-side**, a tightened matrix takes effect
immediately for everyone. Seeded roles: **superuser** (unrestricted, skips the
matrix and sees the operational sections Events, Jobs, Logs, System), **admin**
(full panel access) and **guest** (read-only). If you ever remove your own
access, sign in with the superuser to repair the matrix.

### 10.10 Images & Files

Two media libraries hold every asset editors upload.

- **Upload**: press **Upload** and pick one or more files, or **drag and drop**
  them straight onto the library. Images are processed into responsive variants
  automatically (via `?size=sm|md|lg|thumb`); file types and sizes are
  allow-listed (10 MB cap).
- **Images** appear as a grid of thumbnails (name, dimensions, size, usage);
  **Files** as a table (name, format, size, usage). Use **Copy URL** to paste
  an asset into a page block's image field (§10.3), an email attachment
  (§10.5), or anywhere else; **Open** views it.
- Deleting an asset still referenced by a page is **blocked** — a dialog names
  the pages using it, so you can re-point those pages (§10.3) before deleting.
  Unused assets show an **Unused** marker and delete cleanly.

### 10.11 System (superuser)

A live infrastructure health panel.

- An **overall** chip — `UP` (green), `ATTENTION` (amber) or `DOWN` (red) —
  freshly computed on load, plus an **Errors / Warnings** counter.
- One card per service (WebApi, MongoDB, Redis) with a status dot and detail.
- A tail of recent log lines, filterable by **All / ERROR / WARNING / INFO**.
- Press **Refresh** to re-run the diagnostics. If storage or a service drops,
  the website keeps serving cached content but admin writes and mail pause
  (§11).

### 10.12 Events & Jobs (superuser)

The scheduler automates outbound mail; this section is read-mostly with two
actions.

- **Events** lists scheduled campaigns that may trigger template mail on a
  timer: name, description, type, status, parameters, created date and run
  history. Statuses: `OPEN`, `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`. The
  **play** icon runs an event **now** — for example to fire a campaign
  immediately on top of its schedule; refresh to watch it progress.
- **Jobs** are the delivery records (the "outbox"): job id, started/ended,
  progress %, status and error count. Click a row to open the full detail —
  description, completion, schedule, info, errors and parameters. Failed jobs
  (`FAILED`) get a **Retry** icon that re-queues them with one click, reusing
  the same job identity.

### 10.13 Audit trail

A running history of the **latest 100 operations**, newest first.

- Each row shows **when**, **user**, **collection**, **type** (CREATE / UPDATE /
  DELETE / LOGIN / LOGIN FAILED / PASSWORD …) and a human description.
- Click a row to expand it: record ID, the **old and new values** as JSON, and
  the description. The text is selectable so you can copy whatever you need.
- Treat this as the source of truth when answering "what changed, and who
  changed it?".

### 10.14 Logs (superuser)

A unified, SIEM-style console that merges **WebApi**, **backend** and
**frontend** logging into one stream (up to 500 rows).

- **Source** segmented buttons: All / Web API / Backend / Frontend.
- **Level** dropdown: any level / INFO / WARN / ERROR, with live error /
  warning / info counters.
- Press **Refresh** to pull the newest rows. Use it to trace a visitor's error,
  a failed send or an admin action across all three layers without jumping
  between services.

---

## 11. Operational habits for a healthy site

1. **Rotate default credentials** (superuser, admin, sync, MongoDB) before
   production and keep the real values only in `.env` / the deployment secret
   store — never in code or the repository.
2. **Prefer hide over delete.** Hiding a page or category removes it from the
   public site instantly but keeps content safe for reactivation. Delete only
   with intent, and re-point any references first (the system blocks
   referenced-media deletion for you).
3. **Monitor the Dashboard and System pages.** If MongoDB or Redis drop, the
   site falls back to cached content but admin writes and mail delivery pause.
4. **Drift email jargon:** the mailbox's mailing list (Settings) is separate
   from SMTP (`.env`). Verify SMTP is configured or all "sending" steps (reply,
   compose, account-notification, scheduled campaigns) will be dry-runs.
5. **Back up MongoDB** regularly (a `mongodump` snapshot is enough; the `data/`
   folder in this repo is used for local dumps). Re-seeding can restore starter
   content, but not your edits.
6. **Changes propagate automatically** — you never need to rebuild or restart
   anything after editing content. Rebuild only the `backend` image when you
   change the Flutter admin portal itself.
7. If you bump the seed content (`webapi/wblester_api/seed.py`), it only
   applies on a fresh volume; for ongoing edits use the admin portal instead —
   they survive seed re-runs.

---

## 12. Tests

```bash
# WebApi (pytest; mongomock, fakeredis and a mocked SMTP):
cd webapi
.venv-api\Scripts\activate          # or: source .venv-api/bin/activate
python -m pytest tests -q

# Admin portal (Flutter):
cd backend
flutter pub get
flutter analyze
flutter test

# Public SPA syntax sanity (run per file):
node --check frontend/js/app.js
node --check frontend/js/views/public.js
```

---

## 13. Project documentation

| File | Contents |
| --- | --- |
| `product_requirement_document.txt` | Original requirements |
| `project_plan.md` | Phased plan and decisions (all phases marked complete) |
| `progress.md` | Full session-by-session engineering log, gotchas and verification results |
| `docs/` | Design reference images |