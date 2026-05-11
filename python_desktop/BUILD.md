# Python Desktop MVP

## Локальный запуск клиента

```bash
cd python_desktop
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

По умолчанию клиент подключается к:

- API: `http://31.130.151.42`
- WebSocket: `ws://31.130.151.42:8765/ws/presence`

Настройки и токен устройства хранятся в:

```text
~/.config/presence-desktop/config.json
```

## Запуск WebSocket-сервиса рядом с Laravel

На сервере:

```bash
cd /var/www/work_app/python_desktop
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ws_server.py --db /var/www/work_app/database/database.sqlite --host 0.0.0.0 --port 8765
```

Открыть порт:

```bash
sudo ufw allow 8765/tcp
```

Supervisor:

```ini
[program:presence-python-ws]
command=/var/www/work_app/python_desktop/.venv/bin/python /var/www/work_app/python_desktop/ws_server.py --db /var/www/work_app/database/database.sqlite --host 0.0.0.0 --port 8765
directory=/var/www/work_app/python_desktop
autostart=true
autorestart=true
user=www-data
redirect_stderr=true
stdout_logfile=/var/www/work_app/storage/logs/python-ws.log
```

## Сборка Linux

```bash
cd python_desktop
source .venv/bin/activate
pyinstaller --windowed --onefile --name presence-desktop app.py
```

Результат:

```text
python_desktop/dist/presence-desktop
```

## Сборка Windows

Собирать на Windows:

```powershell
cd python_desktop
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pyinstaller --windowed --onefile --name presence-desktop app.py
```

Результат:

```text
python_desktop\dist\presence-desktop.exe
```

## Проверка MVP

1. Запустить Laravel API на сервере.
2. Запустить `ws_server.py` на сервере.
3. Запустить первый клиент и создать комнату.
4. Запустить второй клиент и войти по invite code.
5. Первый клиент должен показать tray-уведомление и overlay.
6. После закрытия второго клиента первый должен получить `member_offline`.
