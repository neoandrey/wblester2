/* Public site rendering — Garden HUB-style layout driven entirely by the
   cached CMS content (categories, pages + content blocks, settings). */

import {
  getContent,
  getSettings,
  categories,
  pagesOfCategory,
  pageBySlug,
  homePage,
  visiblePages,
} from '../store.js';
import {
  el,
  icon,
  esc,
  rich,
  accentTitle,
  initHeroSlider,
  initGalleryFilters,
  observeReveals,
  initCounters,
  shuffled,
} from '../ui.js';
import { postContactForm } from '../api.js';

/* ------------------------------------------------------------------ chrome */

export function renderTopbar() {
  const s = getSettings();
  const host = document.getElementById('topbar');
  host.innerHTML = '';
  host.append(
    el(
      'div',
      { class: 'container topbar-in' },
      el('div', { class: 'topbar-note' },
        s.contactUsMessage || 'Professional agriculture, real estate and natural resources services'),
      el('ul', { class: 'topbar-links' },
        el('li', {}, el('a', { href: '/contact' }, 'Request Quote')),
        el('li', {}, el('a', { href: '/contact' }, 'Contact')),
        el('li', {}, el('a', { href: '/admin' }, 'Admin')),
      ),
    ),
  );
}

export function renderHeader(currentPath = '/') {
  const s = getSettings();
  const masthead = document.getElementById('masthead');
  masthead.innerHTML = '';

  masthead.append(
    el('div', { class: 'header-contact' },
      el('div', { class: 'container header-contact-in', style: { display: 'flex', justifyContent: 'space-between', gap: '30px' } },
        el('a', { class: 'brand', href: '/' },
          el('img', { src: '/assets/logo.svg', alt: s.siteName || 'WBLester & O' }),
          el('span', { class: 'brand-name' }, 'WBLester & O', el('small', {}, 'From soil to skyline')),
        ),
        el('div', { class: 'header-info' },
          hInfo('i-pin', 'Our Address', s.address || '—'),
          hInfo('i-mail', 'Email Us', s.email || '—'),
          hInfo('i-clock', 'Opening Hours', 'Mon - Fri : 8AM - 5PM'),
          hInfo('i-phone', 'Call Us', s.phoneNumber || '—'),
        ),
      ),
    ),
    el('div', { class: 'container navrow' },
      navToggle(),
      el('nav', { class: 'main-nav', 'aria-label': 'Primary' }, mainMenu(currentPath)),
      el('div', { class: 'nav-phone' },
        el('a', { href: `tel:${(s.phoneNumber || '').replace(/\s+/g, '')}` },
          icon('i-phone'), el('div', {}, el('small', {}, 'Request a callback'), el('b', {}, s.phoneNumber || '')),
        ),
      ),
    ),
  );

  renderMobileNav(currentPath);
}

function hInfo(ic, label, value) {
  return el('div', { class: 'hinfo' }, icon(ic), el('div', {}, el('span', {}, label), value));
}

function landingForCategory(cat) {
  /* Top-most visible page of the category = its overview/landing page.
     Falls back to the category slug when no such page exists. */
  const pages = getContent()?.pages || [];
  const root = pages
    .filter((p) => p.categoryId === cat.categoryId && !p.parentId)
    .sort((a, b) => a.sortOrder - b.sortOrder)[0];
  return root ? root.slug : cat.slug;
}

function menuEntries() {
  return categories().map((cat) => {
    const href = `/page/${landingForCategory(cat)}`;
    return {
      label: cat.categoryName,
      href,
      children: [
        { label: `${cat.categoryName} Overview`, href },
        ...pagesOfCategory(cat.categoryId)
          .filter((p) => p.slug !== landingForCategory(cat))
          .map((p) => ({ label: p.title, href: `/page/${p.slug}` })),
      ],
    };
  });
}

