import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Phase 10 (spec section 27): a self-contained `.next/standalone` build for the production
  // Docker image (see clouddesk/frontend/Dockerfile) — bundles only the traced dependencies a
  // request actually needs, instead of shipping the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
