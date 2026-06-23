"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Section, Card, Loading, ErrorNote, Pill } from "./ui";
import { fmt } from "@/lib/format";
import { fileToCompressedDataUrl } from "@/lib/image";
import type { LeaderEntry } from "@/lib/types";
import { readStorage, writeStorage, STORAGE_KEYS } from "@/lib/brand";

const CATEGORIES = [
  "Wrong Parking",
  "No Parking",
  "Double Parking",
  "Footpath Parking",
  "Blocking Driveway",
  "Bus Bay / Stop",
];

// Gamification ladder. Points come only from officer-verified reports.
const LEVELS = [
  { name: "New Reporter", min: 0, icon: "🌱" },
  { name: "Street Spotter", min: 1, icon: "👀" },
  { name: "Bronze Guardian", min: 100, icon: "🥉" },
  { name: "Silver Guardian", min: 300, icon: "🥈" },
  { name: "Gold Guardian", min: 600, icon: "🥇" },
];
const POINTS_PER_TREE = 100;

function levelFor(points: number) {
  let cur = LEVELS[0];
  let next = LEVELS[1];
  for (let i = 0; i < LEVELS.length; i++) {
    if (points >= LEVELS[i].min) {
      cur = LEVELS[i];
      next = LEVELS[i + 1] ?? LEVELS[i];
    }
  }
  return { cur, next };
}

export default function ResidentCommunity({ index = "02" }: { index?: string }) {
  const [nonce, setNonce] = useState(0);
  const [handle, setHandle] = useState<string>("");

  useEffect(() => {
    setHandle(readStorage(STORAGE_KEYS.handle) ?? "");
  }, []);

  return (
    <Section
      id="community"
      index={index}
      eyebrow="See it? Report it. Earn for it."
      title={<>Report illegal parking — and grow the city.</>}
      lede="Spotted a vehicle parked illegally? Tell the traffic police. An officer reviews every report; verified ones become official challans, earn you green points, and those points plant real trees. You can’t issue fines — you can make the city better."
    >
      <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <ReportForm onSubmitted={() => setNonce((n) => n + 1)} onHandle={setHandle} />
        <div className="space-y-5">
          <GreenWallet handle={handle} nonce={nonce} />
          <Leaderboard nonce={nonce} handle={handle} />
        </div>
      </div>
    </Section>
  );
}

/* ── Report form (with photo) ──────────────────────────────────────────── */

function ReportForm({
  onSubmitted,
  onHandle,
}: {
  onSubmitted: () => void;
  onHandle: (h: string) => void;
}) {
  const [name, setName] = useState("");
  const [vehicle, setVehicle] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [location, setLocation] = useState("");
  const [note, setNote] = useState("");
  const [image, setImage] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const saved = readStorage(STORAGE_KEYS.handle);
    if (saved) setName(saved);
  }, []);

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    setErr(null);
    try {
      setImage(await fileToCompressedDataUrl(f));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Image failed");
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !location.trim()) return;
    setBusy(true);
    setErr(null);
    setDone(null);
    try {
      writeStorage(STORAGE_KEYS.handle, name.trim());
      onHandle(name.trim());
      await api.createReport({
        reporter: name.trim(),
        vehicle: vehicle.trim().toUpperCase(),
        category,
        location: location.trim(),
        note: note.trim(),
        image,
      });
      setDone("Report submitted. An officer will review it — verify earns you 50 green points.");
      setVehicle("");
      setLocation("");
      setNote("");
      setImage("");
      if (fileRef.current) fileRef.current.value = "";
      onSubmitted();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <p className="eyebrow mb-1">Report illegal parking</p>
      <h3 className="font-display mb-4 text-lg font-bold text-ink">Takes 20 seconds</h3>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            className="field"
          />
          <input
            value={vehicle}
            onChange={(e) => setVehicle(e.target.value)}
            placeholder="Vehicle no. (optional)"
            className="field font-mono uppercase tracking-wider"
          />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="field">
          {CATEGORIES.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Where? Area, junction or landmark"
          className="field"
        />
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Anything else? (optional)"
          className="field"
        />

        {/* Photo evidence */}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={(e) => onFile(e.target.files?.[0])}
          className="hidden"
          id="report-photo"
        />
        {image ? (
          <div className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={image} alt="evidence preview" className="h-16 w-24 rounded-md object-cover" />
            <button
              type="button"
              onClick={() => {
                setImage("");
                if (fileRef.current) fileRef.current.value = "";
              }}
              className="text-sm text-ink-muted hover:text-danger"
            >
              Remove photo
            </button>
          </div>
        ) : (
          <label
            htmlFor="report-photo"
            className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-line bg-surface-2 px-3 py-3 text-sm text-ink-muted hover:border-cobalt hover:text-cobalt"
          >
            📷 Attach a photo — stronger evidence, faster verification
          </label>
        )}

        <button
          type="submit"
          disabled={busy || !name.trim() || !location.trim()}
          className="w-full rounded-lg bg-cobalt px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-cobalt-deep disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Submitting…" : "Submit report"}
        </button>
      </form>

      {done ? (
        <p className="mt-3 rounded-lg border border-[#cfe9db] bg-[#e2f3ea] px-3 py-2 text-sm text-[#136b46]">
          {done}
        </p>
      ) : null}
      {err ? <p className="mt-3 font-mono text-xs text-danger">{err}</p> : null}

      <p className="mt-4 font-mono text-[0.7rem] leading-relaxed text-ink-faint">
        Points are awarded only after an officer verifies a report — so false
        reports earn nothing. Be accurate, not fast.
      </p>
    </Card>
  );
}

