"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import type { Hotspot } from "@/lib/types";
import { fmt } from "@/lib/format";
import { heatCss } from "./map/heat";
import { useStation } from "./officer/stationContext";

const MapCanvas = dynamic(() => import("./map/MapCanvas"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full place-items-center bg-asphalt">
      <span className="font-mono text-sm text-[#7e8aa0]">Rendering map…</span>
    </div>
  ),
});

const MAP_LIMIT = 300;

export default function HotspotMap() {
  const { station } = useStation();
  const [selected, setSelected] = useState<Hotspot | null>(null);

  const hotspots = useApi(
    () => api.hotspots(station || undefined, MAP_LIMIT),
    [station],
  );

  const list = hotspots.data ?? [];
  const top = useMemo(() => list.slice(0, 8), [list]);
  const maxPriority = useMemo(
    () => Math.max(1, ...list.map((h) => h.priority_pct)),
    [list],
  );

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
      {/* Map */}
      <div className="relative h-[460px] overflow-hidden rounded-xl border border-asphalt-line bg-asphalt sm:h-[560px]">
        {hotspots.error ? (
          <div className="grid h-full place-items-center px-6 text-center">
            <p className="font-mono text-sm text-[#c98a86]">
              Map data unavailable — {hotspots.error}
              <br />
              Start the API with{" "}
              <code className="text-[#e9b7b3]">.\run.ps1 backend</code>.
            </p>
          </div>
        ) : (
          <MapCanvas
            hotspots={list}
            selectedH3={selected?.h3 ?? null}
            onSelect={setSelected}
          />
        )}

        {station ? (
          <div className="absolute left-3 top-3 rounded-lg border border-asphalt-line bg-asphalt-2/90 px-3 py-1.5 font-mono text-[0.7rem] text-[#cdd6e2] backdrop-blur">
            {station}
          </div>
        ) : null}

        {/* Legend */}
        <div className="absolute bottom-3 left-3 rounded-lg border border-asphalt-line bg-asphalt-2/90 px-3 py-2 backdrop-blur">
          <p className="mb-1.5 font-mono text-[0.62rem] uppercase tracking-wider text-[#7e8aa0]">
            Enforcement priority
          </p>
          <div
            className="h-2 w-40 rounded-full"
            style={{
              background: `linear-gradient(90deg, ${heatCss(0)}, ${heatCss(
                0.5,
              )}, ${heatCss(1)})`,
            }}
          />
          <div className="mt-1 flex justify-between font-mono text-[0.62rem] text-[#9fb0c4]">
            <span>lower</span>
            <span>taller · redder = act first</span>
          </div>
        </div>

        {/* Selected detail */}
        {selected ? (
          <DetailPanel hotspot={selected} onClose={() => setSelected(null)} />
        ) : (
          <div className="absolute right-3 top-3 hidden max-w-[200px] rounded-lg border border-asphalt-line bg-asphalt-2/80 px-3 py-2 text-right font-mono text-[0.68rem] text-[#9fb0c4] backdrop-blur sm:block">
            Tap any hex for the full story →
          </div>
        )}
      </div>

      {/* Ranked list */}
      <div className="flex flex-col gap-2">
        <p className="eyebrow" style={{ color: "#9fb0c4" }}>
          Worst {top.length} this period
        </p>
        {hotspots.loading && list.length === 0 ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-12 animate-pulse rounded-lg bg-asphalt-2"
              />
            ))}
          </div>
        ) : (
          top.map((h) => {
            const active = selected?.h3 === h.h3;
            return (
              <button
                key={h.h3}
                onClick={() => setSelected(h)}
                className={`flex items-center gap-3 rounded-lg border px-3 py-2 text-left transition-colors ${
                  active
                    ? "border-cobalt bg-asphalt-2"
                    : "border-asphalt-line bg-asphalt-2/50 hover:bg-asphalt-2"
                }`}
              >
                <span
                  className="h-7 w-1.5 shrink-0 rounded-full"
                  style={{ background: heatCss(h.priority_pct / maxPriority) }}
                  aria-hidden
                />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-white">
                    {h.display_location}
                  </span>
                  <span className="font-mono text-[0.7rem] text-[#9fb0c4]">
                    #{h.rank} · {h.dominant_station}
                  </span>
                </span>
                <span className="shrink-0 text-right">
                  <span className="block font-mono text-sm font-semibold tnum text-amber">
                    {fmt(h.violation_count)}
                  </span>
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}

function DetailPanel({
  hotspot: h,
  onClose,
}: {
  hotspot: Hotspot;
  onClose: () => void;
}) {
  const flags = [
    h.near_school && "Near school",
    h.near_hospital && "Near hospital",
    h.blocks_bus && "Blocks bus route",
  ].filter(Boolean) as string[];

  return (
    <div className="absolute inset-x-3 bottom-3 max-h-[78%] overflow-auto rounded-xl border border-asphalt-line bg-asphalt-2/95 p-4 backdrop-blur sm:inset-x-auto sm:right-3 sm:top-3 sm:bottom-auto sm:w-[300px]">
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="font-display text-lg font-bold leading-tight text-white">
          {h.display_location}
        </h3>
        <button
          onClick={onClose}
          aria-label="Close detail"
          className="shrink-0 rounded-md px-2 py-0.5 text-[#9fb0c4] hover:bg-asphalt hover:text-white"
        >
          ✕
        </button>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-3 border-b border-asphalt-line pb-3">
        <Field label="Rank" value={`#${h.rank}`} />
        <Field label="Violations" value={fmt(h.violation_count)} />
        <Field label="Peak hours" value={h.peak_hours || "—"} />
        <Field label="Units rec." value={String(h.units_recommended)} />
      </div>

      <p className="mb-3 text-sm leading-relaxed text-[#cdd6e2]">
        {h.nl_summary}
      </p>

      <div className="mb-3 space-y-1.5 font-mono text-[0.72rem] text-[#9fb0c4]">
        <Row k="Intervention" v={h.intervention_type} />
        <Row k="Top vehicle" v={h.dominant_vehicle} />
        <Row k="Top violation" v={h.dominant_violation} />
        <Row k="Road class" v={h.road_class} />
        <Row k="Confidence" v={h.confidence_flag} />
      </div>

      {flags.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {flags.map((f) => (
            <span
              key={f}
              className="rounded-full border border-amber/40 bg-amber/10 px-2 py-0.5 font-mono text-[0.66rem] text-amber"
            >
              ⚠ {f}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="font-mono text-[0.62rem] uppercase tracking-wider text-[#7e8aa0]">
        {label}
      </p>
      <p className="font-mono text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-[#7e8aa0]">{k}</span>
      <span className="text-right text-[#cdd6e2]">{v}</span>
    </div>
  );
}
