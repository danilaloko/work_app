import { enable, isEnabled } from '@tauri-apps/plugin-autostart';
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';

import { createRoom, joinTeam } from './lib/api';
import { closeRoomStatusOverlay, showRoomStatusOverlay } from './lib/overlay';
import { PresenceClient } from './lib/presence';
import { clearDeviceSession, loadConfig, saveConfig } from './lib/storage';
import type { AppConfig, PresenceEvent } from './types';

function isTauri(): boolean {
  return '__TAURI_INTERNALS__' in window;
}

function isOverlayRoute(): boolean {
  return window.location.hash.startsWith('#overlay') || window.location.hash.startsWith('#room-overlay');
}

function eventStateLabel(event: PresenceEvent): string {
  return event.type === 'online' ? 'в сети' : 'вышел из сети';
}

function OverlayView() {
  const params = new URLSearchParams(window.location.hash.split('?')[1] ?? '');
  const name = params.get('name') || 'Участник';
  const avatar = params.get('avatar') || '';
  const state = params.get('state') === 'offline' ? 'offline' : 'online';
  const initials = name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <main className="overlay-window">
      <div className="avatar">
        {avatar ? <img src={avatar} alt="" /> : <span>{initials}</span>}
      </div>
      <strong>{name}</strong>
      <span>{state === 'online' ? 'в сети' : 'вышел из сети'}</span>
    </main>
  );
}

function RoomStatusOverlayView() {
  const params = new URLSearchParams(window.location.hash.split('?')[1] ?? '');
  const room = params.get('room') || 'Комната';
  const status = params.get('status') || 'Не подключено';
  const connected = params.get('connected') === '1';
  const lastName = params.get('lastName') || '';
  const lastState = params.get('lastState') === 'offline' ? 'offline' : 'online';
  const lastDevice = params.get('lastDevice') || '';

  return (
    <main className="room-overlay-window">
      <span className={connected ? 'room-overlay-dot online' : 'room-overlay-dot'} />
      <div>
        <p className="room-overlay-label">Комната</p>
        <strong>{room}</strong>
        <span>{status}</span>
      </div>
      {lastName && (
        <p className="room-overlay-event">
          {lastName} {lastState === 'online' ? 'в сети' : 'вышел'}
          {lastDevice ? ` · ${lastDevice}` : ''}
        </p>
      )}
    </main>
  );
}

