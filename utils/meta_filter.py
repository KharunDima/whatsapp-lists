"""
Фильтрация доменов и IP-сетей для выявления легитимных сервисов WhatsApp и Meta
"""
import re
import ipaddress
import logging
import asyncio
import dns.asyncresolver
import aiohttp
from typing import List, Set, Dict, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MetaFilter:
	"""Фильтр для легитимных сервисов WhatsApp и Meta"""
	
	def __init__(self):
		self._compiled_patterns = self._compile_patterns()
		self.known_meta_cidrs = self._get_known_meta_cidrs()
		self.meta_asns = {"AS32934", "AS63293"}  # Facebook, Meta
		self.cache = {}
		self.cache_ttl = 3600  # 1 час
		
		# Кэш проверенных доменов
		self.domain_cache = {}
		self.dns_resolver = dns.asyncresolver.Resolver()
		self.dns_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
	
	def _compile_patterns(self) -> Dict[str, re.Pattern]:
		"""Компилирует паттерны для фильтрации"""
		patterns = {
			# WhatsApp официальные домены
			"whatsapp_official": re.compile(r'^([a-z0-9-]+\.)*whatsapp\.(com|net)$'),
			"wa_me": re.compile(r'^wa\.me$'),
			"whatsapp_subdomains": re.compile(r'^(c|e|s|m)\d+\.whatsapp\.net$'),
			"whatsapp_service": re.compile(r'^(web|chat|api|call|business|status)\.whatsapp\.com$'),
			
			# Meta/Facebook официальные домены
			"facebook_official": re.compile(r'^([a-z0-9-]+\.)*facebook\.com$'),
			"fbcdn_official": re.compile(r'^([a-z0-9-]+\.)*fbcdn\.net$'),
			"meta_official": re.compile(r'^([a-z0-9-]+\.)*meta\.com$'),
			"meta_domains": re.compile(r'^meta\.([a-z]+\.)?[a-z]+$'),
			"fbsbx_update": re.compile(r'^.*\.update\.fbsbx\.com$'),
			
			# Дополнительные официальные домены Meta
			"fb_watch": re.compile(r'^([a-z0-9-]+\.)*fb\.watch$'),
			"fb_gg": re.compile(r'^([a-z0-9-]+\.)*fb\.gg$'),
			"fb_com": re.compile(r'^([a-z0-9-]+\.)*fb\.com$'),
			"messenger_com": re.compile(r'^([a-z0-9-]+\.)*messenger\.com$'),
			"instagram_com": re.compile(r'^([a-z0-9-]+\.)*instagram\.com$'),
			"threads_net": re.compile(r'^([a-z0-9-]+\.)*threads\.net$'),
			"oculus_com": re.compile(r'^([a-z0-9-]+\.)*oculus\.com$'),
			"workplace_com": re.compile(r'^([a-z0-9-]+\.)*workplace\.com$'),
			
			# Региональные паттерны
			"regional_facebook": re.compile(r'^[a-z]{2}-[a-z]{2}\.facebook\.com$'),
			
			# CDN и инфраструктурные паттерны
			"whatsapp_cdn": re.compile(r'^whatsapp-(cdn|chatd|media|voice|video|stream)-[a-z0-9-]+\.fbcdn\.net$'),
			"edge_cdn": re.compile(r'^edge-[a-z0-9-]+\.(whatsapp\.net|fbcdn\.net)$'),
			"fb_static": re.compile(r'^static\.([a-z0-9-]+\.)?fbcdn\.net$'),
			"fb_external": re.compile(r'^external-[a-z0-9-]+\.(fbcdn\.net|facebook\.com)$'),
			
			# Исключающие паттерны
			"suspicious_tld": re.compile(r'\.(tk|ml|ga|cf|gq|xyz|top|club|site|online|info|biz|cc|pl|ru|de|fr|es|it)$'),
			"fake_domain": re.compile(r'.*(facebook|fb|meta|wa|whatsapp).*\.(com\.|net\.|org\.)?[a-z]{2,}'),
			"middle_keyword": re.compile(r'[a-z0-9]+-(facebook|fb|meta|wa|whatsapp)-[a-z0-9]+'),
			"spam_pattern": re.compile(r'(descargar|baixar|kostenlos|free|gratis|download|apk|mod|plus).*(whatsapp|facebook)'),
			"double_hyphen": re.compile(r'--'),
			
			# Новые форматы (разрешаем)
			"new_subdomain_format": re.compile(r'^[a-z0-9-]+-[a-z0-9-]+\.(whatsapp\.com|fbcdn\.net)$'),
			"cdn_shard": re.compile(r'^[a-z]{3}\d+-\d+\.fna\.fbcdn\.net$'),
			"fna_fbcdn": re.compile(r'^[a-z]{3}\d+\.[a-z]{2}\d+\.fna\.fbcdn\.net$'),
		}
		return patterns
	
	def _get_known_meta_cidrs(self) -> Set[ipaddress.IPv4Network]:
		"""Известные подсети Meta"""
		cidrs = [
			'31.13.0.0/16',
			'66.220.144.0/20',
			'69.63.176.0/20',
			'69.171.224.0/19',
			'129.134.0.0/16',
			'157.240.0.0/16',
			'173.252.64.0/18',
			'179.60.192.0/22',
			'185.60.216.0/22',
			'199.201.64.0/22',
			'204.15.20.0/22',
			'45.64.40.0/22',
			'74.119.76.0/22',
			'102.132.96.0/20',
			'103.4.96.0/22',
			
			# Новые диапазоны
			'31.13.24.0/21',
			'31.13.64.0/18',
			'157.240.8.0/21',
			'157.240.16.0/20',
			'157.240.32.0/19',
			'157.240.64.0/18',
			'157.240.128.0/17',
			
			# IPv6
			'2a03:2880::/32',
			'2620:0:1c00::/48',
			'2401:db00::/32',
		]
		
		return {ipaddress.ip_network(cidr) for cidr in cidrs}
	
	def is_valid_domain_format(self, domain: str) -> bool:
		"""Проверяет базовую валидность формата домена"""
		if not domain or len(domain) > 253 or len(domain) < 4:
			return False
		
		# Базовые проверки
		if domain.startswith('-') or domain.endswith('-'):
			return False
		if '--' in domain:
			return False
		if domain.count('.') < 1:
			return False
		
		# Проверка TLD
		tld = domain.split('.')[-1]
		if len(tld) < 2 or len(tld) > 10:
			return False
		
		return True
	
	def is_whatsapp_domain(self, domain: str) -> bool:
		"""Проверяет, является ли домен легитимным WhatsApp доменом"""
		if not self.is_valid_domain_format(domain):
			return False
		
		# 1. Точные совпадения
		if domain == 'wa.me':
			return True
		
		# 2. WhatsApp официальные домены
		if self._compiled_patterns["whatsapp_official"].match(domain):
			# Проверяем, что это не фишинговый домен в середине
			parts = domain.split('.')
			if len(parts) >= 3:
				# Разрешаем только официальные поддомены
				if parts[-2] == 'whatsapp':
					return True
		
		# 3. Специфичные поддомены WhatsApp
		if self._compiled_patterns["whatsapp_subdomains"].match(domain):
			return True
		
		if self._compiled_patterns["whatsapp_service"].match(domain):
			return True
		
		# 4. WhatsApp CDN через Facebook
		if self._compiled_patterns["whatsapp_cdn"].match(domain):
			return True
		
		# 5. Проверяем по паттернам
		domain_lower = domain.lower()
		
		# WhatsApp инфраструктура
		whatsapp_patterns = [
			r'^bsg\d+\.whatsapp\.net$',
			r'^node\d+\.whatsapp\.net$',
			r'^server\d+\.whatsapp\.net$',
			r'^edge\d+\.whatsapp\.net$',
			r'^media\d+\.whatsapp\.net$',
			r'^mms\d+\.whatsapp\.net$',
			r'^v\d+\.whatsapp\.net$',
			r'^mmg\d+\.whatsapp\.net$',
			r'^pps\d+\.whatsapp\.net$',
		]
		
		for pattern in whatsapp_patterns:
			if re.match(pattern, domain_lower):
				return True
		
		return False
	
	def is_meta_domain(self, domain: str) -> bool:
		"""Проверяет, является ли домен легитимным Meta доменом"""
		if not self.is_valid_domain_format(domain):
			return False
		
		domain_lower = domain.lower()
		
		# 1. Официальные домены Meta/Facebook
		official_patterns = [
			"facebook_official",
			"fbcdn_official",
			"meta_official",
			"fb_com",
			"messenger_com",
			"instagram_com",
			"threads_net",
			"oculus_com",
			"workplace_com",
			"fb_watch",
			"fb_gg",
		]
		
		for pattern_name in official_patterns:
			if self._compiled_patterns[pattern_name].match(domain_lower):
				# Исключаем явно фишинговые поддомены
				if not self._is_phishing_subdomain(domain_lower):
					return True
		
		# 2. Региональные домены Facebook
		if self._compiled_patterns["regional_facebook"].match(domain_lower):
			return True
		
		# 3. FBSBX update домены
		if self._compiled_patterns["fbsbx_update"].match(domain_lower):
			return True
		
		# 4. Meta домены второго уровня
		if self._compiled_patterns["meta_domains"].match(domain_lower):
			# Только если это meta.* (не metabusiness.*)
			if domain_lower.startswith('meta.') and '.' in domain_lower[5:]:
				return True
		
		# 5. CDN и инфраструктура
		infra_patterns = [
			"edge_cdn",
			"fb_static",
			"fb_external",
			"cdn_shard",
			"fna_fbcdn",
			"new_subdomain_format",
		]
		
		for pattern_name in infra_patterns:
			if self._compiled_patterns[pattern_name].match(domain_lower):
				return True
		
		# 6. Известные поддомены
		known_subdomains = {
			'pixel.facebook.com',
			'an.facebook.com',
			'graph.facebook.com',
			'connect.facebook.com',
			'developers.facebook.com',
			'code.facebook.com',
			'fb.com',
			'www.fb.com',
			'm.facebook.com',
			'mobile.facebook.com',
			'l.facebook.com',
			'lm.facebook.com',
			'api.facebook.com',
			'attachments.facebook.com',
			'secure.facebook.com',
			'apps.facebook.com',
			'ads.facebook.com',
			'business.facebook.com',
			'media.fbcdn.net',
			'static.fbcdn.net',
			'scontent.fbcdn.net',
			'video.fbcdn.net',
			'external.fbcdn.net',
		}
		
		if domain_lower in known_subdomains:
			return True
		
		# 7. Проверка по паттернам FNA (Facebook Network Architecture)
		if re.match(r'^f[a-z]{3}\d+-\d+\.fna\.fbcdn\.net$', domain_lower):
			return True
		
		if re.match(r'^[a-z]{3}\d+-\d+\.fna\.facebook\.com$', domain_lower):
			return True
		
		# 8. Домены с регионами в FNA
		if re.match(r'^[a-z]{2}[0-9]+\.[a-z]{2}[0-9]+\.fna\.fbcdn\.net$', domain_lower):
			return True
		
		return False
	
	def _is_phishing_subdomain(self, domain: str) -> bool:
		"""Проверяет, является ли поддомен фишинговым"""
		# Подозрительные паттерны в поддоменах
		suspicious_patterns = [
			r'facebook-color\.',
			r'fb-\w+-\w+\.',
			r'meta-\w+\.',
			r'whatsapp-\w+-\w+\.',
			r'\.5v\.pl$',
			r'\.work$',
			r'\.website$',
			r'\.online$',
		]
		
		for pattern in suspicious_patterns:
			if re.search(pattern, domain, re.IGNORECASE):
				return True
		
		# Проверяем TLD
		if self._compiled_patterns["suspicious_tld"].search(domain):
			return True
		
		# Проверяем спам паттерны
		if self._compiled_patterns["spam_pattern"].search(domain):
			return True
		
		# Проверяем ключевые слова в середине
		if self._compiled_patterns["middle_keyword"].search(domain):
			return True
		
		return False
	
	def is_meta_ip(self, ip: str) -> bool:
		"""Проверяет, принадлежит ли IP подсетям Meta"""
		try:
			ip_obj = ipaddress.ip_address(ip)
			
			# Проверяем известные CIDR
			for network in self.known_meta_cidrs:
				if ip_obj in network:
					return True
			
			# Проверяем IPv6
			if isinstance(ip_obj, ipaddress.IPv6Address):
				# Известные IPv6 подсети Meta
				ipv6_networks = [
					ipaddress.IPv6Network('2a03:2880::/32'),
					ipaddress.IPv6Network('2620:0:1c00::/48'),
					ipaddress.IPv6Network('2401:db00::/32'),
					ipaddress.IPv6Network('2a03:2880:f000::/48'),
					ipaddress.IPv6Network('2a03:2880:f100::/48'),
					ipaddress.IPv6Network('2a03:2880:f200::/48'),
					ipaddress.IPv6Network('2a03:2880:f300::/48'),
				]
				
				for network in ipv6_networks:
					if ip_obj in network:
						return True
		
		except (ValueError, ipaddress.AddressValueError):
			return False
		
		return False
	
	def should_exclude_domain(self, domain: str) -> bool:
		"""Определяет, нужно ли исключить домен"""
		if not domain:
			return True
		
		domain_lower = domain.lower()
		
		# 1. Быстрые проверки формата
		if not self.is_valid_domain_format(domain_lower):
			return True
		
		# 2. Исключаем подозрительные TLD
		if self._compiled_patterns["suspicious_tld"].search(domain_lower):
			return True
		
		# 3. Исключаем спам паттерны
		if self._compiled_patterns["spam_pattern"].search(domain_lower):
			return True
		
		# 4. Исключаем двойные дефисы
		if self._compiled_patterns["double_hyphen"].search(domain_lower):
			return True
		
		# 5. Исключаем явно фишинговые домены
		if self._compiled_patterns["fake_domain"].search(domain_lower):
			# Но разрешаем официальные домены
			if not (self.is_whatsapp_domain(domain_lower) or self.is_meta_domain(domain_lower)):
				return True
		
		# 6. Проверяем домены с цифрами в середине (кроме WhatsApp паттернов)
		if re.search(r'[a-z]+\d+[a-z]+\.', domain_lower):
			# Разрешаем только известные паттерны
			if not (re.match(r'^(c|e|s|m)\d+\.', domain_lower) or
			        re.match(r'^[a-z]{3}\d+\.', domain_lower)):
				return True
		
		return False
	
	def filter_domains(self, domains: List[str]) -> Tuple[List[str], List[str]]:
		"""Фильтрует список доменов, возвращая легитимные и исключенные"""
		legitimate = []
		excluded = []
		
		for domain in domains:
			if self.should_exclude_domain(domain):
				excluded.append(domain)
				continue
			
			# Проверяем, является ли домен легитимным
			if self.is_whatsapp_domain(domain) or self.is_meta_domain(domain):
				legitimate.append(domain)
			else:
				excluded.append(domain)
		
		return legitimate, excluded
	
	async def check_domain_with_dns(self, domain: str) -> bool:
		"""Проверяет домен через DNS"""
		cache_key = f"dns_check:{domain}"
		current_time = datetime.now()
		
		# Проверяем кэш
		if cache_key in self.cache:
			timestamp, result = self.cache[cache_key]
			if current_time - timestamp < timedelta(seconds=self.cache_ttl):
				return result
		
		try:
			# Проверяем A записи
			answers = await self.dns_resolver.resolve(domain, 'A')
			ips = [str(r) for r in answers]
			
			# Проверяем, есть ли хотя бы один IP из сетей Meta
			for ip in ips:
				if self.is_meta_ip(ip):
					self.cache[cache_key] = (current_time, True)
					return True
			
			# Проверяем CNAME записи
			try:
				cname_answers = await self.dns_resolver.resolve(domain, 'CNAME')
				for r in cname_answers:
					cname = str(r.target).rstrip('.')
					# Проверяем, ведет ли CNAME на официальный домен
					if self.is_whatsapp_domain(cname) or self.is_meta_domain(cname):
						self.cache[cache_key] = (current_time, True)
						return True
			except:
				pass
		
		except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
			pass
		except Exception as e:
			logger.debug(f"DNS check error for {domain}: {e}")
		
		self.cache[cache_key] = (current_time, False)
		return False
	
	async def enhance_filter_with_dns(self, domains: List[str]) -> List[str]:
		"""Улучшает фильтрацию с помощью DNS проверок"""
		legitimate = []
		
		# Параллельная проверка DNS
		semaphore = asyncio.Semaphore(50)  # Ограничиваем параллельные запросы
		
		async def check_domain(domain):
			async with semaphore:
				# Проверяем DNS
				has_valid_dns = await self.check_domain_with_dns(domain)
				return domain, has_valid_dns
		
		tasks = [check_domain(domain) for domain in domains]
		results = await asyncio.gather(*tasks, return_exceptions=True)
		
		for result in results:
			if isinstance(result, Exception):
				continue
			
			domain, has_valid_dns = result
			if has_valid_dns:
				legitimate.append(domain)
		
		return legitimate
	
	def filter_cidrs(self, cidrs: List[str]) -> List[str]:
		"""Фильтрует CIDR сети, оставляя только относящиеся к Meta"""
		meta_cidrs = []
		
		for cidr in cidrs:
			try:
				network = ipaddress.ip_network(cidr)
				
				# Проверяем, пересекается ли с известными сетями Meta
				is_meta = False
				for meta_network in self.known_meta_cidrs:
					if network.overlaps(meta_network):
						is_meta = True
						break
				
				# Для новых сетей проверяем, не являются ли они слишком общими
				if not is_meta:
					# Проверяем, не является ли сеть слишком большой или приватной
					if isinstance(network, ipaddress.IPv4Network):
						if network.prefixlen < 8 or network.prefixlen > 24:
							continue
						if network.is_private:
							continue
					else:
						if network.prefixlen < 32 or network.prefixlen > 64:
							continue
						if network.is_private:
							continue
				
				if is_meta:
					meta_cidrs.append(cidr)
			
			except (ValueError, ipaddress.NetmaskValueError):
				continue
		
		return meta_cidrs


def create_meta_filter():
	"""Создает экземпляр фильтра Meta"""
	return MetaFilter()