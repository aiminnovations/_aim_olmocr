import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { settingsApi } from '../services/api';
import { useSettingsStore } from '../store/settingsStore';
import { useAuthStore } from '../store/authStore';
import {
  UserCircleIcon,
  FolderIcon,
  DocumentTextIcon,
  BellIcon,
  PaintBrushIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

const outputFormats = [
  { id: 'markdown', name: 'Markdown', description: 'Clean markdown with LaTeX and tables' },
  { id: 'json', name: 'JSON', description: 'Structured JSON with metadata' },
  { id: 'html', name: 'HTML', description: 'Formatted HTML documents' },
  { id: 'dolma', name: 'Dolma', description: 'Full Dolma dataset format' },
];

const themes = [
  { id: 'light', name: 'Light' },
  { id: 'dark', name: 'Dark' },
  { id: 'system', name: 'System' },
];

export const SettingsPage = () => {
  const { user } = useAuthStore();
  const { settings, setSettings } = useSettingsStore();
  const [localSettings, setLocalSettings] = useState(settings);
  const [saved, setSaved] = useState(false);

  // Fetch settings from server
  const { data: serverSettings } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const response = await settingsApi.get();
      return response.data;
    },
  });

  // Update settings mutation
  const updateMutation = useMutation({
    mutationFn: async (newSettings: typeof localSettings) => {
      const response = await settingsApi.update(newSettings);
      return response.data;
    },
    onSuccess: (data) => {
      setSettings(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  useEffect(() => {
    if (serverSettings) {
      setLocalSettings(serverSettings);
      setSettings(serverSettings);
    }
  }, [serverSettings, setSettings]);

  const handleSave = () => {
    updateMutation.mutate(localSettings);
  };

  const hasChanges = JSON.stringify(localSettings) !== JSON.stringify(settings);

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500">Manage your account and preferences</p>
      </div>

      {/* Profile section */}
      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900 flex items-center">
            <UserCircleIcon className="w-5 h-5 mr-2 text-gray-400" />
            Profile
          </h2>
        </div>
        <div className="p-4">
          <div className="flex items-center">
            {user?.photoURL ? (
              <img
                src={user.photoURL}
                alt=""
                className="w-16 h-16 rounded-full"
              />
            ) : (
              <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center">
                <span className="text-2xl font-medium text-primary-600">
                  {user?.displayName?.[0] || user?.email?.[0] || '?'}
                </span>
              </div>
            )}
            <div className="ml-4">
              <p className="font-medium text-gray-900">
                {user?.displayName || 'No name set'}
              </p>
              <p className="text-sm text-gray-500">{user?.email}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Default paths */}
      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900 flex items-center">
            <FolderIcon className="w-5 h-5 mr-2 text-gray-400" />
            Default Paths
          </h2>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Default Input Folder
            </label>
            <input
              type="text"
              value={localSettings.defaultInputPath}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, defaultInputPath: e.target.value })
              }
              className="input"
              placeholder="input"
            />
            <p className="mt-1 text-xs text-gray-500">
              New uploads will go here by default
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Default Output Folder
            </label>
            <input
              type="text"
              value={localSettings.defaultOutputPath}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, defaultOutputPath: e.target.value })
              }
              className="input"
              placeholder="output"
            />
            <p className="mt-1 text-xs text-gray-500">
              Processed files will be saved here by default
            </p>
          </div>
        </div>
      </div>

      {/* Output format */}
      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900 flex items-center">
            <DocumentTextIcon className="w-5 h-5 mr-2 text-gray-400" />
            Default Output Format
          </h2>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-2 gap-3">
            {outputFormats.map((format) => (
              <button
                key={format.id}
                onClick={() =>
                  setLocalSettings({
                    ...localSettings,
                    defaultOutputFormat: format.id as any,
                  })
                }
                className={clsx(
                  'flex items-start p-3 text-left border rounded-lg transition-colors',
                  localSettings.defaultOutputFormat === format.id
                    ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <div>
                  <div className="font-medium text-sm text-gray-900">
                    {format.name}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {format.description}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900 flex items-center">
            <BellIcon className="w-5 h-5 mr-2 text-gray-400" />
            Notifications
          </h2>
        </div>
        <div className="p-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={localSettings.emailNotifications}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  emailNotifications: e.target.checked,
                })
              }
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="ml-2 text-sm text-gray-700">
              Email notifications for completed jobs
            </span>
          </label>
        </div>
      </div>

      {/* Appearance */}
      <div className="card">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900 flex items-center">
            <PaintBrushIcon className="w-5 h-5 mr-2 text-gray-400" />
            Appearance
          </h2>
        </div>
        <div className="p-4">
          <div className="flex space-x-3">
            {themes.map((theme) => (
              <button
                key={theme.id}
                onClick={() =>
                  setLocalSettings({ ...localSettings, theme: theme.id as any })
                }
                className={clsx(
                  'px-4 py-2 text-sm font-medium rounded-lg border transition-colors',
                  localSettings.theme === theme.id
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-200 text-gray-700 hover:border-gray-300'
                )}
              >
                {theme.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Save button */}
      <div className="flex items-center justify-end space-x-3">
        {saved && (
          <span className="flex items-center text-green-600 text-sm">
            <CheckIcon className="w-4 h-4 mr-1" />
            Settings saved
          </span>
        )}
        <button
          onClick={handleSave}
          disabled={!hasChanges || updateMutation.isPending}
          className={clsx(
            'btn-primary',
            (!hasChanges || updateMutation.isPending) && 'opacity-50 cursor-not-allowed'
          )}
        >
          {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  );
};

export default SettingsPage;
