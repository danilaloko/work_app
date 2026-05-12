import { WebviewWindow } from '@tauri-apps/api/webviewWindow';

import type { AppConfig, PresenceEvent } from '../types';

const ROOM_STATUS_OVERLAY_LABEL = 'room-status-overlay';

function overlayUrl(route: string, params: URLSearchParams): string {
  // В дополнительном окне относительные пути («/index.html…») часто дают «Load failed».
  const url = new URL(window.location.href);
  url.hash = `${route}?${params.toString()}`;

  return url.href;
}

export async function showMemberOverlay(event: PresenceEvent): Promise<void> {
  if (!('__TAURI_INTERNALS__' in window)) {
    return;
  }

  const params = new URLSearchParams({
    name: event.user.name,
    avatar: event.user.avatar_url ?? '',
    device: event.device.name ?? '',
    state: event.type,
  });

  const label = `member-overlay-${event.user.id}-${Date.now()}`;
  const overlay = new WebviewWindow(label, {
    url: overlayUrl('overlay', params),
    title: 'Presence Overlay',
    width: 220,
    height: 220,
    x: 40,
    y: 40,
    decorations: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    focus: false,
  });

  await overlay.once('tauri://created', () => undefined);

  window.setTimeout(() => {
    void overlay.close();
  }, 5000);
}

export async function showRoomStatusOverlay(
  config: AppConfig,
  connected: boolean,
  status: string,
  lastEvent?: PresenceEvent,
): Promise<void> {
  if (!('__TAURI_INTERNALS__' in window)) {
    return;
  }

  const existing = await WebviewWindow.getByLabel(ROOM_STATUS_OVERLAY_LABEL);
  await existing?.close();

  const params = new URLSearchParams({
    room: config.teamName ?? 'Комната',
    status,
    connected: connected ? '1' : '0',
    lastName: lastEvent?.user.name ?? '',
    lastState: lastEvent?.type ?? '',
    lastDevice: lastEvent?.device.name ?? lastEvent?.device.hostname ?? '',
  });

  const overlay = new WebviewWindow(ROOM_STATUS_OVERLAY_LABEL, {
    url: overlayUrl('room-overlay', params),
    title: 'Room Status Overlay',
    width: 320,
    height: 150,
    x: 40,
    y: 280,
    decorations: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    focus: false,
  });

  await overlay.once('tauri://created', () => undefined);
}

export async function closeRoomStatusOverlay(): Promise<void> {
  if (!('__TAURI_INTERNALS__' in window)) {
    return;
  }

  const existing = await WebviewWindow.getByLabel(ROOM_STATUS_OVERLAY_LABEL);
  await existing?.close();
}
