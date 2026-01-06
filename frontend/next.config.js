/** @type {import('next').NextConfig} */

// Production API URL - must use HTTPS to avoid Mixed Content errors
const PRODUCTION_API_URL = 'https://litdocket-production.up.railway.app';
const API_URL = process.env.NEXT_PUBLIC_API_URL || PRODUCTION_API_URL;

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_URL}/api/:path*`,
      },
    ];
  },
  webpack: (config) => {
    config.resolve.alias.canvas = false;
    config.resolve.alias.encoding = false;
    return config;
  },
};

module.exports = nextConfig;