function mainMenu(currentPath) {
  const ul = el('ul', {});
  const add = (label, href, children, extra = {}) => {
    const li = el('li', { class: extra.current ? 'current' : '' });
    li.append(el('a', { href, class: extra.current ? 'active' : '' }, label));
    if (children?.length) {
      const sub = el('ul', { class: 'sub-menu' });
      for (const c of children) {
        sub.append(el('li', {}, el('a', { href: c.href }, c.label)));
      }
      li.append(sub);
    }
    ul.append(li);
  };

  add('Home', '/', null, { current: currentPath === '/' });
  for (const entry of menuEntries()) add(entry.label, entry.href, entry.children);
  add('Contact Us', '/contact', null, { current: currentPath.startsWith('/contact') });
  return ul;
}

function navToggle() {
  return el('button', { class: 'nav-toggle', type: 'button', onclick: openMobileNav },
    icon('i-menu'), 'Menu');
}

function renderMobileNav(currentPath) {
  const host = document.getElementById('mobile-nav-inner');
  host.innerHTML = '';
  host.append(el('a', { href: '/', class: currentPath === '/' ? 'active' : '' }, 'Home'));
  for (const cat of categories()) {
    const landing = landingForCategory(cat);
    host.append(el('div', { class: 'm-group' }, cat.categoryName));
    host.append(el('a', { href: `/page/${landing}` }, `${cat.categoryName} Overview`));
    for (const p of pagesOfCategory(cat.categoryId)) {
      if (p.slug === landing) continue;
      host.append(el('a', { href: `/page/${p.slug}` }, p.title));
    }
  }
  host.append(el('div', { class: 'm-group' }, 'Get in touch'));
  host.append(el('a', { href: '/contact' }, 'Contact Us'));
}

export function openMobileNav() {
  document.getElementById('mobile-nav').classList.add('open');
  document.getElementById('off-canvas-layer').classList.add('show');
}
export function closeMobileNav() {
  document.getElementById('mobile-nav').classList.remove('open');
  document.getElementById('off-canvas-layer').classList.remove('show');
}
document.getElementById('off-canvas-layer').addEventListener('click', closeMobileNav);
document.querySelector('#mobile-nav .close-canvas').addEventListener('click', closeMobileNav);

/* ------------------------------------------------------------------ footer */

export function renderFooter() {
  const s = getSettings();
  const socials = s.socialMedia || {};
  const hours = [
    ['Monday', '8:00 am - 5:00 pm'],
    ['Tuesday', '8:00 am - 5:00 pm'],
    ['Wednesday', '8:00 am - 5:00 pm'],
    ['Thursday', '8:00 am - 5:00 pm'],
    ['Friday', '8:00 am - 5:00 pm'],
    ['Saturday', '9:00 am - 1:00 pm'],
    ['Sunday', 'Closed'],
  ];

  const widgets = el('div', { id: 'footer-widgets', class: 'footer-widgets' },
    el('div', { class: 'container footer-cols' },
      el('div', {},
        el('div', { class: 'f-about' },
          el('img', { src: '/assets/logo.svg', alt: '' }),
          el('b', {}, 'WBLester & O'),
        ),
        el('p', {}, 'WBLester & O brings together agronomists, land advisors and energy consultants who plan, develop and steward land-based assets. From the first soil sample to signed leases and renewable installations — one partner from soil to skyline.'),
        el('div', { class: 'f-social' },
          ...['fb:facebook', 'tw:twitter', 'in:linkedin'].map((pair) => {
            const [key, name] = pair.split(':');
            return el('a', { href: socials[name] || '#', 'aria-label': name, target: '_blank', rel: 'noopener' }, icon(`i-${key}`));
          }),
        ),
      ),
      (() => {
        const menu = el('ul', { class: 'f-menu' });
        for (const p of visiblePages().slice(0, 7)) {
          menu.append(el('li', {}, el('a', { href: `/page/${p.slug}` }, p.title)));
        }
        return el('div', {}, el('h4', {}, 'Explore'), menu);
      })(),
      el('div', {},
        el('h4', {}, 'Contact Us'),
        el('div', { class: 'ft-contact' }, icon('i-pin'), el('p', {}, s.address || '—')),
        el('div', { class: 'ft-contact' }, icon('i-mail'), el('p', {}, s.email || '—')),
        el('div', { class: 'ft-contact' }, icon('i-phone'), el('p', {}, s.phoneNumber || '—')),
        el('div', { class: 'ft-contact' }, icon('i-clock'), el('p', {}, 'Mon-Fri - 8am until 5pm')),
      ),
      el('div', {},
        el('h4', {}, 'Working Hours'),
        el('ul', { class: 'hours' },
          ...hours.map(([day, time]) =>
            el('li', {}, day,
              el('span', { class: time === 'Closed' ? 'hour closed' : 'hour' }, time))),
        ),
      ),
    ),
  );

  const colophon = document.getElementById('colophon');
  colophon.innerHTML = '';
  colophon.append(widgets);
  colophon.append(
    el('footer', { class: 'site-footer' },
      el('div', { class: 'container footer-bar' },
        el('div', {}, `Copyright © ${new Date().getFullYear()} `, el('a', { href: '/' }, 'WBLester & O'), ', All Right Reserved'),
        el('ul', { class: 'footer-menu' },
          el('li', {}, el('a', { href: '/' }, 'Home')),
          el('li', {}, el('a', { href: '/contact' }, 'Request Quote')),
          el('li', {}, el('a', { href: '/admin' }, 'Admin')),
        ),
      ),
    ),
  );

  const up = el('button', { class: 'scroll-top', type: 'button', 'aria-label': 'Back to top', onclick: () => window.scrollTo({ top: 0, behavior: 'smooth' }) }, icon('i-up'));
  document.body.append(up);
  window.addEventListener(
    'scroll',
    () => up.classList.toggle('show', window.scrollY > 480),
    { passive: true },
  );
}

