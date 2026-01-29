"""
Базовый класс для источников данных
"""
import abc
import logging
import re
from typing import  Set
from config.settings import TargetConfig

logger = logging.getLogger(__name__)


class BaseSource(abc.ABC):
    """Абстрактный базовый класс для источников доменов"""

    def __init__(self, target_config: TargetConfig):
        self.target_config = target_config
        self.name = self.__class__.__name__
        self._compiled_exclude = []
        self._compiled_include = []

        # Компилируем regex паттерны для производительности
        for pattern in target_config.exclude_patterns:
            try:
                self._compiled_exclude.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Некорректный exclude паттерн '{pattern}': {e}")

        for pattern in target_config.include_patterns:
            try:
                self._compiled_include.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Некорректный include паттерн '{pattern}': {e}")

    @abc.abstractmethod
    async def get_domains(self) -> Set[str]:
        """Получает домены из источника"""
        pass

    def _filter_domains(self, domains: Set[str]) -> Set[str]:
        """Фильтрует домены по паттернам цели"""
        filtered = set()

        for domain in domains:
            domain_lower = domain.lower().strip()

            if not domain_lower:
                continue

            # Базовые проверки
            if not self._is_valid_domain(domain_lower):
                continue

            # Проверка исключающих паттернов
            if self._matches_exclude(domain_lower):
                continue

            # Проверка ключевых слов (для WhatsApp специфичных доменов)
            if not self._has_keyword(domain_lower):
                # Разрешаем только специфичные домены без ключевых слов
                if not self._is_whatsapp_specific(domain_lower):
                    continue

            # Проверка включающих паттернов (если есть)
            if self._compiled_include and not self._matches_include(domain_lower):
                continue

            filtered.add(domain)

        return filtered

    def _is_valid_domain(self, domain: str) -> bool:
        """Проверяет базовую валидность домена"""
        domain = domain.lower().strip()

        # Проверка длины
        if len(domain) < 4 or len(domain) > 253:
            return False

        # Проверка формата
        if not re.match(r'^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)+$', domain):
            return False

        # Двойные дефисы и точки
        if '--' in domain or '..' in domain:
            return False

        # Запрещенные символы в начале/конце
        if domain.startswith('-') or domain.endswith('-'):
            return False
        if domain.startswith('.') or domain.endswith('.'):
            return False

        # Слишком много поддоменов
        if domain.count('.') > 6:
            return False

        # Проверка TLD
        parts = domain.split('.')
        tld = parts[-1]
        if len(tld) < 2 or len(tld) > 10:
            return False

        return True

    def _matches_exclude(self, domain: str) -> bool:
        """Проверяет соответствие исключающим паттернам"""
        for pattern in self._compiled_exclude:
            try:
                if pattern.search(domain):
                    return True
            except:
                continue
        return False

    def _matches_include(self, domain: str) -> bool:
        """Проверяет соответствие включающим паттернам"""
        for pattern in self._compiled_include:
            try:
                if pattern.search(domain):
                    return True
            except:
                continue
        return False

    def _has_keyword(self, domain: str) -> bool:
        """Проверяет наличие ключевых слов"""
        for keyword in self.target_config.keywords:
            if keyword.lower() in domain:
                return True
        return False

    def _is_whatsapp_specific(self, domain: str) -> bool:
        """Проверяет, является ли домен специфичным для WhatsApp"""
        # Домены CDN Facebook (WhatsApp использует fbcdn.net)
        if domain.endswith('.fbcdn.net'):
            # Проверяем, что это действительно WhatsApp CDN
            whatsapp_patterns = [
                'whatsapp',
                'wa-',
                '-wa',
                'cdn-shv',
                'chatd',
                'mmg',
                'mms',
                'pps'
            ]
            for pattern in whatsapp_patterns:
                if pattern in domain:
                    return True

        # Домены с числовыми паттернами (s1.whatsapp.net, cdn1.fbcdn.net)
        if re.search(r'\.(whatsapp\.net|fbcdn\.net)$', domain):
            # Проверяем числовые паттерны
            if re.search(r'[scme]\d+\.|node\d+\.|edge\d+\.|server\d+\.', domain):
                return True

        return False