import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileBrowser } from '../components/browser/FileBrowser';
import { DropZone } from '../components/upload/DropZone';
import { useFileStore } from '../store/fileStore';
import { XMarkIcon } from '@heroicons/react/24/outline';

export const BrowsePage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [showUpload, setShowUpload] = useState(searchParams.get('upload') === 'true');
  const { currentPath, setCurrentPath } = useFileStore();

  useEffect(() => {
    if (searchParams.get('upload') === 'true') {
      setShowUpload(true);
      // Remove upload param from URL
      searchParams.delete('upload');
      setSearchParams(searchParams);
    }
  }, [searchParams, setSearchParams]);

  return (
    <div className="h-[calc(100vh-8rem)]">
      {/* Upload modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Upload Files</h2>
              <button
                onClick={() => setShowUpload(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              <DropZone
                destinationPath={currentPath || 'input'}
                onUploadComplete={(files) => {
                  console.log('Uploaded files:', files);
                  // Optionally close modal after upload
                  // setShowUpload(false);
                }}
              />
            </div>
            <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
              <p className="text-sm text-gray-500">
                Files will be uploaded to: <code className="bg-gray-200 px-1 rounded">{currentPath || 'input'}/</code>
              </p>
              <button
                onClick={() => setShowUpload(false)}
                className="btn-secondary"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* File browser */}
      <FileBrowser
        mode="input"
        initialPath={currentPath}
        onPathSelect={setCurrentPath}
        selectionMode="multiple"
        showOutputSelector={true}
      />

      {/* Upload FAB */}
      <button
        onClick={() => setShowUpload(true)}
        className="fixed bottom-6 right-6 p-4 bg-primary-600 text-white rounded-full shadow-lg hover:bg-primary-700 transition-colors"
        title="Upload Files"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
          />
        </svg>
      </button>
    </div>
  );
};

export default BrowsePage;
