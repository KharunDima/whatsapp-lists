"""
Анализ IP адресов и создание CIDR сетей
"""
import ipaddress
import logging
from typing import List, Tuple
from config.settings import TargetConfig

logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """Анализатор сетей"""

    def __init__(self, target_config: TargetConfig):
        self.target_config = target_config

        # Известные диапазоны Facebook/WhatsApp
        self.facebook_ranges = [
            ipaddress.IPv4Network('31.13.0.0/16'),
            ipaddress.IPv4Network('66.220.144.0/20'),
            ipaddress.IPv4Network('69.63.176.0/20'),
            ipaddress.IPv4Network('69.171.224.0/19'),
            ipaddress.IPv4Network('74.119.76.0/22'),
            ipaddress.IPv4Network('102.132.96.0/20'),
            ipaddress.IPv4Network('103.4.96.0/22'),
            ipaddress.IPv4Network('129.134.0.0/16'),
            ipaddress.IPv4Network('157.240.0.0/16'),
            ipaddress.IPv4Network('173.252.64.0/18'),
            ipaddress.IPv4Network('179.60.192.0/22'),
            ipaddress.IPv4Network('185.60.216.0/22'),
            ipaddress.IPv4Network('199.201.64.0/22'),
            ipaddress.IPv4Network('204.15.20.0/22'),
        ]

    def analyze_ips(self, ips: List[str]) -> Tuple[List[str], List[str]]:
        """Анализирует IP и создает CIDR сети"""
        # Разделяем IPv4 и IPv6
        ipv4_list = []
        ipv6_list = []

        for ip in set(ips):
            if ':' in ip:
                ipv6_list.append(ip)
            else:
                ipv4_list.append(ip)

        logger.info(f"📊 Обработка {len(ipv4_list)} IPv4 и {len(ipv6_list)} IPv6 адресов")

        # Обрабатываем IPv4
        ipv4_cidrs = self._process_ipv4(ipv4_list)

        # Обрабатываем IPv6
        ipv6_cidrs = self._process_ipv6(ipv6_list)

        return ipv4_cidrs, ipv6_cidrs

    def _process_ipv4(self, ips: List[str]) -> List[str]:
        """Обрабатывает IPv4 адреса"""
        # Начинаем со статических CIDR
        all_cidrs = set(self.target_config.static_cidrs)

        # Добавляем известные диапазоны
        all_cidrs.update(self.target_config.known_ranges.get("ipv4", []))

        if not ips:
            logger.info("ℹ️ Нет IPv4 адресов для обработки")
            return self._optimize_cidrs(list(all_cidrs))

        # Конвертируем IP в объекты
        ip_objects = []
        for ip in ips:
            try:
                ip_obj = ipaddress.IPv4Address(ip)

                # Фильтруем приватные и тестовые IP
                if self._is_valid_ipv4(ip_obj):
                    ip_objects.append(ip_obj)
            except:
                logger.debug(f"⚠️ Некорректный IPv4 адрес: {ip}")

        if not ip_objects:
            logger.warning("⚠️ Не удалось создать объекты IPv4")
            return self._optimize_cidrs(list(all_cidrs))

        # Группируем IP по сетям
        networks = set()

        # Сначала проверяем, попадают ли IP в известные диапазоны Facebook
        facebook_ips = []
        other_ips = []

        for ip_obj in ip_objects:
            is_facebook = False
            for facebook_range in self.facebook_ranges:
                if ip_obj in facebook_range:
                    facebook_ips.append(ip_obj)
                    is_facebook = True
                    break

            if not is_facebook:
                other_ips.append(ip_obj)

        logger.info(f"  • IP в диапазонах Facebook: {len(facebook_ips)}")
        logger.info(f"  • Другие IP: {len(other_ips)}")

        # Для IP Facebook используем более агрессивную агрегацию
        for prefix in [24, 22, 20, 16]:
            for ip_obj in facebook_ips:
                try:
                    network = ipaddress.IPv4Network(f"{ip_obj}/{prefix}", strict=False)
                    if not self._is_private_or_test_network(network):
                        networks.add(network)
                except:
                    continue

        # Для других IP используем консервативную агрегацию
        for prefix in [24, 25, 26]:  # Меньшие префиксы для не-Facebook IP
            for ip_obj in other_ips:
                try:
                    network = ipaddress.IPv4Network(f"{ip_obj}/{prefix}", strict=False)
                    if not self._is_private_or_test_network(network):
                        # Проверяем, не является ли это массовым хостингом/CDN
                        if not self._is_mass_hosting_network(network):
                            networks.add(network)
                except:
                    continue

        # Добавляем найденные сети
        for net in networks:
            all_cidrs.add(str(net))

        # Оптимизируем CIDR
        optimized = self._optimize_cidrs(list(all_cidrs))

        logger.info(f"✅ Создано {len(optimized)} IPv4 CIDR сетей")
        return optimized

    def _process_ipv6(self, ips: List[str]) -> List[str]:
        """Обрабатывает IPv6 адреса"""
        # Статические CIDR (фильтруем только IPv6)
        all_cidrs = set([c for c in self.target_config.static_cidrs if ':' in c])

        # Известные диапазоны
        all_cidrs.update(self.target_config.known_ranges.get("ipv6", []))

        if not ips:
            logger.info("ℹ️ Нет IPv6 адресов для обработки")
            return self._optimize_ipv6_cidrs(list(all_cidrs))

        # Обрабатываем IPv6 адреса
        for ip in ips:
            try:
                ip_obj = ipaddress.IPv6Address(ip)
                network = ipaddress.IPv6Network(f"{ip_obj}/{self.target_config.ipv6_prefix}", strict=False)

                # Пропускаем приватные сети и некорректные CIDR
                if not network.is_private and not self._is_invalid_ipv6_network(network):
                    all_cidrs.add(str(network))
            except:
                logger.debug(f"⚠️ Некорректный IPv6 адрес: {ip}")

        result = self._optimize_ipv6_cidrs(list(all_cidrs))
        logger.info(f"✅ Создано {len(result)} IPv6 CIDR сетей")
        return result

    def _is_invalid_ipv6_network(self, network: ipaddress.IPv6Network) -> bool:
        """Проверяет, является ли IPv6 сеть некорректной"""
        # Исключаем слишком широкие сети и некорректные CIDR
        invalid_networks = [
            ipaddress.IPv6Network("::/0"),
            ipaddress.IPv6Network("::/16"),
            ipaddress.IPv6Network("::/32"),
            ipaddress.IPv6Network("::/48"),
            ipaddress.IPv6Network("::/64"),
            ipaddress.IPv6Network("2001:db8::/32"),  # Documentation network
            ipaddress.IPv6Network("fe80::/10"),  # Link-local
            ipaddress.IPv6Network("fc00::/7"),  # Unique local
            ipaddress.IPv6Network("ff00::/8"),  # Multicast
        ]

        for invalid_net in invalid_networks:
            if network == invalid_net:
                return True

        # Исключаем сети с префиксом больше 64 (слишком специфичные)
        if network.prefixlen > 64:
            return True

        return False

    def _optimize_ipv6_cidrs(self, cidrs: List[str]) -> List[str]:
        """Оптимизирует список IPv6 CIDR сетей"""
        if not cidrs:
            return []

        # Конвертируем в объекты сетей
        networks = []
        for cidr in cidrs:
            try:
                if ':' in cidr:  # Только IPv6
                    network = ipaddress.IPv6Network(cidr, strict=False)

                    # Фильтруем некорректные сети
                    if not self._is_invalid_ipv6_network(network):
                        networks.append(network)
            except:
                logger.debug(f"⚠️ Некорректный IPv6 CIDR: {cidr}")

        if not networks:
            return []

        # Удаляем подсети
        networks.sort(key=lambda x: x.prefixlen)  # Сначала сети с меньшим префиксом

        optimized = []
        for i, net in enumerate(networks):
            is_subnet = False
            for larger_net in networks[:i] + networks[i+1:]:
                if net.subnet_of(larger_net):
                    is_subnet = True
                    break
            if not is_subnet:
                optimized.append(net)

        # Сортируем по IP адресу
        optimized.sort(key=lambda x: x.network_address)

        # Конвертируем обратно в строки
        result = [str(net) for net in optimized]

        return result

    def _is_valid_ipv4(self, ip_obj: ipaddress.IPv4Address) -> bool:
        """Проверяет валидность IPv4 адреса"""
        # Исключаем приватные IP
        if ip_obj.is_private:
            return False

        # Исключаем loopback
        if ip_obj.is_loopback:
            return False

        # Исключаем link-local
        if ip_obj.is_link_local:
            return False

        # Исключаем тестовые сети
        test_nets = [
            ipaddress.IPv4Network('192.0.2.0/24'),    # TEST-NET-1
            ipaddress.IPv4Network('198.51.100.0/24'), # TEST-NET-2
            ipaddress.IPv4Network('203.0.113.0/24'),  # TEST-NET-3
            ipaddress.IPv4Network('198.18.0.0/15'),   # Network benchmark
        ]

        for test_net in test_nets:
            if ip_obj in test_net:
                return False

        return True

    def _is_mass_hosting_network(self, network: ipaddress.IPv4Network) -> bool:
        """Проверяет, не является ли сеть массовым хостингом/CDN"""
        # Крупные провайдеры хостинга/CDN
        mass_hosting_ranges = [
            ipaddress.IPv4Network('1.0.0.0/8'),      # APNIC
            ipaddress.IPv4Network('14.0.0.0/8'),     # ChinaNet
            ipaddress.IPv4Network('27.0.0.0/8'),     # ChinaNet
            ipaddress.IPv4Network('36.0.0.0/8'),     # ChinaNet
            ipaddress.IPv4Network('39.0.0.0/8'),     # ChinaNet
            ipaddress.IPv4Network('42.0.0.0/8'),     # ChinaNet
            ipaddress.IPv4Network('49.0.0.0/8'),     # APNIC
            ipaddress.IPv4Network('58.0.0.0/8'),     # ChinaNet
            ipaddress.IPv4Network('59.0.0.0/8'),     # ChinaNet
            ipaddress.IPv4Network('60.0.0.0/8'),     # APNIC
            ipaddress.IPv4Network('61.0.0.0/8'),     # APNIC
            ipaddress.IPv4Network('111.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('112.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('113.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('114.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('115.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('116.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('117.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('118.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('119.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('120.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('121.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('122.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('123.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('124.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('125.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('171.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('175.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('180.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('182.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('183.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('210.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('211.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('218.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('219.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('220.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('221.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('222.0.0.0/8'),    # ChinaNet
            ipaddress.IPv4Network('223.0.0.0/8'),    # ChinaNet
        ]

        for hosting_range in mass_hosting_ranges:
            if network.overlaps(hosting_range):
                return True

        return False

    def _optimize_cidrs(self, cidrs: List[str]) -> List[str]:
        """Оптимизирует список CIDR сетей"""
        if not cidrs:
            return []

        # Конвертируем в объекты сетей
        networks = []
        for cidr in cidrs:
            try:
                if ':' not in cidr:  # Только IPv4
                    network = ipaddress.IPv4Network(cidr, strict=False)

                    # Фильтруем приватные и тестовые сети
                    if not self._is_private_or_test_network(network):
                        networks.append(network)
            except:
                logger.debug(f"⚠️ Некорректный CIDR: {cidr}")

        if not networks:
            return []

        # Удаляем подсети
        networks.sort(key=lambda x: x.prefixlen)  # Сначала сети с меньшим префиксом (большие сети)

        optimized = []
        for i, net in enumerate(networks):
            is_subnet = False
            for larger_net in networks[:i] + networks[i+1:]:
                if net.subnet_of(larger_net):
                    is_subnet = True
                    break
            if not is_subnet:
                optimized.append(net)

        # Объединяем соседние сети
        merged = self._merge_adjacent_networks(optimized)

        # Сортируем по IP адресу
        merged.sort(key=lambda x: x.network_address)

        # Конвертируем обратно в строки
        result = [str(net) for net in merged]

        return result

    def _merge_adjacent_networks(self, networks: List[ipaddress.IPv4Network]) -> List[ipaddress.IPv4Network]:
        """Объединяет соседние сети"""
        if len(networks) <= 1:
            return networks

        networks.sort(key=lambda x: (x.network_address, x.prefixlen))
        merged = [networks[0]]

        for net in networks[1:]:
            last = merged[-1]

            # Проверяем, можно ли объединить
            if (last.prefixlen == net.prefixlen and
                    last.prefixlen > 8):  # Не объединяем очень большие сети

                # Проверяем, являются ли соседними
                if (last.broadcast_address + 1 == net.network_address):
                    # Объединяем
                    try:
                        supernet = last.supernet(new_prefix=last.prefixlen-1)
                        merged[-1] = supernet
                        continue
                    except:
                        pass

            merged.append(net)

        return merged

    def _is_private_or_test_network(self, network: ipaddress.IPv4Network) -> bool:
        """Проверяет, является ли сеть приватной или тестовой"""
        private_ranges = [
            ipaddress.IPv4Network("10.0.0.0/8"),
            ipaddress.IPv4Network("172.16.0.0/12"),
            ipaddress.IPv4Network("192.168.0.0/16"),
            ipaddress.IPv4Network("100.64.0.0/10"),  # CGNAT
            ipaddress.IPv4Network("127.0.0.0/8"),    # Loopback
            ipaddress.IPv4Network("169.254.0.0/16"), # Link-local
            ipaddress.IPv4Network("192.0.2.0/24"),   # TEST-NET-1
            ipaddress.IPv4Network("198.51.100.0/24"),# TEST-NET-2
            ipaddress.IPv4Network("203.0.113.0/24"), # TEST-NET-3
            ipaddress.IPv4Network("198.18.0.0/15"),  # Network benchmark
        ]

        for private_range in private_ranges:
            if network.overlaps(private_range):
                return True

        return False