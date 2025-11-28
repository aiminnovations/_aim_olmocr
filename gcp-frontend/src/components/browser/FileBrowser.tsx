import React, { useState, useCallback, useMemo } from 'react';
import { FolderTree } from './FolderTree';
import { FileList } from './FileList';
import { PathBreadcrumb } from './PathBreadcrumb';
import { OutputSelector } from './OutputSelector';
import {
  FileItem,
  FolderContents,
  SortConfig,
  ViewMode,
  OutputSettings
} from '../../types/file';
import { useFileBrowser } from '../../hooks/useFileBrowser';
import {
  FolderIcon,
  ListBulletIcon,
  Squares2X2Icon,
  ArrowUpTrayIcon,
  PlayIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface FileBrowserProps {
  mode: 'input' | 'output' | 'browse';
  onFileSelect?: (files: FileItem[]) => void;
  onPathSelect?: (path: string) => void;
  initialPath?: string;
  selectionMode?: 'single' | 'multiple' | 'none';
  showOutputSelector?: boolean;
}

export const FileBrowser: React.FC<FileBrowserProps> = ({
  mode = 'browse',
  onFileSelect,
  onPathSelect,
  initialPath = '',
  selectionMode = 'multiple',
  showOutputSelector = false,
}) => {
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [selectedFiles, setSelectedFiles] = useState<FileItem[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>({ type: 'list', showHidden: false });
  const [sortConfig, setSortConfig] = useState<SortConfig>({ field: 'name', direction: 'asc' });
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [showOutputModal, setShowOutputModal] = useState(false);

  const {
    contents,
    isLoading,
    error,
    refresh,
    createFolder,
    deleteItems,
    moveItems,
    copyItems
  } = useFileBrowser(currentPath);

  // Handle path navigation
  const handleNavigate = useCallback((path: string) => {
    setCurrentPath(path);
    setSelectedFiles([]);
    onPathSelect?.(path);
  }, [onPathSelect]);

  // Handle file selection
  const handleFileSelect = useCallback((file: FileItem, isMultiSelect: boolean) => {
    if (selectionMode === 'none') return;

    if (file.type === 'folder') {
      // Double-click to navigate
      handleNavigate(file.path);
      return;
    }

    setSelectedFiles(prev => {
      if (selectionMode === 'single') {
        return [file];
      }

      if (isMultiSelect) {
        const isSelected = prev.some(f => f.id === file.id);
        if (isSelected) {
          return prev.filter(f => f.id !== file.id);
        }
        return [...prev, file];
      }

      return [file];
    });
  }, [selectionMode, handleNavigate]);

  // Handle selection change
  React.useEffect(() => {
    onFileSelect?.(selectedFiles);
  }, [selectedFiles, onFileSelect]);

  // Sort files
  const sortedContents = useMemo(() => {
    if (!contents) return null;

    const sortFn = (a: FileItem, b: FileItem) => {
      let comparison = 0;

      switch (sortConfig.field) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'modified':
          comparison = (a.modified?.getTime() || 0) - (b.modified?.getTime() || 0);
          break;
        case 'size':
          comparison = (a.size || 0) - (b.size || 0);
          break;
        case 'type':
          comparison = (a.extension || '').localeCompare(b.extension || '');
          break;
      }

      return sortConfig.direction === 'asc' ? comparison : -comparison;
    };

    return {
      ...contents,
      folders: [...contents.folders].sort(sortFn),
      files: [...contents.files].sort(sortFn),
    };
  }, [contents, sortConfig]);

  // Handle sort change
  const handleSort = useCallback((field: SortConfig['field']) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  // Handle context menu actions
  const handleCreateFolder = useCallback(async () => {
    const name = prompt('Enter folder name:');
    if (name) {
      await createFolder(currentPath, name);
      refresh();
    }
  }, [currentPath, createFolder, refresh]);

  const handleDelete = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    const confirm = window.confirm(
      `Delete ${selectedFiles.length} item(s)?`
    );

    if (confirm) {
      await deleteItems(selectedFiles.map(f => f.path));
      setSelectedFiles([]);
      refresh();
    }
  }, [selectedFiles, deleteItems, refresh]);

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-2">
          <PathBreadcrumb
            path={currentPath}
            onNavigate={handleNavigate}
          />
        </div>

        <div className="flex items-center space-x-2">
          {/* View toggle */}
          <div className="flex items-center bg-white rounded border border-gray-300">
            <button
              onClick={() => setViewMode(v => ({ ...v, type: 'list' }))}
              className={clsx(
                'p-1.5 rounded-l',
                viewMode.type === 'list' ? 'bg-blue-100 text-blue-600' : 'text-gray-500 hover:bg-gray-100'
              )}
            >
              <ListBulletIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode(v => ({ ...v, type: 'grid' }))}
              className={clsx(
                'p-1.5 rounded-r',
                viewMode.type === 'grid' ? 'bg-blue-100 text-blue-600' : 'text-gray-500 hover:bg-gray-100'
              )}
            >
              <Squares2X2Icon className="w-4 h-4" />
            </button>
          </div>

          {/* Actions */}
          <button
            onClick={handleCreateFolder}
            className="p-1.5 text-gray-500 hover:bg-gray-100 rounded"
            title="New Folder"
          >
            <FolderIcon className="w-4 h-4" />
          </button>

          {mode === 'input' && selectedFiles.length > 0 && (
            <button
              onClick={() => setShowOutputModal(true)}
              className="flex items-center px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
            >
              <PlayIcon className="w-4 h-4 mr-1" />
              Process ({selectedFiles.length})
            </button>
          )}

          <button
            onClick={refresh}
            className="p-1.5 text-gray-500 hover:bg-gray-100 rounded"
            title="Refresh"
          >
            <ArrowUpTrayIcon className="w-4 h-4 rotate-180" />
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - Folder tree */}
        <div
          className="border-r border-gray-200 overflow-auto bg-gray-50"
          style={{ width: sidebarWidth }}
        >
          <FolderTree
            currentPath={currentPath}
            onNavigate={handleNavigate}
            rootPath=""
          />
        </div>

        {/* Resize handle */}
        <div
          className="w-1 bg-gray-200 cursor-col-resize hover:bg-blue-400"
          onMouseDown={(e) => {
            const startX = e.clientX;
            const startWidth = sidebarWidth;

            const handleMouseMove = (e: MouseEvent) => {
              const newWidth = startWidth + (e.clientX - startX);
              setSidebarWidth(Math.max(150, Math.min(400, newWidth)));
            };

            const handleMouseUp = () => {
              document.removeEventListener('mousemove', handleMouseMove);
              document.removeEventListener('mouseup', handleMouseUp);
            };

            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
          }}
        />

        {/* File list */}
        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-500">
              Error loading contents: {error.message}
            </div>
          ) : sortedContents ? (
            <FileList
              contents={sortedContents}
              selectedFiles={selectedFiles}
              onFileSelect={handleFileSelect}
              onNavigate={handleNavigate}
              viewMode={viewMode}
              sortConfig={sortConfig}
              onSort={handleSort}
              onDelete={handleDelete}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              No contents
            </div>
          )}
        </div>
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
        <span>
          {sortedContents ? (
            `${sortedContents.folders.length} folders, ${sortedContents.files.length} files`
          ) : (
            'Loading...'
          )}
        </span>
        {selectedFiles.length > 0 && (
          <span>{selectedFiles.length} selected</span>
        )}
      </div>

      {/* Output selector modal */}
      {showOutputModal && (
        <OutputSelector
          selectedFiles={selectedFiles}
          onClose={() => setShowOutputModal(false)}
          onConfirm={(settings) => {
            console.log('Process with settings:', settings);
            setShowOutputModal(false);
          }}
        />
      )}
    </div>
  );
};

export default FileBrowser;
