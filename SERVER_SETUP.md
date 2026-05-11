# Запуск на сервере по IP

Инструкция для MVP без домена: Laravel API и Reverb работают по IP-адресу сервера. Desktop-приложение подключается к `http://SERVER_IP` и `ws://SERVER_IP:8080`.

## 1. Подготовить сервер

Пример для Ubuntu:

```bash
sudo apt update
sudo apt install -y nginx sqlite3 supervisor unzip git curl
sudo apt install -y php php-cli php-fpm php-sqlite3 php-mbstring php-xml php-curl php-zip php-bcmath
```

Поставить Composer, если его нет:

```bash
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
php composer-setup.php
sudo mv composer.phar /usr/local/bin/composer
rm composer-setup.php
```

## 2. Загрузить проект

```bash
cd /var/www
sudo git clone <repo-url> work_app
sudo chown -R $USER:www-data work_app
cd work_app
composer install --no-dev --optimize-autoloader
```

Если проекта нет в git, можно загрузить архивом и распаковать в `/var/www/work_app`.

## 3. Настроить `.env`

```bash
cp .env.example .env
php artisan key:generate
```

Минимальные значения:

```env
APP_ENV=production
APP_DEBUG=false
APP_URL=http://SERVER_IP

DB_CONNECTION=sqlite

BROADCAST_CONNECTION=reverb
QUEUE_CONNECTION=database
CACHE_STORE=database
SESSION_DRIVER=database

REVERB_APP_ID=local
REVERB_APP_KEY=local
REVERB_APP_SECRET=local
REVERB_HOST=SERVER_IP
REVERB_PORT=8080
REVERB_SCHEME=http
```

Создать SQLite-базу и миграции:

```bash
touch database/database.sqlite
php artisan migrate --seed --force
php artisan config:cache
php artisan route:cache
```

## 4. Настроить Nginx

Создать конфиг:

```bash
sudo nano /etc/nginx/sites-available/work_app
```

Пример без домена:

```nginx
server {
    listen 80;
    server_name SERVER_IP;
    root /var/www/work_app/public;

    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php-fpm.sock;
    }

    location ~ /\.(?!well-known).* {
        deny all;
    }
}
```

Если сокет PHP-FPM другой, проверить:

```bash
ls /run/php/
```

Включить сайт:

```bash
sudo ln -s /etc/nginx/sites-available/work_app /etc/nginx/sites-enabled/work_app
sudo nginx -t
sudo systemctl reload nginx
```

Проверка:

```bash
curl http://SERVER_IP/up
```

## 5. Запустить queue, scheduler и Reverb

Создать supervisor-конфиг:

```bash
sudo nano /etc/supervisor/conf.d/work_app.conf
```

Пример:

```ini
[program:work-app-queue]
command=php /var/www/work_app/artisan queue:work --sleep=3 --tries=3 --timeout=90
directory=/var/www/work_app
autostart=true
autorestart=true
user=www-data
redirect_stderr=true
stdout_logfile=/var/www/work_app/storage/logs/queue.log

[program:work-app-scheduler]
command=php /var/www/work_app/artisan schedule:work
directory=/var/www/work_app
autostart=true
autorestart=true
user=www-data
redirect_stderr=true
stdout_logfile=/var/www/work_app/storage/logs/scheduler.log

[program:work-app-reverb]
command=php /var/www/work_app/artisan reverb:start --host=0.0.0.0 --port=8080
directory=/var/www/work_app
autostart=true
autorestart=true
user=www-data
redirect_stderr=true
stdout_logfile=/var/www/work_app/storage/logs/reverb.log
```

Запустить:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status
```

## 6. Открыть порты

Если включен firewall:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 8080/tcp
sudo ufw status
```

Порты:

- `80` - Laravel API по HTTP.
- `8080` - Reverb WebSocket по WS.

## 7. Настройки desktop-приложения

В форме приложения указать:

- Server URL: `http://SERVER_IP`
- Reverb host: `SERVER_IP`
- Reverb port: `8080`
- Scheme: `http/ws`
- Invite code: код комнаты, например `DEMO-TEAM` или созданный в приложении.

Для текущего MVP без домена и HTTPS это нормально. Для публичного продукта лучше перейти на домен и HTTPS/WSS.

## 8. Быстрая проверка API

Создать/войти через invite code:

```bash
curl -X POST http://SERVER_IP/api/join \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "invite_code": "DEMO-TEAM",
    "device_name": "Linux laptop",
    "platform": "linux",
    "hostname": "test"
  }'
```

В ответе должен быть `device_token`.

Проверить heartbeat:

```bash
curl -X POST http://SERVER_IP/api/presence/heartbeat \
  -H "Accept: application/json" \
  -H "Authorization: Bearer DEVICE_TOKEN"
```

## Что потом

После проверки по IP стоит сделать:

1. Купить или подключить домен.
2. Настроить HTTPS через Let’s Encrypt.
3. Перевести Reverb на WSS.
4. Закрыть прямой порт `8080` наружу и проксировать WebSocket через Nginx.
5. Поменять в desktop-приложении настройки на:
   - Server URL: `https://your-domain.com`
   - Reverb host: `your-domain.com`
   - Reverb port: `443`
   - Scheme: `https/wss`
6. Заменить `REVERB_APP_KEY`, `REVERB_APP_SECRET` и `APP_KEY` на уникальные production-значения.
7. Собрать Tauri-приложение под Windows/Linux и раздать установщики.
8. Добавить нормальное управление комнатами: список комнат, удаление, роли, админ.
9. Добавить ограничение invite code: срок действия, одноразовые коды или лимит участников.
10. Добавить логирование ошибок и мониторинг процессов supervisor.

Для production-деплоя с доменом лучше использовать HTTPS/WSS сразу, потому что браузеры и desktop webview строже относятся к небезопасным соединениям.
