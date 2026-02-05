"""
Пассивные источники доменов (публичные списки)
"""
import aiohttp
import logging
from typing import Set
from .base import BaseSource

logger = logging.getLogger(__name__)


class PassiveSource(BaseSource):
    """Пассивные источники доменов"""

    async def get_domains(self) -> Set[str]:
        """Получает домены из публичных источников"""
        domains = set()

        # Список публичных источников
        sources = [
            "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
            "https://raw.githubusercontent.com/justdomains/blocklists/master/lists/adguarddns-justdomains.txt",
            "https://raw.githubusercontent.com/justdomains/blocklists/master/lists/easyprivacy-justdomains.txt",
            "https://raw.githubusercontent.com/HybridNetworks/whatsapp-cidr/main/WhatsApp/whatsapp_domainlist.txt",
            "https://raw.githubusercontent.com/itdoginfo/allow-domains/main/Services/meta.lst"
        ]

        async with aiohttp.ClientSession() as session:
            for url in sources:
                try:
                    source_domains = await self._fetch_source(session, url)
                    domains.update(source_domains)
                    logger.debug(f"📖 Источник {url}: {len(source_domains)} доменов")
                except Exception as e:
                    logger.debug(f"⚠️ Ошибка при получении из {url}: {e}")

        return self._filter_domains(domains)

    async def _fetch_source(self, session: aiohttp.ClientSession, url: str) -> Set[str]:
        """Получает домены из источника"""
        domains = set()

        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    lines = text.split('\n')

                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Извлекаем домен
                            parts = line.split()
                            if len(parts) >= 2:
                                domain = parts[-1].strip()  # Берем последний элемент

                                # Проверяем, что это домен
                                if '.' in domain and not domain.startswith('#'):
                                    # Очищаем домен
                                    domain = domain.lower()
                                    if domain.startswith('www.'):
                                        domain = domain[4:]

                                    domains.add(domain)

        except Exception as e:
            logger.debug(f"Ошибка при получении {url}: {e}")

        return domains