/* ── Green wallet: points → trees (simulated) ──────────────────────────── */

function GreenWallet({ handle, nonce }: { handle: string; nonce: number }) {
  const { data } = useApi(() => api.leaderboard(50), [nonce]);
  const [redeemed, setRedeemed] = useState(0);
  const [justPlanted, setJustPlanted] = useState(false);

  // Persist simulated redemptions locally (no payment gateway in the demo).
  useEffect(() => {
    const r = Number(readStorage(STORAGE_KEYS.trees) ?? "0");
    setRedeemed(Number.isFinite(r) ? r : 0);
  }, [handle]);

  const me = useMemo(
    () => (data ?? []).find((e) => e.reporter === handle),
    [data, handle],
  );
  const earned = me?.points ?? 0;
  const available = Math.max(0, earned - redeemed * POINTS_PER_TREE);
  const canPlant = available >= POINTS_PER_TREE;
  const { cur, next } = levelFor(earned);
  const toNext = Math.max(0, next.min - earned);

  // Community total trees (everyone's points / threshold), a feel-good counter.
  const communityTrees = Math.floor(
    (data ?? []).reduce((s, e) => s + e.points, 0) / POINTS_PER_TREE,
  );

  const plant = () => {
    const n = redeemed + 1;
    setRedeemed(n);
    writeStorage(STORAGE_KEYS.trees, String(n));
    setJustPlanted(true);
    setTimeout(() => setJustPlanted(false), 2200);
  };

  return (
    <Card className="!bg-[#f1f8f3] !border-[#cfe9db]">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="eyebrow mb-0.5" style={{ color: "#136b46" }}>
            Green wallet
          </p>
          <h3 className="font-display text-lg font-bold text-[#0f5135]">
            Turn points into trees
          </h3>
        </div>
        <span className="text-3xl" aria-hidden>
          🌳
        </span>
      </div>

      {handle ? (
        <>
          <div className="mb-3 flex items-end justify-between">
            <div>
              <p className="font-display text-3xl font-extrabold tnum text-[#0f5135]">
                {fmt(available)}
              </p>
              <p className="text-xs text-[#2f6b4f]">green points available</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold text-[#0f5135]">
                {cur.icon} {cur.name}
              </p>
              <p className="font-mono text-[0.7rem] text-[#2f6b4f]">
                {toNext > 0 ? `${toNext} pts to ${next.name}` : "max level"}
              </p>
            </div>
          </div>

          <button
            onClick={plant}
            disabled={!canPlant}
            className="w-full rounded-lg bg-[#1f8a5b] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#176c47] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {canPlant
              ? `Plant a tree — ${POINTS_PER_TREE} pts`
              : `${POINTS_PER_TREE - available} more pts to plant a tree`}
          </button>

          {justPlanted ? (
            <p className="mt-2 text-center text-sm font-medium text-[#0f5135]">
              🌱 Tree funded! You’ve planted {redeemed} so far.
            </p>
          ) : redeemed > 0 ? (
            <p className="mt-2 text-center font-mono text-[0.72rem] text-[#2f6b4f]">
              You’ve funded {redeemed} tree{redeemed === 1 ? "" : "s"} 🌳
            </p>
          ) : null}
        </>
      ) : (
        <p className="text-sm text-[#2f6b4f]">
          Submit a report with your name to start earning green points. Verified
          reports plant real trees.
        </p>
      )}

      <p className="mt-3 border-t border-[#cfe9db] pt-2.5 font-mono text-[0.7rem] text-[#2f6b4f]">
        Community has funded{" "}
        <strong className="text-[#0f5135]">{communityTrees} trees</strong> ·
        points redeem to a tree-planting NGO.
      </p>
    </Card>
  );
}

