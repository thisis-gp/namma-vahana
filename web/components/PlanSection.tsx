"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useRole } from "@/lib/role";
import { Section, Card, Loading, ErrorNote, Pill } from "./ui";
import { fmt } from "@/lib/format";
import { useStation } from "./officer/stationContext";
import type { Challan, Patrol } from "@/lib/types";

export default function PlanSection() {
  const { station } = useStation();
  const patrol = useApi(() => api.patrol(station || undefined), [station]);
  const { isOfficer } = useRole();
  const [shift, setShift] = useState<string>("");

  const shifts = useMemo(() => {
    const s = new Set<string>();
    (patrol.data ?? []).forEach((p) => s.add(p.shift));
    return [...s];
  }, [patrol.data]);

  useEffect(() => {
    if (!shift && shifts.length) setShift(shifts[0]);
  }, [shifts, shift]);

  const beats = useMemo(
    () =>
      (patrol.data ?? [])
        .filter((p) => !shift || p.shift === shift)
        .sort((a, b) => a.rank - b.rank)
        .slice(0, 10),
    [patrol.data, shift],
  );

  const [selected, setSelected] = useState<Patrol | null>(null);

  return (
    <Section
      id="plan"
      index="03"
      eyebrow="The deployment"
      title={<>A patrol roster, ready to hand out.</>}
      lede={
        isOfficer
          ? "Optimized beats per shift — each a real hotspot with the unit assigned, what to expect, and what to watch for. Pick a beat to pre-fill a challan."
          : "Where the traffic police focus each shift — optimized from the data. Residents can’t issue fines, but you can report what you see."
      }
    >
      <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <Card className="overflow-hidden !p-0">
          <div className="flex flex-wrap items-center gap-2 border-b border-line p-4">
            <span className="eyebrow mr-1">Shift</span>
            {patrol.loading && shifts.length === 0 ? (
              <span className="font-mono text-sm text-ink-faint">Loading…</span>
            ) : (
              shifts.map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setShift(s);
                    setSelected(null);
                  }}
                  className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                    shift === s
                      ? "bg-cobalt text-white"
                      : "bg-surface-2 text-ink-muted hover:text-ink"
                  }`}
                >
                  {s}
                </button>
              ))
            )}
          </div>

          {patrol.error ? (
            <div className="p-4">
              <ErrorNote error={patrol.error} />
            </div>
          ) : (
            <div className="divide-y divide-line">
              {beats.map((b) => {
                const active = selected?.h3 === b.h3 && selected?.shift === b.shift;
                return (
                  <button
                    key={`${b.shift}-${b.h3}`}
                    onClick={() => setSelected(b)}
                    className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors ${
                      active ? "bg-cobalt-soft" : "hover:bg-surface-2"
                    }`}
                  >
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-surface-2 font-mono text-sm font-semibold text-cobalt">
                      {b.rank}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-ink">
                        {b.display_location}
                      </span>
                      <span className="font-mono text-[0.7rem] text-ink-faint">
                        {b.assigned_unit} · {b.dominant_violation}
                      </span>
                    </span>
                    <span className="shrink-0 text-right">
                      <span className="block font-mono text-sm font-semibold tnum text-ink">
                        {fmt(b.expected_violations)}
                      </span>
                      <span className="font-mono text-[0.62rem] text-ink-faint">
                        expected
                      </span>
                    </span>
                  </button>
                );
              })}
              {beats.length === 0 && !patrol.loading ? (
                <p className="p-4 font-mono text-sm text-ink-faint">
                  No beats for this shift.
                </p>
              ) : null}
            </div>
          )}
        </Card>

        {isOfficer ? <IssueChallan beat={selected} /> : <ResidentNote />}
      </div>
    </Section>
  );
}

function ResidentNote() {
  return (
    <Card>
      <p className="eyebrow mb-1">For residents</p>
      <h3 className="font-display mb-3 text-lg font-bold text-ink">
        Only officers issue challans
      </h3>
      <p className="mb-4 text-sm leading-relaxed text-ink-muted">
        Issuing a fine is a police action. But you can still help: if you spot a
        vehicle parked illegally, report it with the location. An officer
        reviews it, and if it checks out it becomes an official challan — and you
        earn points.
      </p>
      <a
        href="#community"
        className="inline-flex items-center gap-1.5 rounded-lg bg-cobalt px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-cobalt-deep"
      >
        Report a vehicle →
      </a>
    </Card>
  );
}

function IssueChallan({ beat }: { beat: Patrol | null }) {
  const [vehicle, setVehicle] = useState("");
  const [location, setLocation] = useState("");
  const [busy, setBusy] = useState(false);
  const [issued, setIssued] = useState<Challan[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (beat) setLocation(beat.display_location);
  }, [beat]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vehicle.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const c = await api.createChallan({
        vehicle: vehicle.trim().toUpperCase(),
        location: location.trim(),
        station: beat?.police_station ?? "City-wide",
        category: beat?.dominant_violation || "Wrong Parking",
      });
      setIssued((prev) => [c, ...prev].slice(0, 4));
      setVehicle("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <p className="eyebrow mb-1">Act on it</p>
      <h3 className="font-display mb-4 text-lg font-bold text-ink">
        Issue a challan
      </h3>
      <form onSubmit={submit} className="space-y-3">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-ink-muted">
            Vehicle number
          </span>
          <input
            value={vehicle}
            onChange={(e) => setVehicle(e.target.value)}
            placeholder="KA 01 AB 1234"
            className="w-full rounded-lg border border-line bg-surface-2 px-3 py-2 font-mono text-sm uppercase tracking-wider text-ink placeholder:text-ink-faint focus:border-cobalt focus:bg-surface focus:outline-none"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-ink-muted">
            Location {beat ? "(from selected beat)" : ""}
          </span>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Pick a beat, or type a spot"
            className="w-full rounded-lg border border-line bg-surface-2 px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-cobalt focus:bg-surface focus:outline-none"
          />
        </label>
        <button
          type="submit"
          disabled={busy || !vehicle.trim()}
          className="w-full rounded-lg bg-cobalt px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-cobalt-deep disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Issuing…" : "Issue challan"}
        </button>
      </form>

      {err ? (
        <p className="mt-3 font-mono text-xs text-danger">{err}</p>
      ) : null}

      {issued.length > 0 ? (
        <div className="mt-4 border-t border-line pt-3">
          <p className="eyebrow mb-2">Just issued</p>
          <ul className="space-y-1.5">
            {issued.map((c) => (
              <li
                key={c.id}
                className="flex items-center justify-between gap-2 text-sm"
              >
                <span className="font-mono font-medium text-ink">
                  {c.vehicle}
                </span>
                <Pill tone="ok">{c.status}</Pill>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="mt-4 font-mono text-[0.7rem] text-ink-faint">
        Writes to the live operations API — a working enforcement loop, not a
        mockup.
      </p>
    </Card>
  );
}
