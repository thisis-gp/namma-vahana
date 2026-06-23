"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useRole } from "@/lib/role";
import { Section, Loading, ErrorNote } from "./ui";
import { fmt, maskPlate } from "@/lib/format";
import { useStation } from "./officer/stationContext";

export default function OffendersSection({
  index = "07",
}: {
  index?: string;
}) {
  const { station } = useStation();
  const { data, loading, error } = useApi(
    () => api.watchlist(60, station || undefined),
    [station],
  );
  const { isOfficer } = useRole();
  const [showAll, setShowAll] = useState(false);

  const list = data ?? [];
  const shown = showAll ? list : list.slice(0, 12);

  return (
    <Section
      id="offenders"
      index={index}
      eyebrow="Repeat offenders"
      title={<>The same plates, again and again.</>}
      lede={
        isOfficer
          ? station
            ? `Repeat offenders whose hotspot falls under ${station}. Full plates shown for enforcement — worth a targeted notice.`
            : "A handful of vehicles drive a disproportionate share of violations across many locations. Full plates shown for enforcement — worth a targeted notice. Filter to a station above to scope this list."
          : "A handful of vehicles drive a disproportionate share of violations. Plates are masked in the public view — only the traffic police see full numbers."
      }
    >
      {!isOfficer ? (
        <div className="mb-5 flex items-center gap-2 rounded-lg border border-cobalt-soft bg-cobalt-soft px-4 py-2.5 text-sm text-cobalt-deep">
          <span aria-hidden>🔒</span>
          <span>
            Licence plates are masked to protect privacy. Switch to the{" "}
            <strong>Officer</strong> view (top right) to see full numbers.
          </span>
        </div>
      ) : null}
      {loading ? (
        <Loading label="Loading watchlist…" />
      ) : error ? (
        <ErrorNote error={error} />
      ) : list.length === 0 ? (
        <div className="rounded-xl border border-line bg-surface px-4 py-10 text-center text-sm text-ink-muted">
          No repeat offenders pinned to{" "}
          <span className="font-medium text-ink">{station}</span>. Repeat
          offenders are matched to a station by their most-frequent junction —
          clear the filter to see the city-wide list.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line bg-surface">
          <div className="hidden grid-cols-[auto_1fr_auto_auto] gap-4 border-b border-line bg-surface-2 px-4 py-2.5 font-mono text-[0.68rem] uppercase tracking-wider text-ink-faint sm:grid">
            <span>Plate</span>
            <span>Top location</span>
            <span className="text-right">Spots</span>
            <span className="text-right">Violations</span>
          </div>
          <ul className="divide-y divide-line">
            {shown.map((w) => (
              <li
                key={w.vehicle_number}
                className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-1 px-4 py-3 sm:grid-cols-[auto_1fr_auto_auto]"
              >
                <span className="inline-flex items-center rounded-md border-2 border-ink/15 bg-surface-2 px-2 py-1 font-mono text-sm font-semibold tracking-wider text-ink">
                  {maskPlate(w.vehicle_number, isOfficer)}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm text-ink">
                    {w.top_location}
                  </span>
                  <span className="flex flex-wrap items-center gap-x-2 font-mono text-[0.7rem] text-ink-faint">
                    {w.station ? (
                      <span
                        className="rounded bg-cobalt-soft px-1.5 py-0.5 text-cobalt-deep"
                        title={
                          w.station_exact
                            ? "Matched by the offender’s top junction"
                            : "Inferred from the area in the offender’s top location"
                        }
                      >
                        {w.station_exact ? "" : "near "}
                        {w.station}
                      </span>
                    ) : null}
                    <span>
                      {w.vehicle_type} · seen {w.first_seen} → {w.last_seen}
                    </span>
                  </span>
                </span>
                <span className="hidden text-right font-mono text-sm tnum text-ink-muted sm:block">
                  {w.distinct_cells}
                </span>
                <span className="col-span-2 text-right font-mono text-sm font-semibold tnum text-amber sm:col-span-1">
                  {fmt(w.violations)}
                  <span className="text-ink-faint sm:hidden"> violations</span>
                </span>
              </li>
            ))}
          </ul>
          {list.length > 12 ? (
            <button
              onClick={() => setShowAll((v) => !v)}
              className="w-full border-t border-line bg-surface-2 py-2.5 text-sm font-medium text-cobalt hover:bg-cobalt-soft"
            >
              {showAll ? "Show fewer" : `Show all ${list.length} offenders`}
            </button>
          ) : null}
        </div>
      )}
    </Section>
  );
}
