"""
Поиск доменов через CRT.SH с обходом блокировок
"""
import aiohttp
import asyncio
import json
import logging
import re
import random
from typing import Set
from urllib.parse import quote

from .base import BaseSource

logger = logging.getLogger(__name__)


class CRTShSource(BaseSource):
    """Источник доменов из CRT.SH с обходом блокировок"""

    def __init__(self, target_config):
        super().__init__(target_config)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Googlebot/2.1 (+http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)"
        ]

    async def get_domains(self) -> Set[str]:
        """Получает домены из CRT.SH"""
        domains = set()

        # Используем только работающие паттерны на основе диагностики
        patterns = self._get_working_patterns()

        for pattern in patterns:
            try:
                logger.info(f"🌐 CRT.SH: '{pattern}'")

                pattern_domains = await self._query_crt_sh_safe(pattern)

                if pattern_domains:
                    domains.update(pattern_domains)
                    logger.info(f"   Найдено: {len(pattern_domains)} доменов")
                else:
                    logger.debug(f"   Не найдено доменов")

                # Задержка между запросами
                await asyncio.sleep(random.uniform(3, 7))

            except Exception as e:
                logger.warning(f"⚠️ Ошибка для '{pattern}': {str(e)[:100]}")

        # Фильтрация
        filtered = self._filter_domains(domains)
        logger.info(f"✅ CRT.SH: всего {len(filtered)} доменов после фильтрации")
        return filtered

    def _get_working_patterns(self) -> list:
        """Возвращает только работающие паттерны на основе диагностики"""
        # Основные паттерны, которые работают
        working_patterns = [
            "%.whatsapp.net",
            "%.fbcdn.net",
            "whatsapp%",
            "%.fb.com",
            "%.whatsapp.com"
        ]

        return working_patterns

    async def _query_crt_sh_safe(self, pattern: str, timeout: int = 30) -> Set[str]:
        """Безопасный запрос к CRT.SH с ограничением времени"""
        domains = set()

        url = f"https://crt.sh/?q={quote(pattern)}&output=json"
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "application/json",
            "Referer": "https://crt.sh/"
        }

        try:
            # Ограничиваем время выполнения запроса
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False, timeout=timeout) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                        except:
                            text = await response.text()
                            # Пробуем очистить JSON
                            text = text.strip()
                            if text.startswith('['):
                                data = json.loads(text)
                            else:
                                match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
                                if match:
                                    data = json.loads(match.group(0))
                                else:
                                    return set()

                        # Извлекаем домены
                        for item in data:
                            if isinstance(item, dict):
                                # Проверяем разные поля
                                for field in ['name_value', 'common_name', 'dNSName']:
                                    if field in item and item[field]:
                                        found = self._extract_domains(str(item[field]))
                                        domains.update(found)

                    elif response.status == 429:
                        logger.warning(f"   Rate limit для {pattern}")
                    elif response.status == 503:
                        logger.warning(f"   Сервис недоступен для {pattern}")

        except asyncio.TimeoutError:
            logger.warning(f"   Таймаут для {pattern}")
        except Exception as e:
            logger.debug(f"   Ошибка запроса: {e}")

        return domains

    def _extract_domains(self, text: str) -> Set[str]:
        """Извлекает домены из текста"""
        domains = set()

        if not text:
            return domains

        # Регулярное выражение для поиска доменов
        pattern = r'([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'
        matches = re.finditer(pattern, text)

        for match in matches:
            domain = match.group(0).lower().strip()

            # Очистка домена
            domain = self._clean_domain(domain)

            if domain:
                domains.add(domain)

        return domains

    def _clean_domain(self, domain: str) -> str:
        """Очищает домен"""
        if not domain:
            return ""

        domain = domain.lower().strip()

        # Удаляем wildcards
        if domain.startswith('*.'):
            domain = domain[2:]

        # Удаляем протоколы
        if domain.startswith(('http://', 'https://')):
            domain = domain.split('://')[1]

        # Удаляем порт
        if ':' in domain:
            domain = domain.split(':')[0]

        # Удаляем путь
        if '/' in domain:
            domain = domain.split('/')[0]

        # Удаляем www.
        if domain.startswith('www.'):
            domain = domain[4:]

        # Проверяем валидность
        if not self._is_valid_domain(domain):
            return ""

        return domain

    def _is_valid_domain(self, domain: str) -> bool:
        """Проверяет валидность домена (использует метод родительского класса)"""
        # Используем базовую проверку из родительского класса
        return super()._is_valid_domain(domain)