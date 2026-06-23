// Enforcement-heat ramp: amber (low) → deep red (high). Warm, on-theme.
const LOW: [number, number, number] = [244, 161, 0]; // --amber
const MID: [number, number, number] = [233, 99, 23];
const HIGH: [number, number, number] = [196, 43, 34]; // --heat-high

function lerp(a: number, b: number, t: number) {
  return Math.round(a + (b - a) * t);
}

export function heatColor(t: number, alpha = 215): [number, number, number, number] {
  const x = Math.max(0, Math.min(1, t));
  const [from, to, k] = x < 0.5 ? [LOW, MID, x / 0.5] : [MID, HIGH, (x - 0.5) / 0.5];
  return [
    lerp(from[0], to[0], k),
    lerp(from[1], to[1], k),
    lerp(from[2], to[2], k),
    alpha,
  ];
}

export const heatCss = (t: number) => {
  const [r, g, b] = heatColor(t, 255);
  return `rgb(${r}, ${g}, ${b})`;
};
