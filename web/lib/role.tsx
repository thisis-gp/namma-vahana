"use client";

import { usePathname } from "next/navigation";

export type Role = "resident" | "officer";

// The route IS the role now — /officer is the officer experience, everything
// else is resident-facing. This gives distinct entry points (industry standard
// for multi-persona products) instead of one crammed page.
export function useRole(): { role: Role; isOfficer: boolean } {
  const pathname = usePathname();
  const isOfficer = pathname?.startsWith("/officer") ?? false;
  return { role: isOfficer ? "officer" : "resident", isOfficer };
}
