// Processing job types

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface JobProgress {
  current: number;
  total: number;
  percentage: number;
}

export interface JobInput {
  path: string;
  fileName: string;
  fileSize: number;
  pageCount: number;
}

export interface JobOutput {
  path: string;
  format: string;
  files: JobOutputFile[];
}

export interface JobOutputFile {
  name: string;
  path: string;
  size: number;
}

export interface JobMetrics {
  inputTokens: number;
  outputTokens: number;
  processingTimeMs: number;
}

export interface ProcessingJob {
  id: string;
  userId: string;
  status: JobStatus;
  createdAt: Date;
  updatedAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  input: JobInput;
  output: JobOutput;
  progress: JobProgress;
  metrics?: JobMetrics;
  error?: string;
}

export interface CreateJobRequest {
  inputPath: string;
  outputPath: string;
  outputFormat: 'markdown' | 'json' | 'html' | 'dolma';
  options?: {
    includeMetadata?: boolean;
    preserveFolderStructure?: boolean;
    languageFilter?: string[];
  };
}

export interface JobListResponse {
  jobs: ProcessingJob[];
  total: number;
  page: number;
  pageSize: number;
}
