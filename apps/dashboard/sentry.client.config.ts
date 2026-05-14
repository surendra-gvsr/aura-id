import * as Sentry from '@sentry/nextjs';
import { scrubPii } from '@/lib/sentry-scrub';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  debug: false,
  beforeSend: scrubPii,
  denyUrls: [/localhost/, /127\.0\.0\.1/],
});
