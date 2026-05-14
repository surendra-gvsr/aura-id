'use client';

// /capture/confirm — text-only extracted fields review page.
// COMPLIANCE: No <img>, no <video>, no image URL is rendered anywhere on this page.
// Only text fields extracted from the ID scan are shown.

import { Suspense, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { getScan, updateScan } from '@aura/api-client';
import type { ExtractedFields } from '@aura/api-client';
import { ConfirmForm } from './ConfirmForm';

// Inner component that reads search params — must be inside <Suspense> boundary
// because useSearchParams() suspends in Next.js 15+.
function ConfirmPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();

  const scanId = searchParams.get('scan_id');

  const {
    data: scan,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => getScan(scanId!),
    enabled: !!scanId,
    staleTime: 0,
    gcTime: 0,
  });

  const mutation = useMutation({
    mutationFn: (fields: ExtractedFields) => updateScan(scanId!, fields),
    onSuccess: () => {
      // Clear cached scan so stale data is not shown if the clerk scans again
      queryClient.removeQueries({ queryKey: ['scan', scanId] });
      toast.success('Sent to PMS — ready for next guest');
      router.push('/capture');
    },
    onError: () => {
      toast.error('Failed to submit — please try again');
    },
  });

  const handleSubmit = useCallback(
    async (fields: ExtractedFields) => {
      mutation.mutate(fields);
    },
    [mutation]
  );

  if (!scanId) {
    return (
      <main className="p-4">
        <p className="text-sm text-destructive">
          No scan ID — go back and try again.
        </p>
      </main>
    );
  }

  if (isLoading) {
    return (
      <main className="p-4">
        <p className="text-sm text-muted-foreground">Extracting text…</p>
      </main>
    );
  }

  if (error || !scan) {
    return (
      <main className="p-4">
        <p className="text-sm text-destructive">
          Failed to load scan. Please go back and try again.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-md space-y-6 p-4">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold">Review extracted fields</h1>
        <p className="text-sm text-muted-foreground">
          Edit any incorrect values before submitting.
        </p>
      </div>

      {/* ConfirmForm renders only text inputs — no image or video elements */}
      <ConfirmForm
        initialFields={scan.extractedFields ?? {}}
        onSubmit={handleSubmit}
        isSubmitting={mutation.isPending}
      />

      <p className="text-center text-xs text-muted-foreground">
        No photo is shown here — only the extracted text fields.
      </p>
    </main>
  );
}

// Outer page component wraps the inner component in Suspense, which is required
// by Next.js 15+ when any child uses useSearchParams().
export default function ConfirmPage() {
  return (
    <Suspense
      fallback={
        <main className="p-4">
          <p className="text-sm text-muted-foreground">Loading…</p>
        </main>
      }
    >
      <ConfirmPageInner />
    </Suspense>
  );
}
