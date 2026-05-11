import { WebviewWindow } from '@tauri-apps/api/webviewWindow';

import type { PresenceEvent } from '../types';

export async function showMemberOverlay(event: PresenceEvent): Promise<void> {
  if (!('__TAURI_INTERNALS__' in window)) {
    return;
  }

  const params = new URLSearchParams({
    name: event.user.name,
    avatar: event.user.avatar_url ?? '',
    device: event.device.name ?? '',
  });

  const label = `member-overlay-${event.user.id}-${Date.now()}`;
  const overlay = new WebviewWindow(label, {
    url: `/index.html#overlay?${params.toString()}`,
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
