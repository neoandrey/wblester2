/* Admin area served inside the SPA under /admin.
   JWT login + pages/categories/messages/settings management against the
   existing /cpanel/jwt/* endpoints. */

import {
  login as apiLogin,
  logout,
  getTokens,
  dataTable,
  GET,
  PUT,
  POST,
} from '../api.js';
import { el, icon, esc } from '../ui.js';
import { refresh } from '../store.js';

const MENU = [
  ['dashboard', 'i-grid', 'Dashboard'],
  ['pages', 'i-file', 'Pages'],
  ['categories', 'i-grid', 'Categories'],
  ['messages', 'i-inbox', 'Messages'],
  ['settings', 'i-cog', 'Site Settings'],
  ['events', 'i-clock', 'Events'],
  ['jobs', 'i-check', 'Jobs'],
];

export function adminRoute(host) {
  if (!getTokens()) {
    renderLogin(host);
    return;
  }
  const section = location.pathname.replace(/^\/admin\/?/, '') || 'dashboard';
  renderShell(host, section);
}

/* ------------------------------------------------------------------ login */
function renderLogin(host) {
  host.innerHTML = '';
  host.className = 'admin-root';
  const card = el('div', { class: 'login-card' },
    el('div', { class: 'login-brand' },
      el('img', { src: '/assets/logo.svg', alt: '' }),
      el('h2', {}, 'WBLester & O ', el('span', { class: 'main-color' }, 'Admin')),
    ),
    el('form', { class: 'login-form' },
      labelInput('text', 'username', 'Username'),
      labelInput('password', 'password', 'Password'),
      el('button', { class: 'btn btn-green full', type: 'submit' }, 'Sign In'),
      el('p', { class: 'form-status', 'data-status': '1' }),
      el('a', { class: 'back-link', href: '/' }, '\u2190 Back to website'),
    ),
  );
  card.querySelector('form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    const status = card.querySelector('[data-status]');
    status.textContent = 'Signing in…';
    status.className = 'form-status';
    const res = await apiLogin(data.username, data.password);
    if (res.ok) adminRoute(host);
    else {
      status.className = 'form-status err';
      status.textContent = res.message;
    }
  });
  host.append(card);
}

function labelInput(type, name, placeholder) {
  return el('input', { type, name, placeholder, required: '', autocomplete: 'off' });
}

/* ------------------------------------------------------------------ shell */
function renderShell(host, section) {
  host.innerHTML = '';
  host.className = 'admin-root';

  const sidebar = el('aside', { class: 'a-sidebar' },
    el('div', { class: 'a-brand' },
      el('img', { src: '/assets/logo.svg', alt: '' }),
      el('b', {}, 'WBLester ', el('span', { class: 'main-color' }, '& O')),
    ),
    el('nav', {},
      ...MENU.map(([key, ic, label]) =>
        el('a', { href: `/admin/${key}`, class: section === key ? 'active' : '' },
          icon(ic), el('span', {}, label))),
    ),
    el('button', { class: 'a-logout', type: 'button' }, icon('i-out'), 'Sign Out'),
    el('a', { class: 'a-viewsite', href: '/', target: '_blank' }, icon('i-eye'), 'View site'),
  );
  sidebar.querySelector('.a-logout').addEventListener('click', () => {
    logout();
    location.href = '/admin';
  });

  const main = el('main', { class: 'a-main' },
    el('div', { class: 'a-head' },
      el('h1', {}, MENU.find(([k]) => k === section)?.[2] || 'Dashboard'),
      el('button', { class: 'btn btn-outline-g', type: 'button', onclick: manualSync },
        icon('i-refresh'), 'Sync now'),
    ),
    el('div', { class: 'a-body', 'data-section': section }),
  );

  host.append(sidebar, main);
  void loadSection(main.querySelector('.a-body'), section);
}

async function manualSync() {
  await refresh();
}

