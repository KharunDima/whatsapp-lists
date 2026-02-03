"""
Валидация доменов
"""
import re
import logging
from typing import List, Set
from config.settings import TargetConfig
from utils.meta_filter import create_meta_filter
logger = logging.getLogger(__name__)


class DomainValidator:
    """Валидатор доменов"""
    
    def __init__(self, target_config: TargetConfig):
        self.target_config = target_config
        self.meta_filter = create_meta_filter()
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
        """Проверяет валидность домена с использованием Meta фильтра"""
        domain_lower = domain.lower().strip()
        
        # 1. Быстрая проверка исключений
        if self.meta_filter.should_exclude_domain(domain_lower):
            return False
        
        # 2. Проверка через Meta фильтр
        if not (self.meta_filter.is_whatsapp_domain(domain_lower) or
                self.meta_filter.is_meta_domain(domain_lower)):
            return False
        
        # 3. Проверка базовой валидности
        if not self._is_basic_valid(domain_lower):
            return False
        
        # 4. Проверка исключающих паттернов из конфига
        if self._matches_exclude(domain_lower):
            return False
        
        # 5. Проверка включающих паттернов (если есть)
        if self._compiled_include and not self._matches_include(domain_lower):
            return False
        
        return True
    
    def _is_basic_valid(self, domain: str) -> bool:
        """Базовые проверки домена"""
        # Используем проверку из Meta фильтра
        return self.meta_filter.is_valid_domain_format(domain)

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