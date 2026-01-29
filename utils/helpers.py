"""
Вспомогательные функции
"""
import os
from typing import  List
import random

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Настройка логирования"""
    import logging

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    handlers = [logging.StreamHandler()]

    if log_file:
        # Создаем директорию для логов если нужно
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )

def create_output_dir(base_dir: str = "results") -> str:
    """Создает директорию для результатов"""
    # Убрано создание подпапки с временной меткой
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def get_random_user_agent() -> str:
    """Возвращает случайный User-Agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
    ]
    return random.choice(user_agents)

def normalize_domain(domain: str) -> str:
    """Нормализует домен"""
    domain = domain.lower().strip()

    # Удаляем протокол
    if domain.startswith(('http://', 'https://')):
        domain = domain.split('://', 1)[1]

    # Удаляем www.
    if domain.startswith('www.'):
        domain = domain[4:]

    # Удаляем порт
    if ':' in domain:
        domain = domain.split(':')[0]

    # Удаляем путь
    if '/' in domain:
        domain = domain.split('/')[0]

    # Удаляем *
    domain = domain.replace('*.', '')

    return domain

def print_banner():
    """Печатает баннер приложения"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                Domain Scanner Pro v5.0                   ║
║           Advanced Domain Discovery Tool                 ║
╚══════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_statistics(domains: List, ips: List, cidrs: List):
    """Печатает статистику"""
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА:")
    print("="*60)
    print(f"Домены: {len(domains)}")
    print(f"Уникальные IP: {len(set(ips))}")
    print(f"CIDR сети: {len(cidrs)}")
    print("="*60)