async function loadSection(body, section) {
  body.innerHTML = '<p class="a-loading">Loading…</p>';
  try {
    switch (section) {
      case 'dashboard': return await dashboard(body);
      case 'pages': return await pagesSection(body);
      case 'categories': return await categoriesSection(body);
      case 'messages': return await messagesSection(body);
      case 'settings': return await settingsSection(body);
      case 'events': return await eventsSection(body);
      case 'jobs': return await jobsSection(body);
      default: body.textContent = 'Unknown section';
    }
  } catch (err) {
    body.innerHTML = `<p class="form-status err">${esc(String(err))}</p>`;
  }
}

/* -------------------------------------------------------------- dashboard */
const STATUS_LABELS = { 0: 'NEW', 1: 'READ', 2: 'REPLIED', 3: 'ARCHIVED', 4: 'TRASHED' };
const STATUS_NEW = 0;
const STATUS_READ = 1;

async function dashboard(body) {
  const [pagesRes, catsRes, msgsRes] = await Promise.all([
    dataTable.list('Pages'),
    dataTable.list('Categories'),
    dataTable.list('Messages'),
  ]);
  const pages = pagesRes.data?.Pages || [];
  const cats = catsRes.data?.Categories || [];
  const msgs = msgsRes.data?.Messages || [];
  const unread = msgs.filter((m) => m.status === STATUS_NEW).length;

  body.innerHTML = '';
  body.append(
    el('div', { class: 'stat-cards' },
      statCard('i-file', pages.length, 'Total pages'),
      statCard('i-eye', pages.filter((p) => p.visible).length, 'Published'),
      statCard('i-grid', cats.length, 'Categories'),
      statCard('i-inbox', unread, 'New messages'),
    ),
    el('h3', {}, 'Quick actions'),
    el('div', { class: 'quick-row' },
      el('a', { class: 'btn btn-green', href: '/admin/pages' }, 'Edit page content'),
      el('a', { class: 'btn btn-outline-g', href: '/admin/settings' }, 'Banner & settings'),
      el('a', { class: 'btn btn-outline-g', href: '/admin/messages' }, 'Inbox'),
    ),
    el('p', { class: 'hint' },
      'Content edits are pushed live to every visitor within one sync cycle (60s max).'),
  );
}

function statCard(ic, value, label) {
  return el('div', { class: 'stat-card' },
    el('div', { class: 'bubble' }, icon(ic)),
    el('b', {}, String(value ?? 0)),
    el('span', {}, label),
  );
}

/* ------------------------------------------------------------------ pages */
const BLOCK_SPECS = {
  jumbotron: {
    label: 'Banner carousel',
    fields: [],
    itemsField: 'slides',
    itemLabel: 'Slide',
    itemFields: [
      ['imageUrl', 'Image URL (/uploads/…)'],
      ['kicker', 'Kicker line'],
      ['title', 'Title ([word] shows in green)'],
      ['subtitle', 'Subtitle'],
    ],
  },
  hero: { label: 'Page header image', fields: [['imageUrl', 'Background image URL']] },
  richText: { label: 'Rich text', fields: [['html', 'HTML content', 'textarea']] },
  cards: {
    label: 'Services grid',
    fields: [['title', 'Section title'], ['intro', 'Intro paragraph', 'textarea']],
    itemsField: 'items',
    itemLabel: 'Card',
    itemFields: [
      ['imageUrl', 'Image URL'],
      ['title', 'Title'],
      ['text', 'Text', 'textarea'],
      ['slug', 'Links to slug'],
    ],
  },
  features: {
    label: 'Feature boxes',
    fields: [['title', 'Section title'], ['intro', 'Intro paragraph', 'textarea']],
    itemsField: 'items',
    itemLabel: 'Feature',
    itemFields: [['title', 'Title'], ['text', 'Text', 'textarea']],
  },
  steps: {
    label: 'Process steps',
    fields: [['title', 'Section title'], ['intro', 'Intro paragraph', 'textarea']],
    itemsField: 'items',
    itemLabel: 'Step',
    itemFields: [['title', 'Title'], ['text', 'Text', 'textarea']],
  },
  stats: {
    label: 'Counters band',
    fields: [['backgroundImage', 'Background image URL']],
    itemsField: 'items',
    itemLabel: 'Counter',
    itemFields: [['value', 'Value (e.g. 30+)'], ['label', 'Label']],
  },
  gallery: {
    label: 'Gallery',
    fields: [['title', 'Section title'], ['intro', 'Intro paragraph', 'textarea']],
    itemsField: 'items',
    itemLabel: 'Photo',
    itemFields: [
      ['imageUrl', 'Image URL'],
      ['caption', 'Caption'],
      ['category', 'Filter tag'],
    ],
  },
  about: {
    label: 'About split',
    fields: [
      ['title', 'Title'],
      ['lead', 'Green lead line'],
      ['body', 'Body HTML', 'textarea'],
    ],
    itemsField: 'images',
    itemLabel: 'Photo URL',
    itemFields: [],
    stringItems: true,
  },
  testimonials: {
    label: 'Testimonials',
    fields: [],
    itemsField: 'items',
    itemLabel: 'Quote',
    itemFields: [
      ['title', 'Headline'],
      ['quote', 'Quote', 'textarea'],
      ['name', 'Author'],
      ['role', 'Location / role'],
    ],
  },
  partners: {
    label: 'Partners strip',
    fields: [],
    itemsField: 'items',
    itemLabel: 'Chip',
    itemFields: [['label', 'Label']],
  },
  cta: {
    label: 'CTA band',
    fields: [
      ['title', 'Title'],
      ['text', 'Text', 'textarea'],
      ['buttonLabel', 'Button label'],
    ],
  },
  contactForm: { label: 'Quote form', fields: [['title', 'Title'], ['intro', 'Intro', 'textarea']] },
};

