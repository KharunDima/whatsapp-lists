"""
DNS резолвер с кэшированием и балансировкой
"""
import asyncio
import dns.asyncresolver
import dns.resolver
import logging
from typing import Dict, Tuple, List
from config.settings import AppConfig

logger = logging.getLogger(__name__)


class DNSResolver:
    """DNS резолвер с балансировкой и кэшированием"""

    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        self.cache = {}
        self.semaphore = asyncio.Semaphore(app_config.max_concurrent)

        # Создаем несколько резолверов для балансировки
        self.resolvers = []
        for server in app_config.dns_servers:
            resolver = dns.asyncresolver.Resolver()
            resolver.nameservers = [server]
            resolver.timeout = app_config.dns_timeout
            resolver.lifetime = app_config.dns_timeout * 2
            self.resolvers.append(resolver)

    async def resolve_domain(self, domain: str) -> Tuple[List[str], List[str]]:
        """Разрешает домен в IPv4 и IPv6 адреса"""
        # Проверяем кэш
        if domain in self.cache:
            return self.cache[domain]

        async with self.semaphore:
            ipv4_addresses = []
            ipv6_addresses = []

            # Используем случайный резолвер для балансировки
            resolver = self.resolvers[hash(domain) % len(self.resolvers)]

            # Разрешаем IPv4
            try:
                answers = await resolver.resolve(domain, 'A')
                ipv4_addresses = [str(r) for r in answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                pass  # Домен не имеет A записей
            except dns.resolver.Timeout:
                logger.debug(f"⌛ Таймаут IPv4 для {domain}")
            except Exception as e:
                logger.debug(f"⚠️ Ошибка IPv4 для {domain}: {e}")

            # Разрешаем IPv6
            try:
                answers = await resolver.resolve(domain, 'AAAA')
                ipv6_addresses = [str(r) for r in answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                pass  # Домен не имеет AAAA записей
            except dns.resolver.Timeout:
                logger.debug(f"⌛ Таймаут IPv6 для {domain}")
            except Exception as e:
                logger.debug(f"⚠️ Ошибка IPv6 для {domain}: {e}")

            result = (ipv4_addresses, ipv6_addresses)
            self.cache[domain] = result

            return result

    async def resolve_batch(self, domains: List[str]) -> Dict[str, Tuple[List[str], List[str]]]:
        """Пакетное разрешение доменов"""
        logger.info(f"🔍 DNS разрешение для {len(domains)} доменов...")

        results = {}
        resolved_count = 0

        # Разбиваем на батчи
        batch_size = self.app_config.batch_size

        for i in range(0, len(domains), batch_size):
            batch = domains[i:i + batch_size]

            # Создаем задачи для батча
            tasks = []
            for domain in batch:
                task = asyncio.create_task(self.resolve_domain(domain))
                tasks.append((domain, task))

            # Ожидаем завершения батча
            for domain, task in tasks:
                try:
                    ipv4, ipv6 = await task
                    results[domain] = (ipv4, ipv6)

                    if ipv4 or ipv6:
                        resolved_count += 1
                except Exception as e:
                    logger.debug(f"Ошибка разрешения {domain}: {e}")
                    results[domain] = ([], [])

            # Прогресс
            processed = min(i + batch_size, len(domains))
            logger.info(f"  Прогресс: {processed}/{len(domains)} (разрешено: {resolved_count})")

            # Пауза между батчами
            if processed < len(domains):
                await asyncio.sleep(self.app_config.request_delay)

        logger.info(f"✅ Разрешено {resolved_count} из {len(domains)} доменов")
        return results