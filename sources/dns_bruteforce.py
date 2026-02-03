"""
DNS Brute Force для поиска поддоменов
"""
import logging
from typing import Set
from .base import BaseSource

logger = logging.getLogger(__name__)


class DNSBruteforceSource(BaseSource):
    """Источник доменов через DNS Brute Force"""
    
    async def get_domains(self) -> Set[str]:
        """Генерирует домены для DNS Brute Force"""
        domains = set()
        
        # Основные домены для brute force
        base_domains = [
            "whatsapp.com",
            "whatsapp.net",
            "wa.me",
            "fbcdn.net",
            "fastly.net",      # Добавляем Fastly CDN
            "akamai.net",      # Добавляем Akamai CDN
            "cloudfront.net",  # Amazon CloudFront (может использоваться)
            "cloudflare.com",  # Cloudflare (для некоторых сервисов)
            "microsoft.com",   # Для Bing и других сервисов
            "google.com",      # Для Google сервисов
            "apple.com",       # Для iOS сервисов
        ]
        
        # Общие поддомены
        common_subs = [
            # Стандартные
            "www", "web", "api", "chat", "call", "voice", "status",
            "business", "beta", "updates", "support", "help", "blog",
            "newsroom", "cdn", "media", "static", "upload", "download",
            
            # Технические
            "mx", "mail", "smtp", "imap", "pop", "autodiscover",
            "owa", "exchange", "portal", "admin", "secure", "vpn",
            
            # CDN и инфраструктура
            "assets", "images", "img", "video", "stream", "live",
            "ws", "wss", "socket", "push", "notification", "alert",
            
            # Региональные
            "us", "eu", "asia", "apac", "emea", "na", "sa",
            "east", "west", "north", "south", "central",
            
            # WhatsApp специфичные
            "bsg", "mmg", "mmi", "mms", "pps", "v", "edge",
            "whatsapp-cdn-shv", "whatsapp-chatd",
            
            # Новые из анализа трафика
            "g", "m", "e", "c", "s", "v", "p", "d", "f", "x",  # Односимвольные
            "quic", "map", "maps", "location", "geo",
            "a", "b", "q",  # Для Akamai паттернов
        ]
        
        # Специальные поддомены для конкретных доменов
        domain_specific_subs = {
            "whatsapp.net": [
                "g", "m", "e", "c", "s", "v", "p", "d", "f", "x",  # Односимвольные
                "g1", "g2", "g3", "m1", "m2", "m3", "e1", "e2", "e3",  # С цифрами
                "gateway", "global", "media", "message", "chat", "call",
                "voice", "video", "status", "sync", "backup", "restore",
                "notification", "push", "storage", "upload", "download",
                "cdn", "proxy", "lb", "loadbalancer", "edge", "border",
            ],
            "fbcdn.net": [
                "whatsapp-cdn-shv", "whatsapp-chatd", "whatsapp-media",
                "whatsapp-voice", "whatsapp-video", "whatsapp-stream",
                "fb-external", "fb-static", "fb-media", "fb-video",
                "scontent", "external", "staticxx", "video",
                "platform", "api", "graph", "connect",
            ],
            "fastly.net": [
                "quic", "map", "maps", "geo", "location",
                "media", "video", "stream", "cdn", "edge",
                "global", "us", "eu", "asia", "apac",
            ],
            "akamai.net": [
                # Паттерны Akamai: aNNNN.[q|b|g|s].akamai.net
            ],
            "microsoft.com": [
                "bing", "maps", "location", "search",
                "api", "dev", "developer",
            ],
            "google.com": [
                "maps", "gstatic", "apis", "android",
                "firebase", "crashlytics",
            ],
        }
        
        for base in base_domains:
            # Добавляем сам домен
            domains.add(base)
            
            # Добавляем базовые поддомены для всех доменов
            for sub in common_subs:
                domains.add(f"{sub}.{base}")
            
            # Добавляем специфичные поддомены
            if base in domain_specific_subs:
                for sub in domain_specific_subs[base]:
                    domains.add(f"{sub}.{base}")
            
            # Особые обработки для определенных доменов
            if base == "whatsapp.net":
                # Односимвольные домены с цифрами (g1, m2 и т.д.)
                for letter in ['g', 'm', 'e', 'c', 's', 'v', 'p', 'd', 'f', 'x']:
                    for i in range(1, 10):
                        domains.add(f"{letter}{i}.{base}")
            
            elif base == "akamai.net":
                # Генерация Akamai CDN паттернов: aNNNN.[q|b|g|s].akamai.net
                prefixes = ['q', 'b', 'g', 's']  # Типы серверов Akamai
                for prefix in prefixes:
                    # Небольшой диапазон для реалистичных значений
                    for i in [1, 2, 3, 5, 10, 20, 30, 50, 100, 200, 300,
                              400, 500, 600, 700, 800, 900,
                              1000, 1100, 1200, 1300, 1400, 1500]:
                        domains.add(f"a{i}.{prefix}.{base}")
            
            elif base == "fastly.net":
                # Комбинации для Fastly
                prefixes = ['quic', 'map', 'edge', 'cdn']
                suffixes = ['', 'global', 'us', 'eu', 'asia']
                
                for prefix in prefixes:
                    for suffix in suffixes:
                        if suffix:
                            domains.add(f"{prefix}.{suffix}.{base}")
                        else:
                            domains.add(f"{prefix}.{base}")
        
        # Числовые паттерны для WhatsApp
        if "whatsapp" in self.target_config.name.lower():
            # WhatsApp числовые паттерны (расширенный диапазон)
            for i in range(1, 200):  # Увеличиваем диапазон
                # Базовые числовые паттерны
                domains.add(f"s{i}.whatsapp.net")
                domains.add(f"c{i}.whatsapp.net")
                domains.add(f"m{i}.whatsapp.net")
                domains.add(f"e{i}.whatsapp.net")
                domains.add(f"node{i}.whatsapp.net")
                domains.add(f"edge{i}.whatsapp.net")
                domains.add(f"server{i}.whatsapp.net")
                domains.add(f"bsg{i:03d}.whatsapp.net")  # Формат 001, 002
                domains.add(f"mmg{i}.whatsapp.net")
                domains.add(f"mms{i}.whatsapp.net")
                domains.add(f"v{i}.whatsapp.net")
                domains.add(f"pps{i}.whatsapp.net")
                
                # Региональные/кластерные
                domains.add(f"us{i}.whatsapp.net")
                domains.add(f"eu{i}.whatsapp.net")
                domains.add(f"sg{i}.whatsapp.net")  # Singapore
                domains.add(f"in{i}.whatsapp.net")  # India
                domains.add(f"br{i}.whatsapp.net")  # Brazil
                
                # CDN паттерны
                for shard in range(1, 10):
                    for server in range(1, 10):
                        domains.add(f"whatsapp-cdn-shv-{shard}-{server}.fbcdn.net")
                        domains.add(f"whatsapp-chatd-{shard}-{server}.fbcdn.net")
                        domains.add(f"whatsapp-media-{shard}-{server}.fbcdn.net")
                        domains.add(f"whatsapp-voice-{shard}-{server}.fbcdn.net")
                        
                        # Fastly паттерны
                        domains.add(f"whatsapp-{shard}-{server}.fastly.net")
                        domains.add(f"wa-{shard}-{server}.fastly.net")
            
            # Специальные паттерны для шлюзов
            gateway_patterns = [
                "gateway", "gate", "gw", "router", "proxy",
                "entry", "ingress", "egress", "access",
            ]
            
            for pattern in gateway_patterns:
                for i in range(1, 10):
                    domains.add(f"{pattern}{i}.whatsapp.net")
                    domains.add(f"{pattern}-{i}.whatsapp.net")
        
        # Паттерны для внешних сервисов
        external_services = [
            # Bing и Microsoft
            "bing.com",
            "www.bing.com",
            "api.bing.com",
            "dev.bing.com",
            
            # Карты
            "maps.bing.com",
            "maps.google.com",
            "maps.apple.com",
            "nominatim.openstreetmap.org",
            
            # Google сервисы
            "gstatic.com",
            "fonts.gstatic.com",
            "www.gstatic.com",
            "apis.google.com",
            "android.googleapis.com",
            
            # Firebase (для push уведомлений)
            "fcm.googleapis.com",
            "firebasestorage.googleapis.com",
            "firestore.googleapis.com",
            
            # Crashlytics
            "reports.crashlytics.com",
            "settings.crashlytics.com",
        ]
        
        domains.update(external_services)
        
        return self._filter_domains(domains)