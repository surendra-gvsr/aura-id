interface GuestPageFooterProps {
  retentionHours: number;
}

export function GuestPageFooter({ retentionHours }: GuestPageFooterProps) {
  return (
    <footer className="mt-8 border-t pt-4 text-xs text-muted-foreground">
      Aura ID does not process biometric data. Photos are cropped out before
      text extraction. Data retention: <strong>{retentionHours} hours</strong>{' '}
      for images, until deleted for text data.
    </footer>
  );
}