const BLOCK_TYPES = Object.keys(BLOCK_SPECS);

async function pagesSection(body) {
  const res = await dataTable.list('Pages');
  const pages = (res.data?.Pages || []).sort((a, b) => a.pageId - b.pageId);
  const catsRes = await dataTable.list('Categories');
  const cats = catsRes.data?.Categories || [];

  body.innerHTML = '';
  body.append(
    el('div', { class: 'table-toolbar' },
      el('input', { type: 'search', placeholder: 'Filter by title or slug…', 'data-filter': '1' }),
      el('button', { class: 'btn btn-green', type: 'button', onclick: () => openEditor(null) },
        icon('i-plus'), 'New Page'),
    ),
    el('div', { class: 'table-wrap' },
      el('table', { class: 'a-table' },
        el('thead', {}, el('tr', {},
          th('ID'), th('Title'), th('Slug'), th('Category'), th('Order'), th('Visible'), th(''))),
        el('tbody', { 'data-rows': '1' }),
      ),
    ),
  );

  const rows = body.querySelector('[data-rows]');
  const drawRows = (filter = '') => {
    rows.innerHTML = '';
    for (const p of pages) {
      const hay = `${p.title} ${p.slug}`.toLowerCase();
      if (filter && !hay.includes(filter.toLowerCase())) continue;
      const cat = cats.find((c) => c.categoryId === p.categoryId);
      rows.append(el('tr', {},
        td(p.pageId),
        td(p.title),
        td(p.slug),
        td(cat?.categoryName || '—'),
        td(p.sortOrder),
        td(p.visible ? 'Yes' : 'No'),
        el('td', { class: 'row-actions' },
          el('button', { class: 'icon-btn', title: 'Edit', type: 'button', onclick: () => openEditor(p) }, icon('i-edit')),
          el('a', { class: 'icon-btn', title: 'View', href: `/page/${p.slug}`, target: '_blank' }, icon('i-eye')),
          el('button', { class: 'icon-btn danger', title: 'Delete', type: 'button', onclick: () => removeRecord('Pages', p.pageId, p.title) }, icon('i-trash')),
        ),
      ));
    }
  };
  drawRows();
  body.querySelector('[data-filter]').addEventListener('input', (e) => drawRows(e.target.value));

  async function openEditor(page) {
    const isNew = !page;
    const record = structuredClone(page || {
      pageId: null, categoryId: null, parentId: null, title: '',
      slug: '', visible: true, sortOrder: 10, seoTitle: '', seoDescription: '',
      contentJson: { blocks: [] },
    });
    const overlay = el('div', { class: 'modal-overlay' });
    const dialog = el('div', { class: 'modal wide' });
    overlay.append(dialog);
    document.body.append(overlay);

    const close = () => overlay.remove();

    let blocks = record.contentJson?.blocks || [];
    let rawMode = false;

    const drawBlocks = () => {
      const wrap = el('div', {});
      wrap.append(
        el('div', { class: 'blocks-head' },
          el('h3', {}, 'Content blocks'),
          el('div', { style: { display: 'flex', gap: '8px' } },
            el('select', { class: 'add-block', onchange: (e) => {
              if (!e.target.value) return;
              addBlock(e.target.value);
            } },
              el('option', { value: '' }, '+ Add block…'),
              ...BLOCK_TYPES.map((t) => el('option', { value: t }, BLOCK_SPECS[t].label)),
            ),
            el('button', { class: 'btn btn-outline-g', type: 'button', onclick: () => { rawMode = !rawMode; draw(); } },
              rawMode ? 'Structured mode' : 'Raw JSON mode'),
          ),
        ),
      );
      if (rawMode) {
        wrap.append(el('textarea', { class: 'raw-json', spellcheck: 'false' },
          JSON.stringify({ blocks }, null, 2)));
      } else {
        blocks.forEach((block, index) => {
          wrap.append(blockEditor(block, index));
        });
        if (!blocks.length) wrap.append(el('p', { class: 'hint' }, 'No blocks yet — add one above.'));
      }
      return wrap;
    };

    function addBlock(type) {
      const fresh = { type };
      const spec = BLOCK_SPECS[type];
      for (const [f] of spec.fields || []) fresh[f] = '';
      if (spec.itemsField) fresh[spec.itemsField] = spec.stringItems ? [] : [];
      if (type === 'jumbotron') fresh.slides = [{ imageUrl: '', kicker: '', title: '', subtitle: '' }];
      blocks.push(fresh);
      draw();
    }

    function blockEditor(block, index) {
      const spec = BLOCK_SPECS[block.type] || { label: block.type, fields: [] };
      const cardEl = el('details', { class: 'block-card', open: '' });
      const summary = el('summary', {},
        el('b', {}, `${index + 1}. ${spec.label}`),
        el('span', { class: 'block-type' }, block.type),
      );
      const inner = el('div', { class: 'block-inner' });

      for (const [field, labelText, kind] of spec.fields || []) {
        inner.append(labeledField(labelText, block[field] ?? '', (v) => { block[field] = v; }, kind));
      }

      if (spec.itemsField && Array.isArray(block[spec.itemsField])) {
        const listWrap = el('div', { class: 'item-list' });
        const redrawList = () => {
          listWrap.innerHTML = '';
          block[spec.itemsField].forEach((entry, i) => {
            const row = el('fieldset', { class: 'item-entry' },
              el('legend', {}, `${spec.itemLabel} ${i + 1}`));
            if (spec.stringItems) {
              row.append(textControl('', entry ?? '', (v) => { block[spec.itemsField][i] = v; }));
            } else {
              for (const [field, labelText, kind] of spec.itemFields) {
                row.append(labeledField(labelText, entry[field] ?? '', (v) => { entry[field] = v; }, kind));
              }
            }
            row.append(
              el('button', { class: 'mini-btn danger', type: 'button', onclick: () => { block[spec.itemsField].splice(i, 1); redrawList(); draw(); } },
                icon('i-trash'), 'Remove'),
              el('button', { class: 'mini-btn', type: 'button', onclick: () => moveItem(block[spec.itemsField], i, -1) }, '\u2191'),
              el('button', { class: 'mini-btn', type: 'button', onclick: () => moveItem(block[spec.itemsField], i, +1) }, '\u2193'),
            );
            listWrap.append(row);
          });
        };
        redrawList();
        inner.append(listWrap);
        inner.append(el('button', { class: 'mini-btn', type: 'button', onclick: () => {
          block[spec.itemsField].push(spec.stringItems ? '' : emptyItem(spec));
          redrawList();
          draw();
        } }, icon('i-plus'), `Add ${spec.itemLabel.toLowerCase()}`));
      }

      cardEl.append(summary, el('div', { class: 'block-actions' },
        el('button', { class: 'mini-btn', type: 'button', onclick: () => moveItem(blocks, index, -1) }, '\u2191 Up'),
        el('button', { class: 'mini-btn', type: 'button', onclick: () => moveItem(blocks, index, +1) }, '\u2193 Down'),
        el('button', { class: 'mini-btn danger', type: 'button', onclick: () => { blocks.splice(index, 1); draw(); } },
          icon('i-trash'), 'Delete block'),
      ), inner);
      return cardEl;
    }

    function emptyItem(spec) {
      const out = {};
      for (const [f] of spec.itemFields || []) out[f] = '';
      return out;
    }

    function moveItem(arr, index, delta) {
      const to = index + delta;
      if (to < 0 || to >= arr.length) return;
      [arr[index], arr[to]] = [arr[to], arr[index]];
      draw();
    }

    async function save() {
      if (rawMode) {
        try {
          const parsed = JSON.parse(dialog.querySelector('.raw-json').value);
          blocks = Array.isArray(parsed.blocks) ? parsed.blocks : [];
        } catch (err) {
          alert(`Invalid JSON: ${err.message}`);
          return;
        }
      }
      record.contentJson = { blocks };
      const payload = snakePayload(record);
      const res = await dataTable.upsert('Pages', payload);
      if (!res.ok) {
        alert(res.data?.message || 'Save failed');
        return;
      }
      await refresh();
      close();
      void loadSection(document.querySelector('.a-body'), 'pages');
    }

    function draw() {
      dialog.innerHTML = '';
      dialog.append(
        el('div', { class: 'modal-head' },
          el('h2', {}, isNew ? 'New Page' : `Edit — ${record.title}`),
          el('button', { class: 'icon-btn', type: 'button', onclick: close }, icon('i-close'))),
        el('div', { class: 'modal-grid' },
          labeledField('Title', record.title, (v) => { record.title = v; }),
          labeledField('Slug', record.slug, (v) => { record.slug = v; }),
          selectField('Category', record.categoryId, cats, (v) => { record.categoryId = v ? Number(v) : null; }),
          numberField('Sort order', record.sortOrder, (v) => { record.sortOrder = Number(v); }),
          labeledField('SEO title', record.seoTitle || '', (v) => { record.seoTitle = v; }),
          labeledField('SEO description', record.seoDescription || '', (v) => { record.seoDescription = v; }, 'textarea'),
          checkField('Visible', record.visible, (v) => { record.visible = v; }),
        ),
        drawBlocks(),
        el('div', { class: 'modal-foot' },
          el('button', { class: 'btn btn-outline-g', type: 'button', onclick: close }, 'Cancel'),
          el('button', { class: 'btn btn-green', type: 'button', onclick: save }, icon('i-save'), 'Save & publish')),
      );
    }
    draw();
  }
}

