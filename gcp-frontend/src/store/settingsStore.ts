import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UserSettings {
  defaultInputPath: string;
  defaultOutputPath: string;
  defaultOutputFormat: 'markdown' | 'json' | 'html' | 'dolma';
  emailNotifications: boolean;
  theme: 'light' | 'dark' | 'system';
}

interface SettingsState {
  settings: UserSettings;
  isLoaded: boolean;

  // Actions
  setSettings: (settings: Partial<UserSettings>) => void;
  resetSettings: () => void;
  setLoaded: (loaded: boolean) => void;
}

const defaultSettings: UserSettings = {
  defaultInputPath: 'input',
  defaultOutputPath: 'output',
  defaultOutputFormat: 'markdown',
  emailNotifications: true,
  theme: 'system',
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      settings: defaultSettings,
      isLoaded: false,

      setSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        })),

      resetSettings: () => set({ settings: defaultSettings }),

      setLoaded: (isLoaded) => set({ isLoaded }),
    }),
    {
      name: 'settings-storage',
    }
  )
);
