'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export type CameraState = 'idle' | 'starting' | 'ready' | 'error';

export interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  state: CameraState;
  error: string | null;
  capture: () => Promise<Blob | null>;
  toggleFlash: () => void;
  flashOn: boolean;
}

export function useCamera(): UseCameraReturn {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const trackRef = useRef<MediaStreamTrack | null>(null);
  const [state, setState] = useState<CameraState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [flashOn, setFlashOn] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState('starting');

    navigator.mediaDevices
      .getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        } as MediaTrackConstraints,
        audio: false,
      })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        trackRef.current = stream.getVideoTracks()[0] ?? null;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setState('ready');
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
        setState('error');
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const capture = useCallback(async (): Promise<Blob | null> => {
    if (!videoRef.current || state !== 'ready') return null;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(videoRef.current, 0, 0);
    return new Promise<Blob | null>((resolve) => {
      canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.85);
    });
  }, [state]);

  const toggleFlash = useCallback(() => {
    const track = trackRef.current;
    if (!track) return;
    const newVal = !flashOn;
    (track.applyConstraints as (c: Record<string, unknown>) => Promise<void>)({
      advanced: [{ torch: newVal }],
    }).catch(() => {});
    setFlashOn(newVal);
  }, [flashOn]);

  return { videoRef, state, error, capture, toggleFlash, flashOn };
}
