/** User-facing product identity — keep API field names (e.g. parkpulse_coverage) unchanged. */

export const BRAND = {
  name: "Namma Vahana",
  /** Kannada: “our vehicle / our ride” — local, memorable for Bengaluru */
  meaning: "Our ride, our roads",
  tagline: "Smart parking for Namma Bengaluru",
  description:
    "Where parking violations cluster, when to enforce, and the patrol plan that covers more with the same units. Built on Bengaluru enforcement data.",
  productLabel: "Namma Vahana", // charts, proof section
} as const;

export const STORAGE_KEYS = {
  handle: "namma-vahana-handle",
  trees: "namma-vahana-trees",
} as const;

const LEGACY_KEYS: Record<string, string> = {
  [STORAGE_KEYS.handle]: "parkpulse-handle",
  [STORAGE_KEYS.trees]: "parkpulse-trees",
};

export function readStorage(key: string): string | null {
  if (typeof window === "undefined") return null;
  const current = window.localStorage.getItem(key);
  if (current) return current;
  const legacy = LEGACY_KEYS[key];
  if (!legacy) return null;
  const old = window.localStorage.getItem(legacy);
  if (old) {
    window.localStorage.setItem(key, old);
    return old;
  }
  return null;
}

export function writeStorage(key: string, value: string) {
  window.localStorage.setItem(key, value);
}
