import React, { useCallback } from 'react';
import {
  DocumentIcon,
  FolderIcon,
  DocumentTextIcon,
  PhotoIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  PencilIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { format } from 'date-fns';
import { FileItem, FolderContents, SortConfig, ViewMode } from '../../types/file';

interface FileListProps {
  contents: FolderContents;
  selectedFiles: FileItem[];
  onFileSelect: (file: FileItem, isMultiSelect: boolean) => void;
  onNavigate: (path: string) => void;
  viewMode: ViewMode;
  sortConfig: SortConfig;
  onSort: (field: SortConfig['field']) => void;
  onDelete: () => void;
}

const getFileIcon = (file: FileItem) => {
  if (file.type === 'folder') {
    return <FolderIcon className="w-5 h-5 text-yellow-500" />;
  }

  const ext = file.extension?.toLowerCase();

  if (ext === 'pdf') {
    return <DocumentTextIcon className="w-5 h-5 text-red-500" />;
  }

  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext || '')) {
    return <PhotoIcon className="w-5 h-5 text-blue-500" />;
  }

  if (['md', 'txt', 'json', 'html'].includes(ext || '')) {
    return <DocumentTextIcon className="w-5 h-5 text-gray-500" />;
  }

  return <DocumentIcon className="w-5 h-5 text-gray-400" />;
};

const formatFileSize = (bytes?: number): string => {
  if (!bytes) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

const SortHeader: React.FC<{
  label: string;
  field: SortConfig['field'];
  sortConfig: SortConfig;
  onSort: (field: SortConfig['field']) => void;
  className?: string;
}> = ({ label, field, sortConfig, onSort, className }) => (
  <th
    className={clsx(
      'px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100',
      className
    )}
    onClick={() => onSort(field)}
  >
    <div className="flex items-center space-x-1">
      <span>{label}</span>
      {sortConfig.field === field && (
        sortConfig.direction === 'asc' ? (
          <ChevronUpIcon className="w-3 h-3" />
        ) : (
          <ChevronDownIcon className="w-3 h-3" />
        )
      )}
    </div>
  </th>
);

export const FileList: React.FC<FileListProps> = ({
  contents,
  selectedFiles,
  onFileSelect,
  onNavigate,
  viewMode,
  sortConfig,
  onSort,
  onDelete,
}) => {
  const allItems = [...contents.folders, ...contents.files];
  const selectedIds = new Set(selectedFiles.map(f => f.id));

  const handleClick = useCallback((file: FileItem, e: React.MouseEvent) => {
    const isMultiSelect = e.ctrlKey || e.metaKey;
    onFileSelect(file, isMultiSelect);
  }, [onFileSelect]);

  const handleDoubleClick = useCallback((file: FileItem) => {
    if (file.type === 'folder') {
      onNavigate(file.path);
    }
  }, [onNavigate]);

  const handleContextMenu = useCallback((file: FileItem, e: React.MouseEvent) => {
    e.preventDefault();
    // Show context menu
    // For now, just select the file
    if (!selectedIds.has(file.id)) {
      onFileSelect(file, false);
    }
  }, [selectedIds, onFileSelect]);

  if (viewMode.type === 'grid') {
    return (
      <div className="p-4">
        <div className="grid grid-cols-6 gap-4">
          {allItems.map((item) => (
            <div
              key={item.id}
              className={clsx(
                'flex flex-col items-center p-3 rounded-lg cursor-pointer',
                'hover:bg-gray-100',
                selectedIds.has(item.id) && 'bg-blue-100 ring-2 ring-blue-400'
              )}
              onClick={(e) => handleClick(item, e)}
              onDoubleClick={() => handleDoubleClick(item)}
              onContextMenu={(e) => handleContextMenu(item, e)}
            >
              <div className="w-12 h-12 flex items-center justify-center">
                {item.type === 'folder' ? (
                  <FolderIcon className="w-10 h-10 text-yellow-500" />
                ) : (
                  getFileIcon(item)
                )}
              </div>
              <span className="mt-2 text-xs text-center truncate w-full">
                {item.name}
              </span>
            </div>
          ))}
        </div>

        {allItems.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            This folder is empty
          </div>
        )}
      </div>
    );
  }

  // List view
  return (
    <div className="overflow-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50 sticky top-0">
          <tr>
            <th className="w-8 px-3 py-2">
              <input
                type="checkbox"
                className="rounded border-gray-300"
                checked={selectedFiles.length === allItems.length && allItems.length > 0}
                onChange={(e) => {
                  if (e.target.checked) {
                    allItems.forEach(item => {
                      if (!selectedIds.has(item.id)) {
                        onFileSelect(item, true);
                      }
                    });
                  } else {
                    // Deselect all
                    selectedFiles.forEach(file => onFileSelect(file, true));
                  }
                }}
              />
            </th>
            <SortHeader
              label="Name"
              field="name"
              sortConfig={sortConfig}
              onSort={onSort}
              className="flex-1"
            />
            <SortHeader
              label="Modified"
              field="modified"
              sortConfig={sortConfig}
              onSort={onSort}
              className="w-40"
            />
            <SortHeader
              label="Size"
              field="size"
              sortConfig={sortConfig}
              onSort={onSort}
              className="w-24"
            />
            <SortHeader
              label="Type"
              field="type"
              sortConfig={sortConfig}
              onSort={onSort}
              className="w-32"
            />
            <th className="w-20 px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {allItems.map((item) => (
            <tr
              key={item.id}
              className={clsx(
                'hover:bg-gray-50 cursor-pointer',
                selectedIds.has(item.id) && 'bg-blue-50'
              )}
              onClick={(e) => handleClick(item, e)}
              onDoubleClick={() => handleDoubleClick(item)}
              onContextMenu={(e) => handleContextMenu(item, e)}
            >
              <td className="px-3 py-2">
                <input
                  type="checkbox"
                  className="rounded border-gray-300"
                  checked={selectedIds.has(item.id)}
                  onChange={() => {}}
                  onClick={(e) => e.stopPropagation()}
                />
              </td>
              <td className="px-3 py-2">
                <div className="flex items-center">
                  {getFileIcon(item)}
                  <span className="ml-2 text-sm text-gray-900 truncate max-w-md">
                    {item.name}
                  </span>
                </div>
              </td>
              <td className="px-3 py-2 text-sm text-gray-500">
                {item.modified ? format(item.modified, 'MMM d, yyyy HH:mm') : '-'}
              </td>
              <td className="px-3 py-2 text-sm text-gray-500">
                {item.type === 'folder' ? '-' : formatFileSize(item.size)}
              </td>
              <td className="px-3 py-2 text-sm text-gray-500">
                {item.type === 'folder' ? 'Folder' : item.extension?.toUpperCase() || 'File'}
              </td>
              <td className="px-3 py-2 text-right">
                <div className="flex items-center justify-end space-x-1">
                  {item.type === 'file' && (
                    <button
                      className="p-1 text-gray-400 hover:text-blue-600 rounded"
                      onClick={(e) => {
                        e.stopPropagation();
                        // Handle download
                      }}
                      title="Download"
                    >
                      <ArrowDownTrayIcon className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    className="p-1 text-gray-400 hover:text-red-600 rounded"
                    onClick={(e) => {
                      e.stopPropagation();
                      onFileSelect(item, false);
                      onDelete();
                    }}
                    title="Delete"
                  >
                    <TrashIcon className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {allItems.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          This folder is empty
        </div>
      )}
    </div>
  );
};

export default FileList;
