/** Client helpers for Brief unread tracking (localStorage). */

const STORAGE_KEY = "foliotracker.brief.seen";

export function loadSeenKeys(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((x): x is string => typeof x === "string"));
  } catch {
    return new Set();
  }
}

export function saveSeenKeys(keys: Set<string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...keys]));
  } catch {
    /* ignore quota */
  }
}

export function markSeen(keys: Set<string>, eventKey: string): Set<string> {
  const next = new Set(keys);
  next.add(eventKey);
  saveSeenKeys(next);
  return next;
}