export default function App() {
  const [config, setConfig] = useState<AppConfig>(() => loadConfig());
  const [status, setStatus] = useState('Не подключено');
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<PresenceEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autostartEnabled, setAutostartEnabled] = useState(false);
  const clientRef = useRef<PresenceClient | null>(null);

  const hasSession = Boolean(config.deviceToken && config.teamId);
  const canSubmit = useMemo(() => Boolean(config.name && config.inviteCode && config.serverUrl), [config]);
  const latestEvent = events[0];

  useEffect(() => {
    if (isOverlayRoute()) {
      return;
    }

    if (!hasSession) {
      return;
    }

    const client = new PresenceClient(config, {
      onStatus: (next) => {
        setConnected(next.connected);
        setStatus(next.connected ? 'Подключено' : next.message);
      },
      onEvent: (event) => {
        setEvents((current) => [event, ...current].slice(0, 10));
      },
    });

    client.connect();
    clientRef.current = client;

    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, [config, hasSession]);

  useEffect(() => {
    if (!isTauri() || isOverlayRoute()) {
      return;
    }

    void isEnabled().then(setAutostartEnabled).catch(() => setAutostartEnabled(false));
  }, []);

  useEffect(() => {
    if (isOverlayRoute()) {
      return;
    }

    if (!config.roomOverlayAlwaysOn || !hasSession) {
      void closeRoomStatusOverlay();
      return;
    }

    void showRoomStatusOverlay(config, connected, status, latestEvent);
  }, [config, connected, hasSession, latestEvent, status]);

  if (window.location.hash.startsWith('#overlay')) {
    return <OverlayView />;
  }

  if (window.location.hash.startsWith('#room-overlay')) {
    return <RoomStatusOverlayView />;
  }

  async function handleJoin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const response = await joinTeam(config);
      saveSession(response);
      setStatus('Вы вошли в комнату');
    } catch (joinError) {
      setError(joinError instanceof Error ? joinError.message : 'Не удалось войти в комнату');
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateRoom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const response = await createRoom(config);
      saveSession(response);
      setStatus('Комната создана');
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Не удалось создать комнату');
    } finally {
      setBusy(false);
    }
  }

  function saveSession(response: Awaited<ReturnType<typeof joinTeam>>) {
    const next = {
      ...config,
      deviceToken: response.device_token,
      teamId: response.team.id,
      teamName: response.team.name,
      userId: response.user.id,
    };

    saveConfig(next);
    setConfig(next);
  }

  async function handleEnableAutostart() {
    if (!isTauri()) {
      setError('Автозапуск доступен только в desktop-приложении.');
      return;
    }

    try {
      await enable();
      setAutostartEnabled(await isEnabled());
    } catch (autostartError) {
      setError(autostartError instanceof Error ? autostartError.message : 'Не удалось включить автозапуск');
    }
  }

  function updateConfig(patch: Partial<AppConfig>) {
    const next = { ...config, ...patch };
    saveConfig(next);
    setConfig(next);
  }

  function resetSession() {
    clientRef.current?.disconnect();
    void closeRoomStatusOverlay();
    setEvents([]);
    setConnected(false);
    setStatus('Не подключено');
    setConfig(clearDeviceSession(config));
  }

  return (
    <main className="app-shell">
      <section className="panel">
        <div className="header">
          <div>
            <p className="eyebrow">Presence Desktop</p>
            <h1>Совместная работа за ноутом</h1>
          </div>
          <span className={connected ? 'status online' : 'status'}>{status}</span>
        </div>

        {!hasSession && (
          <div className="room-grid">
            <form onSubmit={handleJoin} className="room-card">
              <div>
                <h2>Войти</h2>
                <p className="muted">Подключиться к уже созданной комнате по invite code.</p>
              </div>
              <label>
                Имя
                <input value={config.name} onChange={(event) => updateConfig({ name: event.target.value })} />
              </label>
              <label>
                Invite code
                <input
                  value={config.inviteCode}
                  onChange={(event) => updateConfig({ inviteCode: event.target.value })}
                />
              </label>
              <button type="submit" disabled={!canSubmit || busy}>
                Войти
              </button>
            </form>

            <form onSubmit={handleCreateRoom} className="room-card accent">
              <div>
                <h2>Создать комнату</h2>
                <p className="muted">Придумай invite code и передай его другому человеку.</p>
              </div>
              <label>
                Имя
                <input value={config.name} onChange={(event) => updateConfig({ name: event.target.value })} />
              </label>
              <label>
                Invite code
                <input
                  value={config.inviteCode}
                  onChange={(event) => updateConfig({ inviteCode: event.target.value })}
                />
              </label>
              <button type="submit" disabled={!canSubmit || busy}>
                Создать комнату
              </button>
            </form>
          </div>
        )}

        <div className="actions">
          <button type="button" className="secondary" onClick={resetSession}>
            Сбросить сессию
          </button>
          <button type="button" className="secondary" onClick={handleEnableAutostart}>
            {autostartEnabled ? 'Автозапуск включен' : 'Включить автозапуск'}
          </button>
        </div>

        {error && <p className="error">{error}</p>}

        <div className="settings-card">
          <h2>Настройки</h2>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={config.roomOverlayAlwaysOn}
              onChange={(event) => updateConfig({ roomOverlayAlwaysOn: event.target.checked })}
            />
            <span>
              <strong>Постоянный оверлей комнаты</strong>
              <small>Показывает статус комнаты поверх окон. Входы и выходы участников всё равно всплывают отдельно.</small>
            </span>
          </label>
        </div>

        {hasSession && (
          <div className="session">
            <strong>Вы в комнате: {config.teamName}</strong>
            <span>Токен устройства сохранен локально. Heartbeat отправляется каждые 25 секунд.</span>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Последние события</h2>
        {events.length === 0 ? (
          <p className="muted">Пока нет событий от других участников.</p>
        ) : (
          <ul className="events">
            {events.map((event) => (
              <li key={`${event.user.id}-${event.device.id}-${event.type}-${event.device.online_at ?? event.device.offline_at}`}>
                <strong>{event.user.name}</strong>
                <span>
                  {event.device.name ?? event.device.hostname ?? 'Неизвестное устройство'} {eventStateLabel(event)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
