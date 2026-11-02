#!/data/data/com.termux/files/usr/bin/bash
echo "=========================================="
echo "  ☁️  CLOUDFLARE SETUP ДЛЯ TERMUX (auto-open)"
echo "=========================================="
echo ""

# Проверка termux-api
if command -v termux-open-url >/dev/null 2>&1; then
    echo "✅ termux-open-url найден — браузер откроется сам"
    AUTO_OPEN=1
else
    echo "⚠️  termux-open-url НЕ найден. Поставь: pkg install termux-api"
    echo "   (без него URL придётся открыть вручную)"
    AUTO_OPEN=0
fi
echo ""

# ---------- ШАГ 1: ЛОГИН ----------
echo "=== ШАГ 1/3: ЛОГИН В CLOUDFLARE ==="
echo "Сейчас cloudflared сгенерирует ссылку. Я её поймаю и открою в браузере."
echo "Тебе останется только нажать 'Authorize' в браузере."
echo ""
read -p "Нажми Enter, чтобы начать..."
echo ""

# Запускаем логин в фоне, ловим URL
LOGIN_LOG="$HOME/ai_arb/cf_login.log"
rm -f "$LOGIN_LOG"
cloudflared tunnel login > "$LOGIN_LOG" 2>&1 &
LOGIN_PID=$!

# Ждём появления URL в логе (макс 30 сек)
AUTH_URL=""
for i in $(seq 1 30); do
    AUTH_URL=$(grep -oE 'https://dash\.cloudflare\.com/argotunnel\?[^[:space:]]+' "$LOGIN_LOG" | head -1)
    [ -n "$AUTH_URL" ] && break
    sleep 1
done

if [ -z "$AUTH_URL" ]; then
    echo "❌ Не смог поймать URL за 30 секунд. Лог:"
    cat "$LOGIN_LOG"
    kill -9 $LOGIN_PID 2>/dev/null
    exit 1
fi

echo "🔗 Ссылка авторизации:"
echo "   $AUTH_URL"
echo ""

# Открываем автоматически
if [ "$AUTO_OPEN" = "1" ]; then
    echo "🌐 Открываю в браузере..."
    termux-open-url "$AUTH_URL" 2>/dev/null &
fi

echo ""
echo "⏳ Жду, пока ты нажмёшь 'Authorize' в браузере..."
echo "   (cloudflared ждёт до 15 минут. Если браузер не открылся — открой ссылку вручную)"
echo ""

# Ждём завершения cloudflared (с таймаутом 15 минут)
WAITED=0
while kill -0 $LOGIN_PID 2>/dev/null; do
    sleep 5
    WAITED=$((WAITED + 5))
    if [ $WAITED -ge 900 ]; then
        echo "❌ Прошло 15 минут — авторизация не завершена. Останавливаю."
        kill -9 $LOGIN_PID 2>/dev/null
        exit 1
    fi
    # Каждые 30 сек напоминаем
    if [ $((WAITED % 30)) -eq 0 ]; then
        echo "   ... ждём ($WAITED сек) — нажми 'Authorize' в браузере"
    fi
done

# Проверяем успех по наличию cert.pem
if [ -f "$HOME/.cloudflared/cert.pem" ]; then
    echo "✅ Авторизация успешна! (cert.pem создан)"
else
    echo "❌ Авторизация не завершена. Лог:"
    tail -20 "$LOGIN_LOG"
    exit 1
fi
echo ""

# ---------- ШАГ 2: ТУННЕЛЬ ----------
echo "=== ШАГ 2/3: СОЗДАНИЕ ТУННЕЛЯ ==="
read -p "Имя туннеля [termux-bot]: " tunnel_name
tunnel_name=${tunnel_name:-termux-bot}
cloudflared tunnel create "$tunnel_name" 2>&1 | head -5 || echo "(туннель уже существует)"
echo ""

read -p "Твой домен (например, example.com): " domain
[ -z "$domain" ] && echo "❌ Домен обязателен" && exit 1
read -p "Поддомен (например, bot): " subdomain
[ -z "$subdomain" ] && echo "❌ Поддомен обязателен" && exit 1
full_domain="${subdomain}.${domain}"

echo ""
echo "🌐 Создаю DNS-запись: $full_domain → туннель '$tunnel_name'"
cloudflared tunnel route dns "$tunnel_name" "$full_domain" 2>&1 | head -3 || echo "(DNS уже существует)"
echo ""

# ---------- ШАГ 3: ЗАПУСК ----------
echo "=== ШАГ 3/3: ЗАПУСК ТУННЕЛЯ В ФОНЕ ==="
read -p "Локальный порт скрипта [8000]: " local_port
local_port=${local_port:-8000}

nohup cloudflared tunnel --url "http://localhost:$local_port" run "$tunnel_name" > "$HOME/ai_arb/cloudflared.log" 2>&1 &
echo $! > "$HOME/ai_arb/cloudflared.pid"
sleep 3

if ps -p $(cat "$HOME/ai_arb/cloudflared.pid") >/dev/null 2>&1; then
    echo "✅ Туннель запущен (PID: $(cat $HOME/ai_arb/cloudflared.pid))"
    echo ""
    echo "=========================================="
    echo "  ✅ ГОТОВО"
    echo "=========================================="
    echo "🌐 Публичный адрес: https://$full_domain"
    echo "   Он проксирует → http://localhost:$local_port"
    echo ""
    echo "Управление:"
    echo "  Лог:        tail -f ~/ai_arb/cloudflared.log"
    echo "  Остановка:  kill \$(cat ~/ai_arb/cloudflared.pid)"
else
    echo "❌ Туннель упал. Лог:"
    tail -20 "$HOME/ai_arb/cloudflared.log"
fi
