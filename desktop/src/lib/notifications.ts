import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification';

import type { PresenceEvent } from '../types';

export async function notifyMemberPresence(event: PresenceEvent): Promise<void> {
  if (!('__TAURI_INTERNALS__' in window)) {
    return;
  }

  let permissionGranted = await isPermissionGranted();

  if (!permissionGranted) {
    const permission = await requestPermission();
    permissionGranted = permission === 'granted';
  }

  if (!permissionGranted) {
    return;
  }

  sendNotification({
    title: event.type === 'online' ? `${event.user.name} online` : `${event.user.name} offline`,
    body:
      event.device.name ??
      (event.type === 'online' ? 'Teammate is active' : 'Teammate left the room'),
  });
}
