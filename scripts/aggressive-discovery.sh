#!/bin/bash
# WhatsApp REAL Discovery v4.3
# ТОЛЬКО реально существующие ресурсы
set -euo pipefail

# Определяем путь для сохранения файлов
if [ -d "/home/runner/work/whatsapp-lists/whatsapp-lists" ]; then
    # Мы в GitHub Actions
    LISTS_DIR="/home/runner/work/whatsapp-lists/whatsapp-lists/lists"
    echo "🔧 Обнаружен GitHub Actions, сохраняем в: $LISTS_DIR"
else
    # Локальный запуск
    LISTS_DIR="../lists"
    echo "🔧 Локальный запуск, сохраняем в: $LISTS_DIR"
fi

# Создаем директорию если не существует
mkdir -p "$LISTS_DIR"

echo "========================================"
echo " WhatsApp REAL Discovery v4.3"
echo "========================================"
echo "⚡ ТОЛЬКО РЕАЛЬНО СУЩЕСТВУЮЩИЕ РЕСУРСЫ ⚡"
echo ""

WORK_DIR="/tmp/whatsapp-real-$$"
mkdir -p "$WORK_DIR"

log() { echo "[$(date '+%H:%M:%S')] $1"; }
success() { echo "✅ $1"; }
info() { echo "🔍 $1"; }
warning() { echo "⚠️  $1"; }

# 1. Быстрый поиск реальных доменов
find_real_domains() {
    log "1. Поиск реальных доменов WhatsApp..."
    
    # Основные домены WhatsApp/Meta
    REAL_BASE_DOMAINS=("whatsapp.com" "whatsapp.net" "wa.me" "facebook.com")
    
    # Известные реальные поддомены WhatsApp (сокращенный список для скорости)
    REAL_WHATSAPP_DOMAINS=(
        # Основные
        "web.whatsapp.com" "api.whatsapp.com" "chat.whatsapp.com"
        "call.whatsapp.com" "business.whatsapp.com"
        "status.whatsapp.com" "updates.whatsapp.com"
        "v.whatsapp.com" "s.whatsapp.com" "static.whatsapp.com"
        "mmg.whatsapp.com" "mms.whatsapp.com" "res.whatsapp.com"
        "cdn.whatsapp.com" "media.whatsapp.com"
        "edge.whatsapp.com" "gateway.whatsapp.com"
        "messaging.whatsapp.com" "stun.whatsapp.com" "turn.whatsapp.com"
        "app.whatsapp.com" "desktop.whatsapp.com"
        "android.whatsapp.com" "ios.whatsapp.com"
        "auth.whatsapp.com" "login.whatsapp.com" "account.whatsapp.com"
        "group.whatsapp.com" "channel.whatsapp.com"
        
        # Критические edge-серверы
        "edge-star-shv-01-ams2.facebook.com"
        "edge-star-shv-01-fra3.facebook.com"
        "edge-star-shv-01-lhr2.facebook.com"
        "edge-star-shv-01-mad1.facebook.com"
        "edge-star-shv-01-sin1.facebook.com"
        "edge-star-shv-01-iad3.facebook.com"
        "whatsapp-chatd-edge-shv-01-fra3.facebook.com"
        "whatsapp-chatd-edge-shv-01-ams2.facebook.com"
        "whatsapp-cdn-shv-01-fra3.fbcdn.net"
        "whatsapp-cdn-shv-01-ams2.fbcdn.net"
        
        # Важные CDN
        "scontent.xx.fbcdn.net"
        "scontent-a.xx.fbcdn.net"
        "scontent-b.xx.fbcdn.net"
        "scontent-c.xx.fbcdn.net"
        "graph.facebook.com"
        "connect.facebook.com"
    )
    
    # Проверяем каждый домен
    local total=0
    local found=0
    
    echo "# Реально существующие домены WhatsApp/Meta" > "$WORK_DIR/real-domains.txt"
    
    # Проверяем основные домены
    for domain in "${REAL_BASE_DOMAINS[@]}"; do
        total=$((total + 1))
        if timeout 2 dig +short "$domain" @1.1.1.1 >/dev/null 2>&1; then
            echo "$domain" >> "$WORK_DIR/real-domains.txt"
            found=$((found + 1))
            info "  ✅ $domain"
        fi
    done
    
    # Проверяем известные реальные домены WhatsApp
    info "  Проверяем известные домены WhatsApp..."
    
    for domain in "${REAL_WHATSAPP_DOMAINS[@]}"; do
        total=$((total + 1))
        if timeout 2 dig +short "$domain" @1.1.1.1 >/dev/null 2>&1; then
            echo "$domain" >> "$WORK_DIR/real-domains.txt"
            found=$((found + 1))
            if [ $found -le 10 ] || [ $((found % 20)) -eq 0 ]; then
                info "  ✅ $domain"
            fi
        fi
    done
    
    # Убираем дубликаты
    sort -u "$WORK_DIR/real-domains.txt" > "$WORK_DIR/real-domains-unique.txt"
    mv "$WORK_DIR/real-domains-unique.txt" "$WORK_DIR/real-domains.txt"
    
    local unique_count=$(wc -l < "$WORK_DIR/real-domains.txt" 2>/dev/null || echo 0)
    success "  Найдено реальных доменов: $unique_count"
    
    # Показываем статистику по типам доменов
    echo ""
    info "  Статистика по типам доменов:"
    
    local whatsapp_count=$(grep -c "whatsapp" "$WORK_DIR/real-domains.txt" 2>/dev/null || echo 0)
    local facebook_count=$(grep -c "facebook" "$WORK_DIR/real-domains.txt" 2>/dev/null || echo 0)
    local fbcdn_count=$(grep -c "fbcdn" "$WORK_DIR/real-domains.txt" 2>/dev/null || echo 0)
    local edge_count=$(grep -c "edge" "$WORK_DIR/real-domains.txt" 2>/dev/null || echo 0)
    
    info "    • WhatsApp домены: $whatsapp_count"
    info "    • Facebook домены: $facebook_count"
    info "    • CDN домены (fbcdn): $fbcdn_count"
    info "    • Edge серверы: $edge_count"
}

