#!/bin/bash
# WhatsApp Discovery v5.0
set -e

echo "========================================"
echo " WhatsApp Discovery v5.0"
echo "========================================"

# Переходим в корень проекта
cd "$(dirname "$0")/.."

# Проверяем Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ ОШИБКА: Python3 не установлен"
    exit 1
fi

# Создаем виртуальное окружение если нет
if [ ! -d "venv" ]; then
    echo "🔧 Создаем виртуальное окружение..."
    python3 -m venv venv
fi

# Активируем и устанавливаем зависимости
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Запускаем сканирование
echo "🚀 Запускаем сканирование..."
python main.py whatsapp --output-dir results --log-level INFO

# Показываем результаты
echo ""
echo "📊 РЕЗУЛЬТАТЫ:"
echo "=============="
if [ -f "results/domains.txt" ]; then
    DOMAINS=$(grep -c -v '^#' results/domains.txt 2>/dev/null || echo 0)
    echo "✅ Доменов: $DOMAINS"
fi
if [ -f "results/cidr_ipv4.txt" ]; then
    CIDR4=$(grep -c -v '^#' results/cidr_ipv4.txt 2>/dev/null || echo 0)
    echo "✅ IPv4 CIDR: $CIDR4"
fi
if [ -f "results/cidr_ipv6.txt" ]; then
    CIDR6=$(grep -c -v '^#' results/cidr_ipv6.txt 2>/dev/null || echo 0)
    echo "✅ IPv6 CIDR: $CIDR6"
fi

echo ""
echo "📁 Результаты в: results/"
