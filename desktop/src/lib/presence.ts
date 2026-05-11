import Pusher, { type Channel } from 'pusher-js';

import { sendHeartbeat } from './api';
import { notifyMemberOnline } from './notifications';
import { showMemberOverlay } from './overlay';
import type { AppConfig, PresenceEvent } from '../types';

type PresenceStatus = {
  connected: boolean;
  message: string;
};

type PresenceClientOptions = {
  onStatus: (status: PresenceStatus) => void;
  onEvent: (event: PresenceEvent) => void;
};

export class PresenceClient {
  private pusher?: Pusher;

  private channel?: Channel;

  private heartbeatTimer?: number;

  constructor(
    private readonly config: AppConfig,
    private readonly options: PresenceClientOptions,
  ) {}

  connect(): void {
    if (!this.config.deviceToken || !this.config.teamId) {
      this.options.onStatus({ connected: false, message: 'Join a team first' });
      return;
    }

    this.disconnect();

    const forceTLS = this.config.reverbScheme === 'https';

    this.pusher = new Pusher(this.config.reverbKey, {
      wsHost: this.config.reverbHost,
      wsPort: Number(this.config.reverbPort),
      wssPort: Number(this.config.reverbPort),
      forceTLS,
      enabledTransports: forceTLS ? ['wss'] : ['ws'],
      cluster: 'mt1',
      authEndpoint: `${this.config.serverUrl.replace(/\/$/, '')}/api/broadcasting/auth`,
      auth: {
        headers: {
          Authorization: `Bearer ${this.config.deviceToken}`,
        },
      },
    });

    this.pusher.connection.bind('connected', () => {
      this.options.onStatus({ connected: true, message: 'Connected' });
    });

    this.pusher.connection.bind('disconnected', () => {
      this.options.onStatus({ connected: false, message: 'Disconnected' });
    });

    this.pusher.connection.bind('error', () => {
      this.options.onStatus({ connected: false, message: 'Connection error' });
    });

    this.channel = this.pusher.subscribe(`private-team.${this.config.teamId}`);
    this.channel.bind('member_online', (event: PresenceEvent) => {
      if (event.device.device_uuid === this.config.deviceUuid) {
        return;
      }

      this.options.onEvent(event);
      void notifyMemberOnline(event);
      void showMemberOverlay(event);
    });

    this.startHeartbeat();
  }

  disconnect(): void {
    if (this.heartbeatTimer) {
      window.clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = undefined;
    }

    if (this.channel && this.pusher) {
      this.pusher.unsubscribe(this.channel.name);
    }

    this.pusher?.disconnect();
    this.pusher = undefined;
    this.channel = undefined;
  }

  private startHeartbeat(): void {
    const pulse = async () => {
      try {
        await sendHeartbeat(this.config);
      } catch (error) {
        this.options.onStatus({
          connected: false,
          message: error instanceof Error ? error.message : 'Heartbeat failed',
        });
      }
    };

    void pulse();
    this.heartbeatTimer = window.setInterval(() => {
      void pulse();
    }, 25_000);
  }
}
