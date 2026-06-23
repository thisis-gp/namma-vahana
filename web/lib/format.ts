export const nf = new Intl.NumberFormat("en-IN");

export const fmt = (n: number) => nf.format(Math.round(n));

export const pct = (frac: number, digits = 0) =>
  `${(frac * 100).toFixed(digits)}%`;

export const compact = (n: number) => {
  if (n >= 1_00_000) return `${(n / 1_00_000).toFixed(n >= 10_00_000 ? 0 : 1)}L`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return String(n);
};

export const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);

// Mask a licence plate for public display: keep the state + last 2 chars,
// dot out the middle. "KA05MN3344" → "KA05••••44". Officers see it whole.
export function maskPlate(plate: string, reveal: boolean): string {
  if (reveal || !plate) return plate;
  const p = plate.replace(/\s+/g, "");
  if (p.length <= 4) return p;
  const head = p.slice(0, 4);
  const tail = p.slice(-2);
  return `${head}${"•".repeat(Math.max(2, p.length - 6))}${tail}`;
}

// Bucket a free-text peak-hours string into a part of day, defensively.
export type Daypart = "Morning" | "Midday" | "Evening" | "Night";
export function daypartOf(peak: string): Daypart | null {
  const m = peak.match(/(\d{1,2})/);
  if (!m) return null;
  const h = Number(m[1]);
  if (Number.isNaN(h)) return null;
  if (h >= 5 && h < 12) return "Morning";
  if (h >= 12 && h < 17) return "Midday";
  if (h >= 17 && h < 21) return "Evening";
  return "Night";
}
