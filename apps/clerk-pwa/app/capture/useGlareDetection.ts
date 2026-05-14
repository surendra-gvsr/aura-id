'use client';

import { useCallback, useRef } from 'react';

const GLARE_THRESHOLD = 210;
const SAMPLE_STEP = 8;

export function useGlareDetection(
  videoRef: React.RefObject<HTMLVideoElement | null>
) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const checkGlare = useCallback((): boolean => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return false;

    if (!canvasRef.current)
      canvasRef.current = document.createElement('canvas');
    const canvas = canvasRef.current;
    canvas.width = 160;
    canvas.height = 90;

    const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
    ctx.drawImage(video, 0, 0, 160, 90);
    const { data } = ctx.getImageData(0, 0, 160, 90);

    let sum = 0;
    let count = 0;
    for (let i = 0; i < data.length; i += 4 * SAMPLE_STEP) {
      const r = data[i]!;
      const g = data[i + 1]!;
      const b = data[i + 2]!;
      sum += 0.299 * r + 0.587 * g + 0.114 * b;
      count++;
    }

    return count > 0 && sum / count > GLARE_THRESHOLD;
  }, [videoRef]);

  return { checkGlare };
}