/* ── Leaderboard (bigger, with rank for me) ────────────────────────────── */

const MEDALS = ["🥇", "🥈", "🥉"];

function badgeTone(badge: string): "amber" | "cobalt" | "neutral" | "ok" {
  if (badge.includes("Gold")) return "amber";
  if (badge.includes("Silver")) return "neutral";
  if (badge.includes("Bronze")) return "ok";
  return "cobalt";
}

function maskHandle(h: string) {
  const p = h.split(/\s+/);
  return p.length < 2 ? h : `${p[0]} ${p[1][0]}.`;
}

function Leaderboard({ nonce, handle }: { nonce: number; handle: string }) {
  const { data, loading, error } = useApi(() => api.leaderboard(10), [nonce]);
  const rows = data ?? [];
  const myRank = rows.findIndex((e) => e.reporter === handle);

  return (
    <Card>
      <div className="mb-4 flex items-center gap-2">
        <span aria-hidden className="text-lg">
          🛡️
        </span>
        <div>
          <p className="eyebrow mb-0.5">Verified-only · this season</p>
          <h3 className="font-display text-lg font-bold text-ink">Street Guardians</h3>
        </div>
      </div>

      {loading ? (
        <Loading label="Loading leaderboard…" />
      ) : error ? (
        <ErrorNote error={error} />
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink-muted">No reporters yet — be the first.</p>
      ) : (
        <ol className="space-y-2">
          {rows.map((e: LeaderEntry, i) => {
            const mine = e.reporter === handle;
            return (
              <li
                key={e.reporter}
                className={`flex items-center gap-3 rounded-lg border px-3 py-2 ${
                  mine ? "border-cobalt bg-cobalt-soft" : "border-line bg-surface-2"
                }`}
              >
                <span className="w-6 shrink-0 text-center font-mono text-sm font-semibold text-ink-muted">
                  {MEDALS[i] ?? i + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-ink">
                    {mine ? `${e.reporter} (you)` : maskHandle(e.reporter)}
                  </span>
                  <span className="font-mono text-[0.7rem] text-ink-faint">
                    {e.verified} verified · {e.reports} reported
                  </span>
                </span>
                <Pill tone={badgeTone(e.badge)}>{e.badge}</Pill>
                <span className="w-12 shrink-0 text-right font-mono text-sm font-semibold tnum text-cobalt">
                  {fmt(e.points)}
                </span>
              </li>
            );
          })}
        </ol>
      )}

      {handle && myRank === -1 && rows.length > 0 ? (
        <p className="mt-3 rounded-lg border border-line bg-surface-2 px-3 py-2 text-center text-xs text-ink-muted">
          Submit a report and get it verified to join the board, {handle}.
        </p>
      ) : null}
    </Card>
  );
}