/* ------------------------------------------------------------------- blocks */

const FEATURE_ICONS = ['i-leaf', 'i-shield', 'i-medal', 'i-tree', 'i-drop', 'i-sun', 'i-sprout', 'i-stone'];
const PARTNER_ICONS = ['i-leaf', 'i-shield', 'i-medal', 'i-sun', 'i-sprout', 'i-tree'];

function sectionTitle(block, align = '') {
  return el('div', { class: `sec-title reveal ${align}`.trim() },
    accentTitle(block.title || ''),
    block.intro ? el('p', { class: 'sub' }, block.intro) : null,
  );
}

function asList(v) {
  return Array.isArray(v) ? v : [];
}

export function renderBlock(block, ctx = {}) {
  switch (block.type) {
    case 'jumbotron': return jumbotron(asList(block.slides));
    case 'hero': return pageHero(ctx.page, block);
    case 'richText': return richText(block);
    case 'cards': return cards(block);
    case 'features': return features(block);
    case 'steps': return steps(block);
    case 'stats': return stats(block);
    case 'gallery': return gallery(block);
    case 'about': return aboutSplit(block);
    case 'testimonials': return testimonials(block);
    case 'partners': return partners(block);
    case 'cta': return cta(block);
    case 'contactForm': return quoteSection(block);
    default: return el('div');
  }
}

/* Jumbotron / banner carousel ---------------------------------------------- */
function jumbotron(slidesIn) {
  const slides = slidesIn.length ? shuffled(slidesIn) : [{
    imageUrl: '/uploads/green-hills.jpg',
    kicker: '',
    title: 'From Soil to Skyline',
    subtitle: 'Integrated agriculture, real estate and natural resources services.',
  }];
  const root = el('section', { class: 'hero', id: 'banner' });
  slides.forEach((slide) => {
    root.append(
      el('div', { class: 'hero-slide', style: { backgroundImage: `url("${slide.imageUrl || ''}")` } },
        el('div', { class: 'container hero-caption' },
          slide.kicker ? el('span', { class: 'hero-kicker' }, slide.kicker) : null,
          el('h2', { class: 'hero-title', html: accentHtml(slide.title) }),
          slide.subtitle ? el('p', { class: 'hero-sub' }, slide.subtitle) : null,
          el('div', { class: 'hero-actions' },
            el('a', { class: 'btn btn-outline-w', href: '#services-anchor' }, 'Our Services'),
            el('a', { class: 'btn btn-outline-w', href: '/contact' }, 'Request Quote'),
          ),
        ),
      ),
    );
  });
  root.append(
    el('div', { class: 'hero-dots' }, ...slides.map(() => el('button', { type: 'button', 'aria-label': 'Slide' }))),
    el('div', { class: 'hero-arrows' },
      el('button', { class: 'hero-arrow prev', type: 'button', 'aria-label': 'Previous slide' }, icon('i-up', 'rot-270')),
      el('button', { class: 'hero-arrow next', type: 'button', 'aria-label': 'Next slide' }, icon('i-arrow-r')),
    ),
  );
  requestAnimationFrame(() => initHeroSlider(root));
  return root;
}

