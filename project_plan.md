# WBLESTER CMS â€” Project Plan

## Goal
A responsive Flutter CMS website covering **agriculture, real estate, and natural resources / energy production & sales** in a single website, with an AdminLTE-based admin panel, backed by a **Python Flask API + MongoDB (+ Redis) running in Docker**. The Flutter app keeps its local drift database and synchronizes it with MongoDB through the Flask API.

Source requirements: `product_requirement_document.txt`.

---

## Architecture

```
Flutter Web App (single deployable)
â”œâ”€ Public site  (/ , /page/:slug)          â† guests
â””â”€ Admin panel  (/admin/*, AdminLTE UI)    â† admin/superuser (role-gated)
Local drift DB (offline-first)
        â”‚  JWT Bearer â€” push-sync on mutation + periodic timer
        â–¼
Flask API (:5454)
â”œâ”€ auth (JWT access+refresh, OAuth stretch)
â”œâ”€ sync / data endpoints   â† contract used by DataSyncService
â”œâ”€ CRUD: pages, categories, settings, users, roles, permissions, messages
â”œâ”€ uploads (files/images â†’ GridFS or volume)
â”œâ”€ SMTP/Gmail (contact mail â†’ mailing list, replies via templates)
â””â”€ Redis (cache / rate-limit, optional)
        â”‚
        â–¼
     MongoDB (all collections)
```

### Key decisions
1. **One Flutter web app** with role-gated routes (`/` public, `/admin/*` admin panel).
2. **Vendor** the needed AdminLTE files from `E:\workspace\F\flutter\Flutter_AdminLTE\lib` into `app/lib/admin_ui/` (source project is demo-grade: hardcoded menus, no package exports).
3. **Delete** the Dart `server/` toy once the Flask API replaces it.
4. **Immediate propagation** = push-sync right after admin mutations + short configurable polling timer; WebSocket can be added later behind the same abstraction.
5. Rich editor: `html_editor_enhanced`; file/image uploads via `file_picker`.
6. RBAC matrix enforced client-side (route/widget gating) **and** server-side (Flask authorization decorators):
   - `guest` â†’ read-only
   - `superuser`, `admin` â†’ read + modify
   - `admin` â†’ create + delete

---

## Phase 1 â€” Cleanup & repair foundation
- [x] Remove travel baggage: `lib/ui/home|search_form|results|activities|booking`, `lib/domain/use_cases/booking`, stale tests referencing `compass_app`, `assets/destinations.json`, `assets/activities.json`.
- [x] Fix broken plumbing: complete `lib/config/dependencies.dart` (`dataProviders`), rebuild `lib/routing/router.dart` skeleton, replace deleted `auth_repository.dart` import in LoginViewModel, fix `main_staging.dart`.
- [x] Port AdminLTE theme/layout/components into `app/lib/admin_ui/` and adapt imports.
- [x] Scrub plaintext credentials from `parameters.json` â†’ environment variables; add `.env.example`. Keep `parameters.json` at `app/assets/parameters.json` (loaded by `main_development.dart`).

## Phase 2 â€” Domain model extension (drift v21)
Existing 15 tables already cover Users/Roles/Permissions/SiteSettings/Files/Images/GMailAccounts/IMAPAccounts/MailTemplates/AuditTrail/Jobs/Events/EventTypes/EventTriggers/Schedules. Add:
- [x] `Categories`: id, parentId (self-ref tree for sub-categories), name, slug, visible, sortOrder â†’ drives menus/submenus.
- [x] `Pages`: id, categoryId, title, slug, contentJson (structured blocks), visible, sortOrder, seoTitle, seoDescription.
- [x] `Messages`: id, fromName, fromEmail, subject, body, status (new/read/replied/archived/trashed), replyToId, sentAt â†’ mailbox.
- [x] Migration v20â†’v21 + regenerated schema/migration tests.
- [x] Extend `sync_tables` in `parameters.json`; new repositories following `BaseRepository`.

