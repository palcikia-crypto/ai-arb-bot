#!/data/data/com.termux/files/usr/bin/bash
echo "🚀 НАЧИНАЮ УСТАНОВКУ ОКРУЖЕНИЯ..."
pkg update -y
pkg install python nodejs git -y
echo "📦 УСТАНАВЛИВАЮ PYTHON-БИБЛИОТЕКИ..."
pip install requests beautifulsoup4 huggingface_hub
echo "✅ ВСЁ ГОТОВО! МОЖНО ЗАПУСКАТЬ СКРИПТЫ."
