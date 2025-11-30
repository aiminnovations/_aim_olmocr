import { NavLink, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  FolderIcon,
  CpuChipIcon,
  Cog6ToothIcon,
  DocumentArrowUpIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { useJobStore } from '../../store/jobStore';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Browse Files', href: '/browse', icon: FolderIcon },
  { name: 'Processing', href: '/processing', icon: CpuChipIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

export const Sidebar = () => {
  const location = useLocation();
  const { activeJobs } = useJobStore();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-[calc(100vh-4rem)]">
      <nav className="p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = location.pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={clsx(
                'flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-700 hover:bg-gray-100'
              )}
            >
              <Icon
                className={clsx(
                  'w-5 h-5 mr-3',
                  isActive ? 'text-primary-600' : 'text-gray-400'
                )}
              />
              {item.name}
              {item.name === 'Processing' && activeJobs.length > 0 && (
                <span className="ml-auto inline-flex items-center justify-center w-5 h-5 text-xs font-medium text-white bg-primary-600 rounded-full">
                  {activeJobs.length}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Quick upload */}
      <div className="p-4 border-t border-gray-200">
        <NavLink
          to="/browse?upload=true"
          className="flex items-center justify-center w-full px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
        >
          <DocumentArrowUpIcon className="w-5 h-5 mr-2" />
          Upload Files
        </NavLink>
      </div>

      {/* Storage info */}
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 mb-2">Storage Used</div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-primary-600 h-2 rounded-full"
            style={{ width: '23%' }}
          ></div>
        </div>
        <div className="text-xs text-gray-500 mt-1">2.3 GB of 10 GB</div>
      </div>
    </aside>
  );
};

export default Sidebar;