function accentHtml(text) {
  return esc(text).replace(/\[([^\]]+)\]/g, '<span class="main-color">$1</span>');
}

/* Inner-page hero band -------------------------------------------------------- */
function pageHero(page, block) {
  const img = block?.imageUrl;
  return el('section', { class: 'page-hero', style: img ? { backgroundImage: `url("${img}")` } : {} },
    el('div', { class: 'container page-hero-in' }, el('h1', {}, page?.title || '')),
    el('div', { class: 'crumbs' },
      el('div', { class: 'container crumbs-in' },
        el('a', { href: '/' }, 'Home'),
        el('span', { class: 'sep' }, '\u203A'),
        breadcrumbTrail(page),
      ),
    ),
  );
}

function breadcrumbTrail(page) {
  const parts = [];
  const cat = getContent()?.categories.find((c) => c.categoryId === page?.categoryId);
  if (page?.parentId) {
    const parentPage = getContent()?.pages.find((p) => p.pageId === page.parentId);
    /* /public/content already filters to visible pages, so presence is enough */
    if (parentPage) parts.push(el('a', { href: `/page/${parentPage.slug}` }, parentPage.title), el('span', { class: 'sep' }, '\u203A'));
  } else if (cat && !isCategoryLanding(page)) {
    parts.push(el('a', { href: `/page/${landingForCategory(cat)}` }, cat.categoryName), el('span', { class: 'sep' }, '\u203A'));
  }
  parts.push(el('span', { class: 'here' }, page?.title || ''));
  return parts;
}

function isCategoryLanding(page) {
  const cat = getContent()?.categories.find((c) => c.categoryId === page?.categoryId);
  return cat ? page?.slug === landingForCategory(cat) : false;
}

/* richText ---------------------------------------------------------------------- */
function richText(block) {
  const body = rich(block.html || '');
  if (!body.trim()) return el('div');
  return el('section', { class: 'secpadd', style: { padding: '70px 0' } },
    el('div', { class: 'container prose reveal', html: body }),
  );
}

/* Cards (services grid) ------------------------------------------------------------ */
function cards(block) {
  const items = asList(block.items);
  return el('section', { class: 'secpadd', id: 'services-anchor' },
    el('div', { class: 'container' },
      sectionTitle({ title: block.title, intro: block.intro }, 'text-center'),
      el('div', { class: 'services-grid' },
        ...items.map((item) =>
          el('article', { class: 'svc-card reveal' },
            item.imageUrl
              ? el('a', { class: 'svc-thumb', href: linkFor(item) },
                el('img', { src: item.imageUrl, alt: esc(item.title || ''), loading: 'lazy' }))
              : null,
            el('div', { class: 'svc-body' },
              el('h3', {}, el('a', { href: linkFor(item) }, item.title || '')),
              el('p', {}, item.text || ''),
              el('a', { class: 'btn-link', href: linkFor(item) }, 'Read More', icon('i-arrow-r')),
            ),
          )),
      ),
    ),
  );
}

function linkFor(item) {
  if (!item.slug) return '/contact';
  if (item.slug === 'contact') return '/contact';
  return `/page/${item.slug}`;
}

