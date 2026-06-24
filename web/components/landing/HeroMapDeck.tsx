"use client";

import { useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { TripsLayer } from "@deck.gl/geo-layers";
import {
  IconLayer,
  LineLayer,
  ScatterplotLayer,
  TextLayer,
} from "@deck.gl/layers";
import { FlyToInterpolator } from "@deck.gl/core";
import type { MapViewState } from "@deck.gl/core";
import { Map } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { heatColor } from "@/components/map/heat";
import {
  PATROL_ORIGIN,
  TRIP_MS,
  buildTripFromPath,
  distanceKm,
  tripHead,
  type HeroParking,
  type HeroPin,
} from "./heroMapUtils";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

const CAR_ICON =
  "data:image/svg+xml;charset=utf-8," +
  encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <filter id="s" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow dx="0" dy="5" stdDeviation="4" flood-color="#14181f" flood-opacity=".28"/>
      </filter>
      <g filter="url(#s)" transform="rotate(28 32 32)">
        <rect x="15" y="9" width="34" height="46" rx="9" fill="#fff"/>
        <path d="M20 24h24l-4-10H24z" fill="#9ec5ff"/>
        <path d="M20 39h24l-3 10H23z" fill="#dfe8f7"/>
        <rect x="12" y="23" width="5" height="12" rx="2" fill="#1e45c8"/>
        <rect x="47" y="23" width="5" height="12" rx="2" fill="#1e45c8"/>
        <circle cx="24" cy="54" r="3" fill="#14181f"/>
        <circle cx="40" cy="54" r="3" fill="#14181f"/>
        <rect x="27" y="29" width="10" height="4" rx="2" fill="#1e45c8"/>
      </g>
    </svg>
  `);

function sceneOpacity(activeScene: number, target: number, strength = 1) {
  return activeScene === target ? strength : strength * 0.35;
}

export default function HeroMapDeck({
  hotspots,
  parking,
  spotlight,
  destination,
  routePath,
  maxPriority,
  reduceMotion,
  activeScene,
}: {
  hotspots: HeroPin[];
  parking: HeroParking[];
  spotlight: HeroPin;
  destination: { name: string; lat: number; lon: number };
  routePath: [number, number][];
  maxPriority: number;
  reduceMotion: boolean | null;
  activeScene: number;
}) {
  const [viewState, setViewState] = useState<MapViewState>({
    longitude: destination.lon,
    latitude: destination.lat - 0.012,
    zoom: 12.35,
    pitch: 0,
    bearing: 0,
    minZoom: 10.5,
    maxZoom: 14,
  });
  const [time, setTime] = useState(0);
  const [pulse, setPulse] = useState(0);

  const localRoute = useMemo<[number, number][]>(() => {
    if (routePath.length > 1) {
      const clipped: [number, number][] = [[PATROL_ORIGIN[0], PATROL_ORIGIN[1]]];
      for (const point of routePath) {
        if (distanceKm(destination, { lon: point[0], lat: point[1] }) <= 8) {
          clipped.push(point);
        }
      }
      if (clipped.length > 1) return clipped;
    }
    return [
      PATROL_ORIGIN,
      [
        PATROL_ORIGIN[0] + (destination.lon - PATROL_ORIGIN[0]) * 0.35,
        PATROL_ORIGIN[1] + (destination.lat - PATROL_ORIGIN[1]) * 0.35,
      ],
      [
        PATROL_ORIGIN[0] + (destination.lon - PATROL_ORIGIN[0]) * 0.72,
        PATROL_ORIGIN[1] + (destination.lat - PATROL_ORIGIN[1]) * 0.72,
      ],
      [destination.lon, destination.lat],
    ];
  }, [routePath, destination]);

  const trip = useMemo(
    () => buildTripFromPath(localRoute, TRIP_MS),
    [localRoute],
  );

  const patrolPos = useMemo(
    () => tripHead(trip, reduceMotion ? 0 : time),
    [trip, time, reduceMotion],
  );

  useEffect(() => {
    const id = window.setTimeout(() => {
      setViewState((vs) => ({
        ...vs,
        longitude: destination.lon,
        latitude: destination.lat - 0.014,
        zoom: 12.45,
        pitch: 0,
        bearing: 0,
        transitionDuration: reduceMotion ? 0 : 1600,
        transitionInterpolator: new FlyToInterpolator(),
      }));
    }, 0);
    return () => window.clearTimeout(id);
  }, [destination.lon, destination.lat, reduceMotion]);

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
  }, [destination.lon, destination.lat, reduceMotion]);

  const layers = useMemo(() => {
    const detectAlpha = Math.round(55 + sceneOpacity(activeScene, 0, 40));
    const patrolAlpha = Math.round(120 + sceneOpacity(activeScene, 2, 115));
    const guideAlpha = Math.round(140 + sceneOpacity(activeScene, 1, 100));

    const heat = new ScatterplotLayer<HeroPin>({
      id: "hero-heat-blobs",
      data: hotspots.slice(0, 10),
      getPosition: (d) => [d.lon, d.lat],
      getRadius: (d) =>
        (d.rank <= 3 ? 520 : d.rank <= 6 ? 380 : 280) +
        Math.sin(pulse * Math.PI * 2 + d.rank) * 20,
      getFillColor: (d) =>
        d.rank <= 5 ? [244, 161, 0, detectAlpha] : [234, 67, 53, detectAlpha - 15],
      stroked: false,
      radiusUnits: "meters",
      pickable: false,
    });

    const spotlightRing = new ScatterplotLayer<HeroPin>({
      id: "hero-spotlight",
      data: [spotlight],
      getPosition: (d) => [d.lon, d.lat],
      getRadius: 220 + Math.sin(pulse * Math.PI * 2) * 18,
      getFillColor: [234, 67, 53, 235],
      getLineColor: [255, 255, 255, 255],
      lineWidthMinPixels: 2,
      stroked: true,
      radiusUnits: "meters",
    });

    const patrolLineGlow = new LineLayer({
      id: "hero-patrol-route-glow",
      data: localRoute.slice(1).map((point, i) => ({
        from: localRoute[i],
        to: point,
      })),
      getSourcePosition: (d) => d.from,
      getTargetPosition: (d) => d.to,
      getColor: [30, 101, 230, Math.round(patrolAlpha * 0.35)],
      getWidth: 8,
      widthUnits: "pixels",
      capRounded: true,
      jointRounded: true,
    });

    const patrolLine = new LineLayer({
      id: "hero-patrol-route",
      data: localRoute.slice(1).map((point, i) => ({
        from: localRoute[i],
        to: point,
      })),
      getSourcePosition: (d) => d.from,
      getTargetPosition: (d) => d.to,
      getColor: [0, 92, 230, patrolAlpha],
      getWidth: 3.5,
      widthUnits: "pixels",
      capRounded: true,
      jointRounded: true,
    });

    const patrol = new TripsLayer({
      id: "hero-patrol",
      data: [trip],
      getPath: (d) => d.path,
      getTimestamps: (d) => d.timestamps,
      getColor: [0, 92, 230, patrolAlpha],
      getWidth: 4,
      widthMinPixels: 2,
      trailLength: 260,
      currentTime: time,
      fadeTrail: true,
      capRounded: true,
      jointRounded: true,
    });

    const dots = new ScatterplotLayer<HeroPin>({
      id: "hero-dots",
      data: hotspots.filter((h) => h.rank !== spotlight.rank && h.rank <= 12),
      getPosition: (d) => [d.lon, d.lat],
      getRadius: (d) => (d.rank <= 5 ? 160 : 120),
      getFillColor: (d) => {
        const t = d.priority_pct / maxPriority;
        return heatColor(t, Math.round(detectAlpha * 1.6));
      },
      getLineColor: [255, 255, 255, 160],
      lineWidthMinPixels: 1,
      stroked: true,
      radiusUnits: "meters",
      pickable: false,
    });

    const destinationPin = new ScatterplotLayer({
      id: "hero-destination",
      data: [destination],
      getPosition: (d) => [d.lon, d.lat],
      getRadius: 190,
      getFillColor: [30, 69, 200, 230],
      getLineColor: [255, 255, 255, 240],
      lineWidthMinPixels: 2,
      stroked: true,
      radiusUnits: "meters",
    });

    const depot = new ScatterplotLayer({
      id: "hero-depot",
      data: [{ pos: PATROL_ORIGIN }],
      getPosition: (d) => d.pos,
      getRadius: 170,
      getFillColor: [30, 69, 200, activeScene === 2 ? 200 : 120],
      getLineColor: [255, 255, 255, 200],
      lineWidthMinPixels: 1.5,
      stroked: true,
      radiusUnits: "meters",
    });

    const vehicleGlow = new ScatterplotLayer({
      id: "hero-vehicle-glow",
      data: [{ pos: patrolPos }],
      getPosition: (d) => d.pos,
      getRadius: 180 + Math.sin(pulse * Math.PI * 4) * 16,
      getFillColor: [0, 92, 230, activeScene === 2 ? 90 : 45],
      stroked: false,
      radiusUnits: "meters",
    });

    const vehicle = new IconLayer({
      id: "hero-vehicle",
      data: [{ pos: patrolPos, size: activeScene === 2 ? 40 : 32 }],
      iconAtlas: CAR_ICON,
      iconMapping: {
        car: { x: 0, y: 0, width: 64, height: 64, mask: false },
      },
      getIcon: () => "car",
      getPosition: (d) => d.pos,
      getSize: (d) => d.size,
      sizeUnits: "pixels",
      billboard: true,
    });

    const park = new ScatterplotLayer<HeroParking>({
      id: "hero-park",
      data: parking,
      getPosition: (d) => [d.lon, d.lat],
      getRadius: activeScene === 1 ? 220 : 170,
      getFillColor: [31, 138, 91, guideAlpha],
      getLineColor: [255, 255, 255, 210],
      lineWidthMinPixels: 1.5,
      stroked: true,
      radiusUnits: "meters",
    });

    const parkingLabels = new TextLayer<HeroParking>({
      id: "hero-park-labels",
      data: parking,
      getPosition: (d) => [d.lon, d.lat],
      getText: () => "P",
      getSize: 14,
      getColor: [255, 255, 255, 255],
      getTextAnchor: "middle",
      getAlignmentBaseline: "center",
      fontFamily: "Arial, sans-serif",
      fontWeight: 800,
      billboard: true,
    });

    const destinationLabel = new TextLayer({
      id: "hero-destination-label",
      data: [
        {
          pos: [destination.lon, destination.lat],
          text: destination.name.length > 22
            ? `${destination.name.slice(0, 20)}…`
            : destination.name,
        },
      ],
      getPosition: (d) => d.pos,
      getText: (d) => d.text,
      getPixelOffset: [0, -30],
      getSize: 11,
      getColor: [20, 24, 31, 235],
      getTextAnchor: "middle",
      getAlignmentBaseline: "bottom",
      fontFamily: "Arial, sans-serif",
      fontWeight: 700,
      billboard: true,
    });

    return [
      heat,
      dots,
      patrolLineGlow,
      patrolLine,
      patrol,
      spotlightRing,
      destinationPin,
      destinationLabel,
      depot,
      park,
      parkingLabels,
      vehicleGlow,
      vehicle,
    ];
  }, [
    hotspots,
    spotlight,
    trip,
    time,
    pulse,
    maxPriority,
    parking,
    activeScene,
    localRoute,
    patrolPos,
    destination,
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