# 2. Находим CIDR на основе реальных доменов
find_real_cidr() {
    log "2. Поиск реальных CIDR на основе доменов..."
    
    # Известные сети Meta
    echo "# Известные сети Meta/WhatsApp" > "$WORK_DIR/real-cidr.txt"
    
    KNOWN_CIDR=(
        "157.240.0.0/16"      # Facebook main
        "129.134.0.0/16"      # Facebook
        "31.13.24.0/21"       # Facebook
        "69.63.176.0/20"      # Facebook
        "69.171.224.0/19"     # Facebook
        "66.220.144.0/20"     # Facebook
        "173.252.64.0/18"     # Facebook
        "185.60.216.0/22"     # Facebook
        "31.13.64.0/18"       # Facebook
        "31.13.72.0/24"       # Важная сеть для WhatsApp
        "31.13.73.0/24"       # Важная сеть для WhatsApp
        "31.13.74.0/24"       # Важная сеть для WhatsApp
        "31.13.75.0/24"       # Важная сеть для WhatsApp
    )
    
    info "  Добавляем известные сети Meta..."
    for cidr in "${KNOWN_CIDR[@]}"; do
        echo "$cidr" >> "$WORK_DIR/real-cidr.txt"
    done
    
    # Получаем CIDR из реальных доменов (только первые 50 для скорости)
    info "  Получаем IP из реальных доменов..."
    
    if [ -s "$WORK_DIR/real-domains.txt" ]; then
        counter=0
        while read -r domain && [ $counter -lt 50 ]; do
            [[ -z "$domain" ]] && continue
            
            # Получаем IP для домена
            ip_list=$(timeout 2 dig +short "$domain" A @1.1.1.1 2>/dev/null || true)
            
            for ip in $ip_list; do
                if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                    # Создаем /24 сеть из IP
                    network=$(echo "$ip" | sed 's/\.[0-9]*$/.0\/24/')
                    echo "$network" >> "$WORK_DIR/cidr-from-domains.txt"
                    counter=$((counter + 1))
                    
                    if [ $counter -le 10 ]; then
                        info "    📡 $domain → $ip → $network"
                    fi
                fi
            done
        done < "$WORK_DIR/real-domains.txt"
    fi
    
    # Добавляем CIDR из доменов
    if [ -f "$WORK_DIR/cidr-from-domains.txt" ]; then
        info "  Объединяем все CIDR..."
        cat "$WORK_DIR/cidr-from-domains.txt" >> "$WORK_DIR/real-cidr.txt" 2>/dev/null
    fi
    
    # Убираем дубликаты и приватные сети
    grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+$' "$WORK_DIR/real-cidr.txt" | \
        grep -v -E "^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.|127\.|0\.|169\.254\.)" | \
        sort -u > "$WORK_DIR/real-cidr-final.txt"
    
    local cidr_count=$(wc -l < "$WORK_DIR/real-cidr-final.txt" 2>/dev/null || echo 0)
    success "  Найдено реальных CIDR: $cidr_count"
}