/* Features (icon boxes) --------------------------------------------------------------- */
function features(block) {
  const items = asList(block.items);
  return el('section', { class: 'secpadd features-band' },
    el('div', { class: 'container' },
      sectionTitle({ title: block.title, intro: block.intro }, 'text-center'),
      el('div', { class: 'features-grid' },
        ...items.map((item, i) =>
          el('div', { class: 'feat-box reveal' },
            el('div', { class: 'bubble' }, icon(FEATURE_ICONS[i % FEATURE_ICONS.length])),
            el('h4', {}, item.title || ''),
            el('p', {}, item.text || ''),
          )),
      ),
    ),
  );
}

/* Steps ------------------------------------------------------------------------------------ */
function steps(block) {
  const items = asList(block.items);
  return el('section', { class: 'secpadd' },
    el('div', { class: 'container' },
      sectionTitle({ title: block.title, intro: block.intro }, 'text-center'),
      el('div', { class: 'steps-grid' },
        ...items.map((item, i) =>
          el('div', { class: 'step-card reveal' },
            el('div', { class: 'step-num' }, String(i + 1).padStart(2, '0')),
            el('h4', {}, item.title || ''),
            el('p', {}, item.text || ''),
          )),
      ),
    ),
  );
}

/* Stats parallax ------------------------------------------------------------------------------- */
function stats(block) {
  const items = asList(block.items);
  return el('section', { class: 'stats-band secpadd', style: { backgroundImage: `url("${block.backgroundImage || ''}")` } },
    el('div', { class: 'container stats-in' },
      ...items.map((item) =>
        el('div', { class: 'stat reveal' },
          el('b', { 'data-count': Number(String(item.value).replace(/[^0-9.]/g, '')) || 0, 'data-suffix': String(item.value ?? '').includes('+') ? '+' : (String(item.value ?? '').match(/[A-Za-z%]+$/) || [''])[0] }, '0'),
          el('span', {}, item.label || ''),
        )),
    ),
  );
}

/* Gallery with filters ---------------------------------------------------------------------------- */
function gallery(block) {
  const items = asList(block.items);
  const cats = [...new Set(items.map((i) => i.category).filter(Boolean))];
  return el('section', { class: 'secpadd' },
    el('div', { class: 'container' },
      sectionTitle({ title: block.title, intro: block.intro }, 'text-center'),
      cats.length
        ? el('div', { class: 'gallery-filters', style: { justifyContent: 'center' } },
          el('button', { class: 'active', type: 'button', 'data-filter': '*' }, 'All'),
          ...cats.map((c) => el('button', { type: 'button', 'data-filter': c }, c)))
        : null,
      el('div', { class: 'gallery-grid' },
        ...items.map((item) =>
          el('figure', { class: 'gal-item reveal', 'data-cat': item.category || '' },
            el('img', { src: item.imageUrl, alt: esc(item.caption || ''), loading: 'lazy' }),
            el('figcaption', { class: 'gal-overlay' },
              el('h4', {}, item.caption || ''),
              item.category ? el('small', {}, item.category) : null,
            ),
          )),
      ),
    ),
  );
}

/* About split ----------------------------------------------------------------------------------------- */
function aboutSplit(block) {
  const imgs = asList(block.images);
  const points = asList(block.points);
  return el('section', { class: 'secpadd' },
    el('div', { class: 'container about-split' },
      el('div', { class: 'reveal' },
        el('div', { class: 'about-imgs' },
          ...(imgs.slice(0, 2).map((src) => el('img', { src, alt: esc(block.title || ''), loading: 'lazy' })))),
        points.length
          ? el('ul', { class: 'about-points' },
            ...points.map((pt) => el('li', {}, icon('i-check'), pt)))
          : null,
        el('a', { class: 'btn btn-green', href: '/contact' }, 'Request A Quote'),
      ),
      el('div', { class: 'reveal' },
        sectionTitle({ title: block.title }, 'left'),
        block.lead ? el('p', { class: 'green-para' }, block.lead) : null,
        el('div', { html: rich(block.body || '') }),
      ),
    ),
  );
}

