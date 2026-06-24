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

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchHeroOnce(): Promise<boolean> {
  void import("@/components/landing/HeroMapDeck");

  const [kpis, hotspots, parking] = await Promise.all([
    fetchJson<Kpis>("/api/kpis"),
    fetchJson<Hotspot[]>("/api/hotspots?limit=20"),
    fetchJson<ParkingSpot[]>("/api/parking?limit=12"),
  ]);

  if (kpis) setCache(HERO_CACHE_KEYS.kpis, kpis);
  if (hotspots && hotspots.length >= 3) {
    setCache(HERO_CACHE_KEYS.hotspots, hotspots);
  }
  if (parking && parking.length > 0) {
    setCache(HERO_CACHE_KEYS.parking, parking);
  }

  return hasHeroCache();
}

/** Prefetch landing hero endpoints in parallel (call while splash is visible). */
export async function prefetchHeroBundle(timeoutMs = 25_000): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    if (await fetchHeroOnce()) return true;
    await sleep(2_000);
  }

  return hasHeroCache();
}

export function hasHeroCache(): boolean {
  return (
    peekHeroCache<Kpis>(HERO_CACHE_KEYS.kpis) != null &&
    (peekHeroCache<Hotspot[]>(HERO_CACHE_KEYS.hotspots)?.length ?? 0) >= 3
  );
}
