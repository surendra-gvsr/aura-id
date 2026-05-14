'use client';

import { FramingOverlay } from './FramingOverlay';
import type { UseCameraReturn } from './useCamera';

interface CameraViewfinderProps {
  camera: UseCameraReturn;
  glareWarning: boolean;
}

export function CameraViewfinder({
  camera,
  glareWarning,
}: CameraViewfinderProps) {
  return (
    <div className="relative flex-1 overflow-hidden bg-black">
      {camera.state === 'error' ? (
        <div className="flex h-full items-center justify-center px-8 text-center text-sm text-white">
          {camera.error ?? 'Camera unavailable'}
        </div>
      ) : (
        <>
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video
            ref={camera.videoRef}
            autoPlay
            playsInline
            muted
            className="h-full w-full object-cover"
          />
          <FramingOverlay />
          {glareWarning && (
            <div
              role="alert"
              className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-black/70 px-4 py-2 text-xs text-white"
            >
              Too much glare — adjust the lighting
            </div>
          )}
        </>
      )}
    </div>
  );
}
