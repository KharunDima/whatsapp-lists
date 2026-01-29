"""
Конфигурация приложения
"""
import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class AppConfig:
    """Конфигурация приложения"""

    # Основные настройки
    app_name: str = "Domain Scanner Pro"
    version: str = "5.0.0"

    # Настройки производительности
    timeout: int = 30
    max_concurrent: int = 200
    retry_attempts: int = 3
    retry_delay: float = 1.0

    # Настройки DNS
    dns_timeout: int = 5
    dns_retries: int = 2
    dns_servers: List[str] = field(default_factory=lambda: [
        '8.8.8.8',      # Google DNS
        '1.1.1.1',      # Cloudflare DNS
        '9.9.9.9',      # Quad9
        '208.67.222.222',  # OpenDNS
    ])

    # Настройки поиска
    batch_size: int = 100
    request_delay: float = 0.5
    max_domains_per_source: int = 1000

    # Настройки сохранения
    output_dir: str = "results"
    save_json: bool = True
    save_txt: bool = True

    # Логирование
    log_level: str = "INFO"
    log_file: Optional[str] = "scanner.log"

    # User Agents для обхода блокировок
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Googlebot/2.1 (+http://www.google.com/bot.html)"
    ])


@dataclass
class TargetConfig:
    """Конфигурация цели поиска"""

    name: str
    description: str = ""

    # Ключевые слова для поиска
    keywords: List[str] = field(default_factory=list)

    # Источники данных
    sources: Dict[str, Any] = field(default_factory=lambda: {
        "crt_sh": True,
        "dns_bruteforce": True,
        "passive": True,
        "static": True
    })

    # Статические данные
    static_domains: List[str] = field(default_factory=list)
    static_cidrs: List[str] = field(default_factory=list)

    # Паттерны для поиска
    domain_patterns: List[str] = field(default_factory=list)
    crt_sh_patterns: List[str] = field(default_factory=list)

    # Генерация доменов
    domain_templates: List[str] = field(default_factory=list)
    subdomains: List[str] = field(default_factory=lambda: [
        "www", "web", "api", "chat", "call", "voice", "status",
        "business", "beta", "support", "help", "blog", "newsroom",
        "cdn", "media", "static", "upload", "download", "assets"
    ])

    # Числовые шаблоны
    numeric_patterns: List[str] = field(default_factory=lambda: [
        "s{num}", "c{num}", "m{num}", "e{num}", "node{num}",
        "server{num}", "edge{num}", "bsg{num:03d}"
    ])

    # Фильтрация
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)

    # Настройки сети
    ipv4_prefixes: List[int] = field(default_factory=lambda: [24, 22, 20, 16])
    ipv6_prefix: int = 48

    # Известные диапазоны (если есть)
    known_ranges: Dict[str, List[str]] = field(default_factory=lambda: {
        "ipv4": [],
        "ipv6": []
    })

    @classmethod
    def load_from_file(cls, filepath: str) -> 'TargetConfig':
        """Загружает конфиг из файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Обеспечиваем обратную совместимость
        if 'sources' not in data:
            data['sources'] = {
                "crt_sh": True,
                "dns_bruteforce": True,
                "passive": True,
                "static": True
            }

        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }


def load_target_config(target_name: str) -> TargetConfig:
    """Загружает конфигурацию цели"""
    config_dir = os.path.join(os.path.dirname(__file__), 'targets')
    config_path = os.path.join(config_dir, f"{target_name}.json")

    if os.path.exists(config_path):
        return TargetConfig.load_from_file(config_path)
    else:
        # Создаем минимальный конфиг
        return TargetConfig(
            name=target_name,
            description=f"Configuration for {target_name}",
            keywords=[target_name.lower()],
            crt_sh_patterns=[
                f"%.{target_name.lower()}.com",
                f"%.{target_name.lower()}.net",
                f"{target_name.lower()}%"
            ],
            static_domains=[
                f"{target_name.lower()}.com",
                f"www.{target_name.lower()}.com"
            ]
        )