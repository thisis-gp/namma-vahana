"use client";

import { useMemo } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Section, Card } from "./ui";
import { compact, daypartOf, fmt, pct, type Daypart } from "@/lib/format";
import { useStation } from "./officer/stationContext";

const DAYPARTS: Daypart[] = ["Morning", "Midday", "Evening", "Night"];
const DAYPART_HOURS: Record<Daypart, string> = {
  Morning: "5am – 12pm",
  Midday: "12pm – 5pm",
  Evening: "5pm – 9pm",
  Night: "9pm – 5am",
};

export default function WhenSection() {
  const { station } = useStation();
  const k = useApi(api.kpis);
  const hs = useApi(() => api.hotspots(station || undefined, 500), [station]);

  const { byDaypart, maxDp, interventions, total } = useMemo(() => {
    const list = hs.data ?? [];
    const byDaypart: Record<Daypart, number> = {
      Morning: 0,
      Midday: 0,
      Evening: 0,
      Night: 0,
    };
    const interventions = new Map<string, number>();
    let total = 0;
    for (const h of list) {
      const dp = daypartOf(h.peak_hours);
      if (dp) byDaypart[dp] += h.violation_count;
      total += h.violation_count;
      interventions.set(
        h.intervention_type,
        (interventions.get(h.intervention_type) ?? 0) + 1,
      );
    }
    const maxDp = Math.max(1, ...DAYPARTS.map((d) => byDaypart[d]));
    return {
      byDaypart,
      maxDp,
      total,
      interventions: [...interventions.entries()].sort((a, b) => b[1] - a[1]),
    };
  }, [hs.data]);

  const eveningShare = k.data ? k.data.evening_enforcement_share : 0.002;

  return (
    <Section
      id="when"
      index="02"
      eyebrow="When to be there"
      title={<>The violations peak after dark. Enforcement doesn’t.</>}
      lede={
        <>
          Only <span className="text-ink">{pct(eveningShare, 1)}</span> of
          enforcement currently happens in the evening — the window when parking
          pressure is highest. That mismatch is the easiest win on this page.
        </>
      }
    >
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <p className="eyebrow mb-5">Violations by time of day</p>
          <div className="space-y-4">
            {DAYPARTS.map((d) => {
              const v = byDaypart[d];
              const w = (v / maxDp) * 100;
              const isPeak = v === maxDp;
              return (
                <div key={d}>
                  <div className="mb-1 flex items-baseline justify-between">
                    <span className="text-sm font-medium text-ink">
                      {d}{" "}
                      <span className="font-mono text-[0.7rem] text-ink-faint">
                        {DAYPART_HOURS[d]}
                      </span>
                    </span>
                    <span className="font-mono text-sm tnum text-ink-muted">
                      {compact(v)}
                    </span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-full rounded-full transition-[width] duration-700"
                      style={{
                        width: `${w}%`,
                        background: isPeak
                          ? "var(--amber)"
                          : "var(--cobalt)",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="mt-5 border-t border-line pt-3 font-mono text-[0.7rem] text-ink-faint">
            Peak window of each hotspot, weighted by its violation count
            {total ? ` · ${fmt(total)} violations across top cells` : ""}.
          </p>
        </Card>

        <Card>
          <p className="eyebrow mb-5">What the hotspots need</p>
          <ul className="space-y-2.5">
            {interventions.map(([type, count]) => (
              <li
                key={type}
                className="flex items-center justify-between gap-3 rounded-lg border border-line bg-surface-2 px-3 py-2.5"
              >
                <span className="text-sm font-medium text-ink">{type}</span>
                <span className="font-mono text-sm font-semibold tnum text-cobalt">
                  {count}
                </span>
              </li>
            ))}
            {interventions.length === 0 && hs.loading ? (
              <li className="font-mono text-sm text-ink-faint">Loading…</li>
            ) : null}
          </ul>
          <p className="mt-4 font-mono text-[0.7rem] text-ink-faint">
            Recommended action type per hotspot — not every spot needs a patrol;
            some need signage or towing.
          </p>
        </Card>
      </div>
    </Section>
  );
}
