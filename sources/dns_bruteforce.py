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
        base_domains = ["whatsapp.com", "whatsapp.net", "wa.me", "fbcdn.net"]

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
            "whatsapp-cdn-shv", "whatsapp-chatd"
        ]

        for base in base_domains:
            for sub in common_subs:
                domains.add(f"{sub}.{base}")

        # Числовые паттерны для WhatsApp
        if "whatsapp" in self.target_config.name.lower():
            for i in range(1, 100):
                domains.add(f"s{i}.whatsapp.net")
                domains.add(f"c{i}.whatsapp.net")
                domains.add(f"m{i}.whatsapp.net")
                domains.add(f"e{i}.whatsapp.net")
                domains.add(f"node{i}.whatsapp.net")
                domains.add(f"edge{i}.whatsapp.net")
                domains.add(f"server{i}.whatsapp.net")

                # CDN паттерны
                for shard in range(1, 5):
                    for server in range(1, 5):
                        domains.add(f"whatsapp-cdn-shv-{shard}-{server}.fbcdn.net")
                        domains.add(f"whatsapp-chatd-{shard}-{server}.fbcdn.net")

        return self._filter_domains(domains)