function snakePayload(record) {
  const map = {
    pageId: 'page_id', categoryId: 'category_id', parentId: 'parent_id',
    sortOrder: 'sort_order', seoTitle: 'seo_title',
    seoDescription: 'seo_description', contentJson: 'content_json',
    categoryName: 'category_name', settingsId: 'settings_id',
    siteName: 'site_name', siteTitle: 'site_title',
    siteDescription: 'site_description', phoneNumber: 'phone_number',
    contactUsMessage: 'contact_us_message', googleMap: 'google_map',
    socialMedia: 'social_media', mailingList: 'mailing_list',
    homePageId: 'home_page_id', messageId: 'message_id', fromName: 'from_name',
    sentAt: 'sent_at', currentVersion: 'current_version',
  };
  const out = {};
  for (const [k, v] of Object.entries(record)) out[map[k] || k] = v;
  return out;
}

/* ------------------------------------------------------------- categories */
async function categoriesSection(body) {
  const res = await dataTable.list('Categories');
  const cats = (res.data?.Categories || []).sort((a, b) => a.categoryId - b.categoryId);
  body.innerHTML = '';

  body.append(el('div', { class: 'table-toolbar' },
    el('button', { class: 'btn btn-green', type: 'button', onclick: () => editCat(null) },
      icon('i-plus'), 'New Category')));

  const rows = el('tbody', {});
  const table = el('div', { class: 'table-wrap' },
    el('table', { class: 'a-table' },
      el('thead', {}, el('tr', {},
        th('ID'), th('Name'), th('Slug'), th('Order'), th('Visible'), th(''))),
      rows));
  body.append(table);

  const redraw = () => {
    rows.innerHTML = '';
    for (const c of cats) {
      rows.append(el('tr', {},
        td(c.categoryId), td(c.categoryName), td(c.slug),
        td(c.sortOrder), td(c.visible ? 'Yes' : 'No'),
        el('td', { class: 'row-actions' },
          el('button', { class: 'icon-btn', type: 'button', onclick: () => editCat(c) }, icon('i-edit')),
          el('button', { class: 'icon-btn danger', type: 'button', onclick: () => removeRecord('Categories', c.categoryId, c.categoryName) }, icon('i-trash')),
        )));
    }
  };

  function editCat(cat) {
    const isNew = !cat;
    const record = structuredClone(cat || {
      categoryId: null, parentId: null, categoryName: '',
      slug: '', visible: true, sortOrder: 10,
    });
    const overlay = el('div', { class: 'modal-overlay' });
    const dialog = el('div', { class: 'modal' });
    overlay.append(dialog);
    document.body.append(overlay);
    const draw = () => {
      dialog.innerHTML = '';
      dialog.append(
        el('div', { class: 'modal-head' },
          el('h2', {}, isNew ? 'New Category' : `Edit — ${record.categoryName}`),
          el('button', { class: 'icon-btn', type: 'button', onclick: () => overlay.remove() }, icon('i-close'))),
        el('div', { class: 'modal-grid' },
          labeledField('Name', record.categoryName, (v) => { record.categoryName = v; }),
          labeledField('Slug', record.slug, (v) => { record.slug = v; }),
          numberField('Sort order', record.sortOrder, (v) => { record.sortOrder = Number(v); }),
          checkField('Visible', record.visible, (v) => { record.visible = v; })),
        el('div', { class: 'modal-foot' },
          el('button', { class: 'btn btn-outline-g', type: 'button', onclick: () => overlay.remove() }, 'Cancel'),
          el('button', {
            class: 'btn btn-green', type: 'button',
            onclick: async () => {
              const res = await dataTable.upsert('Categories', snakePayload(record));
              if (!res.ok) return alert(res.data?.message || 'Save failed');
              overlay.remove();
              await refresh();
              void loadSection(document.querySelector('.a-body'), 'categories');
            },
          }, icon('i-save'), 'Save')),
      );
    };
    draw();
  }
  redraw();
}

