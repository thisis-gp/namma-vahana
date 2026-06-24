/** In-memory cache populated during backend warmup — avoids hero waterfall after splash. */
import type { Hotspot, Kpis, ParkingSpot } from "./types";

type Entry = { data: unknown; ts: number };

const store = new Map<string, Entry>();
const TTL_MS = 5 * 60 * 1000;

export const HERO_CACHE_KEYS = {
  kpis: "hero:kpis",
  hotspots: "hero:hotspots",
  parking: "hero:parking",
} as const;

function setCache(key: string, data: unknown) {
  store.set(key, { data, ts: Date.now() });
}

export function peekHeroCache<T>(key: string): T | null {
  const entry = store.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > TTL_MS) {
    store.delete(key);
    return null;
  }
  return entry.data as T;
}

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(path, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

/** Prefetch landing hero endpoints in parallel (call while splash is visible). */
export async function prefetchHeroBundle(timeoutMs = 25_000): Promise<boolean> {
  // Warm the heavy map chunk while API data loads.
  void import("@/components/landing/HeroMapDeck");

  const work = Promise.all([
    fetchJson<Kpis>("/api/kpis").then((d) => d && setCache(HERO_CACHE_KEYS.kpis, d)),
    fetchJson<Hotspot[]>("/api/hotspots?limit=20").then(
      (d) => d && setCache(HERO_CACHE_KEYS.hotspots, d),
    ),
    fetchJson<ParkingSpot[]>("/api/parking?limit=12").then(
      (d) => d && setCache(HERO_CACHE_KEYS.parking, d),
    ),
  ]).then(
    (results) => results.filter(Boolean).length >= 2,
    () => false,
  );

  return Promise.race([
    work,
    new Promise<boolean>((resolve) => setTimeout(() => resolve(false), timeoutMs)),
  ]);
}

export function hasHeroCache(): boolean {
  return (
    peekHeroCache(HERO_CACHE_KEYS.kpis) != null &&
    peekHeroCache(HERO_CACHE_KEYS.hotspots) != null
  );
}
