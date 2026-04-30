import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  trailingSlash: false,
  // Required for S3 + CloudFront deploy (scripts/deploy.ps1 syncs frontend/out).
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;