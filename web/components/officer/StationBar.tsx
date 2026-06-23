"use client";

import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useStation } from "./stationContext";

// Sticky global filter — every officer section reads `station` from context,
// so changing it here re-scopes the whole console to one station.
export default function StationBar() {
  const { data } = useApi(api.stations);
  const { station, setStation } = useStation();
  const stations = [...(data ?? [])].sort((a, b) => b.violations - a.violations);

  return (
    <div className="sticky top-[3.25rem] z-40 border-b border-asphalt-line bg-asphalt/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-3 px-5 py-3 sm:px-8">
        <span className="font-mono text-[0.68rem] uppercase tracking-wider text-[#7e8aa0]">
          Filtering
        </span>
        <select
          value={station}
          onChange={(e) => setStation(e.target.value)}
          className="rounded-lg border border-asphalt-line bg-asphalt-2 px-3 py-1.5 text-sm font-medium text-white focus:border-cobalt focus:outline-none"
        >
          <option value="">All stations ({stations.length})</option>
          {stations.map((s) => (
            <option key={s.police_station} value={s.police_station}>
              {s.police_station}
            </option>
          ))}
        </select>
        {station ? (
          <button
            onClick={() => setStation("")}
            className="rounded-md px-2 py-1 font-mono text-xs text-[#9fb0c4] hover:text-white"
          >
            ✕ clear
          </button>
        ) : (
          <span className="font-mono text-xs text-[#7e8aa0]">
            every section below is scoped to this station
          </span>
        )}
      </div>
    </div>
  );
}
