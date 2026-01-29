"""
Валидация доменов
"""
import re
import logging
from typing import List, Set
from config.settings import TargetConfig

logger = logging.getLogger(__name__)


class DomainValidator:
    """Валидатор доменов"""

    def __init__(self, target_config: TargetConfig):
        self.target_config = target_config
        self._compiled_exclude = []
        self._compiled_include = []

        # Компилируем regex паттерны
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

    def is_valid(self, domain: str) -> bool:
        """Проверяет валидность домена"""
        domain_lower = domain.lower().strip()

        # Базовые проверки
        if not self._is_basic_valid(domain_lower):
            return False

        # Проверка ключевых слов
        if not self._has_keyword(domain_lower):
            # Разрешаем только специфичные WhatsApp домены
            if not self._is_whatsapp_specific(domain_lower):
                return False

        # Проверка исключающих паттернов
        if self._matches_exclude(domain_lower):
            return False

        # Проверка включающих паттернов (если есть)
        if self._compiled_include and not self._matches_include(domain_lower):
            return False

        # Дополнительные проверки для WhatsApp
        return self._is_valid_whatsapp_domain(domain_lower)

    def _is_basic_valid(self, domain: str) -> bool:
        """Базовые проверки домена"""
        if len(domain) < 4 or len(domain) > 253:
            return False

        # Проверка формата
        if not re.match(r'^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)+$', domain):
            return False

        # Двойные дефисы
        if '--' in domain:
            return False

        # Двойные точки
        if '..' in domain:
            return False

        # Начинается или заканчивается дефисом/точкой
        if domain.startswith('-') or domain.endswith('-'):
            return False
        if domain.startswith('.') or domain.endswith('.'):
            return False

        # Слишком много поддоменов
        if domain.count('.') > 5:
            return False

        # Проверка TLD
        parts = domain.split('.')
        if len(parts) < 2:
            return False

        tld = parts[-1]
        if len(tld) < 2 or len(tld) > 10:
            return False

        # Избегаем очевидно некорректных TLD
        invalid_tlds = {'local', 'localhost', 'test', 'example', 'invalid'}
        if tld in invalid_tlds:
            return False

        return True

    def _has_keyword(self, domain: str) -> bool:
        """Проверяет наличие ключевых слов"""
        keywords = self.target_config.keywords
        domain_lower = domain.lower()

        for keyword in keywords:
            if keyword.lower() in domain_lower:
                return True

        return False

    def _is_whatsapp_specific(self, domain: str) -> bool:
        """Проверяет, является ли домен специфичным для WhatsApp"""
        # WhatsApp использует fbcdn.net для CDN
        if domain.endswith('.fbcdn.net'):
            # Проверяем паттерны WhatsApp в субдоменах
            whatsapp_patterns = [
                'whatsapp',
                'wa-',
                '-wa',
                'cdn-shv',
                'chatd',
                'mmg',
                'mms',
                'pps',
                'edge',
                'bsg'
            ]
            for pattern in whatsapp_patterns:
                if pattern in domain:
                    return True

            # Числовые CDN сервера (s1, c1, m1 и т.д.)
            if re.search(r'[scme]\d+\.fbcdn\.net$', domain):
                return True

        # Домены с числовыми серверами WhatsApp
        if domain.endswith('.whatsapp.net'):
            if re.search(r'[scme]\d+\.|node\d+\.|edge\d+\.|server\d+\.', domain):
                return True

        return False

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

    def _is_valid_whatsapp_domain(self, domain: str) -> bool:
        """Дополнительные проверки для WhatsApp доменов"""
        # Избегаем явно сгенерированных или спам доменов
        garbage_patterns = [
            r'--\d+',
            r'whatsapp.*whatsapp',  # повторения
            r'test.*whatsapp',
            r'fake.*whatsapp',
            r'kostenlos.*whatsapp',
            r'whatsapp.*handy',
            r'whatsapp.*gratis',
            r'whatsapp.*free',
            r'\.helpclean\.',
            r'\.wingforum\.',
            r'whatsapp.*\.(de|ru|fr|es|pl|it)$',  # региональные, не относящиеся к инфраструктуре
            r'.*\.(tk|ml|ga|cf|gq|xyz)$',  # бесплатные домены
            r'^localhost\.',
            r'^test\.',
            r'^dev\.',
            r'^staging\.'
        ]

        for pattern in garbage_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return False

        return True

    def filter_domains(self, domains: Set[str]) -> List[str]:
        """Фильтрует список доменов"""
        valid_domains = []

        for domain in domains:
            if self.is_valid(domain):
                valid_domains.append(domain)

        return valid_domains