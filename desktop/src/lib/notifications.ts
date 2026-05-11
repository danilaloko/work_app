import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification';

import type { PresenceEvent } from '../types';

export async function notifyMemberOnline(event: PresenceEvent): Promise<void> {
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
    title: `${event.user.name} online`,
    body: event.device.name ? `${event.device.name} is active` : 'Teammate is active',
  });
}
