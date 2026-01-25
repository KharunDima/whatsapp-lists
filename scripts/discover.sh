cd ~/whatsapp-lists

# Создаем исправленную версию discover.sh
cat > scripts/discover-fixed.sh << 'EOF'
#!/bin/bash
# WhatsApp Optimized List Generator - FIXED VERSION

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN}Генератор оптимизированных списков WhatsApp${NC}"
echo -e "${BLUE}==========================================${NC}"

# Создаем каталог
WORK_DIR="/tmp/whatsapp-optimized-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo -e "${YELLOW}Рабочий каталог:${NC} $WORK_DIR"
echo ""

# ============================================================================
# 1. СОЗДАЕМ ОПТИМИЗИРОВАННЫЙ СПИСОК ДОМЕНОВ
# ============================================================================
DOMAINS_FILE="$WORK_DIR/whatsapp-domains.txt"

echo -e "${YELLOW}1. Создание списка доменов...${NC}"

cat > "$DOMAINS_FILE" << 'DOMAINS_EOF'
whatsapp.com
www.whatsapp.com
web.whatsapp.com
api.whatsapp.com
chat.whatsapp.com
call.whatsapp.com
voice.whatsapp.com
status.whatsapp.com
updates.whatsapp.com
beta.whatsapp.com
s.whatsapp.net
static.whatsapp.net
mmg.whatsapp.net
mmi.whatsapp.net
mms.whatsapp.net
v.whatsapp.net
voip.whatsapp.com
media.fbsbx.com
facebook.com
www.facebook.com
fb.com
www.fb.com
messenger.com
www.messenger.com
fbcdn.net
static.xx.fbcdn.net
scontent.xx.fbcdn.net
DOMAINS_EOF

DOMAIN_COUNT=$(wc -l < "$DOMAINS_FILE")
echo -e "${GREEN}✓ Создан список доменов: $DOMAIN_COUNT записей${NC}"

# ============================================================================
# 2. СОЗДАЕМ ОПТИМИЗИРОВАННЫЙ СПИСОК CIDR
# ============================================================================
echo -e "${YELLOW}2. Создание списка CIDR диапазонов...${NC}"

CIDR_FILE="$WORK_DIR/whatsapp-cidr.txt"

cat > "$CIDR_FILE" << 'CIDR_EOF'
31.13.24.0/21
31.13.64.0/18
45.64.40.0/22
66.220.144.0/20
69.63.176.0/20
69.171.224.0/19
74.119.76.0/22
102.132.96.0/20
103.4.96.0/22
129.134.0.0/16
157.240.0.0/16
173.252.64.0/18
185.60.216.0/22
199.201.64.0/22
204.15.20.0/22
31.13.72.0/24
31.13.73.0/24
31.13.74.0/24
31.13.75.0/24
57.144.245.0/24
CIDR_EOF

CIDR_COUNT=$(wc -l < "$CIDR_FILE")
echo -e "${GREEN}✓ Создан список CIDR: $CIDR_COUNT диапазонов${NC}"

# ============================================================================
# 3. КОПИРУЕМ ФАЙЛЫ В ПАПКУ ПРОЕКТА
# ============================================================================
echo -e "${YELLOW}3. Копирование файлов в папку проекта...${NC}"

# Определяем путь к папке проекта
if [ -f "/home/runner/work/whatsapp-lists/whatsapp-lists/README.md" ]; then
    # GitHub Actions
    PROJECT_DIR="/home/runner/work/whatsapp-lists/whatsapp-lists"
elif [ -f "$(dirname "$0")/../../README.md" ]; then
    # Локально
    PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
else
    PROJECT_DIR="."
fi

LISTS_DIR="$PROJECT_DIR/lists"
mkdir -p "$LISTS_DIR"

cp "$DOMAINS_FILE" "$LISTS_DIR/domains.txt"
cp "$CIDR_FILE" "$LISTS_DIR/cidr.txt"

echo -e "${GREEN}✓ Файлы скопированы в: $LISTS_DIR/${NC}"

# ============================================================================
# 4. ПРОВЕРКА ДОСТУПНОСТИ (упрощенная)
# ============================================================================
echo -e "${YELLOW}4. Быстрая проверка доступности...${NC}"

check_domain() {
    local domain="$1"
    if timeout 2 dig +short "$domain" @8.8.8.8 >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓ $domain доступен${NC}"
        return 0
    else
        echo -e "  ${YELLOW}⚠ $domain не резолвится${NC}"
        return 1
    fi
}

echo "  Проверка ключевых доменов:"
check_domain "whatsapp.com" || true
check_domain "web.whatsapp.com" || true
check_domain "s.whatsapp.net" || true

# ============================================================================
# 5. ИТОГОВЫЙ ВЫВОД
# ============================================================================
echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN}ГЕНЕРАЦИЯ ЗАВЕРШЕНА! ✅${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "${YELLOW}📂 СОЗДАННЫЕ ФАЙЛЫ:${NC}"
echo ""
echo -e "  ${GREEN}1. $LISTS_DIR/domains.txt${NC}"
echo -e "     • Домены: $DOMAIN_COUNT"
echo ""
echo -e "  ${GREEN}2. $LISTS_DIR/cidr.txt${NC}"
echo -e "     • CIDR: $CIDR_COUNT"
echo ""
echo -e "${YELLOW}🚀 ЧТО ДЕЛАТЬ ДАЛЬШЕ:${NC}"
echo -e "  Файлы готовы для использования в PodKop!"
echo ""
echo -e "${BLUE}==========================================${NC}"
EOF

# Делаем исполняемым
chmod +x scripts/discover-fixed.sh
