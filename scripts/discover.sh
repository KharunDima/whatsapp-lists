#!/bin/bash
# WhatsApp Power Discovery System v2.0
set -euo pipefail

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================
WORK_DIR="/tmp/whatsapp-power-$$"
mkdir -p "$WORK_DIR"
LOG_FILE="$WORK_DIR/power-discovery.log"

# Meta/Facebook ASN номера (основные)
META_ASN_LIST=("AS32934" "AS63293" "AS54115" "AS34825")

# Минимальные/максимальные значения
MIN_DOMAINS=20
MIN_CIDR=15
MAX_DOMAINS=150
MAX_CIDR=100

# Пакеты которые нам понадобятся
REQUIRED_PACKAGES=("curl" "jq" "whois" "dig" "nmap" "openssl")

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# ФУНКЦИИ ЛОГИРОВАНИЯ
# ============================================================================
log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
success() { echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"; }

# ============================================================================
# ПРОВЕРКА ЗАВИСИМОСТЕЙ
# ============================================================================
check_dependencies() {
    log "Проверка зависимостей..."
    local missing=()
    
    for pkg in "${REQUIRED_PACKAGES[@]}"; do
        if ! command -v "$pkg" &> /dev/null; then
            missing+=("$pkg")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        warning "Не хватает пакетов: ${missing[*]}"
        log "Установка недостающих пакетов..."
        sudo apt-get update
        sudo apt-get install -y "${missing[@]}" || {
            error "Не удалось установить пакеты"
            return 1
        }
    fi
    
    success "Все зависимости установлены"
}

# ============================================================================
# 1. ПОЛУЧЕНИЕ CIDR ИЗ ASN META/FACEBOOK
# ============================================================================
discover_meta_cidr() {
    log "1. Поиск CIDR через ASN Meta/Facebook..."
    local asn_cidr_file="$WORK_DIR/asn_cidr.txt"
    
    echo "# Meta/Facebook CIDR from ASN" > "$asn_cidr_file"
    
    for asn in "${META_ASN_LIST[@]}"; do
        log "  Анализ $asn..."
        
        # Метод 1: whois (основной) с timeout
        timeout 5 whois -h whois.radb.net "!g$asn" 2>/dev/null | \
            grep -E "^route:|^route6:" | \
            awk '{print $2}' | \
            sort -u >> "$asn_cidr_file" || true
        
        # Метод 2: Статические CIDR Meta
        echo "31.13.24.0/21" >> "$asn_cidr_file"
        echo "31.13.64.0/18" >> "$asn_cidr_file"
        echo "45.64.40.0/22" >> "$asn_cidr_file"
        echo "66.220.144.0/20" >> "$asn_cidr_file"
        echo "69.63.176.0/20" >> "$asn_cidr_file"
        echo "69.171.224.0/19" >> "$asn_cidr_file"
        echo "74.119.76.0/22" >> "$asn_cidr_file"
        echo "102.132.96.0/20" >> "$asn_cidr_file"
        echo "103.4.96.0/22" >> "$asn_cidr_file"
        echo "129.134.0.0/16" >> "$asn_cidr_file"
        echo "157.240.0.0/16" >> "$asn_cidr_file"
        echo "173.252.64.0/18" >> "$asn_cidr_file"
        echo "185.60.216.0/22" >> "$asn_cidr_file"
        echo "199.201.64.0/22" >> "$asn_cidr_file"
        echo "204.15.20.0/22" >> "$asn_cidr_file"
    done
    
    # Уникализация и сортировка
    sort -u "$asn_cidr_file" | grep -v "^#" > "$WORK_DIR/all_cidr.txt"
    
    local cidr_count=$(wc -l < "$WORK_DIR/all_cidr.txt")
    success "  Найдено CIDR: $cidr_count"
    
    # Ограничиваем максимальное количество
    head -$MAX_CIDR "$WORK_DIR/all_cidr.txt" > "$WORK_DIR/filtered_cidr.txt"
}

# ============================================================================
# 2. ПОЛУЧЕНИЕ ДОМЕНОВ
# ============================================================================
discover_domains() {
    log "2. Поиск доменов WhatsApp..."
    
    # Статические домены WhatsApp/Meta
    cat > "$WORK_DIR/static_domains.txt" << 'STATIC_DOMAINS'
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
business.whatsapp.com
s.whatsapp.net
static.whatsapp.net
mmg.whatsapp.net
mmi.whatsapp.net
mms.whatsapp.net
v.whatsapp.net
pps.whatsapp.net
facebook.com
www.facebook.com
fb.com
www.fb.com
messenger.com
www.messenger.com
fbcdn.net
static.xx.fbcdn.net
scontent.xx.fbcdn.net
instagram.com
www.instagram.com
STATIC_DOMAINS
    
    # SSL сертификаты (быстрая проверка)
    log "  Проверка SSL сертификатов..."
    for domain in whatsapp.com facebook.com; do
        timeout 5 openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null < /dev/null | \
            openssl x509 -noout -text 2>/dev/null | \
            grep -o "DNS:[^,]*" 2>/dev/null | \
            sed 's/DNS://g' | tr ',' '\n' | \
            grep -i "whatsapp\|facebook" >> "$WORK_DIR/ssl_domains.txt" || true
    done
    
    # Объединяем все источники
    cat "$WORK_DIR/static_domains.txt" "$WORK_DIR/ssl_domains.txt" 2>/dev/null | \
        sort -u | grep -v "^#" > "$WORK_DIR/all_domains.txt"
    
    # Фильтруем wildcard и некорректные домены
    grep -v '^\*\.' "$WORK_DIR/all_domains.txt" | \
        grep -E '^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)+$' > "$WORK_DIR/filtered_domains.txt"
    
    success "  Найдено доменов: $(wc -l < "$WORK_DIR/filtered_domains.txt")"
}

# ============================================================================
# 3. ВАЛИДАЦИЯ
# ============================================================================
validate_entries() {
    log "3. Валидация записей..."
    
    # Валидация доменов (параллельно, 5 потоков)
    echo "# Validated domains" > "$WORK_DIR/valid_domains.txt"
    
    validate_single_domain() {
        local d="$1"
        # Быстрая проверка DNS
        if timeout 2 dig +short "$d" @1.1.1.1 >/dev/null 2>&1; then
            echo "$d"
        fi
    }
    export -f validate_single_domain
    
    cat "$WORK_DIR/filtered_domains.txt" | xargs -P 5 -I {} bash -c 'validate_single_domain "{}"' >> "$WORK_DIR/valid_domains.txt"
    
    # Валидация CIDR (просто проверка формата)
    echo "# Validated CIDR" > "$WORK_DIR/valid_cidr.txt"
    grep -E '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$' "$WORK_DIR/filtered_cidr.txt" >> "$WORK_DIR/valid_cidr.txt"
    
    success "  Валидных доменов: $(grep -c '^[^#]' "$WORK_DIR/valid_domains.txt")"
    success "  Валидных CIDR: $(grep -c '^[^#]' "$WORK_DIR/valid_cidr.txt")"
}

# ============================================================================
# 4. ЗАПИСЬ РЕЗУЛЬТАТОВ
# ============================================================================
write_results() {
    log "4. Запись результатов..."
    
    mkdir -p lists/
    
    # Домены
    local domain_count=$(grep -c '^[^#]' "$WORK_DIR/valid_domains.txt")
    echo "# WhatsApp Power Discovery v2.0" > lists/domains.txt
    echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')" >> lists/domains.txt
    echo "# Total domains: $domain_count" >> lists/domains.txt
    echo "" >> lists/domains.txt
    cat "$WORK_DIR/valid_domains.txt" >> lists/domains.txt
    
    # CIDR
    local cidr_count=$(grep -c '^[^#]' "$WORK_DIR/valid_cidr.txt")
    echo "# WhatsApp Power Discovery v2.0" > lists/cidr.txt
    echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')" >> lists/cidr.txt
    echo "# Total CIDR: $cidr_count" >> lists/cidr.txt
    echo "" >> lists/cidr.txt
    cat "$WORK_DIR/valid_cidr.txt" >> lists/cidr.txt
    
    success "✅ Файлы созданы:"
    success "  - lists/domains.txt ($domain_count доменов)"
    success "  - lists/cidr.txt ($cidr_count CIDR)"
}

# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================
main() {
    echo "========================================"
    echo " WhatsApp Power Discovery v2.0"
    echo "========================================"
    echo ""
    
    # Создаем директорию
    mkdir -p lists/
    
    # Проверяем зависимости
    check_dependencies
    
    # Выполняем все этапы
    discover_meta_cidr
    discover_domains
    validate_entries
    write_results
    
    # Очистка
    rm -rf "$WORK_DIR"
    
    echo ""
    echo "========================================"
    success " Discovery completed successfully!"
    echo "========================================"
}

# Запуск
main "$@"