# 3. Сохраняем результаты
save_results() {
    log "3. Сохранение результатов..."
    
    mkdir -p "$LISTS_DIR/"
    
    # Инициализируем переменные
    local NEW_DOMAIN_COUNT=0
    
    # Домены
    DOMAIN_COUNT=$(wc -l < "$WORK_DIR/real-domains.txt" 2>/dev/null || echo 0)
    
    cat > "$LISTS_DIR/domains.txt" << EOF
# WhatsApp REAL Discovery v4.3
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# Total domains: $DOMAIN_COUNT
# 
# ⚡ РЕАЛЬНО СУЩЕСТВУЮЩИЕ ДОМЕНЫ WhatsApp/Meta ⚡
# Для использования в PodKop и других обходчиках
# URL: https://raw.githubusercontent.com/KharunDima/whatsapp-lists/main/lists/domains.txt
#

EOF
    cat "$WORK_DIR/real-domains.txt" >> "$LISTS_DIR/domains.txt" 2>/dev/null
    
    # CIDR
    CIDR_COUNT=$(wc -l < "$WORK_DIR/real-cidr-final.txt" 2>/dev/null || echo 0)
    
    cat > "$LISTS_DIR/cidr.txt" << EOF
# WhatsApp REAL Discovery v4.3
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# Total CIDR: $CIDR_COUNT
# 
# ⚡ РЕАЛЬНЫЕ ПОДСЕТИ WhatsApp/Meta ⚡
# Для использования в PodKop и других обходчиках
# URL: https://raw.githubusercontent.com/KharunDima/whatsapp-lists/main/lists/cidr.txt
#

EOF
    cat "$WORK_DIR/real-cidr-final.txt" >> "$LISTS_DIR/cidr.txt" 2>/dev/null
    
    # Создаем простой файл с реально новыми доменами
    if [ -f "$LISTS_DIR/domains.txt.prev" ]; then
        comm -13 <(sort "$LISTS_DIR/domains.txt.prev" 2>/dev/null | grep -v '^#') \
                 <(sort "$LISTS_DIR/domains.txt" 2>/dev/null | grep -v '^#') \
                 > "$WORK_DIR/new-domains.txt" 2>/dev/null || true
        
        NEW_DOMAIN_COUNT=$(wc -l < "$WORK_DIR/new-domains.txt" 2>/dev/null || echo 0)
        
        if [ "$NEW_DOMAIN_COUNT" -gt 0 ]; then
            echo "# 🆕 НОВЫЕ ДОМЕНЫ ($NEW_DOMAIN_COUNT) - $(date '+%Y-%m-%d %H:%M:%S')" > "$LISTS_DIR/NEW_DOMAINS.txt"
            echo "" >> "$LISTS_DIR/NEW_DOMAINS.txt"
            cat "$WORK_DIR/new-domains.txt" >> "$LISTS_DIR/NEW_DOMAINS.txt"
        fi
    fi
    
    # Копируем текущие файлы для следующего сравнения
    cp "$LISTS_DIR/domains.txt" "$LISTS_DIR/domains.txt.prev" 2>/dev/null || true
    cp "$LISTS_DIR/cidr.txt" "$LISTS_DIR/cidr.txt.prev" 2>/dev/null || true
    
    echo ""
    echo "📊 РЕЗУЛЬТАТЫ:"
    echo "=============="
    echo "✅ Реальных доменов: $DOMAIN_COUNT"
    echo "✅ Реальных CIDR: $CIDR_COUNT"
    
    if [ "$NEW_DOMAIN_COUNT" -gt 0 ]; then
        echo ""
        echo "🔥 НОВЫХ ДОМЕНОВ: $NEW_DOMAIN_COUNT"
        echo "   Первые 10 новых доменов:"
        head -10 "$WORK_DIR/new-domains.txt" | while read domain; do
            echo "     • $domain"
        done
        echo ""
        echo "   Все новые домены в файле: $LISTS_DIR/NEW_DOMAINS.txt"
    else
        echo ""
        echo "ℹ️  Новых доменов не найдено (все уже были в предыдущем списке)"
    fi
    
    echo ""
    success "Сохранено:"
    success "  - domains.txt ($DOMAIN_COUNT доменов)"
    success "  - cidr.txt ($CIDR_COUNT CIDR)"
    
    if [ "$NEW_DOMAIN_COUNT" -gt 0 ]; then
        success "  - NEW_DOMAINS.txt ($NEW_DOMAIN_COUNT новых доменов)"
    fi
}

# Основная функция
main() {
    echo ""
    
    # Проверяем необходимые утилиты
    if ! command -v dig >/dev/null 2>&1; then
        echo "❌ ОШИБКА: dig не установлен"
        echo "   Установите: sudo apt-get install dnsutils"
        exit 1
    fi
    
    echo "⚡ ЗАПУСКАЮ РЕАЛЬНЫЙ ПОИСК..."
    echo "   Используем проверенные реальные домены"
    echo ""
    
    find_real_domains
    find_real_cidr
    save_results
    
    # Очистка
    rm -rf "$WORK_DIR"
    
    echo ""
    echo "========================================"
    success " ПОИСК ЗАВЕРШЕН УСПЕШНО!"
    echo "========================================"
    echo ""
    echo "🚀 Для PodKop используйте:"
    echo "   Домены: https://raw.githubusercontent.com/KharunDima/whatsapp-lists/main/lists/domains.txt"
    echo "   CIDR:   https://raw.githubusercontent.com/KharunDima/whatsapp-lists/main/lists/cidr.txt"
    echo ""
    echo "📁 Файлы сохранены в: $LISTS_DIR/"
    echo ""
}

# Запуск
main