/* ---------------------------------------------------------------- messages */
async function messagesSection(body) {
  const res = await dataTable.list('Messages');
  const msgs = (res.data?.Messages || []).sort((a, b) => b.messageId - a.messageId);
  body.innerHTML = '';
  if (!msgs.length) {
    body.append(el('p', { class: 'hint' }, 'No messages yet.'));
    return;
  }
  body.append(el('div', { class: 'msg-list' },
    ...msgs.map((m) =>
      el('article', { class: `msg-card ${m.status === STATUS_NEW ? 'unread' : ''}` },
        el('header', {},
          el('b', {}, m.subject || '(no subject)'),
          el('small', {}, `${m.fromName} · ${m.fromEmail} · ${String(m.sentAt || '').slice(0, 10)}`),
          el('span', { class: `badge ${m.status === STATUS_NEW ? 'new' : ''}` }, STATUS_LABELS[m.status] ?? String(m.status))),
        el('p', {}, m.body || ''),
        el('footer', {},
          el('a', { class: 'mini-btn', href: `mailto:${m.fromEmail}?subject=Re: ${encodeURIComponent(m.subject || '')}` }, 'Reply by email'),
          m.status !== STATUS_READ
            ? el('button', { class: 'mini-btn', type: 'button', onclick: (e) => markRead(m.messageId, e.target.closest('article')) }, 'Mark read')
            : null)))));

  async function markRead(id, cardEl) {
    const res = await PUT(`/cpanel/jwt/messages/${id}/status`, { status: STATUS_READ });
    if (res.ok) {
      cardEl?.classList.remove('unread');
      const badge = cardEl?.querySelector('.badge');
      if (badge) { badge.textContent = STATUS_LABELS[STATUS_READ]; badge.classList.remove('new'); }
    }
  }
}

