import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for the production Docker image (copies only what's needed)
  output: "standalone",
};

export default nextConfig;
