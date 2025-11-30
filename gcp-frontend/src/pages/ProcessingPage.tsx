import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { processingApi } from '../services/api';
import { useJobStore } from '../store/jobStore';
import {
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  DocumentTextIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { format } from 'date-fns';

const statusConfig = {
  pending: {
    icon: ClockIcon,
    color: 'text-gray-500',
    bg: 'bg-gray-100',
    label: 'Pending',
  },
  processing: {
    icon: ArrowPathIcon,
    color: 'text-yellow-600',
    bg: 'bg-yellow-100',
    label: 'Processing',
  },
  completed: {
    icon: CheckCircleIcon,
    color: 'text-green-600',
    bg: 'bg-green-100',
    label: 'Completed',
  },
  failed: {
    icon: XCircleIcon,
    color: 'text-red-600',
    bg: 'bg-red-100',
    label: 'Failed',
  },
  cancelled: {
    icon: XCircleIcon,
    color: 'text-gray-500',
    bg: 'bg-gray-100',
    label: 'Cancelled',
  },
};

export const ProcessingPage = () => {
  const { jobs, setJobs, activeJobs } = useJobStore();

  // Fetch jobs
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const response = await processingApi.list(1, 50);
      return response.data;
    },
    refetchInterval: activeJobs.length > 0 ? 5000 : false, // Poll if active jobs
  });

  useEffect(() => {
    if (data?.jobs) {
      setJobs(data.jobs);
    }
  }, [data, setJobs]);

  const handleCancel = async (jobId: string) => {
    try {
      await processingApi.cancel(jobId);
      refetch();
    } catch (error) {
      console.error('Failed to cancel job:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Processing Queue</h1>
          <p className="text-gray-500">
            {activeJobs.length} active job{activeJobs.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="btn-secondary"
          disabled={isLoading}
        >
          <ArrowPathIcon
            className={clsx('w-4 h-4 mr-2', isLoading && 'animate-spin')}
          />
          Refresh
        </button>
      </div>

      {/* Active jobs */}
      {activeJobs.length > 0 && (
        <div className="card">
          <div className="p-4 border-b border-gray-200 bg-yellow-50">
            <h2 className="font-semibold text-yellow-800">Active Processing</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {activeJobs.map((job) => {
              const status = statusConfig[job.status];
              const Icon = status.icon;

              return (
                <div key={job.id} className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center">
                      <DocumentTextIcon className="w-5 h-5 text-gray-400 mr-2" />
                      <span className="font-medium text-gray-900">
                        {job.input.fileName}
                      </span>
                    </div>
                    <button
                      onClick={() => handleCancel(job.id)}
                      className="text-red-600 hover:text-red-700 text-sm"
                    >
                      Cancel
                    </button>
                  </div>

                  {/* Progress bar */}
                  <div className="mb-2">
                    <div className="flex justify-between text-sm text-gray-500 mb-1">
                      <span>
                        Page {job.progress.current} of {job.progress.total}
                      </span>
                      <span>{job.progress.percentage}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${job.progress.percentage}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center text-xs text-gray-500">
                    <Icon
                      className={clsx('w-4 h-4 mr-1', status.color, {
                        'animate-spin': job.status === 'processing',
                      })}
                    />
                    <span>{status.label}</span>
                    <span className="mx-2">•</span>
                    <span>{job.output.format}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* All jobs */}
      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">All Jobs</h2>
        </div>

        {isLoading ? (
          <div className="p-8 text-center">
            <ArrowPathIcon className="w-8 h-8 text-gray-400 animate-spin mx-auto" />
            <p className="mt-2 text-gray-500">Loading jobs...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <DocumentTextIcon className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No processing jobs yet</p>
            <p className="text-sm">Upload and process a PDF to get started</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    File
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Pages
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Format
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Created
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {jobs.map((job) => {
                  const status = statusConfig[job.status];
                  const Icon = status.icon;

                  return (
                    <tr key={job.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center">
                          <DocumentTextIcon className="w-5 h-5 text-gray-400 mr-2" />
                          <span className="text-sm font-medium text-gray-900 truncate max-w-xs">
                            {job.input.fileName}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={clsx(
                            'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                            status.bg,
                            status.color
                          )}
                        >
                          <Icon
                            className={clsx('w-3 h-3 mr-1', {
                              'animate-spin': job.status === 'processing',
                            })}
                          />
                          {status.label}
                          {job.status === 'processing' &&
                            ` (${job.progress.percentage}%)`}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {job.input.pageCount || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 capitalize">
                        {job.output.format}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {format(new Date(job.createdAt), 'MMM d, HH:mm')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {job.status === 'completed' && job.output.files.length > 0 && (
                          <a
                            href="#"
                            className="text-primary-600 hover:text-primary-700 text-sm mr-3"
                          >
                            Download
                          </a>
                        )}
                        {(job.status === 'pending' || job.status === 'processing') && (
                          <button
                            onClick={() => handleCancel(job.id)}
                            className="text-red-600 hover:text-red-700 text-sm"
                          >
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProcessingPage;
