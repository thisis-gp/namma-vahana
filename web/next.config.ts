import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The backend serves on 127.0.0.1 and the app on localhost — allow both
  // hosts to reach dev resources so HMR/hydration works either way.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
