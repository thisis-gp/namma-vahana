"use client";

import { useMemo } from "react";
import DeckGL from "@deck.gl/react";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { Map } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Hotspot } from "@/lib/types";
import { heatColor } from "./heat";

const DARK_STYLE =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

// Bengaluru.
const INITIAL_VIEW_STATE = {
  longitude: 77.5946,
  latitude: 12.9716,
  zoom: 10.6,
  pitch: 48,
  bearing: -14,
};

export default function MapCanvas({
  hotspots,
  selectedH3,
  onSelect,
}: {
  hotspots: Hotspot[];
  selectedH3: string | null;
  onSelect: (h: Hotspot | null) => void;
}) {
  // Height + colour both encode enforcement PRIORITY (the CIS impact rank),
  // so the tallest, reddest hex is rank #1 — consistent with the ranked list.
  const maxPriority = useMemo(
    () => Math.max(1, ...hotspots.map((h) => h.priority_pct)),
    [hotspots],
  );

  const layer = useMemo(
    () =>
      new H3HexagonLayer<Hotspot>({
        id: "hotspots",
        data: hotspots,
        pickable: true,
        extruded: true,
        elevationScale: 1,
        coverage: 0.92,
        getHexagon: (d) => d.h3,
        getFillColor: (d) => {
          const t = d.priority_pct / maxPriority;
          return heatColor(t, d.h3 === selectedH3 ? 255 : 205);
        },
        getElevation: (d) => (d.priority_pct / maxPriority) * 2600,
        material: {
          ambient: 0.5,
          diffuse: 0.6,
          shininess: 24,
          specularColor: [40, 50, 70],
        },
        autoHighlight: true,
        highlightColor: [255, 255, 255, 90],
        updateTriggers: {
          getFillColor: [selectedH3, maxPriority],
          getElevation: [maxPriority],
        },
      }),
    [hotspots, maxPriority, selectedH3],
  );

  return (
    <DeckGL
      initialViewState={INITIAL_VIEW_STATE}
      controller={{ dragRotate: true }}
      layers={[layer]}
      onClick={(info) => onSelect((info.object as Hotspot) ?? null)}
      getTooltip={({ object }) => {
        const o = object as Hotspot | null;
        if (!o) return null;
        return {
          html: `<div style="font-family:var(--font-mono);font-size:11px">
            <strong>${escapeHtml(o.display_location)}</strong><br/>
            ${o.violation_count.toLocaleString("en-IN")} violations · rank #${o.rank}
          </div>`,
          style: {
            background: "#0f1622",
            color: "#fff",
            border: "1px solid #2a3647",
            borderRadius: "8px",
            padding: "8px 10px",
            boxShadow: "0 6px 24px rgba(0,0,0,0.4)",
          },
        };
      }}
      style={{ position: "absolute", inset: "0" }}
    >
      <Map reuseMaps mapStyle={DARK_STYLE} attributionControl={{ compact: true }} />
    </DeckGL>
  );
}

function escapeHtml(s: string) {
  return s.replace(
    /[&<>"]/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] ?? c,
  );
}
