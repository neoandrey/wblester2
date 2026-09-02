/* App bootstrap + router (History API, server hands deep links to index.html). */

import { initStore, subscribe } from './store.js';
import {
  renderTopbar,
  renderHeader,
  renderFooter,
  homeView,
  pageView,
  contactView,
  renderViewInto,
} from './views/public.js';
import { adminRoute } from './views/admin.js';

const app = document.getElementById('app');
let scrollLock = false;

function resolveRoute() {
  const path = location.pathname.replace(/\/+$/, '') || '/';
  if (path === '/admin' || path.startsWith('/admin/')) return { name: 'admin', path };
  if (path === '/' || path === '/index.html') return { name: 'home', path: '/' };
  if (path === '/contact') return { name: 'contact', path };
  if (path.startsWith('/page/')) {
    return { name: 'page', path, slug: decodeURIComponent(path.slice('/page/'.length)) };
  }
  return { name: '404', path };
}

let lastTitle = '';
function route() {
  const content = window.__content;
  const r = resolveRoute();

  if (content) renderChrome(r);

  if (r.name === 'admin') {
    adminRoute(app, r);
    finishLoad();
    return;
  }

  if (!content) {
    renderBooting();
    finishLoad();
    return;
  }

  switch (r.name) {
    case 'home':
      document.title = `${content.settings.siteName || 'WBLester & O'} — From soil to skyline`;
      renderViewInto(app, homeView());
      break;
    case 'contact':
      document.title = `Contact Us — ${content.settings.siteName || 'WBLester & O'}`;
      renderViewInto(app, contactView());
      break;
    case 'page': {
      const view = pageView(r.slug);
      const page = content.pages.find((p) => p.slug === r.slug);
      if (view && page) {
        document.title = `${page.title} — ${content.settings.siteName || 'WBLester & O'}`;
        renderViewInto(app, view);
      } else {
        renderNotFound();
      }
      break;
    }
    default:
      renderNotFound();
  }

  if (document.title !== lastTitle) {
    lastTitle = document.title;
  }
  if (!scrollLock) window.scrollTo(0, 0);
  scrollLock = false;
  finishLoad();
}

function renderChrome(routeInfo) {
  renderTopbar();
  renderHeader(routeInfo.path);
  renderFooter();
}

function renderNotFound() {
  app.innerHTML = '';
  const section = document.createElement('section');
  section.className = 'secpadd';
  section.style.textAlign = 'center';
  section.innerHTML =
    '<h2>Page <span class="main-color">not found</span></h2>' +
    '<p>The page you are looking for doesn\u2019t exist or is not published.</p>' +
    '<a class="btn btn-green" href="/">Back to Home</a>';
  app.append(section);
}

function renderBooting() {
  app.innerHTML = '';
  const section = document.createElement('section');
  section.className = 'secpadd';
  section.style.textAlign = 'center';
  section.innerHTML =
    '<h2>Welcome to <span class="main-color">WBLester &amp; O</span></h2>' +
    '<p>Loading latest content…</p>';
  app.append(section);
}

function finishLoad() {
  document.getElementById('preloader')?.classList.add('done');

  /* Sticky compact header */
  const masthead = document.getElementById('masthead');
  const onScroll = () => {
    const stuck = window.scrollY > 240;
    masthead.classList.toggle('stuck', stuck);
    document.body.classList.toggle('stuck-main', stuck);
  };
  onScroll();
  window.removeEventListener('scroll', onScroll);
  window.addEventListener('scroll', onScroll, { passive: true });
}

/* Intercept same-origin link clicks for SPA navigation. */
document.addEventListener('click', (event) => {
  const anchor = event.target.closest('a[href]');
  if (!anchor || anchor.dataset.ext) return;
  const href = anchor.getAttribute('href');
  if (!href || /^(https?:|mailto:|tel:|#)/.test(href)) return;
  if (anchor.target === '_blank') return;
  event.preventDefault();
  history.pushState({}, '', href);
  route();
});

window.addEventListener('popstate', route);

subscribe((content) => {
  window.__content = content;
  /* Store only emits when the payload actually changed. Keep the reader's
     position instead of jumping to top on background syncs. */
  scrollLock = true;
  const y = window.scrollY;
  route();
  window.scrollTo(0, y);
});

initStore().finally(() => {
  if (!window.__content) route(); /* offline & empty cache: still show shell */
});
