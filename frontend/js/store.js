/* Content store + periodic synchronisation.
   Cache-first: render from IndexedDB instantly, then revalidate against
   GET /public/content on boot, every 60s, and when the tab regains focus. */

import { cacheGet, cacheSet } from './db.js';
import { GET } from './api.js';

const CACHE_KEY = 'content';
const REVALIDATE_MS = 60_000;

const state = {
  content: null,
  raw: null,
  listeners: new Set(),
  lastSync: null,
  timer: null,
};

export function getContent() {
  return state.content;
}

export function getSettings() {
  return state.content?.settings || {};
}

export function subscribe(fn) {
  state.listeners.add(fn);
  return () => state.listeners.delete(fn);
}

function emit() {
  for (const fn of state.listeners) fn(state.content);
}

export async function initStore() {
  const cached = await cacheGet(CACHE_KEY);
  if (cached?.pages) {
    state.content = cached;
    state.raw = JSON.stringify(cached);
    emit();
  }
  void refresh();

  state.timer = setInterval(() => {
    if (document.visibilityState === 'visible') void refresh();
  }, REVALIDATE_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') void refresh();
  });
}

export async function refresh() {
  const res = await GET('/public/content', { anon: true });
  if (!res.ok || !res.data?.pages) return false;

  /* Ignore per-request noise (fetchedAt) so identical content does not
     trigger a re-render — otherwise every poll wipes in-progress forms. */
  const { fetchedAt, ...payload } = res.data;
  const nextRaw = JSON.stringify(payload);
  if (nextRaw !== state.raw) {
    state.content = payload;
    state.raw = nextRaw;
    await cacheSet(CACHE_KEY, payload);
    emit();
  }
  state.lastSync = new Date();
  return true;
}

/* Derived helpers ---------------------------------------------------------- */
export function visiblePages() {
  return (state.content?.pages || []).filter((p) => p.pageId !== 100);
}

export function pageBySlug(slug) {
  return (state.content?.pages || []).find((p) => p.slug === slug) || null;
}

export function homePage() {
  const pages = state.content?.pages || [];
  return (
    pages.find((p) => p.slug === 'home') ||
    pages.find((p) => p.pageId === getSettings().homePageId) ||
    null
  );
}

export function categories() {
  return [...(state.content?.categories || [])].sort(
    (a, b) => a.sortOrder - b.sortOrder,
  );
}

export function pagesOfCategory(categoryId) {
  return visiblePages()
    .filter((p) => p.categoryId === categoryId)
    .sort((a, b) => a.sortOrder - b.sortOrder);
}

export function subpagesOf(pageId) {
  return visiblePages().filter((p) => p.parentId === pageId);
}
