"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import { HERO_CACHE_KEYS } from "@/lib/hero-cache";
import { useApi } from "@/lib/useApi";
import {
  PATROL_ORIGIN,
  isCoord,
  nearestParking,
  type HeroPin,
} from "./heroMapUtils";

const SPOTLIGHT_COUNT = 3;
const CYCLE_MS = 5000;

const HeroMapDeck = dynamic(() => import("./HeroMapDeck"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full flex-col items-center justify-center gap-3 bg-[#e9eef5]">
      <div className="hero-map-loader h-10 w-10 rounded-full border-2 border-cobalt/30 border-t-cobalt" />
      <p className="font-mono text-[0.65rem] uppercase tracking-widest text-[#9fb0c4]">
        Loading live map
      </p>
    </div>
  ),
});

const STORIES = [
  { tag: "Detect", action: "Violation cluster found" },
  { tag: "Guide", action: "Resident route adjusted" },
  { tag: "Patrol", action: "Officer unit dispatched" },
];

const SCENES = [
  {
    name: "Detect",
    copy: "Sensors and reports reveal parking pressure.",
    tone: "bg-cobalt",
  },
  {
    name: "Guide",
    copy: "Residents see safer parking nearby.",
    tone: "bg-ok",
  },
  {
    name: "Patrol",
    copy: "Officers prioritize the right streets.",
    tone: "bg-amber",
  },
  {
    name: "Improve",
    copy: "Insights reduce repeat congestion.",
    tone: "bg-cobalt",
  },
];

const DEMO_DESTINATIONS = [
  { name: "MG Road", lat: 12.9757, lon: 77.6055 },
  { name: "Indiranagar 100 Feet Road", lat: 12.9784, lon: 77.6408 },
  { name: "Koramangala Forum", lat: 12.9346, lon: 77.6113 },
  { name: "Whitefield", lat: 12.9698, lon: 77.7500 },
  { name: "Jayanagar 4th Block", lat: 12.9299, lon: 77.5826 },
];

