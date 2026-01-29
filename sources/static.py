"""
Статические домены и генерация
"""
import logging
from typing import Set
from .base import BaseSource

logger = logging.getLogger(__name__)


class StaticSource(BaseSource):
    """Источник статических и сгенерированных доменов"""

    async def get_domains(self) -> Set[str]:
        """Получает статические и генерирует домены"""
        domains = set()

        # 1. Статические домены из конфига
        domains.update(self.target_config.static_domains)
        logger.info(f"📋 Статические домены: {len(self.target_config.static_domains)}")

        # 2. Генерация из шаблонов (ограниченная)
        generated = self._generate_from_templates()
        domains.update(generated)
        logger.info(f"🔧 Сгенерировано из шаблонов: {len(generated)}")

        # 3. Генерация поддоменов
        subdomains = self._generate_subdomains()
        domains.update(subdomains)
        logger.info(f"🌐 Сгенерировано поддоменов: {len(subdomains)}")

        # 4. Числовые паттерны (ограниченные)
        numeric = self._generate_numeric_patterns()
        domains.update(numeric)
        logger.info(f"🔢 Числовые паттерны: {len(numeric)}")

        return self._filter_domains(domains)

    def _generate_from_templates(self) -> Set[str]:
        """Генерирует домены из шаблонов"""
        domains = set()

        for template in self.target_config.domain_templates:
            if 'bsg{num:03d}' in template:
                # Генерация bsg паттернов (только реальные)
                for i in [1, 2, 3, 4, 5, 6, 10, 20, 30, 50, 100]:
                    try:
                        domain = template.format(num=f"{i:03d}")
                        domains.add(domain)
                    except:
                        continue
            elif '{shard}' in template and '{server}' in template:
                # Генерация CDN паттернов
                for shard in [1, 2, 3, 4]:
                    for server in [1, 2, 3, 4]:
                        try:
                            domain = template.format(shard=shard, server=server)
                            domains.add(domain)
                        except:
                            continue
            elif '{num}' in template:
                # Ограниченная генерация числовых шаблонов
                for i in range(1, 21):  # Только первые 20
                    try:
                        if ':03d' in template:
                            domain = template.format(num=f"{i:03d}")
                        else:
                            domain = template.format(num=i)
                        domains.add(domain)
                    except:
                        continue
            else:
                domains.add(template)

        return domains

    def _generate_subdomains(self) -> Set[str]:
        """Генерирует поддомены для основных доменов"""
        domains = set()

        # Основные домены для генерации
        base_domains = [
            "whatsapp.com",
            "whatsapp.net",
            "wa.me",
            "fbcdn.net"
        ]

        for base in base_domains:
            # Добавляем сам домен
            domains.add(base)

            # Генерируем только релевантные поддомены
            relevant_subs = [
                "www", "web", "api", "chat", "call", "business",
                "status", "cdn", "static", "media", "upload",
                "download", "assets", "app", "portal", "admin"
            ]

            for sub in relevant_subs:
                if sub in self.target_config.subdomains:
                    domains.add(f"{sub}.{base}")

        return domains

    def _generate_numeric_patterns(self) -> Set[str]:
        """Генерирует числовые паттерны (только реальные)"""
        domains = set()

        # Основные домены для числовых паттернов
        numeric_domains = ["whatsapp.net", "fbcdn.net"]

        for base in numeric_domains:
            for pattern in self.target_config.numeric_patterns:
                # Ограничиваем генерацию
                max_num = 50 if 'whatsapp' in base else 10

                for i in range(1, max_num + 1):
                    try:
                        if ':03d' in pattern:
                            sub = pattern.format(num=f"{i:03d}")
                        else:
                            sub = pattern.format(num=i)

                        domain = f"{sub}.{base}"

                        # Проверяем, что это релевантный паттерн
                        if self._is_relevant_numeric_pattern(domain):
                            domains.add(domain)
                    except:
                        continue

        return domains

    def _is_relevant_numeric_pattern(self, domain: str) -> bool:
        """Проверяет, является ли числовой паттерн релевантным"""
        # Релевантные паттерны WhatsApp
        relevant_patterns = [
            r'[scme]\d+\.whatsapp\.net$',
            r'node\d+\.whatsapp\.net$',
            r'edge\d+\.whatsapp\.net$',
            r'server\d+\.whatsapp\.net$',
            r'bsg\d+\.whatsapp\.net$',
            r'whatsapp-cdn-shv[-\d]+\.fbcdn\.net$',
            r'whatsapp-chatd[-\d]+\.fbcdn\.net$',
        ]

        import re
        for pattern in relevant_patterns:
            if re.match(pattern, domain):
                return True

        return False