"use client";

import dynamic from "next/dynamic";
import { StationProvider } from "./stationContext";
import StationBar from "./StationBar";
import CommandSection from "./CommandSection";
import WhenSection from "../WhenSection";
import PlanSection from "../PlanSection";
import ProofSection from "../ProofSection";
import OffendersSection from "../OffendersSection";
import OfficerReports from "./OfficerReports";
import { Section } from "../ui";

const HotspotMap = dynamic(() => import("../HotspotMap"), { ssr: false });

export default function OfficerConsole() {
  return (
    <StationProvider>
      <StationBar />
      <CommandSection />

      <Section
        id="where"
        index="02"
        eyebrow="Where it happens"
        title={<>Where the city actually jams.</>}
        lede="Every hex is a street-sized cell, sized and coloured by enforcement priority. The tall red ones are where a unit changes the most outcomes. Tap one."
        dark
      >
        <HotspotMap />
      </Section>

      <WhenSection />
      <PlanSection />
      <ProofSection />
      <OffendersSection index="06" />
      <OfficerReports index="07" />
    </StationProvider>
  );
}
