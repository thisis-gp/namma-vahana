"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Section, Card, Loading, ErrorNote, Pill } from "../ui";
import type { Report } from "@/lib/types";

export default function OfficerReports({ index = "07" }: { index?: string }) {
  const [nonce, setNonce] = useState(0);
  const { data, loading, error } = useApi(() => api.reports("Pending"), [nonce]);
  const [acting, setActing] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [done, setDone] = useState<Set<number>>(new Set());

  const queue = (data ?? []).filter((r) => !done.has(r.id));

  const act = async (r: Report, action: "verify" | "reject") => {
    setActing(r.id);
    try {
      const res = await api.actOnReport(r.id, action, "ASI on duty");
      setDone((s) => new Set(s).add(r.id));
      setToast(
        action === "verify"
          ? res.challan_id
            ? `Verified — challan ${res.challan_id} issued, +50 pts to ${r.reporter}.`
            : `Verified — +50 pts to ${r.reporter} (no plate, no challan).`
          : `Report from ${r.reporter} rejected.`,
      );
      setNonce((n) => n + 1);
    } catch {
      setToast("Action failed — is the backend running?");
    } finally {
      setActing(null);
    }
  };

  return (
    <Section
      id="reports"
      index={index}
      eyebrow="Citizen reports"
      title={<>Review what the city reported.</>}
      lede="Residents are your eyes on the street. Verify a real report and it becomes an official challan, crediting the reporter. The public never issues fines — you stay the authority."
    >
      {toast ? (
        <p className="mb-4 rounded-lg border border-cobalt-soft bg-cobalt-soft px-4 py-2.5 text-sm text-cobalt-deep">
          {toast}
        </p>
      ) : null}

      {loading ? (
        <Loading label="Loading reports…" />
      ) : error ? (
        <ErrorNote error={error} />
      ) : queue.length === 0 ? (
        <Card>
          <p className="py-6 text-center text-sm text-ink-muted">
            Queue clear — no pending citizen reports. Nicely done.
          </p>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {queue.map((r) => (
            <Card key={r.id} className="!p-0 overflow-hidden">
              {r.image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={r.image}
                  alt={`Evidence for ${r.location}`}
                  className="h-36 w-full object-cover"
                />
              ) : (
                <div className="flex h-36 w-full items-center justify-center bg-surface-2 font-mono text-xs text-ink-faint">
                  no photo attached
                </div>
              )}
              <div className="p-4">
                <div className="mb-1.5 flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-ink">{r.location}</h3>
                  <Pill tone="amber">{r.category}</Pill>
                </div>
                <p className="mb-2 text-sm text-ink-muted">{r.note || "—"}</p>
                <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[0.7rem] text-ink-faint">
                  <span>
                    by <span className="text-ink">{r.reporter}</span>
                  </span>
                  {r.vehicle ? (
                    <span className="font-semibold text-ink">{r.vehicle}</span>
                  ) : (
                    <span>no plate</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => act(r, "verify")}
                    disabled={acting === r.id}
                    className="flex-1 rounded-md bg-cobalt px-3 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-cobalt-deep disabled:opacity-50"
                  >
                    {acting === r.id ? "…" : "Verify → challan"}
                  </button>
                  <button
                    onClick={() => act(r, "reject")}
                    disabled={acting === r.id}
                    className="rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:border-danger hover:text-danger disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </Section>
  );
}