/* Testimonials --------------------------------------------------------------------------------------------- */
function testimonials(block) {
  const items = asList(block.items);
  return el('section', { class: 'testi-band secpadd' },
    el('div', { class: 'container' },
      el('h3', { class: 'feed-title' }, icon('i-quote'), 'Customer Feedback'),
      el('div', { class: 'testi-track' },
        ...items.map((t) =>
          el('blockquote', { class: 'testi-card reveal' },
            icon('i-quote', 'quote'),
            t.title ? el('h4', {}, t.title) : null,
            el('p', {}, t.quote || ''),
            el('div', { class: 'testi-meta' },
              el('div', {}, el('b', {}, t.name || ''), el('small', {}, t.role || '')),
              el('div', { class: 'testi-stars' }, ...Array.from({ length: 5 }, () => icon('i-star', 'fill'))),
            ),
          )),
      ),
    ),
  );
}

/* Partners strip ------------------------------------------------------------------------------------------------ */
function partners(block) {
  const items = asList(block.items);
  if (!items.length) return el('div');
  return el('section', { class: 'partners' },
    el('div', { class: 'container partners-row' },
      ...items.map((item, i) =>
        el('div', { class: 'partner-chip reveal' }, icon(PARTNER_ICONS[i % PARTNER_ICONS.length]), item.label || '')),
    ),
  );
}

/* CTA band ---------------------------------------------------------------------------------------------------------- */
function cta(block) {
  return el('section', { class: 'cta-band', style: { padding: '56px 0' } },
    el('div', { class: 'container cta-in' },
      el('div', {},
        accentTitle(block.title || '', 'h2').cloneNode(true),
        block.text ? el('p', {}, block.text) : null),
      el('a', { class: 'btn btn-outline-w', style: { borderColor: '#fff' }, href: '/contact' }, block.buttonLabel || 'Request This Service'),
    ),
  );
}

/* Quote form (+ optional map via settings.googleMap) ------------------------------------------------------------------ */
export function quoteSection(block = {}) {
  const s = getSettings();
  return el('section', { class: 'secpadd', style: { background: 'var(--tint)' } },
    el('div', { class: 'container' },
      sectionTitle({ title: block.title || 'Request a Free Quote', intro: block.intro || 'Tell us about your project and our team will respond within one business day.' }, 'text-center'),
      el('form', { class: 'quote-form', style: { maxWidth: '900px', margin: '0 auto' } },
        el('div', { class: 'form-grid' },
          field('text', 'name', 'Your Name*', true),
          field('text', 'phone', 'Phone Number*', true),
          field('email', 'email', 'Email Id*', true),
          field('text', 'subject', block.subjectPlaceholder || 'Subject'),
          el('div', { class: 'field full' },
            el('textarea', { name: 'body', placeholder: 'Your Message...', required: true })),
          el('div', { class: 'field full' },
            el('button', { class: 'btn btn-green full', type: 'submit', style: { width: '100%' } }, 'Submit Request')),
        ),
        el('p', { class: 'form-note' }, el('b', {}, 'Note: '), 'We don\u2019t do spam and your mail id is very confidential.'),
        el('p', { class: 'form-status', 'data-status': '1' }),
      ),
      s.googleMap
        ? el('div', { class: 'map-area', style: { marginTop: '56px' } },
          el('iframe', { src: s.googleMap, loading: 'lazy', title: 'Our location', referrerPolicy: 'no-referrer-when-downgrade' }))
        : null,
    ),
  );
}

function field(type, name, placeholder, required) {
  return el('div', { class: 'field' },
    el('input', { type, name, placeholder, required: required ? '' : null }));
}

export function wireQuoteForms(root) {
  root.querySelectorAll('form.quote-form').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const status = form.querySelector('[data-status]');
      const data = Object.fromEntries(new FormData(form).entries());
      status.className = 'form-status';
      status.textContent = 'Sending...';
      const res = await postContactForm(data);
      if (res.ok) {
        form.reset();
        status.className = 'form-status ok';
        status.textContent = 'Thank you! Your request has been received — we will be in touch shortly.';
      } else {
        status.className = 'form-status err';
        status.textContent = res.data?.message || 'Something went wrong. Please try again.';
      }
    });
  });
}

