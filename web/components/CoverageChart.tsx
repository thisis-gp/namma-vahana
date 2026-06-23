"use client";

import { useMemo } from "react";
import type { Backtest } from "@/lib/types";
import { BRAND } from "@/lib/brand";

const W = 640;
const H = 300;
const PAD = { t: 20, r: 20, b: 38, l: 44 };

export default function CoverageChart({
  data,
  selectedK,
}: {
  data: Backtest[];
  selectedK: number;
}) {
  const sorted = useMemo(() => [...data].sort((a, b) => a.k - b.k), [data]);

  if (sorted.length === 0) return null;

  const ks = sorted.map((d) => d.k);
  const kMin = Math.min(...ks);
  const kMax = Math.max(...ks);
  const yMax = Math.min(
    1,
    Math.max(...sorted.map((d) => Math.max(d.parkpulse_coverage, d.reactive_coverage))) *
      1.15,
  );

  const x = (k: number) =>
    PAD.l + ((k - kMin) / Math.max(1, kMax - kMin)) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - v / yMax) * (H - PAD.t - PAD.b);

  const path = (key: "parkpulse_coverage" | "reactive_coverage") =>
    sorted.map((d, i) => `${i === 0 ? "M" : "L"} ${x(d.k)} ${y(d[key])}`).join(" ");

  const sel = sorted.reduce((best, d) =>
    Math.abs(d.k - selectedK) < Math.abs(best.k - selectedK) ? d : best,
  );

  const yTicks = [0, 0.25, 0.5, 0.75].filter((t) => t <= yMax);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      role="img"
      aria-label={`Coverage versus units deployed. At ${sel.k} units, ${BRAND.productLabel} covers ${Math.round(
        sel.parkpulse_coverage * 100,
      )} percent versus ${Math.round(sel.reactive_coverage * 100)} percent reactive.`}
    >
      {/* grid + y labels */}
      {yTicks.map((t) => (
        <g key={t}>
          <line
            x1={PAD.l}
            x2={W - PAD.r}
            y1={y(t)}
            y2={y(t)}
            stroke="var(--line)"
            strokeWidth={1}
          />
          <text
            x={PAD.l - 8}
            y={y(t) + 4}
            textAnchor="end"
            className="fill-[var(--ink-faint)]"
            style={{ font: "500 11px var(--font-mono)" }}
          >
            {Math.round(t * 100)}%
          </text>
        </g>
      ))}

      {/* selected-k marker */}
      <line
        x1={x(sel.k)}
        x2={x(sel.k)}
        y1={PAD.t}
        y2={H - PAD.b}
        stroke="var(--cobalt)"
        strokeWidth={1}
        strokeDasharray="4 4"
        opacity={0.5}
      />

      {/* reactive (muted) */}
      <path d={path("reactive_coverage")} fill="none" stroke="var(--ink-faint)" strokeWidth={2} />
      {/* parkpulse (cobalt) */}
      <path d={path("parkpulse_coverage")} fill="none" stroke="var(--cobalt)" strokeWidth={3} />

      {/* selected dots */}
      <circle cx={x(sel.k)} cy={y(sel.reactive_coverage)} r={4} fill="var(--ink-faint)" />
      <circle cx={x(sel.k)} cy={y(sel.parkpulse_coverage)} r={5} fill="var(--cobalt)" />

      {/* x labels */}
      {sorted
        .filter((_, i) => i % Math.ceil(sorted.length / 6) === 0 || sorted[i].k === kMax)
        .map((d) => (
          <text
            key={d.k}
            x={x(d.k)}
            y={H - PAD.b + 18}
            textAnchor="middle"
            className="fill-[var(--ink-faint)]"
            style={{ font: "500 11px var(--font-mono)" }}
          >
            {d.k}
          </text>
        ))}
      <text
        x={(W + PAD.l - PAD.r) / 2}
        y={H - 4}
        textAnchor="middle"
        className="fill-[var(--ink-muted)]"
        style={{ font: "500 11px var(--font-mono)" }}
      >
        units / hotspots deployed →
      </text>
    </svg>
  );
}
