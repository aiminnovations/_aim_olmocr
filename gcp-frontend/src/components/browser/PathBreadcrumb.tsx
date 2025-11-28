import React, { useMemo } from 'react';
import { ChevronRightIcon, HomeIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { BreadcrumbItem } from '../../types/file';

interface PathBreadcrumbProps {
  path: string;
  onNavigate: (path: string) => void;
  maxItems?: number;
}

export const PathBreadcrumb: React.FC<PathBreadcrumbProps> = ({
  path,
  onNavigate,
  maxItems = 5,
}) => {
  const breadcrumbs = useMemo((): BreadcrumbItem[] => {
    if (!path) {
      return [{ name: 'Home', path: '' }];
    }

    const parts = path.split('/').filter(Boolean);
    const items: BreadcrumbItem[] = [{ name: 'Home', path: '' }];

    let currentPath = '';
    for (const part of parts) {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      items.push({ name: part, path: currentPath });
    }

    return items;
  }, [path]);

  // If too many items, show ellipsis
  const displayItems = useMemo(() => {
    if (breadcrumbs.length <= maxItems) {
      return breadcrumbs;
    }

    const first = breadcrumbs.slice(0, 1);
    const last = breadcrumbs.slice(-(maxItems - 2));

    return [
      ...first,
      { name: '...', path: '' },
      ...last,
    ];
  }, [breadcrumbs, maxItems]);

  return (
    <nav className="flex items-center space-x-1" aria-label="Breadcrumb">
      {displayItems.map((item, index) => (
        <React.Fragment key={item.path || `ellipsis-${index}`}>
          {index > 0 && (
            <ChevronRightIcon className="w-4 h-4 text-gray-400" />
          )}

          {item.name === '...' ? (
            <span className="px-2 text-sm text-gray-400">...</span>
          ) : (
            <button
              onClick={() => onNavigate(item.path)}
              className={clsx(
                'flex items-center px-2 py-1 text-sm rounded',
                'hover:bg-gray-200',
                index === displayItems.length - 1
                  ? 'font-medium text-gray-900'
                  : 'text-gray-600'
              )}
            >
              {index === 0 ? (
                <HomeIcon className="w-4 h-4" />
              ) : (
                item.name
              )}
            </button>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
};

export default PathBreadcrumb;
