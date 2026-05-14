'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createScan } from '@aura/api-client';
import type { Scan } from '@aura/api-client';
import { toast } from 'sonner';
import { useOfflineQueue } from './useOfflineQueue';

interface UploadParams {
  image: Blob;
  hotelId: string;
  sessionToken: string;
}

export function useUpload() {
  const queryClient = useQueryClient();
  const { enqueue } = useOfflineQueue();

  return useMutation<Scan, Error, UploadParams>({
    mutationKey: ['upload-scan'],
    mutationFn: ({ image, hotelId }) => createScan(image, hotelId),
    onMutate: () => {
      toast.loading('Uploading…', { id: 'upload' });
    },
    onSuccess: () => {
      toast.loading('Extracting text…', { id: 'upload' });
      queryClient.invalidateQueries({ queryKey: ['scans'] });
    },
    onError: async (error, variables) => {
      toast.dismiss('upload');
      toast.error('No connection — saved for retry');
      await enqueue(variables.image, variables.hotelId, variables.sessionToken);
    },
    onSettled: () => {
      toast.dismiss('upload');
    },
  });
}
