"use client";

import { api } from "@/lib/api";
import { HERO_CACHE_KEYS } from "@/lib/hero-cache";
import { useApi } from "@/lib/useApi";
import { useRole } from "@/lib/role";
import { fmt } from "@/lib/format";
import Logo from "@/components/brand/Logo";
import { BRAND } from "@/lib/brand";

export default function Footer() {
  const { data: k } = useApi(api.kpis, [], HERO_CACHE_KEYS.kpis);
  const { isOfficer } = useRole();

  return (
    <footer className="bg-asphalt text-[#aeb9c7]">
      <div className="mx-auto w-full max-w-6xl px-5 py-14 sm:px-8">
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-sm">
            <div className="mb-3">
              <Logo variant="light" />
            </div>
            <p className="text-sm leading-relaxed">
              {BRAND.tagline} — turning {k ? fmt(k.total_violations) : "298,443"}{" "}
              historical violations into where to go, when, and what to do for
              Bengaluru Traffic Police and residents.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-x-10 gap-y-2 font-mono text-[0.78rem]">
            <span className="text-[#7e8aa0]">Period</span>
            <span className="text-white">
              {k ? `${k.date_min} → ${k.date_max}` : "Nov 2023 – Apr 2024"}
            </span>
            <span className="text-[#7e8aa0]">Stations</span>
            <span className="text-white">{k ? k.n_stations : "54"}</span>
            <span className="text-[#7e8aa0]">Hotspot cells</span>
            <span className="text-white">{k ? fmt(k.n_hotspots) : "2,532"}</span>
            <span className="text-[#7e8aa0]">Model P@20</span>
            <span className="text-white">
              {k ? k.precision_at_20.toFixed(2) : "0.85"} vs{" "}
              {k ? k.naive_precision_at_20.toFixed(2) : "0.75"} naive
            </span>
          </div>
        </div>

        <div className="mt-10 border-t border-asphalt-line pt-5 text-[0.72rem] leading-relaxed text-[#7e8aa0]">
          <p>
            <strong className="text-[#9fb0c4]">Methodology note.</strong> The
            congestion-impact score is a <em>proxy</em> built from violation
            volume, severity, road class and peak concentration — not a direct
            measurement of traffic flow. All figures are derived solely from the
            provided enforcement dataset; no external data is used.
          </p>
        </div>
      </div>
    </footer>
  );
}
