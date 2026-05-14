interface CaptureNoticeProps {
  retentionHours: number;
}

export function CaptureNotice({ retentionHours }: CaptureNoticeProps) {
  return (
    <div
      role="note"
      className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      <p>
        We extract text from this ID — name, date of birth, document number,
        address. The photograph of the person is automatically removed from the
        image before processing and is never analyzed by AI. ID images are
        deleted after <strong>{retentionHours} hours</strong>.
      </p>
      <a
        href="/privacy"
        className="mt-1 block text-xs text-amber-700 underline"
      >
        How we handle ID data →
      </a>
    </div>
  );
}
