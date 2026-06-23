export const PATROL_ORIGIN: [number, number] = [77.58, 12.968];
export const TRIP_MS = 14_000;

export type HeroPin = {
  lat: number;
  lon: number;
  h3: string;
  rank: number;
  label: string;
  violations: number;
  priority_pct: number;
};

export type HeroParking = {
  lat: number;
  lon: number;
  name: string;
};

export function isCoord(lon: unknown, lat: unknown): lon is number {
  return Number.isFinite(lon) && Number.isFinite(lat);
}

export function buildTrip(
  from: [number, number],
  to: [number, number],
  durationMs = TRIP_MS,
) {
  const steps = 32;
  const path: [number, number][] = [];
  const timestamps: number[] = [];
  for (let i = 0; i <= steps; i++) {
    const f = i / steps;
    const lon = from[0] + (to[0] - from[0]) * f;
    const lat = from[1] + (to[1] - from[1]) * f;
    const bend = Math.sin(f * Math.PI) * 0.012;
    path.push([lon + bend, lat - bend * 0.35]);
    timestamps.push((durationMs / steps) * i);
  }
  return { path, timestamps, duration: durationMs };
}

export type HeroTrip = ReturnType<typeof buildTrip>;

export function tripHead(trip: HeroTrip, timeMs: number): [number, number] {
  const t = timeMs % trip.duration;
  let i = 1;
  while (i < trip.timestamps.length && trip.timestamps[i] < t) i++;
  const t0 = trip.timestamps[i - 1] ?? 0;
  const t1 = trip.timestamps[i] ?? trip.duration;
  const f = t1 === t0 ? 0 : (t - t0) / (t1 - t0);
  const [lon0, lat0] = trip.path[i - 1] ?? trip.path[0];
  const [lon1, lat1] = trip.path[i] ?? trip.path[trip.path.length - 1];
  return [lon0 + (lon1 - lon0) * f, lat0 + (lat1 - lat0) * f];
}

function dist2(
  a: { lat: number; lon: number },
  b: { lat: number; lon: number },
) {
  const dlat = a.lat - b.lat;
  const dlon = a.lon - b.lon;
  return dlat * dlat + dlon * dlon;
}

export function nearestParking(
  spotlight: HeroPin,
  parking: HeroParking[],
  n = 2,
): HeroParking[] {
  return [...parking]
    .sort((a, b) => dist2(a, spotlight) - dist2(b, spotlight))
    .slice(0, n);
}
