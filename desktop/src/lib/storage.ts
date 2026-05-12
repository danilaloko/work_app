import type { AppConfig } from '../types';

const STORAGE_KEY = 'presence.desktop.config';

export function createDeviceUuid(): string {
  return crypto.randomUUID();
}

export function defaultConfig(): AppConfig {
  return {
    serverUrl: 'http://31.130.151.42',
    reverbKey: 'local',
    reverbHost: '31.130.151.42',
    reverbPort: '8080',
    reverbScheme: 'http',
    name: '',
    inviteCode: 'DEMO-TEAM',
    deviceName: navigator.userAgent.includes('Linux') ? 'Linux laptop' : 'Work laptop',
    deviceUuid: createDeviceUuid(),
    roomOverlayAlwaysOn: false,
  };
}

export function loadConfig(): AppConfig {
  const raw = localStorage.getItem(STORAGE_KEY);

  if (!raw) {
    return defaultConfig();
  }

  return {
    ...defaultConfig(),
    ...JSON.parse(raw),
  };
}

export function saveConfig(config: AppConfig): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

export function clearDeviceSession(config: AppConfig): AppConfig {
  const next = {
    ...config,
    deviceToken: undefined,
    teamId: undefined,
    teamName: undefined,
    userId: undefined,
  };

  saveConfig(next);

  return next;
}
