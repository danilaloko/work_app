import type { AppConfig, HeartbeatResponse, JoinResponse } from '../types';

function apiUrl(config: AppConfig, path: string): string {
  return `${config.serverUrl.replace(/\/$/, '')}${path}`;
}

async function parseJson<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message = payload?.message ?? 'Request failed';
    throw new Error(message);
  }

  return payload as T;
}

export async function joinTeam(config: AppConfig): Promise<JoinResponse> {
  const response = await fetch(apiUrl(config, '/api/join'), {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: config.name,
      invite_code: config.inviteCode,
      device_uuid: config.deviceUuid,
      device_name: config.deviceName,
      platform: navigator.platform,
      hostname: config.deviceName,
    }),
  });

  return parseJson<JoinResponse>(response);
}

export async function createRoom(config: AppConfig): Promise<JoinResponse> {
  const response = await fetch(apiUrl(config, '/api/rooms'), {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: config.name,
      invite_code: config.inviteCode,
      device_uuid: config.deviceUuid,
      device_name: config.deviceName,
      platform: navigator.platform,
      hostname: config.deviceName,
    }),
  });

  return parseJson<JoinResponse>(response);
}

export async function sendHeartbeat(config: AppConfig): Promise<HeartbeatResponse> {
  if (!config.deviceToken) {
    throw new Error('Device token is missing');
  }

  const response = await fetch(apiUrl(config, '/api/presence/heartbeat'), {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${config.deviceToken}`,
    },
  });

  return parseJson<HeartbeatResponse>(response);
}
