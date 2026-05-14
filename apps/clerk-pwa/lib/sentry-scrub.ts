import type { ErrorEvent, EventHint } from '@sentry/nextjs';

const PII_KEY_RE =
  /name|email|dob|date.?of.?birth|doc|passport|license|address/i;

function scrubObject(obj: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => {
      if (PII_KEY_RE.test(k)) return [k, '[Filtered]'];
      if (typeof v === 'object' && v !== null)
        return [k, scrubObject(v as Record<string, unknown>)];
      return [k, v];
    })
  );
}

export function scrubPii(
  event: ErrorEvent,
  _hint: EventHint
): ErrorEvent | null {
  if (event.request?.data && typeof event.request.data === 'object') {
    event.request.data = scrubObject(
      event.request.data as Record<string, unknown>
    );
  }
  if (event.extra) {
    event.extra = scrubObject(event.extra as Record<string, unknown>);
  }
  if (event.user) {
    event.user = event.user.id ? { id: event.user.id } : {};
  }
  return event;
}
