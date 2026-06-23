"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import Logo from "@/components/brand/Logo";

const RESIDENT_LINKS = [
  { id: "parking", label: "Find parking" },
  { id: "community", label: "Report & rewards" },
];

const OFFICER_LINKS = [
  { id: "command", label: "Command" },
  { id: "where", label: "Hotspots" },
  { id: "plan", label: "Patrol" },
  { id: "proof", label: "Impact" },
  { id: "offenders", label: "Watchlist" },
  { id: "reports", label: "Reports" },
];

export default function Nav() {
  const pathname = usePathname() ?? "/";
  const isOfficer = pathname.startsWith("/officer");
  const isResident = pathname.startsWith("/resident");
  const onLanding = !isOfficer && !isResident;

  const [active, setActive] = useState("");
  const [scrolled, setScrolled] = useState(false);
  const links = isOfficer ? OFFICER_LINKS : isResident ? RESIDENT_LINKS : [];

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!links.length) return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActive(e.target.id);
      },
      { rootMargin: "-45% 0px -50% 0px" },
    );
    for (const l of links) {
      const el = document.getElementById(l.id);
      if (el) obs.observe(el);
    }
    return () => obs.disconnect();
  }, [links]);

  return (
    <header
      className={`sticky top-0 z-50 border-b transition-colors ${
        scrolled
          ? "border-line bg-ground/85 backdrop-blur-md"
          : "border-transparent bg-transparent"
      }`}
    >
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-5 py-3 sm:px-8">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <Logo size="md" />
          {isOfficer ? (
            <span className="ml-1 rounded bg-asphalt px-1.5 py-0.5 font-mono text-[0.6rem] font-semibold uppercase tracking-wider text-white">
              Officer
            </span>
          ) : null}
        </Link>

        <nav className="hidden flex-1 items-center justify-center gap-1 lg:flex">
          {links.map((l) => (
            <a
              key={l.id}
              href={`#${l.id}`}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                active === l.id
                  ? "bg-cobalt-soft text-cobalt-deep"
                  : "text-ink-muted hover:text-ink"
              }`}
            >
              {l.label}
            </a>
          ))}
        </nav>

        {/* Context switch */}
        <div className="flex shrink-0 items-center gap-2">
          {onLanding ? (
            <>
              <Link
                href="/officer"
                className="hidden rounded-lg px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:text-ink sm:block"
              >
                Officer console
              </Link>
              <Link
                href="/resident"
                className="rounded-lg bg-cobalt px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-cobalt-deep"
              >
                Find parking
              </Link>
            </>
          ) : isOfficer ? (
            <Link
              href="/resident"
              className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:border-cobalt hover:text-cobalt"
            >
              ↩ Resident view
            </Link>
          ) : (
            <Link
              href="/officer"
              className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:border-cobalt hover:text-cobalt"
            >
              Officer console →
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