/* ---------------------------------------------------------------- settings */
async function settingsSection(body) {
  const res = await GET('/cpanel/jwt/settings');
  const s = res.data || {};
  const form = el('form', { class: 'settings-form' });

  const FIELDS = [
    ['site_name', 'Site name'],
    ['site_title', 'Site title'],
    ['site_description', 'Site description', 'textarea'],
    ['address', 'Address'],
    ['email', 'Public email'],
    ['phone_number', 'Phone number'],
    ['contact_us_message', 'Topbar message'],
    ['google_map', 'Google Map embed URL'],
    ['mailing_list', 'Mailing list (one email per line)', 'textarea'],
  ];

  for (const [key, label, kind] of FIELDS) {
    const value = key === 'mailing_list'
      ? (Array.isArray(s.mailing_list) ? s.mailing_list.join('\n') : '')
      : s[key] || '';
    form.append(labeledField(label, value, () => {}, kind, key));
  }
  form.append(
    el('button', { class: 'btn btn-green', type: 'submit' }, icon('i-save'), 'Save Settings'),
    el('p', { class: 'form-status', 'data-status': '1' }),
  );
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const status = form.querySelector('[data-status]');
    status.textContent = 'Saving…';
    status.className = 'form-status';
    const payload = {};
    for (const [key] of FIELDS) {
      const input = form.querySelector(`[name="${key}"]`);
      payload[key] = key === 'mailing_list'
        ? input.value.split('\n').map((x) => x.trim()).filter(Boolean)
        : input.value;
    }
    const save = await PUT('/cpanel/jwt/settings', payload);
    if (save.ok) {
      status.className = 'form-status ok';
      status.textContent = 'Saved — public site updates on next sync.';
      await refresh();
    } else {
      status.className = 'form-status err';
      status.textContent = save.data?.message || 'Save failed';
    }
  });

  body.innerHTML = '';
  body.append(form);
}

