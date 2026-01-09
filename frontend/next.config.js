/** @type {import('next').NextConfig} */

// Production API URL - HTTPS required, NEVER allow localhost in production
const PRODUCTION_API_URL = 'https://litdocket-production.up.railway.app';

// Get safe API URL - reject localhost/http in production
function getSafeApiUrl() {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  const isProduction = process.env.NODE_ENV === 'production';

  // In production, NEVER allow localhost or HTTP
  if (isProduction) {
    if (!envUrl || envUrl.includes('localhost') || envUrl.includes('127.0.0.1') || envUrl.startsWith('http://')) {
      console.log('[next.config.js] Production mode: Using HTTPS production URL');
      return PRODUCTION_API_URL;
    }
  }

  return envUrl || PRODUCTION_API_URL;
}

const API_URL = getSafeApiUrl();
console.log('[next.config.js] API_URL:', API_URL);

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
  // CRITICAL: Headers for Firebase popup authentication
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin-allow-popups', // Required for Firebase Google Sign-In popup
          },
        ],
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
