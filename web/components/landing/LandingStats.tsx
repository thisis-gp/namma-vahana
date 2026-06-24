"use client";

import { api } from "@/lib/api";
import { HERO_CACHE_KEYS } from "@/lib/hero-cache";
import { useApi } from "@/lib/useApi";
import { compact, fmt, pct } from "@/lib/format";

export default function LandingStats() {
  const { data: k } = useApi(api.kpis, [], HERO_CACHE_KEYS.kpis);

  return (
    <section className="border-b border-line bg-ground">
      <div className="mx-auto w-full max-w-6xl px-5 py-16 sm:px-8 sm:py-20">
        <div className="grid items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="eyebrow mb-3">The insight everything is built on</p>
            <h2 className="font-display text-3xl font-extrabold leading-tight tracking-tight sm:text-[2.6rem]">
              {k ? (
                <>
                  <span className="text-cobalt">{pct(k.top20_impact_share, 0)}</span>{" "}
                  of the city’s parking chaos comes from just 20 streets.
                </>
              ) : (
                <span className="text-ink-muted">Loading violation intelligence…</span>
              )}
            </h2>
            <p className="mt-4 max-w-lg text-lg leading-relaxed text-ink-muted">
              Violations cluster hard. That’s bad news if you park blindly — and
              a precise map if you’re deploying officers. Same data, opposite
              uses.
            </p>
          </div>

          <dl className="grid grid-cols-2 gap-x-8 gap-y-8 border-t border-line pt-8 lg:border-l lg:border-t-0 lg:pl-10 lg:pt-0">
            <Metric
              value={k ? compact(k.total_violations) : "—"}
              label="violations analyzed"
              sub={k ? `${k.date_min} → ${k.date_max}` : ""}
            />
            <Metric
              value={k ? fmt(k.n_hotspots) : "—"}
              label="hotspot cells ranked"
              sub={k ? `${k.n_stations} police stations` : ""}
            />
            <Metric
              value={k ? `+${k.uplift_pp.toFixed(1)}pp` : "—"}
              label="coverage vs reactive"
              sub={k ? `same ${k.uplift_k} units` : ""}
              accent
            />
            <Metric
              value={k ? fmt(k.repeat_offenders) : "—"}
              label="repeat offenders"
              sub={k ? pct(k.repeat_offender_share, 1) + " of vehicles" : ""}
            />
          </dl>
        </div>
      </div>
    </section>
  );
}

function Metric({
  value,
  label,
  sub,
  accent,
}: {
  value: string;
  label: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div>
      <dd
        className={`font-display whitespace-nowrap text-3xl font-extrabold tnum leading-none ${
          accent ? "text-amber" : "text-ink"
        }`}
      >
        {value}
      </dd>
      <dt className="mt-2 text-sm font-medium text-ink">{label}</dt>
      {sub ? (
        <p className="mt-0.5 font-mono text-[0.68rem] text-ink-faint">{sub}</p>
      ) : null}
    </div>
  );
}
