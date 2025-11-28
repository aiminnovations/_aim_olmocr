import React, { useState, useCallback, useEffect } from 'react';
import {
  FolderIcon,
  FolderOpenIcon,
  ChevronRightIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { useFileBrowser } from '../../hooks/useFileBrowser';
import { FileItem } from '../../types/file';

interface FolderTreeProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  rootPath: string;
}

interface TreeNodeProps {
  folder: FileItem;
  currentPath: string;
  onNavigate: (path: string) => void;
  level: number;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  folder,
  currentPath,
  onNavigate,
  level,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [children, setChildren] = useState<FileItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const isSelected = currentPath === folder.path;
  const isAncestor = currentPath.startsWith(folder.path + '/');

  // Auto-expand if this is an ancestor of current path
  useEffect(() => {
    if (isAncestor && !isExpanded) {
      setIsExpanded(true);
    }
  }, [isAncestor, isExpanded]);

  const handleToggle = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();

    if (!isExpanded && children.length === 0) {
      setIsLoading(true);
      try {
        // Fetch children - this would call the API
        const response = await fetch(`/api/v1/browse/${encodeURIComponent(folder.path)}`);
        const data = await response.json();
        setChildren(data.folders || []);
      } catch (error) {
        console.error('Failed to load children:', error);
      } finally {
        setIsLoading(false);
      }
    }

    setIsExpanded(!isExpanded);
  }, [isExpanded, children.length, folder.path]);

  const handleClick = useCallback(() => {
    onNavigate(folder.path);
  }, [folder.path, onNavigate]);

  return (
    <div>
      <div
        className={clsx(
          'flex items-center py-1 px-2 cursor-pointer rounded-sm',
          'hover:bg-gray-200',
          isSelected && 'bg-blue-100 text-blue-700',
        )}
        style={{ paddingLeft: `${level * 16 + 4}px` }}
        onClick={handleClick}
      >
        <button
          onClick={handleToggle}
          className="p-0.5 hover:bg-gray-300 rounded mr-1"
        >
          {isLoading ? (
            <div className="w-4 h-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
          ) : isExpanded ? (
            <ChevronDownIcon className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRightIcon className="w-4 h-4 text-gray-500" />
          )}
        </button>

        {isExpanded ? (
          <FolderOpenIcon className="w-4 h-4 text-yellow-500 mr-2" />
        ) : (
          <FolderIcon className="w-4 h-4 text-yellow-500 mr-2" />
        )}

        <span className="text-sm truncate">{folder.name}</span>
      </div>

      {isExpanded && children.length > 0 && (
        <div>
          {children.map((child) => (
            <TreeNode
              key={child.id}
              folder={child}
              currentPath={currentPath}
              onNavigate={onNavigate}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const FolderTree: React.FC<FolderTreeProps> = ({
  currentPath,
  onNavigate,
  rootPath,
}) => {
  const [rootFolders, setRootFolders] = useState<FileItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadRootFolders = async () => {
      try {
        const response = await fetch(`/api/v1/browse/${encodeURIComponent(rootPath)}`);
        const data = await response.json();
        setRootFolders(data.folders || []);
      } catch (error) {
        console.error('Failed to load root folders:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadRootFolders();
  }, [rootPath]);

  // Default root items
  const defaultRoots: FileItem[] = [
    {
      id: 'input',
      name: 'Input',
      path: 'input',
      type: 'folder',
    },
    {
      id: 'output',
      name: 'Output',
      path: 'output',
      type: 'folder',
    },
  ];

  return (
    <div className="py-2">
      {/* Quick access */}
      <div className="px-3 py-1 text-xs font-medium text-gray-500 uppercase">
        Quick Access
      </div>

      {defaultRoots.map((folder) => (
        <TreeNode
          key={folder.id}
          folder={folder}
          currentPath={currentPath}
          onNavigate={onNavigate}
          level={0}
        />
      ))}

      {/* All folders */}
      <div className="px-3 py-1 mt-4 text-xs font-medium text-gray-500 uppercase">
        All Folders
      </div>

      {isLoading ? (
        <div className="px-4 py-2 text-sm text-gray-500">Loading...</div>
      ) : rootFolders.length > 0 ? (
        rootFolders.map((folder) => (
          <TreeNode
            key={folder.id}
            folder={folder}
            currentPath={currentPath}
            onNavigate={onNavigate}
            level={0}
          />
        ))
      ) : (
        <div className="px-4 py-2 text-sm text-gray-500">No folders</div>
      )}
    </div>
  );
};

export default FolderTree;
