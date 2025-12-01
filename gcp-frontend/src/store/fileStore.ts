import { create } from 'zustand';
import type { FileItem, SortConfig, ViewMode } from '../types/file';

interface FileState {
  // Current path and contents
  currentPath: string;
  selectedFiles: FileItem[];

  // View settings
  viewMode: ViewMode;
  sortConfig: SortConfig;

  // Sidebar
  sidebarWidth: number;
  sidebarCollapsed: boolean;

  // Actions
  setCurrentPath: (path: string) => void;
  setSelectedFiles: (files: FileItem[]) => void;
  addSelectedFile: (file: FileItem) => void;
  removeSelectedFile: (fileId: string) => void;
  clearSelection: () => void;
  toggleFileSelection: (file: FileItem) => void;
  setViewMode: (mode: ViewMode) => void;
  setSortConfig: (config: SortConfig) => void;
  setSidebarWidth: (width: number) => void;
  toggleSidebar: () => void;
}

export const useFileStore = create<FileState>()((set, get) => ({
  currentPath: '',
  selectedFiles: [],
  viewMode: { type: 'list', showHidden: false },
  sortConfig: { field: 'name', direction: 'asc' },
  sidebarWidth: 250,
  sidebarCollapsed: false,

  setCurrentPath: (path) =>
    set({
      currentPath: path,
      selectedFiles: [], // Clear selection on path change
    }),

  setSelectedFiles: (files) => set({ selectedFiles: files }),

  addSelectedFile: (file) =>
    set((state) => ({
      selectedFiles: [...state.selectedFiles, file],
    })),

  removeSelectedFile: (fileId) =>
    set((state) => ({
      selectedFiles: state.selectedFiles.filter((f) => f.id !== fileId),
    })),

  clearSelection: () => set({ selectedFiles: [] }),

  toggleFileSelection: (file) => {
    const { selectedFiles } = get();
    const isSelected = selectedFiles.some((f) => f.id === file.id);

    if (isSelected) {
      set({
        selectedFiles: selectedFiles.filter((f) => f.id !== file.id),
      });
    } else {
      set({
        selectedFiles: [...selectedFiles, file],
      });
    }
  },

  setViewMode: (viewMode) => set({ viewMode }),

  setSortConfig: (sortConfig) => set({ sortConfig }),

  setSidebarWidth: (sidebarWidth) => set({ sidebarWidth }),

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}));
