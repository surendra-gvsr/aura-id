import type { NextConfig } from 'next';
import { createSecureHeaders } from 'next-secure-headers';

const supabaseHost = process.env.NEXT_PUBLIC_SUPABASE_URL
  ? new URL(process.env.NEXT_PUBLIC_SUPABASE_URL).host
  : '*.supabase.co';

const sentryHost = process.env.NEXT_PUBLIC_SENTRY_DSN
  ? new URL(process.env.NEXT_PUBLIC_SENTRY_DSN).host
  : 'o*.ingest.sentry.io';

const apiHost = process.env.NEXT_PUBLIC_API_URL
  ? new URL(process.env.NEXT_PUBLIC_API_URL).host
  : 'localhost:4000';

const secureHeaders = createSecureHeaders({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'"],
      imgSrc: ["'self'", 'data:'],
      connectSrc: [
        "'self'",
        `https://${supabaseHost}`,
        `wss://${supabaseHost}`,
        `https://${sentryHost}`,
        `https://${apiHost}`,
        'http://localhost:4000',
      ],
      fontSrc: ["'self'"],
      objectSrc: ["'none'"],
      frameSrc: ['https://billing.stripe.com'],
      frameAncestors: ["'none'"],
      baseURI: ["'self'"],
      formAction: ["'self'"],
    },
  },
  forceHTTPSRedirect: [
    true,
    { maxAge: 31536000, includeSubDomains: true, preload: true },
  ],
  referrerPolicy: 'strict-origin-when-cross-origin',
  nosniff: 'nosniff',
  frameGuard: 'deny',
  xssProtection: 'block-rendering',
});

const config: NextConfig = {
  reactStrictMode: true,
  transpilePackages: [
    '@aura/ui',
    '@aura/consent',
    '@aura/api-client',
    '@aura/types',
  ],
  async headers() {
    return [
      { source: '/(.*)', headers: secureHeaders },
      {
        source: '/guests/(.*)',
        headers: [{ key: 'Cache-Control', value: 'no-store, max-age=0' }],
      },
      {
        source: '/data-requests/(.*)',
        headers: [{ key: 'Cache-Control', value: 'no-store, max-age=0' }],
      },
    ];
  },
};

export default config;
