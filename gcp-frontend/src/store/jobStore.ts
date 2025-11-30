import { create } from 'zustand';
import type { ProcessingJob } from '../types/job';

interface JobState {
  // Jobs list
  jobs: ProcessingJob[];
  activeJobs: ProcessingJob[];

  // Selected job for details
  selectedJobId: string | null;

  // Polling
  isPolling: boolean;

  // Actions
  setJobs: (jobs: ProcessingJob[]) => void;
  addJob: (job: ProcessingJob) => void;
  updateJob: (job: Partial<ProcessingJob> & { id: string }) => void;
  removeJob: (jobId: string) => void;
  setSelectedJobId: (jobId: string | null) => void;
  setPolling: (polling: boolean) => void;
}

export const useJobStore = create<JobState>()((set, get) => ({
  jobs: [],
  activeJobs: [],
  selectedJobId: null,
  isPolling: false,

  setJobs: (jobs) =>
    set({
      jobs,
      activeJobs: jobs.filter(
        (j) => j.status === 'pending' || j.status === 'processing'
      ),
    }),

  addJob: (job) =>
    set((state) => {
      const jobs = [job, ...state.jobs];
      return {
        jobs,
        activeJobs: jobs.filter(
          (j) => j.status === 'pending' || j.status === 'processing'
        ),
      };
    }),

  updateJob: (updatedJob) =>
    set((state) => {
      const jobs = state.jobs.map((job) =>
        job.id === updatedJob.id ? { ...job, ...updatedJob } : job
      );
      return {
        jobs,
        activeJobs: jobs.filter(
          (j) => j.status === 'pending' || j.status === 'processing'
        ),
      };
    }),

  removeJob: (jobId) =>
    set((state) => {
      const jobs = state.jobs.filter((j) => j.id !== jobId);
      return {
        jobs,
        activeJobs: jobs.filter(
          (j) => j.status === 'pending' || j.status === 'processing'
        ),
        selectedJobId:
          state.selectedJobId === jobId ? null : state.selectedJobId,
      };
    }),

  setSelectedJobId: (selectedJobId) => set({ selectedJobId }),

  setPolling: (isPolling) => set({ isPolling }),
}));
