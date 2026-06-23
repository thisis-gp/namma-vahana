"use client";

import { useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import { H3HexagonLayer, TripsLayer } from "@deck.gl/geo-layers";
import { ArcLayer, ColumnLayer, ScatterplotLayer } from "@deck.gl/layers";
import { FlyToInterpolator } from "@deck.gl/core";
import type { MapViewState } from "@deck.gl/core";
import { Map } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { heatColor } from "@/components/map/heat";
import {
  PATROL_ORIGIN,
  TRIP_MS,
  buildTrip,
  tripHead,
  type HeroParking,
  type HeroPin,
} from "./heroMapUtils";

const MAP_STYLE =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

const BASE_VIEW: MapViewState = {
  longitude: 77.5946,
  latitude: 12.9716,
  zoom: 10.9,
  pitch: 38,
  bearing: -12,
  minZoom: 9,
  maxZoom: 14,
};

function radarAlpha(pulse: number, phase: number) {
  const wave = (pulse + phase) % 1;
  return Math.round(90 * (1 - wave));
}

export default function HeroMapDeck({
  hotspots,
  parking,
  spotlight,
  maxPriority,
  reduceMotion,
}: {
  hotspots: HeroPin[];
  parking: HeroParking[];
  spotlight: HeroPin;
  maxPriority: number;
  reduceMotion: boolean | null;
}) {
  const [viewState, setViewState] = useState<MapViewState>({
    ...BASE_VIEW,
    longitude: spotlight.lon,
    latitude: spotlight.lat,
    zoom: 11.05,
  });
  const [time, setTime] = useState(0);
  const [pulse, setPulse] = useState(0);

  const trip = useMemo(
    () => buildTrip(PATROL_ORIGIN, [spotlight.lon, spotlight.lat]),
    [spotlight.lon, spotlight.lat],
  );

  const patrolPos = useMemo(
    () => tripHead(trip, reduceMotion ? 0 : time),
    [trip, time, reduceMotion],
  );

  useEffect(() => {
    setViewState((vs) => ({
      ...vs,
      longitude: spotlight.lon,
      latitude: spotlight.lat,
      zoom: 11.05,
      pitch: 42,
      bearing: -8 + spotlight.rank * 3,
      transitionDuration: reduceMotion ? 0 : 2400,
      transitionInterpolator: new FlyToInterpolator(),
    }));
  }, [spotlight.lon, spotlight.lat, spotlight.rank, reduceMotion]);

  useEffect(() => {
    if (reduceMotion) return;
    let frame = 0;
    const start = performance.now();
    const tick = () => {
      const elapsed = performance.now() - start;
      setTime(elapsed % TRIP_MS);
      setPulse((elapsed / 1000) % 1);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [spotlight.rank, reduceMotion]);

  const layers = useMemo(() => {
    const heatPulse = 1.2 + Math.sin(pulse * Math.PI * 2) * 0.25;

    const heat = new HeatmapLayer<HeroPin>({
      id: "hero-heat",
      data: hotspots,
      getPosition: (d) => [d.lon, d.lat],
      getWeight: (d) => Math.sqrt(d.violations),
      radiusPixels: 58,
      intensity: heatPulse,
      threshold: 0.03,
      colorRange: [
        [0, 0, 0, 0],
        [65, 182, 196, 90],
        [253, 174, 97, 160],
        [215, 48, 39, 220],
        [165, 0, 38, 255],
      ],
    });

    const arcGlow = new ArcLayer({
      id: "hero-arc-glow",
      data: [{ source: PATROL_ORIGIN, target: [spotlight.lon, spotlight.lat] }],
      getSourcePosition: (d) => d.source,
      getTargetPosition: (d) => d.target,
      getSourceColor: [30, 69, 200, 40],
      getTargetColor: [234, 67, 53, 120],
      getWidth: 8,
      greatCircle: true,
    });

    const arc = new ArcLayer({
      id: "hero-arc",
      data: [{ source: PATROL_ORIGIN, target: [spotlight.lon, spotlight.lat] }],
      getSourcePosition: (d) => d.source,
      getTargetPosition: (d) => d.target,
      getSourceColor: [96, 165, 250, 120],
      getTargetColor: [234, 67, 53, 240],
      getWidth: 2.5,
      greatCircle: true,
    });

    const patrol = new TripsLayer({
      id: "hero-patrol",
      data: [trip],
      getPath: (d) => d.path,
      getTimestamps: (d) => d.timestamps,
      getColor: [96, 165, 250, 240],
      getWidth: 6,
      widthMinPixels: 4,
      trailLength: 320,
      currentTime: time,
      fadeTrail: true,
      capRounded: true,
      jointRounded: true,
    });

    const dots = new ScatterplotLayer<HeroPin>({
      id: "hero-dots",
      data: hotspots.filter((h) => h.rank !== spotlight.rank),
      getPosition: (d) => [d.lon, d.lat],
      getRadius: (d) => (d.rank <= 5 ? 300 : 200),
      getFillColor: (d) => {
        const t = d.priority_pct / maxPriority;
        return heatColor(t, 210);
      },
      getLineColor: [255, 255, 255, 180],
      lineWidthMinPixels: 1.5,
      stroked: true,
      radiusUnits: "meters",
      pickable: false,
    });

    const hex = new H3HexagonLayer<HeroPin>({
      id: "hero-hex",
      data: [spotlight],
      getHexagon: (d) => d.h3,
      extruded: true,
      elevationScale: 1,
      coverage: 0.94,
      getFillColor: [234, 67, 53, 175],
      getElevation: 1800 + Math.sin(pulse * Math.PI * 2) * 220,
      material: {
        ambient: 0.45,
        diffuse: 0.65,
        shininess: 32,
        specularColor: [255, 120, 100],
      },
      pickable: false,
    });

    const pillar = new ColumnLayer<HeroPin>({
      id: "hero-pillar",
      data: [spotlight],
      getPosition: (d) => [d.lon, d.lat],
      getFillColor: [234, 67, 53, 220],
      getElevation: 2400 + Math.sin(pulse * Math.PI * 2) * 200,
      radius: 180,
      elevationScale: 1,
      extruded: true,
      pickable: false,
    });

    const rings = [0, 0.33, 0.66].map(
      (phase, i) =>
        new ScatterplotLayer({
          id: `hero-ring-${i}`,
          data: [spotlight],
          getPosition: (d: HeroPin) => [d.lon, d.lat],
          getRadius: 350 + ((pulse + phase) % 1) * 900,
          getFillColor: [234, 67, 53, radarAlpha(pulse, phase)],
          stroked: false,
          radiusUnits: "meters",
          pickable: false,
        }),
    );

    const core = new ScatterplotLayer<HeroPin>({
      id: "hero-core",
      data: [spotlight],
      getPosition: (d) => [d.lon, d.lat],
      getRadius: 380 + Math.sin(pulse * Math.PI * 2) * 50,
      getFillColor: [255, 255, 255, 235],
      getLineColor: [234, 67, 53, 255],
      lineWidthMinPixels: 3,
      stroked: true,
      radiusUnits: "meters",
    });

    const depot = new ScatterplotLayer({
      id: "hero-depot",
      data: [{ pos: PATROL_ORIGIN }],
      getPosition: (d) => d.pos,
      getRadius: 280,
      getFillColor: [30, 69, 200, 200],
      getLineColor: [255, 255, 255, 220],
      lineWidthMinPixels: 2,
      stroked: true,
      radiusUnits: "meters",
    });

    const vehicle = new ScatterplotLayer({
      id: "hero-vehicle",
      data: [{ pos: patrolPos }],
      getPosition: (d) => d.pos,
      getRadius: 120,
      getFillColor: [255, 255, 255, 255],
      getLineColor: [30, 69, 200, 255],
      lineWidthMinPixels: 3,
      stroked: true,
      radiusUnits: "meters",
    });

    const vehicleGlow = new ScatterplotLayer({
      id: "hero-vehicle-glow",
      data: [{ pos: patrolPos }],
      getPosition: (d) => d.pos,
      getRadius: 260 + Math.sin(pulse * Math.PI * 4) * 40,
      getFillColor: [96, 165, 250, 90],
      stroked: false,
      radiusUnits: "meters",
    });

    const park = new ScatterplotLayer<HeroParking>({
      id: "hero-park",
      data: parking,
      getPosition: (d) => [d.lon, d.lat],
      getRadius: 240,
      getFillColor: [31, 138, 91, 230],
      getLineColor: [255, 255, 255, 220],
      lineWidthMinPixels: 2,
      stroked: true,
      radiusUnits: "meters",
    });

    return [
      heat,
      arcGlow,
      arc,
      patrol,
      dots,
      hex,
      pillar,
      ...rings,
      core,
      depot,
      vehicleGlow,
      vehicle,
      park,
    ];
  }, [
    hotspots,
    spotlight,
    trip,
    time,
    pulse,
    maxPriority,
    parking,
    patrolPos,
  ]);

  return (
    <DeckGL
      viewState={viewState}
      onViewStateChange={({ viewState: vs }) => setViewState(vs as MapViewState)}
      controller={false}
      layers={layers}
      style={{ width: "100%", height: "100%" }}
    >
      <Map reuseMaps mapStyle={MAP_STYLE} attributionControl={{ compact: true }} />
    </DeckGL>
  );
}
