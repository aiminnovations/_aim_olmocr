import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { FileItem, FolderContents } from '../types/file';

interface UseFileBrowserReturn {
  contents: FolderContents | null;
  isLoading: boolean;
  error: Error | null;
  refresh: () => void;
  createFolder: (parentPath: string, name: string) => Promise<void>;
  deleteItems: (paths: string[]) => Promise<void>;
  moveItems: (items: FileItem[], destinationPath: string) => Promise<void>;
  copyItems: (items: FileItem[], destinationPath: string) => Promise<void>;
  renameItem: (item: FileItem, newName: string) => Promise<void>;
}

export function useFileBrowser(path: string): UseFileBrowserReturn {
  const queryClient = useQueryClient();

  // Fetch folder contents
  const {
    data: contents,
    isLoading,
    error,
    refetch,
  } = useQuery<FolderContents, Error>({
    queryKey: ['browse', path],
    queryFn: async () => {
      const response = await api.get(`/browse/${encodeURIComponent(path || '')}`);
      return response.data;
    },
    staleTime: 30000, // 30 seconds
  });

  // Create folder mutation
  const createFolderMutation = useMutation({
    mutationFn: async ({ parentPath, name }: { parentPath: string; name: string }) => {
      const fullPath = parentPath ? `${parentPath}/${name}` : name;
      await api.post('/folders', { path: fullPath });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['browse', path] });
    },
  });

  // Delete items mutation
  const deleteItemsMutation = useMutation({
    mutationFn: async (paths: string[]) => {
      await api.post('/files/delete', { paths });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['browse', path] });
    },
  });

  // Move items mutation
  const moveItemsMutation = useMutation({
    mutationFn: async ({ sourcePaths, destination }: { sourcePaths: string[]; destination: string }) => {
      await api.post('/files/move', { sourcePaths, destination });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['browse'] });
    },
  });

  // Copy items mutation
  const copyItemsMutation = useMutation({
    mutationFn: async ({ sourcePaths, destination }: { sourcePaths: string[]; destination: string }) => {
      await api.post('/files/copy', { sourcePaths, destination });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['browse'] });
    },
  });

  // Rename item mutation
  const renameItemMutation = useMutation({
    mutationFn: async ({ oldPath, newName }: { oldPath: string; newName: string }) => {
      await api.post('/files/rename', { oldPath, newName });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['browse', path] });
    },
  });

  const createFolder = useCallback(async (parentPath: string, name: string) => {
    await createFolderMutation.mutateAsync({ parentPath, name });
  }, [createFolderMutation]);

  const deleteItems = useCallback(async (paths: string[]) => {
    await deleteItemsMutation.mutateAsync(paths);
  }, [deleteItemsMutation]);

  const moveItems = useCallback(async (items: FileItem[], destinationPath: string) => {
    const sourcePaths = items.map(item => item.path);
    await moveItemsMutation.mutateAsync({ sourcePaths, destination: destinationPath });
  }, [moveItemsMutation]);

  const copyItems = useCallback(async (items: FileItem[], destinationPath: string) => {
    const sourcePaths = items.map(item => item.path);
    await copyItemsMutation.mutateAsync({ sourcePaths, destination: destinationPath });
  }, [copyItemsMutation]);

  const renameItem = useCallback(async (item: FileItem, newName: string) => {
    await renameItemMutation.mutateAsync({ oldPath: item.path, newName });
  }, [renameItemMutation]);

  return {
    contents: contents || null,
    isLoading,
    error: error || null,
    refresh: refetch,
    createFolder,
    deleteItems,
    moveItems,
    copyItems,
    renameItem,
  };
}

export default useFileBrowser;
