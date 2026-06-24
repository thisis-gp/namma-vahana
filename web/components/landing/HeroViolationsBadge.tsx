"use client";

import { api } from "@/lib/api";
import { compact } from "@/lib/format";
import { HERO_CACHE_KEYS } from "@/lib/hero-cache";
import { useApi } from "@/lib/useApi";

/** Hero chip — only shows a count when KPIs have loaded from the API. */
export default function HeroViolationsBadge() {
  const { data: k, loading } = useApi(api.kpis, [], HERO_CACHE_KEYS.kpis);

  if (loading && !k) {
    return (
      <span className="rounded-full border border-line bg-white/75 px-3 py-1 text-ink-faint">
        Loading dataset…
      </span>
    );
  }

  if (!k) return null;

  return (
    <span className="rounded-full border border-line bg-white/75 px-3 py-1">
      {compact(k.total_violations)} violations analyzed
    </span>
  );
}