/* ---------------------------------------------------------------- events */
async function eventsSection(body) {
  const res = await GET('/cpanel/jwt/scheduler/events');
  const events = (res.data?.Events || []).sort((a, b) => b.event_id - a.event_id);
  body.innerHTML = '';
  if (!events.length) {
    body.append(el('p', { class: 'hint' }, 'No scheduled events yet.'));
    return;
  }
  body.append(el('div', { class: 'table-wrap' },
    el('table', { class: 'a-table' },
      el('thead', {}, el('tr', {},
        th('ID'), th('Event'), th('Type'), th('Status'), th('Last send'), th(''))),
      el('tbody', {},
        ...events.map((e) => el('tr', {},
          td(e.event_id),
          td(e.event_name),
          td(e.event_type),
          td(e.event_status),
          td(String((e.job_history || []).slice(-1)[0] || '—')),
          el('td', { class: 'row-actions' },
            el('button', { class: 'icon-btn', title: 'Run now', type: 'button',
              onclick: () => runEvent(e) }, icon('i-refresh'))),
        ))))));

  async function runEvent(ev) {
    const run = await POST(`/cpanel/jwt/scheduler/events/${ev.event_id}/run`);
    if (!run.ok) return alert(run.data?.message || 'Run failed');
    alert(`Event #${ev.event_id} enqueued${run.data?.job ? ` (job ${run.data.job})` : ''}.`);
    await refresh();
    void loadSection(document.querySelector('.a-body'), 'events');
  }
}

