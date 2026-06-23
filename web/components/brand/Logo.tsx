import { BRAND } from "@/lib/brand";

const SIZES = { sm: 28, md: 32, lg: 40 } as const;

type LogoProps = {
  size?: keyof typeof SIZES;
  showWordmark?: boolean;
  /** Light wordmark for dark backgrounds (footer, map overlay) */
  variant?: "default" | "light";
  className?: string;
};

/** Street-signage mark: cobalt badge, amber band, pin + road lines. */
export function LogoMark({
  size = 32,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <rect width="32" height="32" rx="7" fill="#1e45c8" />
      <path
        d="M0 7c0-3.866 3.134-7 7-7h18c3.866 0 7 3.134 7 7v3H0V7z"
        fill="#f4a100"
      />
      <path
        d="M16 9.5c-2.35 0-4.25 1.75-4.25 3.9 0 3 4.25 7.85 4.25 7.85s4.25-4.85 4.25-7.85c0-2.15-1.9-3.9-4.25-3.9z"
        fill="white"
      />
      <circle cx="16" cy="13.2" r="1.5" fill="#1e45c8" />
      <path
        d="M8.5 23.5h15"
        stroke="white"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity="0.92"
      />
      <path
        d="M10.5 26.5h11"
        stroke="white"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.55"
      />
    </svg>
  );
}

export default function Logo({
  size = "md",
  showWordmark = true,
  variant = "default",
  className = "",
}: LogoProps) {
  const px = SIZES[size];
  const light = variant === "light";

  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark size={px} className="shrink-0 drop-shadow-sm" />
      {showWordmark ? (
        <span className="font-display text-lg font-extrabold leading-none tracking-tight">
          <span
            className={
              light ? "font-semibold text-[#9fb0c4]" : "font-semibold text-ink-muted"
            }
          >
            Namma
          </span>{" "}
          <span className={light ? "text-white" : "text-ink"}>Vahana</span>
        </span>
      ) : (
        <span className="sr-only">{BRAND.name}</span>
      )}
    </span>
  );
}
