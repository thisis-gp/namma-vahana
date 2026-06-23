"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Section, Card, Loading, ErrorNote, Pill } from "./ui";
import { parkingRisk } from "@/lib/risk";
import { fileToCompressedDataUrl } from "@/lib/image";
import type { Citizen, ParkingSpot } from "@/lib/types";
import { readStorage, writeStorage, STORAGE_KEYS } from "@/lib/brand";

const KINDS = ["Roadside", "Open ground", "Building", "Pay-and-park"];
const PRICES = ["Free", "Paid"];

interface Dest {
  label: string;
  lat: number;
  lon: number;
  risk_band: string;
  fine_risk: number;
}

export default function FindParking({ index = "01" }: { index?: string }) {
  const places = useApi(() => api.citizen(800), []);
  const [q, setQ] = useState("");
  const [dest, setDest] = useState<Dest | null>(null);
  const [openSug, setOpenSug] = useState(false);
  const [nonce, setNonce] = useState(0);

  // Destination suggestions from the dataset (no external geocoder).
  const suggestions = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (needle.length < 2 || dest) return [];
    const seen = new Set<string>();
    const out: Citizen[] = [];
    for (const c of places.data ?? []) {
      const label = c.display_location || c.junction_name;
      if (!label || seen.has(label)) continue;
      if (
        label.toLowerCase().includes(needle) ||
        c.dominant_station.toLowerCase().includes(needle)
      ) {
        seen.add(label);
        out.push(c);
      }
      if (out.length >= 6) break;
    }
    return out;
  }, [q, places.data, dest]);

  const spots = useApi(
    () =>
      api.parking({
        nearLat: dest?.lat,
        nearLon: dest?.lon,
        limit: dest ? 8 : 6,
      }),
    [dest?.lat, dest?.lon, nonce],
  );
  const list = spots.data ?? [];
  const risk = dest ? parkingRisk(dest.risk_band) : null;

  return (
    <Section
      id="parking"
      index={index}
      eyebrow="Park smart"
      title={<>Where are you headed?</>}
      lede="Tell us your destination. We’ll warn you how closely the area is watched for parking violations, then show the spots the community has mapped nearby — so you can park without risking a fine."
    >
      {/* Destination search */}
      <div className="relative mb-6 max-w-2xl">
        <div className="flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-3.5 shadow-sm focus-within:border-cobalt">
          <span aria-hidden className="text-cobalt">
            ⌖
          </span>
          <input
            value={dest ? dest.label : q}
            onChange={(e) => {
              setQ(e.target.value);
              setDest(null);
              setOpenSug(true);
            }}
            onFocus={() => setOpenSug(true)}
            placeholder="e.g. Indiranagar, MG Road, Koramangala…"
            className="w-full bg-transparent text-base text-ink placeholder:text-ink-faint focus:outline-none"
            autoComplete="off"
            aria-label="Where are you headed?"
          />
          {dest ? (
            <button
              onClick={() => {
                setDest(null);
                setQ("");
              }}
              className="rounded px-2 text-sm text-ink-faint hover:text-ink"
              aria-label="Clear"
            >
              ✕
            </button>
          ) : null}
        </div>

        {openSug && suggestions.length > 0 ? (
          <ul className="absolute z-20 mt-2 w-full overflow-hidden rounded-xl border border-line bg-surface shadow-xl">
            {suggestions.map((c) => {
              const t = parkingRisk(c.risk_band);
              return (
                <li key={c.h3}>
                  <button
                    onClick={() => {
                      setDest({
                        label: c.display_location || c.junction_name,
                        lat: c.lat,
                        lon: c.lon,
                        risk_band: c.risk_band,
                        fine_risk: c.fine_risk,
                      });
                      setOpenSug(false);
                    }}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-left hover:bg-surface-2"
                  >
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ background: t.dot }}
                    />
                    <span className="min-w-0 flex-1 truncate text-sm text-ink">
                      {c.display_location || c.junction_name}
                    </span>
                    <span className={`shrink-0 text-xs font-medium ${t.text}`}>
                      {c.risk_band}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>

      {/* Area-risk warning (reworded per request) */}
      {dest && risk ? (
        <div
          className={`mb-6 flex items-start gap-3 rounded-xl border px-4 py-3.5 ${risk.bg} ${
            risk.safe ? "border-[#cfe9db]" : "border-[#f1c7c4]"
          }`}
        >
          <span aria-hidden className="text-xl leading-none">
            {risk.safe ? "✅" : "⚠️"}
          </span>
          <div>
            <p className={`text-sm font-semibold ${risk.text}`}>
              {risk.safe
                ? `${dest.label} sees relatively few parking violations — lower fine-risk here.`
                : `${dest.label} is heavily recorded for parking violations — be aware: parking carelessly here has a high chance of a fine.`}
            </p>
            <p className="mt-0.5 text-sm text-ink-muted">
              Below are community-mapped parking spots near here. Found them
              useful, or out of date? Like or flag them to help the next driver.
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        <div>
          <p className="eyebrow mb-3">
            {dest ? `Parking near ${dest.label}` : "Top community spots"}
          </p>
          {spots.loading ? (
            <Loading label="Finding parking…" />
          ) : spots.error ? (
            <ErrorNote error={spots.error} />
          ) : list.length === 0 ? (
            <Card>
              <p className="text-sm text-ink-muted">
                No spots mapped here yet. Know one? Add it on the right and help
                the next driver.
              </p>
            </Card>
          ) : (
            <ul className="space-y-3">
              {list.map((s) => (
                <SpotCard key={s.id} spot={s} onVoted={() => setNonce((n) => n + 1)} />
              ))}
            </ul>
          )}
        </div>

        <AddSpot dest={dest} onAdded={() => setNonce((n) => n + 1)} />
      </div>
    </Section>
  );
}

function SpotCard({ spot: s, onVoted }: { spot: ParkingSpot; onVoted: () => void }) {
  const risk = parkingRisk(s.risk_band);
  const [busy, setBusy] = useState(false);

  const vote = async (kind: "up" | "flag") => {
    setBusy(true);
    try {
      await api.voteParking(s.id, kind);
      onVoted();
    } catch {
      /* non-critical */
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="overflow-hidden rounded-xl border border-line bg-surface">
      <div className="flex gap-4 p-4">
        {s.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={s.image}
            alt={s.name}
            className="h-20 w-24 shrink-0 rounded-lg object-cover"
          />
        ) : null}
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate text-base font-semibold text-ink">{s.name}</h3>
              <p className="font-mono text-[0.72rem] text-ink-faint">
                {s.area}
                {s.distance_km != null ? ` · ${s.distance_km} km away` : ""}
              </p>
            </div>
            <span
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${risk.bg} ${risk.text}`}
            >
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: risk.dot }} />
              {risk.safe ? "Safer" : "Caution"}
            </span>
          </div>

          <div className="mb-2 flex flex-wrap items-center gap-1.5">
            <Pill tone="neutral">{s.kind}</Pill>
            <Pill tone={s.price === "Free" ? "ok" : "cobalt"}>{s.price}</Pill>
            <span className="font-mono text-[0.7rem] text-ink-faint">· {risk.label}</span>
          </div>

          {s.note ? (
            <p className="mb-2 text-sm leading-relaxed text-ink-muted">{s.note}</p>
          ) : null}

          <div className="flex items-center justify-between border-t border-line pt-2.5">
            <span className="font-mono text-[0.7rem] text-ink-faint">
              added by {s.added_by}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => vote("up")}
                disabled={busy}
                className="flex items-center gap-1 rounded-md border border-line px-2 py-1 text-xs font-medium text-ink-muted transition-colors hover:border-ok hover:text-ok disabled:opacity-50"
              >
                👍 {s.upvotes}
              </button>
              <button
                onClick={() => vote("flag")}
                disabled={busy}
                className="flex items-center gap-1 rounded-md border border-line px-2 py-1 text-xs font-medium text-ink-muted transition-colors hover:border-danger hover:text-danger disabled:opacity-50"
                title="Spot gone, full, or wrong"
              >
                🚩 {s.flags}
              </button>
            </div>
          </div>
        </div>
      </div>
    </li>
  );
}

function AddSpot({ dest, onAdded }: { dest: Dest | null; onAdded: () => void }) {
  const [name, setName] = useState("");
  const [area, setArea] = useState("");
  const [kind, setKind] = useState(KINDS[0]);
  const [price, setPrice] = useState(PRICES[0]);
  const [note, setNote] = useState("");
  const [who, setWho] = useState("");
  const [image, setImage] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [imgErr, setImgErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (dest) setArea(dest.label);
  }, [dest]);
  useEffect(() => {
    const saved = readStorage(STORAGE_KEYS.handle);
    if (saved) setWho(saved);
  }, []);

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    setImgErr(null);
    try {
      setImage(await fileToCompressedDataUrl(f));
    } catch (e) {
      setImgErr(e instanceof Error ? e.message : "Image failed");
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !area.trim()) return;
    setBusy(true);
    setDone(false);
    try {
      if (who.trim()) writeStorage(STORAGE_KEYS.handle, who.trim());
      await api.createParking({
        name: name.trim(),
        area: area.trim(),
        lat: dest?.lat,
        lon: dest?.lon,
        kind,
        price,
        note: note.trim(),
        added_by: who.trim() || "Anonymous",
        image,
      });
      setDone(true);
      setName("");
      setNote("");
      setImage("");
      if (fileRef.current) fileRef.current.value = "";
      onAdded();
    } catch {
      /* keep simple */
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <p className="eyebrow mb-1">Help the next driver</p>
      <h3 className="font-display mb-3 text-lg font-bold text-ink">Add a parking spot</h3>
      <form onSubmit={submit} className="space-y-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Spot name e.g. BDA ground"
          className="field"
        />
        <input
          value={area}
          onChange={(e) => setArea(e.target.value)}
          placeholder="Area / locality"
          className="field"
        />
        <div className="grid grid-cols-2 gap-3">
          <select value={kind} onChange={(e) => setKind(e.target.value)} className="field">
            {KINDS.map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
          <select value={price} onChange={(e) => setPrice(e.target.value)} className="field">
            {PRICES.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Tip (optional) — e.g. free after 7pm"
          className="field"
        />
        <input
          value={who}
          onChange={(e) => setWho(e.target.value)}
          placeholder="Your name (optional)"
          className="field"
        />

        {/* Photo */}
        <div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            onChange={(e) => onFile(e.target.files?.[0])}
            className="hidden"
            id="spot-photo"
          />
          {image ? (
            <div className="flex items-center gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={image} alt="preview" className="h-14 w-20 rounded-md object-cover" />
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
              htmlFor="spot-photo"
              className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-line bg-surface-2 px-3 py-2.5 text-sm text-ink-muted hover:border-cobalt hover:text-cobalt"
            >
              📷 Add a photo (optional)
            </label>
          )}
          {imgErr ? <p className="mt-1 text-xs text-danger">{imgErr}</p> : null}
        </div>

        <button
          type="submit"
          disabled={busy || !name.trim() || !area.trim()}
          className="w-full rounded-lg bg-cobalt px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-cobalt-deep disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Adding…" : "Add spot"}
        </button>
      </form>
      {done ? (
        <p className="mt-3 rounded-lg border border-[#cfe9db] bg-[#e2f3ea] px-3 py-2 text-sm text-[#136b46]">
          Added — and we’ve auto-graded its fine-risk from the data. Thanks for
          helping out.
        </p>
      ) : null}
      <p className="mt-4 font-mono text-[0.7rem] leading-relaxed text-ink-faint">
        Spots are community-contributed and auto-checked against the violations
        dataset — if one sits in a hotspot, drivers see a caution.
      </p>
    </Card>
  );
}
