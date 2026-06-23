// Shared mapping from a risk band string to parking-friendly meaning + colour.
export interface RiskTone {
  label: string;
  text: string;
  bg: string;
  dot: string;
  safe: boolean;
}

export function parkingRisk(band: string): RiskTone {
  const b = (band || "").toLowerCase();
  if (b.includes("very high") || b.includes("high"))
    return {
      label: "High fine-risk — caution",
      text: "text-[#a3201a]",
      bg: "bg-[#fbe4e3]",
      dot: "#c42b22",
      safe: false,
    };
  if (b.includes("mod") || b.includes("med"))
    return {
      label: "Moderate fine-risk",
      text: "text-[#8a5a00]",
      bg: "bg-amber-soft",
      dot: "#f4a100",
      safe: false,
    };
  if (b.includes("low"))
    return {
      label: "Low fine-risk — safer",
      text: "text-[#136b46]",
      bg: "bg-[#e2f3ea]",
      dot: "#1f8a5b",
      safe: true,
    };
  return {
    label: "Risk unknown",
    text: "text-ink-muted",
    bg: "bg-surface-2",
    dot: "#8a93a0",
    safe: false,
  };
}
