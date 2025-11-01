/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_URL || 'http://localhost:3001'}/api/v1/:path*`,
      },
    ];
  },
  async redirects() {
    return [
      // Legacy Flask route redirects
      {
        source: '/dashboard',
        destination: '/dashboard/overview',
        permanent: true,
      },
      {
        source: '/profile/:id',
        destination: '/profiles/:id',
        permanent: true,
      },
      {
        source: '/work-request/:id',
        destination: '/work/:id',
        permanent: true,
      },
      {
        source: '/login',
        destination: '/auth/signin',
        permanent: true,
      },
      {
        source: '/register',
        destination: '/auth/signup',
        permanent: true,
      },
      {
        source: '/jobs',
        destination: '/work-requests',
        permanent: true,
      },
      {
        source: '/contractors',
        destination: '/professionals',
        permanent: true,
      },
      // Legacy API redirects (handled by Cloudflare but backup)
      {
        source: '/api/v1/:path*',
        destination: '/api/:path*',
        permanent: true,
      },
      // Help and support redirects
      {
        source: '/help',
        destination: '/support',
        permanent: true,
      },
      {
        source: '/contact',
        destination: '/support/contact',
        permanent: true,
      },
      // Legal page redirects
      {
        source: '/terms',
        destination: '/legal/terms',
        permanent: true,
      },
      {
        source: '/privacy',
        destination: '/legal/privacy',
        permanent: true,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;