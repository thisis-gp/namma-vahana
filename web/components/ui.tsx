import type { ReactNode } from "react";

export function Section({
  id,
  index,
  eyebrow,
  title,
  lede,
  children,
  dark = false,
}: {
  id: string;
  index: string;
  eyebrow: string;
  title: ReactNode;
  lede?: ReactNode;
  children: ReactNode;
  dark?: boolean;
}) {
  return (
    <section
      id={id}
      className={
        dark
          ? "bg-asphalt text-white"
          : "border-t border-line bg-ground text-ink"
      }
    >
      <div className="mx-auto w-full max-w-6xl px-5 py-16 sm:px-8 sm:py-24">
        <header className="mb-9 max-w-3xl">
          <div className="mb-3 flex items-center gap-3">
            <span
              className={`section-index text-sm ${dark ? "!text-amber" : ""}`}
            >
              {index}
            </span>
            <span
              className="eyebrow"
              style={dark ? { color: "#9fb0c4" } : undefined}
            >
              {eyebrow}
            </span>
          </div>
          <h2 className="font-display text-3xl font-extrabold leading-tight tracking-tight sm:text-[2.6rem]">
            {title}
          </h2>
          {lede ? (
            <p
              className={`mt-4 text-lg leading-relaxed ${
                dark ? "text-[#aeb9c7]" : "text-ink-muted"
              }`}
            >
              {lede}
            </p>
          ) : null}
        </header>
        {children}
      </div>
    </section>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-line bg-surface p-5 shadow-[0_1px_0_rgba(20,24,31,0.03)] ${className}`}
    >
      {children}
    </div>
  );
}

export function Stat({
  value,
  label,
  sub,
  accent = false,
}: {
  value: ReactNode;
  label: string;
  sub?: ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col">
      <span
        className={`font-display text-3xl font-extrabold tnum leading-none sm:text-4xl ${
          accent ? "text-cobalt" : "text-ink"
        }`}
      >
        {value}
      </span>
      <span className="mt-2 text-sm font-medium text-ink">{label}</span>
      {sub ? <span className="mt-0.5 text-xs text-ink-muted">{sub}</span> : null}
    </div>
  );
}

export function Pill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "cobalt" | "amber" | "danger" | "ok";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-surface-2 text-ink-muted border-line",
    cobalt: "bg-cobalt-soft text-cobalt-deep border-cobalt-soft",
    amber: "bg-amber-soft text-[#8a5a00] border-amber-soft",
    danger: "bg-[#fbe4e3] text-[#a3201a] border-[#fbe4e3]",
    ok: "bg-[#e2f3ea] text-[#136b46] border-[#e2f3ea]",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[0.7rem] font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-ink-muted">
      <span
        className="h-3 w-3 animate-pulse rounded-full bg-cobalt"
        aria-hidden
      />
      <span className="font-mono text-sm">{label}</span>
    </div>
  );
}

export function ErrorNote({ error }: { error: string }) {
  return (
    <div className="rounded-lg border border-[#f1c7c4] bg-[#fbe4e3] px-4 py-3 text-sm text-[#a3201a]">
      <span className="font-medium">Couldn’t load this section.</span>{" "}
      <span className="font-mono text-xs">{error}</span>
      <p className="mt-1 text-xs text-[#a3201a]/80">
        Start the API with{" "}
        <code className="rounded bg-white/60 px-1">.\run.ps1 backend</code> and
        refresh.
      </p>
    </div>
  );
}