/* -------------------------------------------------------------------- views */

export function blocksOf(page) {
  return page?.contentJson?.blocks || [];
}

export function renderViewInto(host, nodes) {
  host.innerHTML = '';
  host.append(...nodes.flat());
  observeReveals(host);
  initCounters(host);
  initGalleryFilters(host);
  wireQuoteForms(host);
}

export function homeView() {
  const home = homePage();
  const nodes = [];
  for (const block of blocksOf(home)) {
    nodes.push(renderBlock(block, { page: home }));
  }
  if (!nodes.length) {
    nodes.push(el('section', { class: 'secpadd text-center' },
      el('h2', {}, 'Welcome to ', el('span', { class: 'main-color' }, 'WBLester & O'))));
  }
  return nodes;
}

export function pageView(slug) {
  const page = pageBySlug(slug);
  if (!page) return null;
  const nodes = [];
  for (const block of blocksOf(page)) {
    nodes.push(renderBlock(block, { page }));
  }

  /* /public/content already filters to visible pages */
  const subs = (getContent()?.pages || []).filter(
    (p) => p.parentId === page.pageId,
  ).sort((a, b) => a.sortOrder - b.sortOrder);

  if (subs.length) {
    nodes.push(subpagesBand(subs));
  }
  return nodes;
}

function subpagesBand(subs) {
  return el('section', { class: 'secpadd', style: { paddingTop: '20px' } },
    el('div', { class: 'container' },
      sectionTitle({ title: 'Related Services', intro: 'Explore more within this practice area.' }, 'text-center'),
      el('div', { class: 'services-grid', style: { gridTemplateColumns: 'repeat(3, 1fr)' } },
        ...subs.map((sub) =>
          el('article', { class: 'svc-card reveal' },
            el('div', { class: 'svc-body' },
              el('h3', {}, el('a', { href: `/page/${sub.slug}` }, sub.title)),
              seoOrIntro(sub),
              el('a', { class: 'btn-link', href: `/page/${sub.slug}` }, 'Learn More', icon('i-arrow-r')),
            )))),
    ));
}

function seoOrIntro(sub) {
  const firstRich = blocksOf(sub).find((b) => b.type === 'richText');
  const text = (firstRich?.html || '').replace(/<[^>]+>/g, ' ').trim();
  const short = text.split(/\s+/).slice(0, 22).join(' ');
  return el('p', {}, short ? `${short}…` : '');
}

export function contactView() {
  const s = getSettings();
  return [
    el('section', { class: 'page-hero', style: { backgroundImage: 'url("/uploads/garden-estate.jpg")' } },
      el('div', { class: 'container page-hero-in' }, el('h1', {}, 'Contact Us')),
      el('div', { class: 'crumbs' },
        el('div', { class: 'container crumbs-in' },
          el('a', { href: '/' }, 'Home'), el('span', { class: 'sep' }, '\u203A'),
          el('span', { class: 'here' }, 'Contact')))),
    el('section', { class: 'secpadd' },
      el('div', { class: 'container' },
        sectionTitle({ title: 'We Are Here to Help You Grow', intro: 'Reach out for consultations, valuations, lease negotiations or renewable feasibility studies.' }, 'text-center'),
        el('div', { class: 'contact-cards' },
          contactCard('i-pin', 'Visit Us', s.address || '—'),
          contactCard('i-mail', 'Email Us', s.email || '—'),
          contactCard('i-phone', 'Call Now', s.phoneNumber || '—'),
        ),
      ),
      quoteSection({}),
    ),
  ];
}

function contactCard(ic, title, value) {
  return el('div', { class: 'contact-card reveal' },
    el('div', { class: 'bubble' }, icon(ic)),
    el('h4', {}, title),
    el('div', {}, value),
  );
}
