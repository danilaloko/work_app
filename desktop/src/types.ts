export type AppConfig = {
  serverUrl: string;
  reverbKey: string;
  reverbHost: string;
  reverbPort: string;
  reverbScheme: 'http' | 'https';
  name: string;
  inviteCode: string;
  deviceName: string;
  deviceUuid: string;
  deviceToken?: string;
  teamId?: number;
  teamName?: string;
  userId?: number;
};

export type JoinResponse = {
  device_token: string;
  team: {
    id: number;
    name: string;
  };
  user: MemberUser;
  device: MemberDevice;
};

export type HeartbeatResponse = {
  status: 'online';
  last_seen_at: string;
  team: {
    id: number;
    name: string;
  };
  user: MemberUser;
  device: MemberDevice;
};

export type PresenceEvent = {
  team_id: number;
  user: MemberUser;
  device: MemberDevice & {
    last_seen_at?: string;
    online_at?: string;
    offline_at?: string;
  };
};

export type MemberUser = {
  id: number;
  name: string;
  avatar_url: string | null;
};

export type MemberDevice = {
  id: number;
  device_uuid: string;
  name: string | null;
  platform: string | null;
  hostname: string | null;
};
