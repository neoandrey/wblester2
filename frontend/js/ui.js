/* DOM helpers + interactive behaviours (slider, reveal, counters, filters). */

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (k === 'style' && typeof v === 'object') {
      Object.assign(node.style, v);
    } else node.setAttribute(k, v);
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(child));
  }
  return node;
}

export function icon(name, cls = '') {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', `icon ${cls}`.trim());
  svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', `#${name}`);
  svg.append(use);
  return svg;
}

const escMap = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };
export function esc(str = '') {
  return String(str).replace(/[&<>"]/g, (c) => escMap[c]);
}

/* Minimal HTML renderer for CMS richText fragments (whitelisted tags). */
const ALLOWED = /^<\/?(p|br|b|strong|i|em|ul|ol|li|h2|h3|h4|blockquote|a|span)(\s[^>]*)?>$/i;
export function rich(html = '') {
  const holder = el('div');
  const tmp = document.createElement('template');
  tmp.innerHTML = html || '';
  const walk = (node, target) => {
    for (const child of node.content
      ? [...node.content.childNodes]
      : [...node.childNodes]) {
      if (child.nodeType === Node.TEXT_NODE) {
        target.append(child.textContent);
      } else if (
        child.nodeType === Node.ELEMENT_NODE &&
        ALLOWED.test(`<${child.localName}>`)
      ) {
        const copy = child.cloneNode(false);
        for (const attr of [...copy.attributes]) {
          if (!/^href$|^title$/.test(attr.name)) copy.removeAttribute(attr.name);
          if (attr.name === 'href' && !/^(https?:|\/|#|mailto:)/i.test(attr.value)) {
            copy.removeAttribute('href');
          }
        }
        target.append(copy);
        walk(child, copy);
      }
    }
  };
  walk(tmp, holder);
  return holder.innerHTML;
}

/** Highlight words wrapped in [brackets] with the accent color. */
export function accentTitle(text, tag = 'h2') {
  const parts = String(text || '').split(/(\[[^\]]+\])/g);
  return el(tag, {}, ...parts.map((part) =>
    part.startsWith('[') && part.endsWith(']')
      ? el('span', { class: 'main-color' }, part.slice(1, -1))
      : part,
  ));
}

/* Reveal-on-scroll ----------------------------------------------------------- */
let observer;
export function observeReveals(root = document) {
  observer ??= new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.12 },
  );
  root.querySelectorAll('.reveal:not(.in-view)').forEach((n) => observer.observe(n));
}

/* Count-up numbers -------------------------------------------------------------- */
export function initCounters(root = document) {
  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        io.unobserve(entry.target);
        const target = Number(entry.target.dataset.count || 0);
        const suffix = entry.target.dataset.suffix || '';
        const start = performance.now();
        const dur = 1600;
        const tick = (now) => {
          const t = Math.min(1, (now - start) / dur);
          const eased = 1 - Math.pow(1 - t, 3);
          entry.target.textContent =
            Math.round(target * eased).toLocaleString() + suffix;
          if (t < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      }
    },
    { threshold: 0.4 },
  );
  root.querySelectorAll('[data-count]').forEach((n) => io.observe(n));
}

/* Hero slider ---------------------------------------------------------------------- */
export function initHeroSlider(root) {
  const slides = [...root.querySelectorAll('.hero-slide')];
  if (slides.length < 1) return;
  let idx = 0;
  let timer = null;

  const dots = root.querySelector('.hero-dots');
  const show = (next) => {
    slides[idx].classList.remove('active', 'zooming');
    idx = (next + slides.length) % slides.length;
    const active = slides[idx];
    void active.offsetWidth; /* restart animations */
    active.classList.add('active', 'zooming');
    dots?.querySelectorAll('button').forEach((d, i) => {
      d.classList.toggle('active', i === idx);
    });
  };
  const play = () => {
    stop();
    if (slides.length > 1) timer = setInterval(() => show(idx + 1), 6000);
  };
  const stop = () => timer && clearInterval(timer);

  dots?.querySelectorAll('button').forEach((dot, i) => {
    dot.addEventListener('click', () => {
      show(i);
      play();
    });
  });
  root.querySelector('.hero-arrow.prev')
    ?.addEventListener('click', () => {
      show(idx - 1);
      play();
    });
  root.querySelector('.hero-arrow.next')
    ?.addEventListener('click', () => {
      show(idx + 1);
      play();
    });

  let startX = null;
  root.addEventListener('pointerdown', (e) => {
    startX = e.clientX;
  });
  root.addEventListener('pointerup', (e) => {
    if (startX == null) return;
    const dx = e.clientX - startX;
    if (Math.abs(dx) > 60) show(idx + (dx < 0 ? 1 : -1));
    startX = null;
    play();
  });
  root.addEventListener('mouseenter', stop);
  root.addEventListener('mouseleave', play);

  slides[0].classList.add('active', 'zooming');
  dots?.children[0]?.classList.add('active');
  play();
}

/* Gallery filters ----------------------------------------------------------------------- */
export function initGalleryFilters(root) {
  root.querySelectorAll('.gallery-filters button').forEach((btn) => {
    btn.addEventListener('click', () => {
      root
        .querySelectorAll('.gallery-filters button')
        .forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const f = btn.dataset.filter;
      root.querySelectorAll('.gal-item').forEach((item) => {
        item.classList.toggle('hide', f !== '*' && item.dataset.cat !== f);
      });
    });
  });
}

/* Fisher-Yates shuffle — used to randomise banner slide order per visit. */
export function shuffled(list) {
  const out = [...list];
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}