export default function CityMap() {
  const reduceMotion = useReducedMotion();
  const [spotlightIdx, setSpotlightIdx] = useState(0);
  const [paused, setPaused] = useState(false);
  const [cycleProgress, setCycleProgress] = useState(0);
  const [destination, setDestination] = useState(DEMO_DESTINATIONS[0]);
  const [destinationQuery, setDestinationQuery] = useState(
    DEMO_DESTINATIONS[0].name,
  );
  const [routePath, setRoutePath] = useState<[number, number][]>([]);
  const [routeSummary, setRouteSummary] = useState<{
    distanceKm: number;
    durationMin: number;
  } | null>(null);
  const [routeStatus, setRouteStatus] = useState("Routing");
  const [searchOpen, setSearchOpen] = useState(false);

  const hotspots = useApi(() => api.hotspots(undefined, 20), [], HERO_CACHE_KEYS.hotspots);
  const parking = useApi(() => api.parking({ limit: 12 }), [], HERO_CACHE_KEYS.parking);

  const model = useMemo(() => {
    const hs = hotspots.data ?? [];
    if (hs.length < 3) return null;

    const pins: HeroPin[] = hs
      .slice()
      .sort((a, b) => a.rank - b.rank)
      .filter((h) => isCoord(h.lon, h.lat))
      .map((h) => ({
        lat: h.lat,
        lon: h.lon,
        h3: h.h3,
        rank: h.rank,
        label: h.display_location,
        violations: h.violation_count,
        priority_pct: h.priority_pct,
      }));

    if (pins.length < 3) return null;

    const maxPriority = Math.max(1, ...pins.map((p) => p.priority_pct));
    const spotlights = pins.slice(0, SPOTLIGHT_COUNT);
    const parkingPins = (parking.data ?? [])
      .filter((p) => isCoord(p.lon, p.lat))
      .slice(0, 8)
      .map((p) => ({
        lat: p.lat as number,
        lon: p.lon as number,
        name: p.name,
      }));

    return {
      pins,
      spotlights,
      parking: parkingPins,
      maxPriority,
      total: hs.length,
    };
  }, [hotspots.data, parking.data]);

  useEffect(() => {
    if (!model || paused || reduceMotion) return;
    const timer = setInterval(() => {
      setSpotlightIdx((i) => (i + 1) % model.spotlights.length);
    }, CYCLE_MS);
    return () => clearInterval(timer);
  }, [model, paused, reduceMotion]);

  useEffect(() => {
    if (!model || paused || reduceMotion) return;
    const start = performance.now();
    const tick = () => {
      const p = (performance.now() - start) / CYCLE_MS;
      setCycleProgress(p >= 1 ? 0 : p);
    };
    tick();
    const id = setInterval(tick, 60);
    return () => clearInterval(id);
  }, [spotlightIdx, model, paused, reduceMotion]);

  useEffect(() => {
    let alive = true;
    const controller = new AbortController();
    const loadRoute = async () => {
      setRouteStatus("Routing");
      try {
        const url = new URL(
          `https://router.project-osrm.org/route/v1/driving/${PATROL_ORIGIN[0]},${PATROL_ORIGIN[1]};${destination.lon},${destination.lat}`,
        );
        url.searchParams.set("overview", "full");
        url.searchParams.set("geometries", "geojson");
        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok) throw new Error(`OSRM ${res.status}`);
        const json = await res.json();
        const route = json?.routes?.[0];
        const coords = route?.geometry?.coordinates;
        if (!Array.isArray(coords) || coords.length < 2) {
          throw new Error("No route geometry");
        }
        if (!alive) return;
        setRoutePath(
          coords
            .filter((p: unknown[]) => Number.isFinite(p?.[0]) && Number.isFinite(p?.[1]))
            .map((p: number[]) => [p[0], p[1]] as [number, number]),
        );
        setRouteSummary({
          distanceKm: Math.max(0.1, (Number(route.distance) || 0) / 1000),
          durationMin: Math.max(1, Math.round((Number(route.duration) || 0) / 60)),
        });
        setRouteStatus("Live route");
      } catch {
        if (!alive || controller.signal.aborted) return;
        setRoutePath([]);
        setRouteSummary(null);
        setRouteStatus("Demo route");
      }
    };
    loadRoute();
    return () => {
      alive = false;
      controller.abort();
    };
  }, [destination]);

  const parkingNearDest = useMemo(() => {
    if (!model) return [];
    return nearestParking(destination, model.parking, 3, 4);
  }, [destination, model]);

  const mapHotspots = useMemo(() => {
    if (!model) return [];
    const near = model.pins.filter(
      (p) =>
        Math.abs(p.lat - destination.lat) < 0.09 &&
        Math.abs(p.lon - destination.lon) < 0.11,
    );
    return (near.length >= 4 ? near : model.pins).slice(0, 12);
  }, [model, destination]);

  const spotlight =
    model?.spotlights[Math.min(spotlightIdx, model.spotlights.length - 1)] ??
    model?.pins[0];

  const story = STORIES[spotlightIdx] ?? STORIES[0];
  const activeScene = Math.min(
    SCENES.length - 1,
    Math.floor(cycleProgress * SCENES.length),
  );
  const parkingNear =
    parkingNearDest.length > 0 ? parkingNearDest : [];
  const loading = hotspots.loading && !model;
  const failed = hotspots.error && !model;

  const pause = useCallback(() => setPaused(true), []);
  const resume = useCallback(() => setPaused(false), []);
  const chooseDestination = useCallback(
    async (value: string) => {
      const query = value.trim();
      if (!query) return;
      const next =
        DEMO_DESTINATIONS.find(
          (d) => d.name.toLowerCase() === query.toLowerCase(),
        ) ??
        DEMO_DESTINATIONS.find((d) =>
          d.name.toLowerCase().includes(query.toLowerCase()),
        );
      if (next) {
        setDestination(next);
        setDestinationQuery(next.name);
        setSearchOpen(false);
        setPaused(false);
        return;
      }

      setRouteStatus("Finding place");
      try {
        const url = new URL("https://nominatim.openstreetmap.org/search");
        url.searchParams.set("format", "jsonv2");
        url.searchParams.set("limit", "1");
        url.searchParams.set("countrycodes", "in");
        url.searchParams.set("q", `${query}, Bengaluru, Karnataka, India`);
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Nominatim ${res.status}`);
        const [place] = await res.json();
        const lat = Number(place?.lat);
        const lon = Number(place?.lon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
          throw new Error("No geocode result");
        }
        setDestination({
          name: place?.name || query,
          lat,
          lon,
        });
        setDestinationQuery(place?.name || query);
        setSearchOpen(false);
        setPaused(false);
      } catch {
        setRouteStatus("Place not found");
        setDestinationQuery(destination.name);
      }
    },
    [destination],
  );

  const filteredSuggestions = useMemo(() => {
    const q = destinationQuery.trim().toLowerCase();
    if (!q) return DEMO_DESTINATIONS;
    return DEMO_DESTINATIONS.filter((d) => d.name.toLowerCase().includes(q));
  }, [destinationQuery]);

  return (
    <div
      className="hero-map-shell group relative overflow-hidden rounded-2xl border border-white/80 bg-white shadow-[0_30px_90px_-32px_rgba(20,24,31,0.5)]"
      onMouseEnter={pause}
      onMouseLeave={resume}
    >
      {/* Animated gradient frame */}
      <div
        aria-hidden
        className="hero-map-frame pointer-events-none absolute -inset-px rounded-2xl"
      />

      <div className="relative aspect-[1.08/1] w-full overflow-hidden rounded-2xl bg-[#e9eef5] sm:aspect-[4/3] lg:aspect-[1.48/1]">
        {loading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 bg-[#e9eef5]">
            <div className="hero-map-loader h-10 w-10 rounded-full border-2 border-cobalt/30 border-t-cobalt" />
            <p className="font-mono text-[0.65rem] uppercase tracking-widest text-ink-muted">
              Scanning Bengaluru
            </p>
          </div>
        ) : failed ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
            <p className="text-sm text-[#cdd6e2]">Map unavailable</p>
            <p className="font-mono text-[0.65rem] text-[#7e8aa0]">
              Run <code className="text-cobalt">.\run.ps1 backend</code>
            </p>
          </div>
        ) : model && spotlight ? (
          <HeroMapDeck
            hotspots={mapHotspots}
            parking={parkingNearDest}
            spotlight={spotlight}
            destination={destination}
            routePath={routePath}
            maxPriority={model.maxPriority}
            reduceMotion={reduceMotion}
            activeScene={activeScene}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 bg-[#e9eef5] px-6 text-center">
            <div className="hero-map-loader h-10 w-10 rounded-full border-2 border-cobalt/30 border-t-cobalt" />
            <p className="font-mono text-[0.65rem] uppercase tracking-widest text-ink-muted">
              Loading enforcement data
            </p>
          </div>
        )}

        {/* Scan sweep */}
        {!reduceMotion && model ? (
          <div aria-hidden className="hero-map-scan pointer-events-none absolute inset-0 z-[1]" />
        ) : null}

        {/* Soft edge wash, like a product map sitting inside the hero. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(248,251,255,0.18)_0%,rgba(248,251,255,0.04)_26%,rgba(248,251,255,0)_58%),radial-gradient(ellipse_at_center,transparent_58%,rgba(255,255,255,0.08)_100%)]"
        />

        <div className="pointer-events-none absolute left-1/2 top-[42%] z-10 hidden -translate-x-1/2 -translate-y-1/2 text-center lg:block">
          <p className="font-display text-xl font-extrabold leading-none text-ink/75 drop-shadow-[0_2px_8px_rgba(255,255,255,0.9)] xl:text-2xl">
            Bengaluru
          </p>
          <p className="font-display text-lg font-extrabold leading-none text-ink/60 drop-shadow-[0_2px_8px_rgba(255,255,255,0.9)] xl:text-xl">
            ಬೆಂಗಳೂರು
          </p>
        </div>

        {/* Compact legend */}
        {model ? (
          <div className="absolute right-3 top-14 z-10 hidden rounded-xl border border-white/80 bg-white/92 px-3 py-2 shadow-[0_18px_50px_-32px_rgba(20,24,31,0.65)] backdrop-blur-md lg:block">
            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[0.62rem]">
              {[
                { color: "bg-ok", label: "Parking" },
                { color: "bg-heat-high", label: "Busy" },
                { color: "bg-cobalt", label: "Route" },
                { color: "bg-amber", label: "Hotspot" },
              ].map((item) => (
                <span key={item.label} className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 shrink-0 rounded-full ${item.color}`} />
                  <span className="font-semibold text-ink-muted">{item.label}</span>
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {/* Live badge */}
        <div className="absolute right-4 top-4 z-10 hidden items-center gap-2 sm:flex">
          <span className="flex items-center gap-1.5 rounded-full border border-white/70 bg-white/88 px-2.5 py-1 shadow-sm backdrop-blur-md">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ok opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-ok" />
            </span>
            <span className="font-mono text-[0.58rem] uppercase tracking-wider text-ink-muted">
              {routeStatus}
            </span>
          </span>
        </div>

        {model ? (
          <form
            className="absolute left-3 top-3 z-20 hidden md:block"
            onSubmit={(e) => {
              e.preventDefault();
              chooseDestination(destinationQuery);
            }}
          >
            <div className="relative flex max-w-[17rem] items-center gap-2 rounded-xl border border-white/80 bg-white/94 p-2 shadow-[0_18px_50px_-34px_rgba(20,24,31,0.72)] backdrop-blur-md">
              <label className="sr-only" htmlFor="hero-destination">
                Enter destination
              </label>
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-cobalt text-xs font-bold text-white">
                To
              </span>
              <input
                id="hero-destination"
                value={destinationQuery}
                onChange={(e) => {
                  setDestinationQuery(e.target.value);
                  setSearchOpen(true);
                }}
                onFocus={() => setSearchOpen(true)}
                onBlur={() => {
                  window.setTimeout(() => setSearchOpen(false), 160);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Escape") setSearchOpen(false);
                }}
                className="min-w-0 flex-1 bg-transparent text-sm font-semibold text-ink outline-none placeholder:text-ink-faint"
                placeholder="Enter destination"
                autoComplete="off"
              />
              {searchOpen && filteredSuggestions.length > 0 ? (
                <ul className="absolute left-0 right-0 top-[calc(100%+0.35rem)] overflow-hidden rounded-xl border border-line bg-white py-1 shadow-[0_18px_50px_-28px_rgba(20,24,31,0.55)]">
                  {filteredSuggestions.map((d) => (
                    <li key={d.name}>
                      <button
                        type="button"
                        className="block w-full px-3 py-2 text-left text-sm font-medium text-ink hover:bg-cobalt-soft"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => chooseDestination(d.name)}
                      >
                        {d.name}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </form>
        ) : null}
      </div>

      {/* Workflow panel */}
      <div className="absolute inset-x-3 bottom-3 z-10 sm:inset-x-5 sm:bottom-4">
        {model && spotlight ? (
          <div className="rounded-2xl border border-white/85 bg-white/94 p-2.5 shadow-[0_24px_70px_-36px_rgba(20,24,31,0.72)] backdrop-blur-md">
            <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
              {SCENES.map((scene, i) => (
                <button
                  key={scene.name}
                  type="button"
                  onClick={() => setSpotlightIdx(i % model.spotlights.length)}
                  className={`group flex min-w-0 items-center gap-2 rounded-xl px-2 py-1.5 text-left transition-colors sm:px-2.5 sm:py-2 ${
                    i === activeScene ? "bg-cobalt-soft" : "hover:bg-surface-2"
                  }`}
                >
                  <span
                    className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-bold text-white shadow-[0_10px_24px_-16px_rgba(20,24,31,0.6)] sm:h-9 sm:w-9 sm:text-sm ${scene.tone}`}
                  >
                    {i + 1}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-xs font-bold text-ink sm:text-sm">
                      {scene.name}
                    </span>
                    <span className="hidden text-xs leading-snug text-ink-muted sm:line-clamp-2 md:block">
                      {scene.copy}
                    </span>
                  </span>
                </button>
              ))}
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={spotlight.rank}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
                className="mt-1.5 hidden flex-col gap-2 border-t border-line pt-2 lg:flex 2xl:flex-row 2xl:items-center 2xl:justify-between 2xl:gap-4 2xl:pt-1.5"
              >
                <p className="min-w-0 text-xs leading-relaxed text-ink-muted 2xl:truncate">
                  <span className="font-mono font-semibold uppercase tracking-wider text-amber">
                    {story.tag}
                  </span>{" "}
                  <span className="font-semibold text-ink">{spotlight.label}</span>{" "}
                  · <span className="tnum font-semibold text-ink">{fmt(spotlight.violations)}</span>{" "}
                  violations · {story.action}
                  {parkingNear.length > 0
                    ? ` · Parking: ${parkingNear.map((p) => p.name).join(" / ")}`
                    : ""}
                  {routeSummary
                    ? ` · ${routeSummary.distanceKm.toFixed(1)} km · ${routeSummary.durationMin} min`
                    : ""}
                </p>
                <Link
                  href="/officer"
                  className="w-fit shrink-0 rounded-full bg-cobalt px-4 py-2 font-mono text-[0.65rem] font-medium text-white shadow-[0_14px_32px_-20px_rgba(30,69,200,0.85)] transition-all hover:bg-cobalt-deep"
                >
                  Open command map →
                </Link>
              </motion.div>
            </AnimatePresence>
          </div>
        ) : null}
      </div>
    </div>
  );
}