## Phase 3 â€” Flask API + Docker (`api/`)
- [x] Flask app factory + blueprints: `auth`, `sync`, `data`, `pages`, `categories`, `settings`, `users`, `roles`, `permissions`, `messages`, `uploads`.
- [x] MongoEngine documents mirroring every drift table (BasicColumns equivalent: `createdDatetime`, `lastModifiedDate`, `currentVersion`).
- [x] Auth: flask-jwt-extended (access+refresh), password hashing + lockout honoring Users columns; OAuth (Google via Authlib) as a stretch goal.
- [x] Sync contract: implement `cpanel/jwt/sync` (pull deltas by `current_version`/`last_modified_date` per table config; push upserts; server bumps versions) and `cpanel/jwt/data` (paged fetches) exactly as `DataSyncService` expects; M2M auth via `api_username`/`api_password` moved to env vars.
- [x] Mail: Contact Us POST â†’ store Message + send to mailing list; reply endpoint uses MailTemplates; SMTP credentials configurable.
- [x] Uploads â†’ GridFS/volume; URLs stored into Files/Images collections.
- [x] docker-compose.yml (`mongo`, `redis`, `api`) + `.env.example`; seed script creating roles, permission matrix, default SiteSettings, starter pages for the three verticals.
- [x] pytest suite: auth, sync deltas, CRUD, uploads, mail (mocked SMTP).

## Phase 4 â€” Admin panel (AdminLTE-based)
- [x] JWT login screen; tokens in `flutter_secure_storage`; refresh on 401.
- [x] Dashboard: InfoBox stats (pages count, unread mail, recent audit trail).
- [x] Pages manager: DataTable2 list (search/sort/pagination), CRUD, show/hide toggle, rich-text editor, image/file pickers wired to uploads.
- [x] Categories manager: tree CRUD (categories/sub-categories), reorder, show/hide.
- [x] Mailbox: folders (inbox/unread/replied/archived/trashed), reader, reply composer, delete/archive.
- [x] Settings page bound to SiteSettings (logo/theme, phone, address, Google Map, mailing list, mailbox accounts, homePageId).
- [x] Users / Roles / Permissions CRUD enforcing the RBAC matrix.
- [x] Data-driven sidebar menu model filtered by permissions (replaces hardcoded AdminLTE sidebar).
- [x] Audit trail viewer.

## Phase 5 â€” Public website
- [x] Theme derived from SiteSettings; palette mixing green/yellow/blue/white/orange.
- [x] Dynamic nav: visible categories/sub-categories â†’ menus/submenus.
- [x] Routes `/` (from `homePageId`) and `/page/:slug`; block renderer (hero/text/galleries/cards).
- [x] Responsive typography/images/spacing via shared breakpoint helpers.
- [x] Contact Us form â†’ POST to Flask API â†’ success/failure states.
- [x] Sync-on-navigate + timer so backend changes appear immediately.

## Phase 6 â€” Verification & polish
- [x] Dart unit tests (repos/viewmodels); widget tests for key screens.
- [x] End-to-end integration test: login â†’ edit page in admin â†’ change visible on public site after sync.
- [x] Responsive QA at mobile/tablet/desktop widths; WASM web build green.
- [x] README rewrite (architecture, docker instructions, seed data).


## Phase 7 - Public website v2 (CMS-driven, session 4)
- [x] Unauthenticated browser routing: every protected route (including `/`) sends HTML navigations to the branded `/login` page; API clients keep JSON (401/index). Public aliases: `/login`, `/uploads/<file>`.
- [x] Branded server-rendered login page (api/wblester_api/login_page.py).
- [x] Subpage hierarchy: Pages.parent_id (drift schema v22 with migration + generated test schemas), admin editor parent dropdown.
- [x] CMS nav tree: categories = menus, pages = submenus, subpages = nested items (nav_tree.dart); desktop MenuAnchor/SubmenuButton + mobile drawer accordion; orphan promotion when a parent page is hidden.
- [x] Home landing page (seeded `home` page, id 100): hero carousel, services cards, stats band, why-us, request CTA - all driven by seeded blocks from the API.
- [x] Block renderer for hero, richText, cards, cta, contactForm blocks incl. breadcrumbs + subpage card grids on content pages.
- [x] Request-service flow: `/request/:slug` prefilling page context, posts to public `POST /contact`; success state.
- [x] Brand identity: tri-color W&O ring logo (app/assets/logo.svg) + wordmark; green/gold/blue palette in public_theme.dart.
- [x] Real photography seeded via Wikimedia Commons into seed_assets/, copied to uploads by the seeder; absolute media URLs via PUBLIC_BASE_URL.
- [x] Mini HTML renderer (html_text.dart) for richText blocks with unit tests; nav-tree unit tests.

