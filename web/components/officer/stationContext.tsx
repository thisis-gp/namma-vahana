"use client";

import { createContext, useContext, useState } from "react";

interface StationCtx {
  station: string; // "" = all stations
  setStation: (s: string) => void;
}

const Ctx = createContext<StationCtx | null>(null);

export function StationProvider({ children }: { children: React.ReactNode }) {
  const [station, setStation] = useState("");
  return <Ctx.Provider value={{ station, setStation }}>{children}</Ctx.Provider>;
}

export function useStation(): StationCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useStation must be used within StationProvider");
  return ctx;
}
