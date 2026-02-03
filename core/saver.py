"""
Сохранение результатов
"""
import json
import logging
import aiofiles
import ipaddress
from datetime import datetime
from typing import List, Dict, Any
from config.settings import TargetConfig

logger = logging.getLogger(__name__)


class ResultSaver:
    """Сохранение результатов в файлы"""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
    
    async def save_results(self,
                           domains: List[Dict[str, Any]],
                           ipv4_cidrs: List[str],
                           ipv6_cidrs: List[str],
                           target_config: TargetConfig):
        """Сохраняет все результаты"""
        
        # Разделяем домены на те, у которых есть IP и те, у которых нет
        domains_with_ips = [d for d in domains if d.get('ips') and len(d.get('ips', [])) > 0]
        domains_without_ips = [d for d in domains if not d.get('ips') or len(d.get('ips', [])) == 0]
        
        logger.info(f"💾 Для сохранения: {len(domains_with_ips)} доменов с IP, {len(domains_without_ips)} без IP")
        
        # 1. Сохраняем ТОЛЬКО домены с IP в domains.txt
        await self._save_domains_with_ips(domains_with_ips)
        
        # 2. Отдельно сохраняем домены без IP (опционально, для отладки)
        if domains_without_ips:
            await self._save_domains_without_ips(domains_without_ips)
        
        # 3. Сохраняем CIDR сети
        await self._save_cidrs(ipv4_cidrs, ipv6_cidrs)
        
        # 4. Сохраняем полный отчет в JSON
        await self._save_json_report(domains_with_ips, domains_without_ips,
                                     ipv4_cidrs, ipv6_cidrs, target_config)
    
    async def _save_domains_with_ips(self, domains_with_ips: List[Dict[str, Any]]):
        """Сохраняет ТОЛЬКО домены с IP в TXT файл"""
        filename = f"{self.output_dir}/domains.txt"
        
        # Извлекаем только домены с IP
        domains = [d['domain'] for d in domains_with_ips]
        domains = sorted(set(domains))  # Уникальные и отсортированные
        
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            # Заголовок
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await f.write(f"# Domain Scanner Results\n")
            await f.write(f"# Generated: {timestamp}\n")
            await f.write(f"# Total domains with IP addresses: {len(domains)}\n")
            await f.write("#" * 50 + "\n\n")
            
            # Только домены с IP
            for domain in domains:
                await f.write(f"{domain}\n")
        
        logger.info(f"📁 Домены с IP сохранены: {filename} ({len(domains)} доменов)")
    
    async def _save_domains_without_ips(self, domains_without_ips: List[Dict[str, Any]]):
        """Сохраняет домены без IP в отдельный файл (для отладки)"""
        filename = f"{self.output_dir}/domains_no_ip.txt"
        
        domains = [d['domain'] for d in domains_without_ips]
        domains = sorted(set(domains))
        
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await f.write(f"# Domains without IP addresses\n")
            await f.write(f"# Generated: {timestamp}\n")
            await f.write(f"# Total domains: {len(domains)}\n")
            await f.write("# These domains did not resolve to any IP address\n")
            await f.write("#" * 50 + "\n\n")
            
            for domain in domains:
                await f.write(f"{domain}\n")
        
        logger.info(f"📁 Домены без IP сохранены: {filename} ({len(domains)} доменов)")
    
    async def _save_cidrs(self, ipv4_cidrs: List[str], ipv6_cidrs: List[str]):
        """Сохраняет CIDR сети в отдельные файлы"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # IPv4 CIDR
        if ipv4_cidrs:
            filename = f"{self.output_dir}/cidr_ipv4.txt"
            
            # Сортируем CIDR
            def sort_ipv4(cidr):
                try:
                    net = ipaddress.IPv4Network(cidr)
                    return (net.network_address._ip, net.prefixlen)
                except:
                    return (0, 0)
            
            sorted_cidrs = sorted(ipv4_cidrs, key=sort_ipv4)
            
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(f"# IPv4 CIDR Networks\n")
                await f.write(f"# Generated: {timestamp}\n")
                await f.write(f"# Total networks: {len(sorted_cidrs)}\n")
                await f.write("#" * 50 + "\n\n")
                
                for cidr in sorted_cidrs:
                    await f.write(f"{cidr}\n")
            
            logger.info(f"📁 IPv4 CIDR сохранены: {filename} ({len(sorted_cidrs)} сетей)")
        
        # IPv6 CIDR
        if ipv6_cidrs:
            filename = f"{self.output_dir}/cidr_ipv6.txt"
            
            # Фильтруем некорректные CIDR
            filtered_ipv6_cidrs = []
            for cidr in ipv6_cidrs:
                try:
                    network = ipaddress.IPv6Network(cidr)
                    # Исключаем некорректные сети
                    if str(network.network_address) != "::" or network.prefixlen < 32:
                        filtered_ipv6_cidrs.append(cidr)
                except:
                    logger.debug(f"⚠️ Пропущен некорректный IPv6 CIDR: {cidr}")
            
            # Сортируем CIDR
            def sort_ipv6(cidr):
                try:
                    net = ipaddress.IPv6Network(cidr)
                    return (net.network_address._ip, net.prefixlen)
                except:
                    return (0, 0)
            
            sorted_cidrs = sorted(filtered_ipv6_cidrs, key=sort_ipv6)
            
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(f"# IPv6 CIDR Networks\n")
                await f.write(f"# Generated: {timestamp}\n")
                await f.write(f"# Total networks: {len(sorted_cidrs)}\n")
                await f.write("#" * 50 + "\n\n")
                
                for cidr in sorted_cidrs:
                    await f.write(f"{cidr}\n")
            
            logger.info(f"📁 IPv6 CIDR сохранены: {filename} ({len(sorted_cidrs)} сетей)")
    
    async def _save_json_report(self,
                                domains_with_ips: List[Dict[str, Any]],
                                domains_without_ips: List[Dict[str, Any]],
                                ipv4_cidrs: List[str],
                                ipv6_cidrs: List[str],
                                target_config: TargetConfig):
        """Сохраняет полный отчет в JSON"""
        filename = f"{self.output_dir}/report.json"
        
        # Собираем статистику
        unique_ips = set()
        for domain in domains_with_ips:
            unique_ips.update(domain.get('ips', []))
        
        report = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "target": target_config.name,
                "description": target_config.description,
                "statistics": {
                    "total_domains_scanned": len(domains_with_ips) + len(domains_without_ips),
                    "domains_with_ips": len(domains_with_ips),
                    "domains_without_ips": len(domains_without_ips),
                    "unique_ips": len(unique_ips),
                    "ipv4_count": len([ip for ip in unique_ips if '.' in ip]),
                    "ipv6_count": len([ip for ip in unique_ips if ':' in ip]),
                    "ipv4_networks": len(ipv4_cidrs),
                    "ipv6_networks": len(ipv6_cidrs)
                }
            },
            "domains_with_ips": domains_with_ips[:500],  # Ограничиваем для производительности
            "domains_without_ips_count": len(domains_without_ips),
            "networks": {
                "ipv4": ipv4_cidrs,
                "ipv6": ipv6_cidrs
            },
            "config": target_config.to_dict()
        }
        
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(report, indent=2, ensure_ascii=False))
        
        logger.info(f"📊 JSON отчет сохранен: {filename}")