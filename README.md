# WhatsApp Lists for Podkop

Автоматически обновляемые списки доменов и IP-адресов WhatsApp для Podkop на OpenWRT.

## Как это работает?

1. **GitHub Actions** запускается каждые 6 часов
2. **Скрипт обнаружения** ищет актуальные домены и IP WhatsApp
3. **Списки проверяются** на работоспособность
4. **Результаты публикуются** в этом репозитории
5. **Podkop** подтягивает обновления по URL

## Использование

### Для пользователей Podkop:

| Раздел в Podkop | Куда добавить | URL для вставки |
| :--- | :--- | :--- |
| **Списки доменов** | `Секции` → `Внешние списки доменов` → `URL` | `https://raw.githubusercontent.com/.../domains.txt` |
| **Списки подсетей** | `Секции` → `Внешние списки подсетей` → `URL` | `https://raw.githubusercontent.com/.../cidr.txt` |
- **Домены:** `https://raw.githubusercontent.com/KharunDima/whatsapp-lists/main/lists/domains.txt`
- **CIDR:** `https://raw.githubusercontent.com/KharunDima/whatsapp-lists/main/lists/cidr.txt`

### Для разработчиков:

```bash
# Клонировать репозиторий
git clone https://github.com/KharunDima/whatsapp-lists.git
```
```bash
# Запустить скрипт обнаружения вручную
cd whatsapp-lists
```
```bash
# Даем права на выполнение скрипта поиска
chmod +x scripts/discover.sh
```
```bash
# Запускаем  скрипт
./scripts/discover.sh
```
```
Структура
text
├── .github/workflows/    # Автоматические обновления
├── scripts/              # Скрипты обнаружения
├── lists/                # Актуальные списки
├── history/              # Архив версий
└── podkop-instructions.txt  # Инструкция
```




## **Как запустить:**

1. **Создайте новый репозиторий** на GitHub
2. **Скопируйте все файлы** из структуры выше
3. **Замените `KharunDima`** на ваш GitHub username
4. **Запустите workflow вручную** через Actions → Update WhatsApp Lists → Run workflow
5. **Добавьте ссылки в Podkop** как указано в инструкции

## **Преимущества этого подхода:**

✅ **Автоматическое обновление** - каждые 6 часов  
✅ **Проверка работоспособности** - скрипт верификации  
✅ **История изменений** - можно откатиться  
✅ **Простота для пользователей** - только 2 URL  
✅ **Надежность** - работает даже если скрипт упал  
✅ **Прозрачность** - все изменения в истории Git  
