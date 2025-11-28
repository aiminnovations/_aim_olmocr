import { useState, useCallback, useRef } from 'react';
import { api } from '../services/api';

interface UploadResult {
  path: string;
  size: number;
  contentType: string;
}

interface UseUploadReturn {
  uploadFile: (
    file: File,
    destinationPath: string,
    onProgress?: (progress: number) => void
  ) => Promise<UploadResult>;
  cancelUpload: (id: string) => void;
  isUploading: boolean;
}

export function useUpload(): UseUploadReturn {
  const [isUploading, setIsUploading] = useState(false);
  const abortControllers = useRef<Map<string, AbortController>>(new Map());

  const uploadFile = useCallback(async (
    file: File,
    destinationPath: string,
    onProgress?: (progress: number) => void
  ): Promise<UploadResult> => {
    const uploadId = `${Date.now()}-${file.name}`;
    const abortController = new AbortController();
    abortControllers.current.set(uploadId, abortController);

    setIsUploading(true);

    try {
      // Step 1: Get signed URL for upload
      const { data: { signedUrl, path } } = await api.post('/upload/init', {
        fileName: file.name,
        contentType: file.type,
        destinationPath,
        fileSize: file.size,
      });

      // Step 2: Upload directly to GCS using signed URL
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            onProgress?.(progress);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        };

        xhr.onerror = () => reject(new Error('Upload failed'));
        xhr.onabort = () => reject(new Error('Upload cancelled'));

        // Handle abort
        abortController.signal.addEventListener('abort', () => {
          xhr.abort();
        });

        xhr.open('PUT', signedUrl);
        xhr.setRequestHeader('Content-Type', file.type);
        xhr.send(file);
      });

      // Step 3: Confirm upload completion
      await api.post('/upload/complete', { path });

      return {
        path,
        size: file.size,
        contentType: file.type,
      };
    } finally {
      abortControllers.current.delete(uploadId);
      setIsUploading(false);
    }
  }, []);

  const cancelUpload = useCallback((id: string) => {
    const controller = abortControllers.current.get(id);
    if (controller) {
      controller.abort();
      abortControllers.current.delete(id);
    }
  }, []);

  return {
    uploadFile,
    cancelUpload,
    isUploading,
  };
}

export default useUpload;
