#!/bin/bash
# Improved WhatsApp lists verification script
set -euo pipefail

echo "🔍 Проверка списков WhatsApp..."
echo "======================================"

# 1. Проверка структуры файлов
echo "1. Проверка структуры файлов:"
if [ -f lists/domains.txt ] && [ -f lists/cidr.txt ]; then
    echo "  ✅ Оба файла существуют"
    echo "  📊 Домены: $(wc -l < lists/domains.txt) строк"
    echo "  📊 CIDR: $(wc -l < lists/cidr.txt) строк"
else
    echo "  ❌ Файлы не найдены!"
    exit 1
fi

# 2. Проверка даты генерации
echo -e "\n2. Проверка даты генерации:"
if grep -q "Generated:" lists/domains.txt && grep -q "Generated:" lists/cidr.txt; then
    DOMAIN_DATE=$(grep "Generated:" lists/domains.txt | tail -1)
    CIDR_DATE=$(grep "Generated:" lists/cidr.txt | tail -1)
    echo "  ✅ Домены: $DOMAIN_DATE"
    echo "  ✅ CIDR: $CIDR_DATE"
else
    echo "  ⚠️  Дата генерации не найдена"
fi

# 3. Быстрая проверка ключевых доменов (более надежная)
echo -e "\n3. Быстрая проверка доступности:"
check_domain() {
    local domain="$1"
    # Пробуем разные методы
    if timeout 5 curl -s -I "https://$domain" >/dev/null 2>&1; then
        echo "  ✅ $domain (через HTTPS)"
        return 0
    elif timeout 5 curl -s -I "http://$domain" >/dev/null 2>&1; then
        echo "  ✅ $domain (через HTTP)"
        return 0
    elif timeout 5 nslookup "$domain" >/dev/null 2>&1; then
        echo "  ✅ $domain (DNS разрешается)"
        return 0
    else
        echo "  ⚠️  $domain (не удалось проверить)"
        return 1
    fi
}

# Проверяем только ключевые домены
KEY_DOMAINS=("web.whatsapp.com" "whatsapp.com" "api.whatsapp.com")
for domain in "${KEY_DOMAINS[@]}"; do
    if grep -q "$domain" lists/domains.txt; then
        check_domain "$domain"
    fi
done

# 4. Проверка CIDR формата
echo -e "\n4. Проверка CIDR (первые 5):"
head -5 lists/cidr.txt | grep -v '^#' | while read cidr; do
    if [[ "$cidr" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        echo "  ✅ $cidr (валидный формат)"
    elif [ -n "$cidr" ]; then
        echo "  ⚠️  $cidr (некорректный формат)"
    fi
done

echo -e "\n======================================"
echo "✅ Проверка завершена. Списки готовы к использованию."
echo "📅 Обновлено: $(grep 'Generated:' lists/domains.txt | tail -1)"
