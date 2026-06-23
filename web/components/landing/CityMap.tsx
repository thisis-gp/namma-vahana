"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { isCoord, nearestParking, type HeroPin } from "./heroMapUtils";

const SPOTLIGHT_COUNT = 3;
const CYCLE_MS = 5000;

const HeroMapDeck = dynamic(() => import("./HeroMapDeck"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full flex-col items-center justify-center gap-3 bg-asphalt">
      <div className="hero-map-loader h-10 w-10 rounded-full border-2 border-cobalt/30 border-t-cobalt" />
      <p className="font-mono text-[0.65rem] uppercase tracking-widest text-[#9fb0c4]">
        Loading live map
      </p>
    </div>
  ),
});

const STORIES = [
  { tag: "Worst zone", action: "Avoid parking here" },
  { tag: "Priority #2", action: "High enforcement risk" },
  { tag: "Priority #3", action: "Patrol on standby" },
];

export default function CityMap() {
  const reduceMotion = useReducedMotion();
  const [spotlightIdx, setSpotlightIdx] = useState(0);
  const [paused, setPaused] = useState(false);
  const [cycleProgress, setCycleProgress] = useState(0);

  const hotspots = useApi(() => api.hotspots(undefined, 50), []);
  const parking = useApi(() => api.parking({ limit: 12 }), []);

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
      .slice(0, 3)
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
    if (!model || paused || reduceMotion) {
      setCycleProgress(0);
      return;
    }
    setCycleProgress(0);
    const start = performance.now();
    const tick = () => {
      const p = (performance.now() - start) / CYCLE_MS;
      setCycleProgress(p >= 1 ? 0 : p);
    };
    tick();
    const id = setInterval(tick, 60);
    return () => clearInterval(id);
  }, [spotlightIdx, model, paused, reduceMotion]);

  const spotlight =
    model?.spotlights[Math.min(spotlightIdx, model.spotlights.length - 1)] ??
    model?.pins[0];

  const story = STORIES[spotlightIdx] ?? STORIES[0];
  const parkingNear =
    model && spotlight
      ? nearestParking(spotlight, model.parking, 2)
      : [];
  const loading = hotspots.loading && !model;
  const failed = hotspots.error && !model;

  const pause = useCallback(() => setPaused(true), []);
  const resume = useCallback(() => setPaused(false), []);

  return (
    <div
      className="hero-map-shell group relative overflow-hidden rounded-2xl shadow-[0_24px_80px_-20px_rgba(20,24,31,0.55)]"
      onMouseEnter={pause}
      onMouseLeave={resume}
    >
      {/* Animated gradient frame */}
      <div
        aria-hidden
        className="hero-map-frame pointer-events-none absolute -inset-px rounded-2xl"
      />

      <div className="relative aspect-[4/3] w-full overflow-hidden rounded-2xl bg-asphalt">
        {loading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 bg-asphalt">
            <div className="hero-map-loader h-10 w-10 rounded-full border-2 border-cobalt/30 border-t-cobalt" />
            <p className="font-mono text-[0.65rem] uppercase tracking-widest text-[#9fb0c4]">
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
            hotspots={model.pins.slice(0, 20)}
            parking={parkingNear}
            spotlight={spotlight}
            maxPriority={model.maxPriority}
            reduceMotion={reduceMotion}
          />
        ) : null}

        {/* Scan sweep */}
        {!reduceMotion && model ? (
          <div aria-hidden className="hero-map-scan pointer-events-none absolute inset-0 z-[1]" />
        ) : null}

        {/* Vignette */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_40%,rgba(15,22,34,0.55)_100%)]"
        />

        {/* Visual legend */}
        {model ? (
          <div className="absolute left-3 top-3 z-10 flex flex-col gap-1.5">
            {[
              { color: "bg-heat-high", label: "Fine risk" },
              { color: "bg-cobalt", label: "Patrol route" },
              { color: "bg-ok", label: "Safe parking" },
            ].map((item) => (
              <span
                key={item.label}
                className="flex items-center gap-1.5 rounded-full border border-asphalt-line/80 bg-asphalt-2/85 px-2 py-0.5 backdrop-blur-md"
              >
                <span className={`h-2 w-2 rounded-full ${item.color}`} />
                <span className="font-mono text-[0.52rem] uppercase tracking-wider text-[#cdd6e2]">
                  {item.label}
                </span>
              </span>
            ))}
          </div>
        ) : null}

        {/* Live badge */}
        <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-full border border-asphalt-line bg-asphalt-2/90 px-2.5 py-1 backdrop-blur-md">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ok opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-ok" />
            </span>
            <span className="font-mono text-[0.58rem] uppercase tracking-wider text-[#cdd6e2]">
              Bengaluru live
            </span>
          </span>
        </div>
      </div>

      {/* Story panel */}
      <div className="absolute inset-x-0 bottom-0 z-10 bg-gradient-to-t from-asphalt via-asphalt/95 to-transparent px-4 pb-4 pt-10">
        {model && spotlight ? (
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-[min(100%,300px)]">
              <div className="mb-2.5 flex items-center gap-1.5">
                {model.spotlights.map((s, i) => (
                  <button
                    key={s.rank}
                    type="button"
                    onClick={() => setSpotlightIdx(i)}
                    className={`rounded-full px-2 py-0.5 font-mono text-[0.58rem] font-semibold transition-all ${
                      i === spotlightIdx
                        ? "bg-cobalt text-white shadow-[0_0_16px_rgba(30,69,200,0.5)]"
                        : "bg-asphalt-line/80 text-[#9fb0c4] hover:bg-asphalt-line"
                    }`}
                  >
                    #{s.rank}
                  </button>
                ))}
                <span className="ml-1 font-mono text-[0.55rem] uppercase tracking-wider text-ok">
                  {paused ? "Paused" : "Auto-scan"}
                </span>
              </div>
              {!reduceMotion && !paused ? (
                <div className="mb-2 h-0.5 w-full max-w-[200px] overflow-hidden rounded-full bg-asphalt-line/60">
                  <div
                    className="h-full rounded-full bg-cobalt transition-[width] duration-75 ease-linear"
                    style={{ width: `${cycleProgress * 100}%` }}
                  />
                </div>
              ) : null}

              <AnimatePresence mode="wait">
                <motion.div
                  key={spotlight.rank}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                >
                  <p className="font-mono text-[0.6rem] uppercase tracking-widest text-amber">
                    {story.tag}
                  </p>
                  <p className="mt-0.5 line-clamp-2 font-display text-lg font-bold leading-tight text-white">
                    {spotlight.label}
                  </p>
                  <p className="mt-1 text-sm text-[#9fb0c4]">
                    <span className="tnum text-2xl font-bold text-white">
                      {fmt(spotlight.violations)}
                    </span>{" "}
                    violations · {story.action}
                  </p>
                </motion.div>
              </AnimatePresence>

              {parkingNear.length > 0 ? (
                <p className="mt-2 font-mono text-[0.55rem] text-ok">
                  Nearest safe parking: {parkingNear.map((p) => p.name).join(" · ")}
                </p>
              ) : null}
            </div>

            <Link
              href="/officer"
              className="shrink-0 rounded-full bg-cobalt px-4 py-2 font-mono text-[0.65rem] font-medium text-white shadow-[0_0_24px_rgba(30,69,200,0.45)] transition-all hover:bg-cobalt-deep hover:shadow-[0_0_32px_rgba(30,69,200,0.6)]"
            >
              Explore 3D map →
            </Link>
          </div>
        ) : null}
      </div>
    </div>
  );
}
