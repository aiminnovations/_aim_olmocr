import React, { useState, useCallback } from 'react';
import {
  XMarkIcon,
  FolderIcon,
  DocumentTextIcon,
  CodeBracketIcon,
  GlobeAltIcon,
  TableCellsIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { FileItem, OutputSettings } from '../../types/file';

interface OutputSelectorProps {
  selectedFiles: FileItem[];
  onClose: () => void;
  onConfirm: (settings: OutputSettings) => void;
  defaultSettings?: Partial<OutputSettings>;
}

const outputFormats = [
  {
    id: 'markdown' as const,
    name: 'Markdown',
    description: 'Clean markdown with LaTeX equations and HTML tables',
    icon: DocumentTextIcon,
    extension: '.md',
  },
  {
    id: 'json' as const,
    name: 'JSON (Dolma)',
    description: 'Structured JSON with metadata and attributes',
    icon: CodeBracketIcon,
    extension: '.jsonl',
  },
  {
    id: 'html' as const,
    name: 'HTML',
    description: 'Formatted HTML with styling',
    icon: GlobeAltIcon,
    extension: '.html',
  },
  {
    id: 'dolma' as const,
    name: 'Dolma Dataset',
    description: 'Full Dolma format with page attributes',
    icon: TableCellsIcon,
    extension: '.jsonl.gz',
  },
];

export const OutputSelector: React.FC<OutputSelectorProps> = ({
  selectedFiles,
  onClose,
  onConfirm,
  defaultSettings,
}) => {
  const [settings, setSettings] = useState<OutputSettings>({
    path: defaultSettings?.path || 'output',
    format: defaultSettings?.format || 'markdown',
    includeMetadata: defaultSettings?.includeMetadata ?? true,
    preserveFolderStructure: defaultSettings?.preserveFolderStructure ?? true,
  });

  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [customPath, setCustomPath] = useState(settings.path);

  const handlePathChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setCustomPath(e.target.value);
  }, []);

  const handlePathBlur = useCallback(() => {
    setSettings(s => ({ ...s, path: customPath }));
  }, [customPath]);

  const handleFormatChange = useCallback((format: OutputSettings['format']) => {
    setSettings(s => ({ ...s, format }));
  }, []);

  const handleSubmit = useCallback(() => {
    onConfirm(settings);
  }, [settings, onConfirm]);

  const totalPages = selectedFiles.reduce((sum, file) => {
    // Estimate pages - in real app, this would come from metadata
    return sum + 1;
  }, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Process {selectedFiles.length} PDF{selectedFiles.length > 1 ? 's' : ''}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Output path */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Output Location
            </label>
            <div className="flex items-center space-x-2">
              <div className="flex-1 relative">
                <FolderIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={customPath}
                  onChange={handlePathChange}
                  onBlur={handlePathBlur}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter output path..."
                />
              </div>
              <button
                onClick={() => setShowFolderPicker(true)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Browse...
              </button>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Output will be saved to: gs://olmocr-bucket/{settings.path}/
            </p>
          </div>

          {/* Output format */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Output Format
            </label>
            <div className="grid grid-cols-2 gap-3">
              {outputFormats.map((format) => {
                const Icon = format.icon;
                const isSelected = settings.format === format.id;

                return (
                  <button
                    key={format.id}
                    onClick={() => handleFormatChange(format.id)}
                    className={clsx(
                      'flex items-start p-3 text-left border rounded-lg transition-colors',
                      isSelected
                        ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-500'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    )}
                  >
                    <Icon className={clsx(
                      'w-5 h-5 mt-0.5 mr-3',
                      isSelected ? 'text-blue-600' : 'text-gray-400'
                    )} />
                    <div>
                      <div className={clsx(
                        'font-medium text-sm',
                        isSelected ? 'text-blue-900' : 'text-gray-900'
                      )}>
                        {format.name}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {format.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Options */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              Options
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={settings.includeMetadata}
                onChange={(e) => setSettings(s => ({
                  ...s,
                  includeMetadata: e.target.checked
                }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">
                Include metadata (page count, tokens, processing time)
              </span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={settings.preserveFolderStructure}
                onChange={(e) => setSettings(s => ({
                  ...s,
                  preserveFolderStructure: e.target.checked
                }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">
                Preserve folder structure from input
              </span>
            </label>
          </div>

          {/* Summary */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-gray-500">Files</div>
                <div className="font-medium">{selectedFiles.length}</div>
              </div>
              <div>
                <div className="text-gray-500">Est. Pages</div>
                <div className="font-medium">~{totalPages}</div>
              </div>
              <div>
                <div className="text-gray-500">Est. Cost</div>
                <div className="font-medium">~${(totalPages * 0.0002).toFixed(4)}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t border-gray-200 space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
          >
            Start Processing
          </button>
        </div>
      </div>
    </div>
  );
};

export default OutputSelector;
