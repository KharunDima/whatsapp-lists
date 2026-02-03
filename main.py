"""
Domain Scanner Pro v5.0
Главный скрипт для поиска доменов и сетей
"""
import asyncio
import argparse
import sys
import os
import logging


# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import AppConfig, TargetConfig, load_target_config
from core.resolver import DNSResolver
from core.analyzer import NetworkAnalyzer
from core.saver import ResultSaver
from utils.helpers import setup_logging, create_output_dir, print_banner
from utils.validator import DomainValidator
from utils.meta_filter import create_meta_filter  # Добавляем импорт

# Импортируем источники
from sources.static import StaticSource
from sources.crtsh import CRTShSource
from sources.dns_bruteforce import DNSBruteforceSource
from sources.passive import PassiveSource

logger = logging.getLogger(__name__)


class DomainScanner:
    """Основной класс сканера"""
    
    def __init__(self, app_config: AppConfig, target_config: TargetConfig):
        self.app_config = app_config
        self.target_config = target_config
        self.validator = DomainValidator(target_config)
        self.meta_filter = create_meta_filter()  # Добавляем инициализацию Meta фильтра
        
        # Инициализация компонентов
        self.resolver = DNSResolver(app_config)
        self.analyzer = NetworkAnalyzer(target_config)
    
    async def run(self):
        """Основной метод выполнения"""
        try:
            print_banner()
            logger.info("=" * 70)
            logger.info(f"🔍 Domain Scanner Pro v5.0 - Target: {self.target_config.name}")
            logger.info("=" * 70)
            
            # 1. Сбор и предварительная валидация доменов
            logger.info("\n📁 Этап 1: Сбор и валидация доменов...")
            all_domains = await self._collect_and_validate_domains()
            
            if not all_domains:
                logger.error("❌ Домены не найдены!")
                return
            
            logger.info(f"✅ Всего собрано доменов после валидации: {len(all_domains)}")
            
            # 2. DNS разрешение
            logger.info("\n🔍 Этап 2: DNS разрешение...")
            domains_list = list(all_domains)
            ip_data = await self.resolver.resolve_batch(domains_list)
            
            # 3. Подготовка данных для сохранения - ТОЛЬКО домены с IP
            logger.info("\n📊 Этап 3: Подготовка данных...")
            domain_results = []
            valid_domains_list = []  # Только домены с IP
            all_ips = []
            domains_without_ips = []
            
            for domain in domains_list:
                ipv4, ipv6 = ip_data.get(domain, ([], []))
                ips = ipv4 + ipv6
                
                if ips:  # Только домены с IP
                    all_ips.extend(ips)
                    valid_domains_list.append(domain)
                    
                    domain_results.append({
                        'domain': domain,
                        'ips': ips,
                        'ipv4_count': len(ipv4),
                        'ipv6_count': len(ipv6),
                        'has_ips': True
                    })
                else:
                    domains_without_ips.append({
                        'domain': domain,
                        'ips': [],
                        'ipv4_count': 0,
                        'ipv6_count': 0,
                        'has_ips': False
                    })
            
            # Статистика
            unique_ips = set(all_ips)
            ipv4_count = len([ip for ip in unique_ips if '.' in ip])
            ipv6_count = len([ip for ip in unique_ips if ':' in ip])
            
            logger.info(f"✅ Разрешенные домены: {len(valid_domains_list)} из {len(domains_list)}")
            logger.info(f"✅ Уникальных IP: {len(unique_ips)} (IPv4: {ipv4_count}, IPv6: {ipv6_count})")
            
            # 4. Создание CIDR сетей
            logger.info("\n🔗 Этап 4: Создание CIDR сетей...")
            ipv4_cidrs, ipv6_cidrs = self.analyzer.analyze_ips(list(unique_ips))
            
            logger.info(f"✅ Создано CIDR сетей: {len(ipv4_cidrs) + len(ipv6_cidrs)}")
            logger.info(f"   • IPv4: {len(ipv4_cidrs)}")
            logger.info(f"   • IPv6: {len(ipv6_cidrs)}")
            
            # 5. Сохранение результатов
            logger.info("\n💾 Этап 5: Сохранение результатов...")
            output_dir = create_output_dir(self.app_config.output_dir)
            saver = ResultSaver(output_dir)
            
            await saver.save_results(
                domains=domain_results + domains_without_ips,  # Все домены, но разделенные
                ipv4_cidrs=ipv4_cidrs,
                ipv6_cidrs=ipv6_cidrs,
                target_config=self.target_config
            )
            
            # 6. Финальная статистика
            self._print_final_statistics(
                all_domains_count=len(domains_list),
                domains_with_ips=len(valid_domains_list),
                domains_without_ips=len(domains_without_ips),
                unique_ips=unique_ips,
                ipv4_cidrs=ipv4_cidrs,
                ipv6_cidrs=ipv6_cidrs,
                output_dir=output_dir
            )
        
        except KeyboardInterrupt:
            logger.info("\n\n⚠️ Поиск прерван пользователем")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
    
    async def _collect_domains(self) -> set:
        """Собирает домены из всех источников"""
        all_domains = set()
        
        # Инициализация источников
        sources = []
        
        if self.target_config.sources.get("static", True):
            sources.append(StaticSource(self.target_config))
        
        if self.target_config.sources.get("crt_sh", True):
            sources.append(CRTShSource(self.target_config))
        
        if self.target_config.sources.get("dns_bruteforce", True):
            sources.append(DNSBruteforceSource(self.target_config))
        
        if self.target_config.sources.get("passive", True):
            sources.append(PassiveSource(self.target_config))
        
        logger.info(f"📡 Используемые источники: {len(sources)}")
        
        # Сбор доменов из всех источников
        for source in sources:
            try:
                logger.info(f"🔄 Источник: {source.name}")
                domains = await source.get_domains()
                all_domains.update(domains)
                logger.info(f"   Найдено: {len(domains)} доменов")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка в источнике {source.name}: {e}")
        
        return all_domains
    
    async def _collect_and_validate_domains(self) -> set:
        """Собирает и проводит расширенную валидацию доменов с Meta фильтром"""
        # Сначала собираем все домены
        all_domains = await self._collect_domains()
        
        if not all_domains:
            return set()
        
        logger.info(f"📊 Всего доменов собрано: {len(all_domains)}")
        
        # Применяем Meta фильтр
        logger.info("🔄 Применение Meta фильтра...")
        
        legitimate_domains, excluded_domains = self.meta_filter.filter_domains(list(all_domains))
        
        logger.info(f"✅ Легитимные домены: {len(legitimate_domains)}")
        logger.info(f"🗑️  Исключено: {len(excluded_domains)}")
        
        # Примеры исключенных доменов
        if excluded_domains and len(excluded_domains) > 0:
            logger.debug(f"📝 Примеры исключенных доменов:")
            for domain in excluded_domains[:5]:
                logger.debug(f"   • {domain}")
        
        # Дополнительная DNS проверка для сомнительных доменов
        logger.info("🔍 Дополнительная DNS проверка...")
        enhanced_domains = await self.meta_filter.enhance_filter_with_dns(legitimate_domains)
        
        logger.info(f"✅ После DNS проверки: {len(enhanced_domains)} доменов")
        
        return set(enhanced_domains)
    
    def _print_final_statistics(self, all_domains_count, domains_with_ips, domains_without_ips,
                                unique_ips, ipv4_cidrs, ipv6_cidrs, output_dir):
        """Печатает финальную статистику"""
        logger.info("\n" + "=" * 70)
        logger.info("🎉 ПОИСК ЗАВЕРШЕН УСПЕШНО!")
        logger.info("=" * 70)
        logger.info("📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
        logger.info(f"   • Всего собрано доменов: {all_domains_count}")
        logger.info(f"   • Домены с IP адресами: {domains_with_ips}")
        logger.info(f"   • Домены без IP адресов: {domains_without_ips}")
        logger.info(f"   • Уникальные IP: {len(unique_ips)}")
        logger.info(f"     - IPv4: {len([ip for ip in unique_ips if '.' in ip])}")
        logger.info(f"     - IPv6: {len([ip for ip in unique_ips if ':' in ip])}")
        logger.info(f"   • CIDR сети: {len(ipv4_cidrs) + len(ipv6_cidrs)}")
        logger.info(f"     - IPv4: {len(ipv4_cidrs)}")
        logger.info(f"     - IPv6: {len(ipv6_cidrs)}")
        logger.info("=" * 70)
        
        # Примеры результатов
        logger.info("\n🔗 Примеры CIDR сетей:")
        sample_cidrs = ipv4_cidrs[:10] + ipv6_cidrs[:5]
        for i, cidr in enumerate(sample_cidrs):
            logger.info(f"  {i+1:2d}. {cidr}")
        
        if len(ipv4_cidrs) > 10 or len(ipv6_cidrs) > 5:
            remaining = (len(ipv4_cidrs) - 10) + max(0, len(ipv6_cidrs) - 5)
            logger.info(f"  ... и еще {remaining} сетей")
        
        logger.info(f"\n📁 Результаты сохранены в: {output_dir}/")
        logger.info("📄 Файлы:")
        logger.info(f"   - domains.txt ({domains_with_ips} доменов с IP)")
        if ipv4_cidrs:
            logger.info(f"   - cidr_ipv4.txt ({len(ipv4_cidrs)} IPv4 сетей)")
        if ipv6_cidrs:
            logger.info(f"   - cidr_ipv6.txt ({len(ipv6_cidrs)} IPv6 сетей)")
        logger.info(f"   - report.json (полный отчет)")
        
        # Важное замечание
        logger.info(f"\n💡 Важно: В domains.txt сохранены только домены с IP адресами.")
        logger.info(f"   Полный список всех доменов (с IP и без) доступен в report.json")


async def main_async(args):
    """Основная асинхронная функция"""
    # Загружаем конфигурации
    app_config = AppConfig(
        timeout=args.timeout,
        max_concurrent=args.concurrent,
        output_dir=args.output_dir,
        log_level=args.log_level,
        log_file=args.log_file
    )
    
    try:
        target_config = load_target_config(args.target)
    except FileNotFoundError:
        logger.error(f"❌ Конфигурация для цели '{args.target}' не найдена!")
        logger.info(f"📁 Создайте файл: config/targets/{args.target}.json")
        logger.info("   Или используйте --list-targets чтобы увидеть доступные цели")
        return
    
    # Создаем и запускаем сканер
    scanner = DomainScanner(app_config, target_config)
    await scanner.run()


def list_targets():
    """Показывает список доступных целей"""
    import os
    
    config_dir = os.path.join(os.path.dirname(__file__), 'config', 'targets')
    
    print("\n📋 Доступные цели поиска:")
    print("=" * 40)
    
    if os.path.exists(config_dir):
        targets = []
        for file in os.listdir(config_dir):
            if file.endswith('.json'):
                target_name = file[:-5]
                try:
                    config = load_target_config(target_name)
                    targets.append((target_name, config.description))
                except:
                    targets.append((target_name, "(ошибка загрузки)"))
        
        if not targets:
            print("  ❌ Нет конфигураций целей")
            print(f"  Создайте файлы в: {config_dir}")
        else:
            for name, desc in sorted(targets):
                print(f"  • {name:15} - {desc[:60]}")
    else:
        print(f"  ❌ Директория не найдена: {config_dir}")
        print(f"  Создайте: mkdir -p {config_dir}")
    
    print("\nДля создания новой цели:")
    print("  python main.py --create-target <имя>")


def create_target(target_name: str):
    """Создает шаблон конфигурации для новой цели"""
    import json
    import os
    
    config_dir = os.path.join(os.path.dirname(__file__), 'config', 'targets')
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, f"{target_name}.json")
    
    if os.path.exists(config_path):
        print(f"❌ Конфигурация для '{target_name}' уже существует!")
        return
    
    template = {
        "name": target_name,
        "description": f"Поиск доменов для {target_name}",
        
        "keywords": [target_name.lower()],
        
        "sources": {
            "crt_sh": True,
            "dns_bruteforce": True,
            "passive": True,
            "static": True
        },
        
        "static_domains": [
            f"{target_name.lower()}.com",
            f"www.{target_name.lower()}.com"
        ],
        
        "static_cidrs": [],
        
        "crt_sh_patterns": [
            f"%.{target_name.lower()}.com",
            f"%.{target_name.lower()}.net"
        ],
        
        "domain_patterns": [],
        "domain_templates": [],
        
        "subdomains": [
            "www", "web", "api", "chat", "status", "support"
        ],
        
        "numeric_patterns": [
            "s{num}", "c{num}", "m{num}", "e{num}"
        ],
        
        "exclude_patterns": [],
        "include_patterns": [],
        
        "ipv4_prefixes": [24, 22, 20],
        "ipv6_prefix": 48,
        
        "known_ranges": {
            "ipv4": [],
            "ipv6": []
        }
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Создан шаблон конфигурации: {config_path}")
    print("📝 Отредактируйте файл перед использованием.")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Domain Scanner Pro v5.0 - Advanced Domain Discovery Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s whatsapp              # Поиск доменов WhatsApp
  %(prog)s --list-targets        # Показать все цели
  %(prog)s --create-target zoom  # Создать конфиг для Zoom
  
Опции настройки:
  %(prog)s whatsapp --timeout 60 --concurrent 200
  %(prog)s whatsapp --log-level DEBUG
  %(prog)s whatsapp --output-dir my_results
        """
    )
    
    parser.add_argument(
        'target',
        nargs='?',
        help='Цель поиска (например: whatsapp, telegram)'
    )
    
    parser.add_argument(
        '--list-targets',
        action='store_true',
        help='Показать список доступных целей'
    )
    
    parser.add_argument(
        '--create-target',
        metavar='NAME',
        help='Создать шаблон конфигурации для новой цели'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Таймаут запросов в секундах (по умолчанию: 30)'
    )
    
    parser.add_argument(
        '--concurrent',
        type=int,
        default=200,
        help='Максимальное количество одновременных запросов (по умолчанию: 200)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='results',
        help='Директория для результатов (по умолчанию: results)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Уровень логирования (по умолчанию: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        help='Файл для сохранения логов'
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    setup_logging(args.log_level, args.log_file)
    
    # Проверка аргументов
    if args.list_targets:
        list_targets()
        return
    
    if args.create_target:
        create_target(args.create_target)
        return
    
    if not args.target:
        parser.print_help()
        print("\n❌ Не указана цель поиска!")
        print("Используйте --list-targets чтобы увидеть доступные цели")
        print("Или --create-target чтобы создать новую цель")
        return
    
    # Проверка зависимостей
    try:
        import aiohttp
        import dns.asyncresolver
        import ipaddress
    except ImportError as e:
        print(f"❌ Не установлены зависимости: {e}")
        print("📦 Установите: pip install -r requirements.txt")
        sys.exit(1)
    
    # Запуск
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()