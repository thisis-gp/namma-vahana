import type {
  Backtest,
  Challan,
  ChallanStatus,
  Citizen,
  Hotspot,
  Kpis,
  LeaderEntry,
  NbForecast,
  Officer,
  ParkingSpot,
  Patrol,
  Report,
  Station,
  StationSummary,
  Watch,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  (typeof window !== "undefined" || process.env.NODE_ENV === "production"
    ? ""
    : "http://127.0.0.1:8000");

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} — ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  kpis: () => get<Kpis>("/api/kpis"),
  hotspots: (station?: string, limit?: number) => {
    const q = new URLSearchParams();
    if (station) q.set("station", station);
    if (limit) q.set("limit", String(limit));
    const qs = q.toString();
    return get<Hotspot[]>(`/api/hotspots${qs ? `?${qs}` : ""}`);
  },
  stations: () => get<Station[]>("/api/stations"),
  citizen: (limit?: number) =>
    get<Citizen[]>(`/api/citizen${limit ? `?limit=${limit}` : ""}`),
  backtest: () => get<Backtest[]>("/api/backtest"),
  nbForecast: () => get<NbForecast[]>("/api/nb-forecast"),
  patrol: (station?: string, shift?: string) => {
    const q = new URLSearchParams();
    if (station) q.set("station", station);
    if (shift) q.set("shift", shift);
    const qs = q.toString();
    return get<Patrol[]>(`/api/patrol${qs ? `?${qs}` : ""}`);
  },
  watchlist: (limit = 60, station?: string) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (station) q.set("station", station);
    return get<Watch[]>(`/api/watchlist?${q.toString()}`);
  },
  challans: () => get<Challan[]>("/api/challans"),
  createChallan: async (body: {
    vehicle: string;
    location: string;
    category?: string;
    amount?: number;
    station?: string;
    status?: ChallanStatus;
  }): Promise<Challan> => {
    const res = await fetch(`${API_BASE}/api/challans`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Could not issue challan (${res.status})`);
    return res.json() as Promise<Challan>;
  },

  reports: (status?: string, reporter?: string) => {
    const q = new URLSearchParams();
    if (status) q.set("status", status);
    if (reporter) q.set("reporter", reporter);
    const qs = q.toString();
    return get<Report[]>(`/api/reports${qs ? `?${qs}` : ""}`);
  },
  createReport: async (body: {
    reporter: string;
    vehicle?: string;
    category?: string;
    location: string;
    note?: string;
    image?: string;
  }): Promise<Report> => {
    const res = await fetch(`${API_BASE}/api/reports`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Could not submit report (${res.status})`);
    return res.json() as Promise<Report>;
  },
  actOnReport: async (
    id: number,
    action: "verify" | "reject",
    officer = "Officer on duty",
  ): Promise<Report> => {
    const res = await fetch(`${API_BASE}/api/reports/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, officer }),
    });
    if (!res.ok) throw new Error(`Could not update report (${res.status})`);
    return res.json() as Promise<Report>;
  },
  leaderboard: (limit = 10) =>
    get<LeaderEntry[]>(`/api/leaderboard?limit=${limit}`),

  parking: (opts?: {
    area?: string;
    nearLat?: number;
    nearLon?: number;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (opts?.area) q.set("area", opts.area);
    if (opts?.nearLat != null) q.set("near_lat", String(opts.nearLat));
    if (opts?.nearLon != null) q.set("near_lon", String(opts.nearLon));
    if (opts?.limit) q.set("limit", String(opts.limit));
    const qs = q.toString();
    return get<ParkingSpot[]>(`/api/parking${qs ? `?${qs}` : ""}`);
  },
  createParking: async (body: {
    name: string;
    area: string;
    lat?: number;
    lon?: number;
    kind?: string;
    price?: string;
    note?: string;
    added_by?: string;
    image?: string;
  }): Promise<ParkingSpot> => {
    const res = await fetch(`${API_BASE}/api/parking`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Could not add spot (${res.status})`);
    return res.json() as Promise<ParkingSpot>;
  },
  voteParking: async (id: number, kind: "up" | "flag"): Promise<ParkingSpot> => {
    const res = await fetch(`${API_BASE}/api/parking/${id}/vote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind }),
    });
    if (!res.ok) throw new Error(`Vote failed (${res.status})`);
    return res.json() as Promise<ParkingSpot>;
  },

  officers: (station?: string) =>
    get<Officer[]>(`/api/officers${station ? `?station=${encodeURIComponent(station)}` : ""}`),
  assignOfficer: async (
    id: number,
    patch: { beat_h3?: string; area?: string; patrol_window?: string; shift?: string; status?: string },
  ): Promise<Officer> => {
    const res = await fetch(`${API_BASE}/api/officers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!res.ok) throw new Error(`Assignment failed (${res.status})`);
    return res.json() as Promise<Officer>;
  },
  stationSummary: (station: string) =>
    get<StationSummary>(`/api/station-summary?station=${encodeURIComponent(station)}`),
};