---
## Phase 8 - Public SPA at root + backend UX hardening (session 5)
- [x] `/` serves the compiled Flutter public website to browsers (SPA_DIR bind mount of `app/build/web`); catch-all route serves bundle assets and hands deep links (e.g. `/cpanel/dashboard`) to index.html so GoRouter owns client-side routing; machine clients keep the JSON API index; unknown paths 404 JSON for APIs, index for browsers.
- [x] Backend stays JWT-protected: only `/`, SPA assets, `/login`, `/logs`, `/uploads/*` and `/health` are anonymous; every `/cpanel/**` data endpoint still requires tokens.
- [x] Logging infrastructure (logging_setup.py): rotating file handler into LOG_DIR + structured JSON lines for the status page; read_recent_logs tail helper.
- [x] Diagnostics endpoint `GET /cpanel/jwt/diagnostics` (superuser-only): service statuses (API/MongoDB/Redis), log tail, warn/error counts, overall status.
- [x] System-status console `GET /logs`: branded server-rendered page with service cards, warning/error highlighting in the live log table, filter chips and auto-refresh; unauthenticated visitors get a sign-in-required gate.
- [x] Login page UX: wider responsive card, per-field JS validation (yellow warnings / red errors), CapsLock hint, submit-time summary dialog listing all issues with fix suggestions.
- [x] Lighter green brand palette (public_theme.dart) + nature-themed leaf/ring logo.svg; shared public_widgets.dart (SectionOverline/SectionTitle/HoverLift/CTAs); polished home, page blocks, header CTA, gradient stats band and footer.
- [x] docker-compose: spa bind mount fixed to repo-root relative path (`./app/build/web`), LOG_DIR volume, gunicorn access logs.

---
## Phase 9 - Garden-Hub restyle + backend quick wins (session 6)
- [x] New CMS block vocabulary (seed.py + public_blocks.dart): `jumbotron` (slides with `[gold]` highlight syntax), `about`, `steps`, `stats`, `gallery`, `testimonials`, plus shared `cta`/`contactForm` panels.
- [x] Home page fully CMS-driven: jumbotron slider (6s auto-advance, Ken Burns, kicker chip, dots/arrows), about collage, image service cards, numbered steps band, parallax stats, gallery grid with hover zoom, testimonials carousel, CTA gradient band, contact panel — all editable from the admin panel.
- [x] Generic page renderer extended: vertical landings + subpages render the new block types; shared widgets in public_blocks.dart (CtaBand, ContactPanel) reused by home and pages.
- [x] Garden-Hub inspired top bar above the header with phone/email pulled from site settings ("From soil to skyline" tagline).
- [x] Seed content rewritten for all 19 pages (3 vertical landings + 15 subpages + home): benefit-led professional copy, 18 curated Commons photos (garden/estate/nature set added).
- [x] Backend: `/admin` (+ `/admin/<path>`) serves the SPA as the admin entry point; unauthenticated HTML requests still route to `/login`.
- [x] Login dialog header changed to "Fix X issues to sign in".
- [x] Shared branding.py: inline SVG logo mirroring app/assets/logo.svg used by login page and /logs console.

