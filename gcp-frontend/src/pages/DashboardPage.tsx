import { Link } from 'react-router-dom';
import {
  DocumentTextIcon,
  FolderIcon,
  ClockIcon,
  CheckCircleIcon,
  ArrowUpTrayIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';
import { useJobStore } from '../store/jobStore';
import { useAuthStore } from '../store/authStore';

export const DashboardPage = () => {
  const { user } = useAuthStore();
  const { jobs, activeJobs } = useJobStore();

  const completedJobs = jobs.filter((j) => j.status === 'completed');
  const recentJobs = jobs.slice(0, 5);

  const stats = [
    {
      name: 'Files Processed',
      value: completedJobs.length.toString(),
      icon: DocumentTextIcon,
      color: 'bg-blue-500',
    },
    {
      name: 'Active Jobs',
      value: activeJobs.length.toString(),
      icon: CpuChipIcon,
      color: 'bg-yellow-500',
    },
    {
      name: 'Total Pages',
      value: completedJobs
        .reduce((acc, j) => acc + (j.input.pageCount || 0), 0)
        .toLocaleString(),
      icon: FolderIcon,
      color: 'bg-green-500',
    },
    {
      name: 'Storage Used',
      value: '2.3 GB',
      icon: ClockIcon,
      color: 'bg-purple-500',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome section */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl p-6 text-white">
        <h1 className="text-2xl font-bold">
          Welcome back, {user?.displayName?.split(' ')[0] || 'there'}!
        </h1>
        <p className="mt-1 text-primary-100">
          Ready to convert more PDFs? Upload files or browse your documents.
        </p>
        <div className="mt-4 flex space-x-3">
          <Link
            to="/browse?upload=true"
            className="inline-flex items-center px-4 py-2 bg-white text-primary-700 text-sm font-medium rounded-lg hover:bg-primary-50"
          >
            <ArrowUpTrayIcon className="w-4 h-4 mr-2" />
            Upload Files
          </Link>
          <Link
            to="/browse"
            className="inline-flex items-center px-4 py-2 bg-primary-500 text-white text-sm font-medium rounded-lg hover:bg-primary-400"
          >
            <FolderIcon className="w-4 h-4 mr-2" />
            Browse Files
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="card p-4">
              <div className="flex items-center">
                <div className={`${stat.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">{stat.name}</p>
                  <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent jobs */}
        <div className="card">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Jobs</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {recentJobs.length > 0 ? (
              recentJobs.map((job) => (
                <div key={job.id} className="p-4 flex items-center">
                  <div
                    className={`w-2 h-2 rounded-full mr-3 ${
                      job.status === 'completed'
                        ? 'bg-green-500'
                        : job.status === 'processing'
                        ? 'bg-yellow-500'
                        : job.status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-gray-400'
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {job.input.fileName}
                    </p>
                    <p className="text-xs text-gray-500">
                      {job.input.pageCount} pages • {job.output.format}
                    </p>
                  </div>
                  <div className="text-xs text-gray-500">
                    {job.status === 'processing' ? (
                      <span className="text-yellow-600">{job.progress.percentage}%</span>
                    ) : (
                      <span className="capitalize">{job.status}</span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-gray-500">
                <DocumentTextIcon className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>No jobs yet</p>
                <p className="text-sm">Upload a PDF to get started</p>
              </div>
            )}
          </div>
          {recentJobs.length > 0 && (
            <div className="p-4 border-t border-gray-200">
              <Link
                to="/processing"
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                View all jobs →
              </Link>
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="card">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Quick Actions</h2>
          </div>
          <div className="p-4 grid grid-cols-2 gap-4">
            <Link
              to="/browse/input"
              className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
            >
              <FolderIcon className="w-8 h-8 text-primary-600 mb-2" />
              <span className="text-sm font-medium text-gray-900">Input Folder</span>
            </Link>
            <Link
              to="/browse/output"
              className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
            >
              <CheckCircleIcon className="w-8 h-8 text-green-600 mb-2" />
              <span className="text-sm font-medium text-gray-900">Output Folder</span>
            </Link>
            <Link
              to="/processing"
              className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
            >
              <CpuChipIcon className="w-8 h-8 text-yellow-600 mb-2" />
              <span className="text-sm font-medium text-gray-900">Processing Queue</span>
            </Link>
            <Link
              to="/settings"
              className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
            >
              <ClockIcon className="w-8 h-8 text-purple-600 mb-2" />
              <span className="text-sm font-medium text-gray-900">Settings</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
