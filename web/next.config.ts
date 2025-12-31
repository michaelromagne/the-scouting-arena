import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  /* config options here */

  // Disable ESLint during build for Railway deployment
  eslint: {
    ignoreDuringBuilds: true,
  },

  // Disable TypeScript errors during build for Railway deployment
  typescript: {
    ignoreBuildErrors: true,
  },

  // Webpack configuration to handle path aliases
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, 'src'),
    };
    return config;
  },
};

export default nextConfig;
