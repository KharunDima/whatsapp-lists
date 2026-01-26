#!/bin/bash
# WhatsApp Power Discovery v2.1 - GitHub Actions compatible
set -euo pipefail

echo "========================================"
echo " WhatsApp Power Discovery v2.1"
echo "========================================"

# Конфигурация
WORK_DIR="/tmp/whatsapp-discovery-$$"
mkdir -p "$WORK_DIR"

# Функции простого логирования
log() { echo "[$(date '+%H:%M:%S')] $1"; }
success() { echo "✅ $1"; }
warning() { echo "⚠️  $1"; }
error() { echo "❌ $1"; }

# ============================================================================
# 1. ПОЛУЧЕНИЕ CIDR ИЗ ASN META/FACEBOOK
# ============================================================================
discover_meta_cidr() {
    log "1. Поиск CIDR через ASN Meta/Facebook..."
    
    # Статические CIDR Meta/Facebook (основные)
    cat > "$WORK_DIR/static_cidr.txt" << 'STATIC_CIDR'
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
STATIC_CIDR
    
    # Пробуем whois (с timeout на случай если сервер не отвечает)
    log "  Запрос whois для AS32934 (Meta)..."
    timeout 10 whois -h whois.radb.net "!gAS32934" 2>/dev/null | \
        grep -E "^route:|^route6:" | \
        awk '{print $2}' | \
        head -20 > "$WORK_DIR/whois_cidr.txt" || true
    
    # Объединяем
    cat "$WORK_DIR/static_cidr.txt" "$WORK_DIR/whois_cidr.txt" 2>/dev/null | \
        sort -u | grep -v "^#" > "$WORK_DIR/all_cidr.txt"
    
    # Фильтруем приватные подсети
    grep -v -E "^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.|127\.|0\.|169\.254\.)" \
        "$WORK_DIR/all_cidr.txt" > "$WORK_DIR/filtered_cidr.txt"
    
    success "  Найдено CIDR: $(wc -l < "$WORK_DIR/filtered_cidr.txt")"
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
    
    # SSL сертификаты (опционально, если openssl доступен)
    if command -v openssl >/dev/null 2>&1; then
        log "  Проверка SSL сертификатов..."
        for domain in whatsapp.com facebook.com; do
            timeout 5 openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null < /dev/null | \
                openssl x509 -noout -text 2>/dev/null | \
                grep -o "DNS:[^,]*" 2>/dev/null | \
                sed 's/DNS://g' | tr ',' '\n' | \
                grep -i "whatsapp\|facebook" >> "$WORK_DIR/ssl_domains.txt" 2>/dev/null || true
        done
    fi
    
    # Объединяем все источники
    cat "$WORK_DIR/static_domains.txt" "$WORK_DIR/ssl_domains.txt" 2>/dev/null | \
        sort -u | grep -v "^#" | grep -v '^\*\.' > "$WORK_DIR/all_domains.txt"
    
    success "  Найдено доменов: $(wc -l < "$WORK_DIR/all_domains.txt")"
}

# ============================================================================
# 3. ВАЛИДАЦИЯ
# ============================================================================
validate_entries() {
    log "3. Валидация записей..."
    
    # Валидация доменов (простая проверка DNS)
    echo "# Validated domains" > "$WORK_DIR/valid_domains.txt"
    
    validate_domain() {
        local d="$1"
        # Быстрая проверка DNS через 1.1.1.1 (Cloudflare)
        if timeout 2 dig +short "$d" @1.1.1.1 >/dev/null 2>&1; then
            echo "$d"
        fi
    }
    
    # Проверяем домены (без параллелизма для простоты)
    while read -r domain; do
        [[ -z "$domain" ]] && continue
        [[ "$domain" =~ ^# ]] && continue
        validate_domain "$domain" >> "$WORK_DIR/valid_domains.txt"
    done < "$WORK_DIR/all_domains.txt"
    
    # Валидация CIDR (просто проверка формата)
    echo "# Validated CIDR" > "$WORK_DIR/valid_cidr.txt"
    grep -E '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$' \
        "$WORK_DIR/filtered_cidr.txt" >> "$WORK_DIR/valid_cidr.txt"
    
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
    echo "# WhatsApp Power Discovery v2.1" > lists/domains.txt
    echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')" >> lists/domains.txt
    echo "# Total domains: $domain_count" >> lists/domains.txt
    echo "" >> lists/domains.txt
    cat "$WORK_DIR/valid_domains.txt" >> lists/domains.txt
    
    # CIDR
    local cidr_count=$(grep -c '^[^#]' "$WORK_DIR/valid_cidr.txt")
    echo "# WhatsApp Power Discovery v2.1" > lists/cidr.txt
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
    echo ""
    
    # Создаем директорию
    mkdir -p lists/
    
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
