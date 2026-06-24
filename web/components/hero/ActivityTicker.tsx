"use client";

import { api } from "@/lib/api";
import { HERO_CACHE_KEYS } from "@/lib/hero-cache";
import { useApi } from "@/lib/useApi";
import { fmt } from "@/lib/format";

export default function ActivityTicker() {
  const k = useApi(api.kpis, [], HERO_CACHE_KEYS.kpis);
  const reports = useApi(() => api.reports(), []);
  const challans = useApi(() => api.challans(), []);

  const all = reports.data ?? [];
  const verified = all.filter((r) => r.status === "Verified").length;
  const pending = all.filter((r) => r.status === "Pending").length;

  const items = [
    { label: "citizen reports", value: all.length ? fmt(all.length) : "—" },
    { label: "verified by police", value: fmt(verified) },
    { label: "awaiting review", value: fmt(pending) },
    {
      label: "challans on record",
      value: challans.data ? fmt(challans.data.length) : "—",
    },
    {
      label: "coverage vs reactive",
      value: k.data ? `+${k.data.uplift_pp.toFixed(1)}pp` : "—",
      accent: true,
    },
  ];

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border border-line bg-surface/70 px-4 py-3 backdrop-blur">
      <span className="flex items-center gap-2 font-mono text-[0.7rem] uppercase tracking-wider text-ink-muted">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ok opacity-60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-ok" />
        </span>
        Live
      </span>
      {items.map((it) => (
        <span key={it.label} className="flex items-baseline gap-1.5">
          <span
            className={`font-mono text-sm font-semibold tnum ${
              it.accent ? "text-amber" : "text-ink"
            }`}
          >
            {it.value}
          </span>
          <span className="text-xs text-ink-muted">{it.label}</span>
        </span>
      ))}
    </div>
  );
}
