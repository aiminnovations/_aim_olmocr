import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { getIdToken } from './auth';

// Create axios instance with default config
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    try {
      const token = await getIdToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      // User not authenticated, continue without token
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid, redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// File Browser API
export interface BrowseResponse {
  path: string;
  files: Array<{
    id: string;
    name: string;
    path: string;
    type: 'file';
    size: number;
    modified: string;
    contentType: string;
  }>;
  folders: Array<{
    id: string;
    name: string;
    path: string;
    type: 'folder';
  }>;
  parent?: string;
}

// Upload API
export interface InitUploadRequest {
  fileName: string;
  contentType: string;
  destinationPath: string;
  fileSize: number;
}

export interface InitUploadResponse {
  signedUrl: string;
  path: string;
  expiresAt: string;
}

// Processing API
export interface CreateJobRequest {
  inputPath: string;
  outputPath: string;
  outputFormat: 'markdown' | 'json' | 'html' | 'dolma';
  options?: {
    includeMetadata?: boolean;
    preserveFolderStructure?: boolean;
  };
}

export interface Job {
  id: string;
  userId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  createdAt: string;
  updatedAt: string;
  startedAt?: string;
  completedAt?: string;
  input: {
    path: string;
    fileName: string;
    fileSize: number;
    pageCount: number;
  };
  output: {
    path: string;
    format: string;
    files: Array<{
      name: string;
      path: string;
      size: number;
    }>;
  };
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
  metrics?: {
    inputTokens: number;
    outputTokens: number;
    processingTimeMs: number;
  };
  error?: string;
}

// Settings API
export interface UserSettings {
  defaultInputPath: string;
  defaultOutputPath: string;
  defaultOutputFormat: 'markdown' | 'json' | 'html' | 'dolma';
  emailNotifications: boolean;
  theme: 'light' | 'dark' | 'system';
}

// API Functions
export const browseApi = {
  list: (path: string) =>
    api.get<BrowseResponse>(`/browse/${encodeURIComponent(path || '')}`),

  createFolder: (path: string) =>
    api.post('/folders', { path }),

  delete: (paths: string[]) =>
    api.post('/files/delete', { paths }),

  move: (sourcePaths: string[], destination: string) =>
    api.post('/files/move', { sourcePaths, destination }),

  copy: (sourcePaths: string[], destination: string) =>
    api.post('/files/copy', { sourcePaths, destination }),

  rename: (oldPath: string, newName: string) =>
    api.post('/files/rename', { oldPath, newName }),
};

export const uploadApi = {
  init: (data: InitUploadRequest) =>
    api.post<InitUploadResponse>('/upload/init', data),

  complete: (path: string) =>
    api.post('/upload/complete', { path }),
};

export const processingApi = {
  create: (data: CreateJobRequest) =>
    api.post<Job>('/process', data),

  list: (page = 1, pageSize = 20) =>
    api.get<PaginatedResponse<Job>>('/jobs', { params: { page, pageSize } }),

  get: (jobId: string) =>
    api.get<Job>(`/jobs/${jobId}`),

  cancel: (jobId: string) =>
    api.delete(`/jobs/${jobId}`),

  getOutput: (jobId: string) =>
    api.get(`/jobs/${jobId}/output`),
};

export const settingsApi = {
  get: () =>
    api.get<UserSettings>('/settings'),

  update: (settings: Partial<UserSettings>) =>
    api.put<UserSettings>('/settings', settings),
};

export const downloadApi = {
  getSignedUrl: (fileId: string) =>
    api.get<{ url: string; expiresAt: string }>(`/download/${fileId}`),

  batchDownload: (fileIds: string[]) =>
    api.post<{ url: string }>('/download/batch', { fileIds }),
};

export { api };
export default api;
