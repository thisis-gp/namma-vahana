"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Section, Card, Loading, ErrorNote, Pill } from "../ui";
import { fmt, pct } from "@/lib/format";
import { useStation } from "./stationContext";
import type { Officer } from "@/lib/types";

const SHIFTS = ["Morning", "Afternoon", "Evening", "Night"];

export default function CommandSection() {
  const { station } = useStation();
  const officers = useApi(() => api.officers(station || undefined), [station]);
  const summary = useApi(
    () => (station ? api.stationSummary(station) : Promise.resolve(null)),
    [station],
  );
  const [nonce, setNonce] = useState(0);
  void nonce;

  const list = officers.data ?? [];
  const totals = useMemo(() => {
    const target = list.reduce((s, o) => s + o.target, 0);
    const done = list.reduce((s, o) => s + o.done, 0);
    return { target, done, pct: target ? done / target : 0 };
  }, [list]);

  return (
    <Section
      id="command"
      index="01"
      eyebrow="Command & accountability"
      title={
        station ? <>{station} — deployment</> : <>Who’s deployed, and how they’re tracking.</>
      }
      lede="Targets are derived from the violations data — the expected enforcement load on each officer’s beat — so deployment is fair and progress is auditable. Assign beats, set patrol windows, and see who’s on track."
      dark
    >
      {/* Accountability summary */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DarkStat
          label="Officers on duty"
          value={list.length ? fmt(list.length) : "—"}
          sub={station ? station : "across all stations"}
        />
        <DarkStat
          label="Weekly target (data-derived)"
          value={totals.target ? fmt(totals.target) : "—"}
          sub="expected enforcement actions"
        />
        <DarkStat
          label="Completed"
          value={totals.done ? fmt(totals.done) : "—"}
          sub={`${pct(totals.pct, 0)} of target`}
          accent
        />
        <DarkStat
          label={station ? "Enforcement gap" : "Stations covered"}
          value={
            station && summary.data
              ? pct(summary.data.enforcement_gap, 0)
              : station
                ? "—"
                : new Set(list.map((o) => o.station)).size.toString()
          }
          sub={
            station && summary.data
              ? `${summary.data.gap_confidence} confidence`
              : "filter to a station for detail"
          }
        />
      </div>

      {officers.loading ? (
        <Loading label="Loading roster…" />
      ) : officers.error ? (
        <ErrorNote error={officers.error} />
      ) : (
        <Card className="!bg-asphalt-2 !border-asphalt-line !p-0">
          <div className="hidden grid-cols-[1.4fr_1.6fr_1fr_1.2fr_auto] gap-3 border-b border-asphalt-line px-4 py-2.5 font-mono text-[0.66rem] uppercase tracking-wider text-[#7e8aa0] lg:grid">
            <span>Officer</span>
            <span>Assigned beat / area</span>
            <span>Patrol window</span>
            <span>Target progress</span>
            <span>Assign</span>
          </div>
          <ul className="divide-y divide-asphalt-line">
            {list.map((o) => (
              <OfficerRow key={o.id} officer={o} onChange={() => setNonce((n) => n + 1)} />
            ))}
            {list.length === 0 ? (
              <li className="px-4 py-6 text-center font-mono text-sm text-[#7e8aa0]">
                No officers rostered at this station.
              </li>
            ) : null}
          </ul>
        </Card>
      )}
    </Section>
  );
}

function OfficerRow({
  officer: o,
  onChange,
}: {
  officer: Officer;
  onChange: () => void;
}) {
  const [shift, setShift] = useState(o.shift);
  const [window, setWindow] = useState(o.patrol_window ?? "");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  const ratio = o.target ? o.done / o.target : 0;
  const onTrack = ratio >= 0.85;
  const behind = ratio < 0.6;

  const save = async () => {
    setBusy(true);
    setSaved(false);
    try {
      await api.assignOfficer(o.id, { shift, patrol_window: window });
      setSaved(true);
      onChange();
      setTimeout(() => setSaved(false), 1800);
    } catch {
      /* non-critical */
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="grid grid-cols-1 gap-3 px-4 py-3 lg:grid-cols-[1.4fr_1.6fr_1fr_1.2fr_auto] lg:items-center">
      <div>
        <p className="text-sm font-semibold text-white">{o.name}</p>
        <p className="font-mono text-[0.68rem] text-[#7e8aa0]">
          {o.badge} · {o.station}
        </p>
      </div>

      <p className="text-sm text-[#cdd6e2]">{o.area ?? "Unassigned"}</p>

      <select
        value={window}
        onChange={(e) => setWindow(e.target.value)}
        className="rounded-md border border-asphalt-line bg-asphalt px-2 py-1 font-mono text-xs text-white focus:border-cobalt focus:outline-none"
      >
        {[o.patrol_window, "7am–10am", "12pm–3pm", "5pm–8pm", "8pm–11pm"]
          .filter((v, i, a) => v && a.indexOf(v) === i)
          .map((w) => (
            <option key={w} value={w as string}>
              {w}
            </option>
          ))}
      </select>

      <div>
        <div className="mb-1 flex items-center justify-between font-mono text-[0.7rem]">
          <span className="text-[#cdd6e2]">
            {fmt(o.done)} / {fmt(o.target)}
          </span>
          <Pill tone={onTrack ? "ok" : behind ? "danger" : "amber"}>
            {onTrack ? "On track" : behind ? "Behind" : "Near"}
          </Pill>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-asphalt">
          <div
            className="h-full rounded-full"
            style={{
              width: `${Math.min(100, ratio * 100)}%`,
              background: onTrack ? "var(--ok)" : behind ? "var(--danger)" : "var(--amber)",
            }}
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <select
          value={shift}
          onChange={(e) => setShift(e.target.value)}
          className="rounded-md border border-asphalt-line bg-asphalt px-2 py-1 text-xs text-white focus:border-cobalt focus:outline-none"
        >
          {SHIFTS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <button
          onClick={save}
          disabled={busy}
          className="rounded-md bg-cobalt px-3 py-1 text-xs font-semibold text-white transition-colors hover:bg-cobalt-deep disabled:opacity-50"
        >
          {busy ? "…" : saved ? "✓" : "Save"}
        </button>
      </div>
    </li>
  );
}

function DarkStat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-xl border border-asphalt-line bg-asphalt-2 p-4">
      <p className="font-mono text-[0.66rem] uppercase tracking-wider text-[#7e8aa0]">
        {label}
      </p>
      <p
        className={`font-display mt-1 text-2xl font-extrabold tnum ${
          accent ? "text-amber" : "text-white"
        }`}
      >
        {value}
      </p>
      {sub ? <p className="mt-0.5 font-mono text-[0.66rem] text-[#7e8aa0]">{sub}</p> : null}
    </div>
  );
}
