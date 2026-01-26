#!/bin/bash
# WhatsApp Power Verification v2.6
set -euo pipefail

echo "================================================"
echo "    WhatsApp Power Verification v2.6"
echo "================================================"
echo ""

# Проверка файлов
if [ ! -f lists/domains.txt ] || [ ! -f lists/cidr.txt ]; then
    echo "❌ ОШИБКА: Файлы списков не найдены!"
    exit 1
fi

# Простой подсчет
DOMAIN_COUNT=$(grep -c '^[^#]' lists/domains.txt 2>/dev/null || echo "0")
CIDR_COUNT=$(grep -c '^[^#]' lists/cidr.txt 2>/dev/null || echo "0")

echo "📊 СТАТИСТИКА ФАЙЛОВ:"
echo "   • Домены: $DOMAIN_COUNT записей"
echo "   • CIDR: $CIDR_COUNT записей"
echo "   • Дата: $(grep 'Generated:' lists/domains.txt | head -1 | cut -d: -f2-)"

# Проверка 1: Wildcard домены
echo -e "\n1. Проверка wildcard доменов:"
if grep -q '^\*\.' lists/domains.txt 2>/dev/null; then
    WILDCARD_COUNT=$(grep -c '^\*\.' lists/domains.txt)
    echo "   ❌ Найдено wildcard доменов: $WILDCARD_COUNT"
else
    echo "   ✅ Wildcard доменов нет"
fi

# Проверка 2: Ключевые домены
echo -e "\n2. Проверка ключевых доменов:"
check_domain() {
    if timeout 2 dig +short "$1" >/dev/null 2>&1; then
        echo "   ✅ $1"
    else
        echo "   ⚠️  $1"
    fi
}

for domain in web.whatsapp.com whatsapp.com api.whatsapp.com; do
    if grep -q "^$domain$" lists/domains.txt; then
        check_domain "$domain"
    else
        echo "   ❌ $domain (отсутствует)"
    fi
done

# Проверка 3: Случайные домены
echo -e "\n3. Проверка случайных доменов:"
if [ "$DOMAIN_COUNT" -gt 3 ] 2>/dev/null; then
    for domain in $(grep '^[^#]' lists/domains.txt | shuf -n 3); do
        if timeout 2 dig +short "$domain" >/dev/null 2>&1; then
            echo "   ✅ $domain"
        else
            echo "   ⚠️  $domain"
        fi
    done
else
    echo "   ℹ️  Недостаточно доменов для проверки"
fi

# Проверка 4: Формат CIDR
echo -e "\n4. Проверка формата CIDR:"
BAD_CIDR=0
if [ "$CIDR_COUNT" -gt 0 ] 2>/dev/null; then
    while read -r cidr; do
        if [[ ! "$cidr" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
            BAD_CIDR=$((BAD_CIDR + 1))
        fi
    done < <(grep '^[^#]' lists/cidr.txt 2>/dev/null)
fi

if [ "$BAD_CIDR" -eq 0 ] 2>/dev/null; then
    echo "   ✅ Все CIDR правильного формата"
else
    echo "   ❌ Неправильных CIDR: $BAD_CIDR"
fi

# Проверка 5: Приватные подсети
echo -e "\n5. Проверка приватных подсетей:"
PRIVATE_COUNT=0
if [ "$CIDR_COUNT" -gt 0 ] 2>/dev/null; then
    PRIVATE_COUNT=$(grep '^[^#]' lists/cidr.txt 2>/dev/null | grep -E "^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.|127\.|0\.|169\.254\.)" | wc -l 2>/dev/null || echo "0")
fi

if [ "$PRIVATE_COUNT" = "0" ] 2>/dev/null; then
    echo "   ✅ Приватных подсетей нет"
else
    echo "   ❌ Приватных подсетей: $PRIVATE_COUNT"
fi

# Итоговая оценка
echo -e "\n================================================"
echo "ИТОГОВАЯ ОЦЕНКА:"

TOTAL_SCORE=0
[ "$DOMAIN_COUNT" -ge 25 ] 2>/dev/null && TOTAL_SCORE=$((TOTAL_SCORE + 2))
[ "$DOMAIN_COUNT" -ge 15 ] 2>/dev/null && TOTAL_SCORE=$((TOTAL_SCORE + 1))
[ "$CIDR_COUNT" -ge 15 ] 2>/dev/null && TOTAL_SCORE=$((TOTAL_SCORE + 2))
[ "$CIDR_COUNT" -ge 10 ] 2>/dev/null && TOTAL_SCORE=$((TOTAL_SCORE + 1))
[ "$BAD_CIDR" -eq 0 ] 2>/dev/null && TOTAL_SCORE=$((TOTAL_SCORE + 1))
[ "$PRIVATE_COUNT" = "0" ] 2>/dev/null && TOTAL_SCORE=$((TOTAL_SCORE + 1))

case $TOTAL_SCORE in
    6|7)
        echo "✅ ОТЛИЧНО! Полностью готово для PodKop"
        EXIT_CODE=0
        ;;
    4|5)
        echo "⚠️  ХОРОШО. Можно использовать"
        EXIT_CODE=0
        ;;
    *)
        echo "❌ ТРЕБУЕТСЯ УЛУЧШЕНИЕ"
        EXIT_CODE=1
        ;;
esac

echo "================================================"
exit $EXIT_CODE
