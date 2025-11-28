import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  CloudArrowUpIcon,
  DocumentIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { FileUploadProgress } from '../../types/file';
import { useUpload } from '../../hooks/useUpload';

interface DropZoneProps {
  destinationPath: string;
  onUploadComplete?: (files: FileUploadProgress[]) => void;
  maxFileSize?: number; // in bytes
  maxFiles?: number;
  acceptedFormats?: string[];
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const DropZone: React.FC<DropZoneProps> = ({
  destinationPath,
  onUploadComplete,
  maxFileSize = 100 * 1024 * 1024, // 100MB default
  maxFiles = 50,
  acceptedFormats = ['.pdf', '.png', '.jpg', '.jpeg'],
}) => {
  const [uploads, setUploads] = useState<FileUploadProgress[]>([]);
  const { uploadFile, cancelUpload } = useUpload();

  const onDrop = useCallback(async (acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      rejectedFiles.forEach(rejection => {
        const error = rejection.errors.map((e: any) => e.message).join(', ');
        setUploads(prev => [
          ...prev,
          {
            id: `rejected-${Date.now()}-${rejection.file.name}`,
            file: rejection.file,
            progress: 0,
            status: 'error',
            error,
          },
        ]);
      });
    }

    // Start uploading accepted files
    const newUploads: FileUploadProgress[] = acceptedFiles.map(file => ({
      id: `${Date.now()}-${file.name}`,
      file,
      progress: 0,
      status: 'pending' as const,
    }));

    setUploads(prev => [...prev, ...newUploads]);

    // Upload files in parallel (with limit)
    const uploadPromises = newUploads.map(async (upload) => {
      try {
        // Update status to uploading
        setUploads(prev =>
          prev.map(u =>
            u.id === upload.id ? { ...u, status: 'uploading' as const } : u
          )
        );

        const result = await uploadFile(upload.file, destinationPath, (progress) => {
          setUploads(prev =>
            prev.map(u =>
              u.id === upload.id ? { ...u, progress } : u
            )
          );
        });

        // Update status to completed
        setUploads(prev =>
          prev.map(u =>
            u.id === upload.id
              ? { ...u, status: 'completed' as const, progress: 100, uploadedPath: result.path }
              : u
          )
        );

        return { ...upload, status: 'completed' as const, uploadedPath: result.path };
      } catch (error) {
        // Update status to error
        setUploads(prev =>
          prev.map(u =>
            u.id === upload.id
              ? { ...u, status: 'error' as const, error: (error as Error).message }
              : u
          )
        );

        return { ...upload, status: 'error' as const, error: (error as Error).message };
      }
    });

    const results = await Promise.all(uploadPromises);
    onUploadComplete?.(results);
  }, [destinationPath, uploadFile, onUploadComplete]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    maxSize: maxFileSize,
    maxFiles,
  });

  const removeUpload = useCallback((id: string) => {
    const upload = uploads.find(u => u.id === id);
    if (upload?.status === 'uploading') {
      cancelUpload(id);
    }
    setUploads(prev => prev.filter(u => u.id !== id));
  }, [uploads, cancelUpload]);

  const clearCompleted = useCallback(() => {
    setUploads(prev => prev.filter(u => u.status !== 'completed'));
  }, []);

  const hasUploads = uploads.length > 0;
  const completedCount = uploads.filter(u => u.status === 'completed').length;
  const errorCount = uploads.filter(u => u.status === 'error').length;

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={clsx(
          'relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          isDragActive && !isDragReject && 'border-blue-500 bg-blue-50',
          isDragReject && 'border-red-500 bg-red-50',
          !isDragActive && 'border-gray-300 hover:border-gray-400 bg-gray-50'
        )}
      >
        <input {...getInputProps()} />

        <CloudArrowUpIcon
          className={clsx(
            'w-12 h-12 mx-auto mb-4',
            isDragActive && !isDragReject && 'text-blue-500',
            isDragReject && 'text-red-500',
            !isDragActive && 'text-gray-400'
          )}
        />

        {isDragReject ? (
          <p className="text-red-600 font-medium">
            Some files are not accepted
          </p>
        ) : isDragActive ? (
          <p className="text-blue-600 font-medium">
            Drop files here...
          </p>
        ) : (
          <>
            <p className="text-gray-600 font-medium">
              Drag and drop PDF files here
            </p>
            <p className="text-sm text-gray-500 mt-1">
              or click to browse
            </p>
          </>
        )}

        <p className="text-xs text-gray-400 mt-4">
          Accepted formats: {acceptedFormats.join(', ')} |
          Max size: {formatFileSize(maxFileSize)} |
          Max files: {maxFiles}
        </p>
      </div>

      {/* Upload list */}
      {hasUploads && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
            <span className="text-sm font-medium text-gray-700">
              Uploads ({uploads.length})
            </span>
            <div className="flex items-center space-x-4 text-xs">
              {completedCount > 0 && (
                <span className="text-green-600">
                  {completedCount} completed
                </span>
              )}
              {errorCount > 0 && (
                <span className="text-red-600">
                  {errorCount} failed
                </span>
              )}
              {completedCount > 0 && (
                <button
                  onClick={clearCompleted}
                  className="text-blue-600 hover:text-blue-700"
                >
                  Clear completed
                </button>
              )}
            </div>
          </div>

          {/* File list */}
          <div className="max-h-64 overflow-auto">
            {uploads.map((upload) => (
              <div
                key={upload.id}
                className="flex items-center px-4 py-2 border-b border-gray-100 last:border-0"
              >
                <DocumentIcon className="w-5 h-5 text-gray-400 mr-3" />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center">
                    <span className="text-sm text-gray-900 truncate">
                      {upload.file.name}
                    </span>
                    <span className="ml-2 text-xs text-gray-500">
                      ({formatFileSize(upload.file.size)})
                    </span>
                  </div>

                  {upload.status === 'uploading' && (
                    <div className="mt-1">
                      <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${upload.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {upload.status === 'error' && (
                    <p className="text-xs text-red-500 mt-0.5">
                      {upload.error}
                    </p>
                  )}
                </div>

                <div className="ml-4 flex items-center">
                  {upload.status === 'pending' && (
                    <span className="text-xs text-gray-500">Pending</span>
                  )}
                  {upload.status === 'uploading' && (
                    <span className="text-xs text-blue-600">
                      {upload.progress}%
                    </span>
                  )}
                  {upload.status === 'completed' && (
                    <CheckCircleIcon className="w-5 h-5 text-green-500" />
                  )}
                  {upload.status === 'error' && (
                    <ExclamationCircleIcon className="w-5 h-5 text-red-500" />
                  )}

                  <button
                    onClick={() => removeUpload(upload.id)}
                    className="ml-2 p-1 text-gray-400 hover:text-gray-600 rounded"
                  >
                    <XMarkIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DropZone;
