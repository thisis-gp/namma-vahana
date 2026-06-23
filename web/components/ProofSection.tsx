"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Section, Card, Loading, ErrorNote } from "./ui";
import { fmt, pct } from "@/lib/format";
import CoverageChart from "./CoverageChart";
import { BRAND } from "@/lib/brand";

export default function ProofSection() {
  const bt = useApi(api.backtest);
  const fc = useApi(api.nbForecast);

  const data = useMemo(
    () => [...(bt.data ?? [])].sort((a, b) => a.k - b.k),
    [bt.data],
  );
  const [k, setK] = useState<number | null>(null);

  useEffect(() => {
    if (k === null && data.length) {
      // default to the k with the biggest uplift
      const best = data.reduce((a, b) => (b.uplift_pp > a.uplift_pp ? b : a));
      setK(best.k);
    }
  }, [data, k]);

  const sel = useMemo(() => {
    if (!data.length || k === null) return null;
    return data.reduce((best, d) =>
      Math.abs(d.k - k) < Math.abs(best.k - k) ? d : best,
    );
  }, [data, k]);

  const topForecast = useMemo(
    () => [...(fc.data ?? [])].sort((a, b) => b.forecast_next_week - a.forecast_next_week).slice(0, 6),
    [fc.data],
  );
  const fcMax = Math.max(1, ...topForecast.map((f) => f.upper_95));

  return (
    <Section
      id="proof"
      index="04"
      eyebrow="Does it actually work?"
      title={<>Same units. More violations caught.</>}
      lede={`We replayed history: rank hotspots with ${BRAND.productLabel}, then check how many of the next period’s violations that patrol would have actually covered — versus a reactive plan that chases last week’s complaints. Drag the slider.`}
    >
      <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        <Card>
          {bt.loading ? (
            <Loading label="Loading backtest…" />
          ) : bt.error ? (
            <ErrorNote error={bt.error} />
          ) : (
            <>
              <div className="mb-4 flex flex-wrap items-end gap-x-8 gap-y-3">
                <Readout
                  label={`${BRAND.productLabel} covers`}
                  value={sel ? pct(sel.parkpulse_coverage, 1) : "—"}
                  tone="cobalt"
                />
                <Readout
                  label="Reactive covers"
                  value={sel ? pct(sel.reactive_coverage, 1) : "—"}
                  tone="muted"
                />
                <Readout
                  label="Uplift"
                  value={sel ? `+${sel.uplift_pp.toFixed(1)}pp` : "—"}
                  tone="amber"
                />
              </div>

              {sel ? <CoverageChart data={data} selectedK={sel.k} /> : null}

              <div className="mt-5 border-t border-line pt-4">
                <label
                  htmlFor="k"
                  className="mb-2 flex items-center justify-between text-sm"
                >
                  <span className="font-medium text-ink">Units deployed</span>
                  <span className="font-mono font-semibold text-cobalt">
                    {sel?.k ?? "—"}
                  </span>
                </label>
                <input
                  id="k"
                  type="range"
                  min={0}
                  max={data.length - 1}
                  value={
                    sel ? data.findIndex((d) => d.k === sel.k) : 0
                  }
                  onChange={(e) => setK(data[Number(e.target.value)]?.k ?? null)}
                  className="w-full accent-[var(--cobalt)]"
                  aria-valuetext={`${sel?.k ?? 0} units`}
                />
                <div className="mt-2 flex items-center gap-2 font-mono text-xs text-ink-muted">
                  <span className="inline-block h-1 w-5 rounded bg-cobalt" />
                  {BRAND.productLabel}
                  <span className="ml-3 inline-block h-1 w-5 rounded bg-[var(--ink-faint)]" />
                  Reactive
                </div>
              </div>
            </>
          )}
        </Card>

        <Card>
          <p className="eyebrow mb-1">Looking ahead</p>
          <h3 className="font-display mb-4 text-lg font-bold text-ink">
            Next week’s forecast
          </h3>
          {fc.loading ? (
            <Loading label="Loading forecast…" />
          ) : fc.error ? (
            <ErrorNote error={fc.error} />
          ) : (
            <ul className="space-y-3">
              {topForecast.map((f) => (
                <li key={f.police_station}>
                  <div className="mb-1 flex items-baseline justify-between gap-2">
                    <span className="truncate text-sm font-medium text-ink">
                      {f.police_station}
                    </span>
                    <span className="font-mono text-sm font-semibold tnum text-ink">
                      {fmt(f.forecast_next_week)}
                    </span>
                  </div>
                  {/* 95% CI range bar */}
                  <div className="relative h-2 rounded-full bg-surface-2">
                    <div
                      className="absolute h-full rounded-full bg-cobalt-soft"
                      style={{
                        left: `${(f.lower_95 / fcMax) * 100}%`,
                        width: `${((f.upper_95 - f.lower_95) / fcMax) * 100}%`,
                      }}
                    />
                    <div
                      className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-cobalt"
                      style={{ left: `${(f.forecast_next_week / fcMax) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 font-mono text-[0.7rem] text-ink-faint">
            Predicted violations next week with a 95% confidence range
            (negative-binomial model).
          </p>
        </Card>
      </div>
    </Section>
  );
}

function Readout({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "cobalt" | "amber" | "muted";
}) {
  const c =
    tone === "cobalt"
      ? "text-cobalt"
      : tone === "amber"
        ? "text-amber"
        : "text-ink-muted";
  return (
    <div>
      <p className="text-xs font-medium text-ink-muted">{label}</p>
      <p className={`font-display text-3xl font-extrabold tnum ${c}`}>{value}</p>
    </div>
  );
}