/* ------------------------------------------------------------------- jobs */
const JOB_LABELS = { 0: 'QUEUED', 1: 'RUNNING', 2: 'SUCCEEDED', 3: 'FAILED' };

async function jobsSection(body) {
  const res = await GET('/cpanel/jwt/scheduler/jobs');
  const jobs = (res.data?.Jobs || [])
    .sort((a, b) => String(b.start_time || '').localeCompare(String(a.start_time || '')));
  body.innerHTML = '';
  if (!jobs.length) {
    body.append(el('p', { class: 'hint' }, 'No mail jobs yet.'));
    return;
  }
  body.append(el('div', { class: 'table-wrap' },
    el('table', { class: 'a-table' },
      el('thead', {}, el('tr', {},
        th('Job'), th('Name'), th('Status'), th('Complete'), th('Started'), th('Errors'), th(''))),
      el('tbody', {},
        ...jobs.map((j) => {
          const st = j.job_status ?? -1;
          const failed = Number(st) === 3;
          return el('tr', {},
            td(j.job_id),
            td(j.name),
            el('td', {}, el('span', { class: `badge ${failed ? 'err' : st === 2 ? 'new' : ''}` },
              JOB_LABELS[st] ?? String(st))),
            td(j.complete ? 'yes' : 'no'),
            td(String(j.start_time || '').replace('T', ' ').slice(0, 19)),
            td((j.errors || []).join('; ') || '—'),
            el('td', { class: 'row-actions' },
              failed
                ? el('button', { class: 'icon-btn', title: 'Retry', type: 'button',
                    onclick: () => retryJob(j) }, icon('i-refresh'))
                : null),
          );
        })))));

  async function retryJob(j) {
    const run = await POST(`/cpanel/jwt/scheduler/jobs/${encodeURIComponent(j.job_id)}/retry`);
    if (!run.ok) return alert(run.data?.message || 'Retry failed');
    alert('Job re-queued.');
    await refresh();
    void loadSection(document.querySelector('.a-body'), 'jobs');
  }
}

/* ------------------------------------------------------------ tiny helpers */
function th(t) { return el('th', {}, t); }
function td(t) { return el('td', {}, String(t ?? '')); }

function labeledField(label, value, onChange, kind = 'input', name = null) {
  const control = textControl(kind, value, onChange);
  if (name) control.name = name;
  return el('label', { class: 'labeled' }, el('span', {}, label), control);
}

function textControl(kind, value, onChange) {
  if (kind === 'textarea') {
    return el('textarea', { rows: '4', oninput: (e) => onChange(e.target.value) }, value ?? '');
  }
  return el('input', { type: 'text', value: value ?? '', oninput: (e) => onChange(e.target.value) });
}

function numberField(label, value, onChange) {
  return el('label', { class: 'labeled' }, el('span', {}, label),
    el('input', { type: 'number', value: value ?? 0, oninput: (e) => onChange(e.target.value) }));
}

function checkField(label, checked, onChange) {
  return el('label', { class: 'labeled checkbox' },
    el('input', { type: 'checkbox', ...(checked ? { checked: '' } : {}), onchange: (e) => onChange(e.target.checked) }),
    el('span', {}, label));
}

function selectField(label, selectedId, options, onChange) {
  return el('label', { class: 'labeled' }, el('span', {}, label),
    el('select', { onchange: (e) => onChange(e.target.value) },
      el('option', { value: '' }, '— none —'),
      ...options.map((o) => el('option', {
        value: String(o.categoryId),
        ...(Number(selectedId) === o.categoryId ? { selected: '' } : {}),
      }, o.categoryName))));
}

async function removeRecord(table, id, title) {
  if (!confirm(`Delete "${title}" (#${id})? This cannot be undone.`)) return;
  const res = await dataTable.remove(table, id);
  if (!res.ok) return alert(res.data?.message || 'Delete failed');
  await refresh();
  const section = location.pathname.replace(/^\/admin\/?/, '') || 'dashboard';
  void loadSection(document.querySelector('.a-body'), section);
}
