// File and folder types for the file browser

export interface FileItem {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'folder';
  size?: number;
  modified?: Date;
  contentType?: string;
  thumbnail?: string;
  extension?: string;
}

export interface FolderContents {
  path: string;
  files: FileItem[];
  folders: FileItem[];
  parent?: string;
}

export interface BreadcrumbItem {
  name: string;
  path: string;
}

export interface FileUploadProgress {
  id: string;
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
  uploadedPath?: string;
}

export interface OutputSettings {
  path: string;
  format: 'markdown' | 'json' | 'html' | 'dolma';
  includeMetadata: boolean;
  preserveFolderStructure: boolean;
}

export type SortField = 'name' | 'modified' | 'size' | 'type';
export type SortDirection = 'asc' | 'desc';

export interface SortConfig {
  field: SortField;
  direction: SortDirection;
}

export interface ViewMode {
  type: 'list' | 'grid';
  showHidden: boolean;
}