---
## Phase 10 - Vanilla-JS SPA replaces the Flutter frontend (session 7)
- [x] **Pivot**: delete the entire Flutter `app/` project (frontend was slow to boot and drifted from the Garden-Hub reference); replace with a dependency-free single-page application in `webapp/` that closely mimics https://st.ourhtmldemo.com/template/gardenhub/ (topbar, contact header, dashed dark nav, hero slider, services grid, feature boxes, filterable gallery, about+quote split, testimonials band, partner strip, map, 4-column footer).
- [x] Stack: vanilla ES modules (no framework, no build step) — `db.js` IndexedDB cache (drift-equivalent offline store), `api.js` fetch wrapper with JWT attach + silent refresh retry, `store.js` stale-while-revalidate sync engine (cache-first paint → `/public/content` diff → re-render; 60 s timer + tab-visibility revalidate), `ui.js` DOM builders + slider/filter/counters/reveal helpers, History-API router in `app.js`.
- [x] Backend: anonymous `GET /public/content` returns all visible categories/pages (with content blocks) + whitelisted public settings subset; the configured home page is always included even if toggled invisible; home page now seeded visible.
- [x] Public views: header/topbar/footer chrome from settings+categories, block renderer for jumbotron (shuffled slides = random banner), cards, features, gallery (filter chips), about split, steps, stats counters, testimonials, partners, cta, richText, quote form (+ OSM/Google map iframe from settings), contact view, subpage card bands.
- [x] Admin panel inside the same SPA at `/admin/*`: JWT login screen, dashboard stats, Pages manager (structured per-block-type editors with repeatable item lists, reorder, raw-JSON mode), Categories manager, Messages inbox (mark read / reply by email), Site Settings form; every save pushes through the existing `/cpanel/jwt/data|settings|messages` endpoints and triggers a store re-sync.
- [x] New seed blocks for the home narrative: `features` (6 trust boxes) and `partners` (6 chips); gallery items tagged with filter categories; google_map seeded as an embeddable OpenStreetMap URL.
- [x] docker-compose SPA mount repointed `./app/build/web` → `./webapp`; assets salvaged (`logo.svg`, `user.jpg`).
- [x] Verification: pytest 44/44 in container; headless-browser DOM checks confirm home renders all 11 seeded blocks, deep links render page-hero/crumbs, `/admin` renders the login shell; static/upload serving unchanged.

---
## Phase 11 - Category landings reachable + client-attracting content (session 8)
- [x] **Nav fix (the "missing pages" bug)**: desktop menu, mobile nav and breadcrumbs resolved each category to `/page/<category-slug>`, which matched no page (`agriculture` vs `agriculture-home`) → Page Not Found. New `landingForCategory()` resolves each category's top-most visible page (categoryId match, no parent) with slug fallback; used by `menuEntries()`, `renderMobileNav()`, `breadcrumbTrail()` and `isCategoryLanding()` (webapp/js/views/public.js).
- [x] Breadcrumb/subpage latent bug: public content omits `visible`, so `parentPage.visible`/`p.visible` guards always failed — parent crumbs never rendered and child-page bands were empty on parent pages; guards removed (payload is already visible-filtered).
- [x] 5 new topical photos from Wikimedia Commons (irrigation-pivot, interior, solar-install, wind-farm, feedlot) added to MEDIA registry → seed_assets → uploads volume.
- [x] Agriculture / Real Estate / Energy landings rebuilt in seed.py with the full home-grade block vocabulary: hero, about, features (4 icon boxes), services cards, steps (4-step process), stats parallax counters band, 6-item filterable gallery, 3 testimonials, partners strip, CTA, contact form.
- [x] Hero images corrected: Real Estate now uses realestate-hero.jpg (was garden-estate), Energy uses energy-hero.jpg solar+wind aerial (was nature-reserve waterfall); dedicated heroes also reused inside galleries.
- [x] Fresh-volume rebuild (`docker compose down -v && up -d --build`) so the idempotent seeder applies new blocks/media.
- [x] Verification: API tests 44/44; category E2E 8/8 (nav hrefs, click-through SPA navigation, rich sections on all three landings, gallery filter chips, mobile nav overview entries, breadcrumb parent/category resolution); full browser E2E 9/9; admin CRUD flow smoke all green.

---
## Execution order
Phase 1 -> Phase 2 -> ... -> Phase 9 -> Phase 10 -> Phase 11 (Flutter app removed in Phase 10; Phases 1–9 history retained).
First concrete steps: Phase 1 cleanup + Flask API auth/sync skeleton (everything consumes those).
