'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@aura/ui';
import { CaptureNotice } from '@aura/consent';
import { createClient } from '@/lib/supabase/client';
import { CameraViewfinder } from './CameraViewfinder';
import { useCamera } from './useCamera';
import { useGlareDetection } from './useGlareDetection';
import { useUpload } from './useUpload';

const DEFAULT_RETENTION_HOURS = 24;

export default function CapturePage() {
  const router = useRouter();
  const camera = useCamera();
  const { checkGlare } = useGlareDetection(camera.videoRef);
  const upload = useUpload();
  const [glareWarning, setGlareWarning] = useState(false);
  const [retentionHours, setRetentionHours] = useState(DEFAULT_RETENTION_HOURS);

  useEffect(() => {
    if (camera.state !== 'ready') return;
    const id = setInterval(() => setGlareWarning(checkGlare()), 2000);
    return () => clearInterval(id);
  }, [camera.state, checkGlare]);

  useEffect(() => {
    fetch('/api/hotels/me')
      .then((r) => r.json())
      .then((hotel: { imageRetentionHours?: number }) => {
        if (hotel.imageRetentionHours)
          setRetentionHours(hotel.imageRetentionHours);
      })
      .catch(() => {});
  }, []);

  const handleCapture = useCallback(async () => {
    if (upload.isPending) return;
    const blob = await camera.capture();
    if (!blob) return;

    navigator.vibrate?.(30);

    let uploadBlob = blob;
    if (blob.size > 1_048_576) {
      uploadBlob = await compressToTarget(blob, 1_048_576);
    }

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    const sessionToken = session?.access_token ?? 'anon';

    upload.mutate(
      { image: uploadBlob, hotelId: 'placeholder', sessionToken },
      {
        onSuccess: (scan) => {
          router.push(`/capture/confirm?scan_id=${scan.id}`);
        },
      }
    );
  }, [camera, router, upload]);

  return (
    <div className="flex h-dvh flex-col">
      <div className="p-3">
        <CaptureNotice retentionHours={retentionHours} />
      </div>

      <CameraViewfinder camera={camera} glareWarning={glareWarning} />

      <div className="flex items-center justify-between bg-black px-6 py-4">
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:text-white/80"
          onClick={() => router.push('/history')}
        >
          History
        </Button>

        <button
          onClick={handleCapture}
          disabled={camera.state !== 'ready' || upload.isPending}
          aria-label="Capture ID"
          className="h-16 w-16 rounded-full border-4 border-white bg-white/20 transition-transform hover:bg-white/30 active:scale-95 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
        />

        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:text-white/80"
          onClick={camera.toggleFlash}
        >
          {camera.flashOn ? 'Flash On' : 'Flash Off'}
        </Button>
      </div>
    </div>
  );
}

async function compressToTarget(
  blob: Blob,
  targetBytes: number
): Promise<Blob> {
  const bitmap = await createImageBitmap(blob);
  const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
  const ctx = canvas.getContext('2d')!;
  ctx.drawImage(bitmap, 0, 0);

  let quality = 0.8;
  let result = await canvas.convertToBlob({ type: 'image/jpeg', quality });
  while (result.size > targetBytes && quality > 0.3) {
    quality -= 0.1;
    result = await canvas.convertToBlob({ type: 'image/jpeg', quality });
  }
  return result;
}
