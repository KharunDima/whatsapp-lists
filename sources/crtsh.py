"""
Поиск доменов через CRT.SH - парсинг HTML версия
"""
import aiohttp
import asyncio
import logging
import re
import random
from typing import Set
from urllib.parse import quote
from bs4 import BeautifulSoup

from .base import BaseSource

logger = logging.getLogger(__name__)


class CRTShSource(BaseSource):
    """Источник доменов из CRT.SH с парсингом HTML"""
    
    def __init__(self, target_config):
        super().__init__(target_config)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
    
    async def get_domains(self) -> Set[str]:
        """Получает домены из CRT.SH через HTML парсинг"""
        domains = set()
        
        # Паттерны для поиска (используем простые, без %)
        patterns = [
            ("whatsapp.net", "whatsapp.net"),
            ("whatsapp.com", "whatsapp.com"),
            ("wa.me", "wa.me"),
            ("fbcdn.net", "fbcdn.net"),
            ("facebook.com", "facebook.com"),
            ("fb.com", "fb.com"),
        ]
        
        for name, pattern in patterns:
            try:
                logger.info(f"🌐 CRT.SH HTML: {name}")
                pattern_domains = await self._query_crt_sh_html(pattern)
                
                if pattern_domains:
                    domains.update(pattern_domains)
                    logger.info(f"   Найдено: {len(pattern_domains)} доменов")
                    
                    # Покажем примеры
                    if len(pattern_domains) > 0:
                        sample = list(pattern_domains)[:3]
                        for domain in sample:
                            logger.debug(f"     • {domain}")
                else:
                    logger.debug(f"   Не найдено доменов")
                
                # Задержка между запросами
                await asyncio.sleep(random.uniform(5, 8))
            
            except Exception as e:
                logger.warning(f"⚠️ Ошибка для '{name}': {str(e)[:100]}")
        
        # Фильтрация
        filtered = self._filter_domains(domains)
        logger.info(f"✅ CRT.SH: всего {len(filtered)} доменов после фильтрации")
        return filtered
    
    async def _query_crt_sh_html(self, pattern: str, timeout: int = 60) -> Set[str]:
        """Запрос к CRT.SH с парсингом HTML"""
        domains = set()
        
        # URL для HTML поиска (без &output=json)
        url = f"https://crt.sh/?q={quote(pattern)}"
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    
                    logger.debug(f"   Статус: {response.status}")
                    
                    if response.status == 200:
                        html = await response.text()
                        
                        # Парсим HTML с BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Метод 1: Ищем в таблице результатов
                        table_domains = self._parse_results_table(soup)
                        domains.update(table_domains)
                        
                        # Метод 2: Ищем во всем тексте
                        text_domains = self._extract_domains_from_text(html)
                        domains.update(text_domains)
                        
                        # Метод 3: Ищем ссылки
                        link_domains = self._parse_links(soup)
                        domains.update(link_domains)
                        
                        logger.debug(f"   HTML парсинг: найдено {len(domains)} доменов")
                    
                    elif response.status == 429:
                        logger.warning(f"   Rate limit, ждем 20 секунд...")
                        await asyncio.sleep(20)
                    elif response.status == 502 or response.status == 503:
                        logger.warning(f"   Сервис временно недоступен (HTTP {response.status})")
                    else:
                        logger.warning(f"   HTTP {response.status}")
        
        except asyncio.TimeoutError:
            logger.warning(f"   Таймаут запроса")
        except aiohttp.ClientError as e:
            logger.warning(f"   Ошибка клиента: {e}")
        except Exception as e:
            logger.debug(f"   Ошибка запроса: {e}")
        
        return domains
    
    def _parse_results_table(self, soup) -> Set[str]:
        """Парсит таблицу результатов CRT.SH"""
        domains = set()
        
        try:
            # Ищем таблицу с результатами
            tables = soup.find_all('table')
            
            for table in tables:
                # Ищем строки таблицы
                rows = table.find_all('tr')
                
                for row in rows:
                    # Ищем ячейки с доменами
                    cells = row.find_all('td')
                    
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if text:
                            # Очищаем и добавляем домен
                            domain = self._clean_domain(text)
                            if domain and self._is_potential_target_domain(domain):
                                domains.add(domain)
                            
                            # Также проверяем ссылки в ячейке
                            links = cell.find_all('a')
                            for link in links:
                                href = link.get('href', '')
                                if href and '?id=' in href:
                                    # Это может быть ссылка на сертификат
                                    link_text = link.get_text(strip=True)
                                    if link_text:
                                        domain = self._clean_domain(link_text)
                                        if domain and self._is_potential_target_domain(domain):
                                            domains.add(domain)
        
        except Exception as e:
            logger.debug(f"   Ошибка парсинга таблицы: {e}")
        
        return domains
    
    def _extract_domains_from_text(self, html: str) -> Set[str]:
        """Извлекает домены из текста HTML"""
        domains = set()
        
        if not html:
            return domains
        
        # Убираем HTML теги для чистого текста
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Ищем домены в тексте
        # Паттерн для доменов
        domain_pattern = r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
        matches = re.findall(domain_pattern, text)
        
        for match in matches:
            cleaned = self._clean_domain(match)
            if cleaned and self._is_potential_target_domain(cleaned):
                domains.add(cleaned)
        
        return domains
    
    def _parse_links(self, soup) -> Set[str]:
        """Парсит ссылки на странице"""
        domains = set()
        
        try:
            links = soup.find_all('a')
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Проверяем URL ссылки
                if href:
                    # Извлекаем домен из URL
                    domain_from_href = self._extract_domain_from_url(href)
                    if domain_from_href and self._is_potential_target_domain(domain_from_href):
                        domains.add(domain_from_href)
                
                # Проверяем текст ссылки
                if text:
                    domain_from_text = self._clean_domain(text)
                    if domain_from_text and self._is_potential_target_domain(domain_from_text):
                        domains.add(domain_from_text)
        
        except Exception as e:
            logger.debug(f"   Ошибка парсинга ссылок: {e}")
        
        return domains
    
    def _extract_domain_from_url(self, url: str) -> str:
        """Извлекает домен из URL"""
        if not url:
            return ""
        
        # Убираем протокол
        url = re.sub(r'^https?://', '', url)
        
        # Убираем путь и параметры
        url = url.split('/')[0]
        url = url.split('?')[0]
        url = url.split('#')[0]
        
        # Убираем порт
        url = url.split(':')[0]
        
        return self._clean_domain(url)
    
    def _is_potential_target_domain(self, domain: str) -> bool:
        """Проверяет, может ли домен быть целью"""
        if not domain:
            return False
        
        domain_lower = domain.lower()
        
        # Ключевые слова Facebook/WhatsApp
        target_keywords = [
            'whatsapp', 'wa', 'facebook', 'fb', 'meta', 'fbcdn',
            'instagram', 'oculus', 'threads', 'workplace'
        ]
        
        # Проверяем наличие ключевых слов
        for keyword in target_keywords:
            if keyword in domain_lower:
                return True
        
        # Также разрешаем домены с паттернами инфраструктуры
        infra_patterns = [
            r'\.fna\.(whatsapp\.net|fbcdn\.net)$',
            r'f[a-z]{3}\d+-\d+\.fna\.',
            r'[scme]\d+\.whatsapp\.net$',
            r'node\d+\.whatsapp\.net$',
            r'edge\d+\.whatsapp\.net$',
            r'server\d+\.whatsapp\.net$',
            r'bsg\d+\.whatsapp\.net$',
        ]
        
        for pattern in infra_patterns:
            if re.search(pattern, domain_lower):
                return True
        
        return False
    
    def _clean_domain(self, domain: str) -> str:
        """Очищает домен"""
        if not domain:
            return ""
        
        domain = domain.lower().strip()
        
        # Удаляем wildcard
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
        
        # Удаляем кавычки и лишние символы
        domain = domain.strip('"\'`<>[]()')
        
        # Проверяем валидность
        if not self._is_valid_domain(domain):
            return ""
        
        return domain
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Проверяет валидность домена"""
        if not domain or len(domain) < 4 or len(domain) > 253:
            return False
        
        # Должна содержать точку
        if '.' not in domain:
            return False
        
        # Не IP адрес
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
            return False
        
        # Двойные дефисы или точки
        if '--' in domain or '..' in domain:
            return False
        
        # Не начинается/заканчивается дефисом или точкой
        if domain.startswith(('-', '.')) or domain.endswith(('-', '.')):
            return False
        
        # Проверка TLD
        parts = domain.split('.')
        if len(parts) < 2:
            return False
        
        tld = parts[-1]
        if len(tld) < 2 or len(tld) > 10:
            return False
        
        return True
    
    def _filter_domains(self, domains: Set[str]) -> Set[str]:
        """Фильтрация доменов"""
        filtered = set()
        
        for domain in domains:
            domain_lower = domain.lower()
            
            # Быстрые проверки
            if not domain_lower or len(domain_lower) < 4:
                continue
            
            # Пропускаем явный мусор
            if self._is_garbage_domain(domain_lower):
                continue
            
            # Проверяем исключающие паттерны
            if self._matches_exclude(domain_lower):
                continue
            
            # Должен содержать ключевые слова или быть инфраструктурой
            if self._is_potential_target_domain(domain_lower):
                filtered.add(domain_lower)
        
        return filtered
    
    def _is_garbage_domain(self, domain: str) -> bool:
        """Проверяет, является ли домен мусором"""
        garbage_patterns = [
            r'\.click$',
            r'\.gratis$',
            r'\.free$',
            r'\.download$',
            r'\.apk$',
            r'cloudflaressl\.com$',
            r'\.tk$|\.ml$|\.ga$|\.cf$|\.gq$|\.xyz$|\.top$|\.club$|\.site$|\.online$|\.info$',
            r'whatsapp.*whatsapp',  # Повторения
            r'descargar.*whatsapp',
            r'baixar.*whatsapp',
            r'kostenlos.*whatsapp',
            r'--\d+',  # Двойные дефисы с числами
        ]
        
        for pattern in garbage_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return True
        
        return False