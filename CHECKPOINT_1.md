# 📋 ОТЧЕТ ПО КОНТРОЛЬНОЙ ТОЧКЕ №1: ПРОЕКТИРОВАНИЕ И СТАРТ

**Название проекта:** SecretGuard — локальный менеджер секретов для CI/CD

**Команда / Разработчик:**
- Лесовский Егор Сергеевич — DevOps / Инженер по логированию
- Жабенко Илья Алексеевич — Backend-разработчик / Архитектор

---

## 1. Архитектурный план и концепция

**Цель сервиса:**
SecretGuard — это локальный CLI-инструмент для безопасного хранения, управления и версионирования секретов (паролей, токенов, ключей API) в CI/CD-пайплайнах и на локальных машинах разработчиков. Сервис решает проблему безопасного хранения чувствительной информации в открытом виде в репозиториях, предоставляя шифрование и контроль версий.

**Целевой интерфейс:** CLI (Command Line Interface) с поддержкой интерактивных подсказок и цветного вывода.

**Выбранный стек:**
- **Язык программирования:** Python 3.11
- **CLI-фреймворк:** Click
- **Система логирования:** Loguru
- **Криптография:** Cryptography (Fernet)
- **Конфигурация:** PyYAML
- **Линтеры:** Flake8, Black
- **Тестирование:** Pytest
- **Управление окружением:** python-dotenv
- **VCS:** Git, GitHub

---

## 2. Проектирование (UML-диаграммы)

### Диаграмма вариантов использования (Use Case)

```mermaid
graph TD
    User[Пользователь] -->|Инициализирует проект| Init[secretguard init]
    User -->|Добавляет секрет| Add[secretguard add <key> <value>]
    User -->|Получает секрет| Get[secretguard get <key>]
    User -->|Просматривает все ключи| List[secretguard list]
    User -->|Удаляет секрет| Delete[secretguard delete <key>]
    User -->|Просматривает логи| Logs[secretguard logs]
    User -->|Экспортирует секреты| Export[secretguard export]
    User -->|Импортирует секреты| Import[secretguard import]
    
    Add --> Storage[(SecretStorage)]
    Get --> Storage
    List --> Storage
    Delete --> Storage
    Export --> Storage
    Import --> Storage
    
    Storage --> Crypto[Криптографическое ядро]
    Storage --> Versioning[Система версионирования]
    
    Init --> FS[Файловая система .secretguard/]
    Add --> Logger[Loguru логирование]
    Get --> Logger
    Delete --> Logger
    Logs --> Logger
```

### Диаграмма последовательности (Sequence) взаимодействия модулей

```mermaid
sequenceDiagram
    participant User as Пользователь
    participant CLI as CLI (Click)
    participant Logger as Loguru
    participant Storage as SecretStorage
    participant Crypto as Crypto Core
    participant FS as Файловая система

    User->>CLI: secretguard add db_pass "123456"
    CLI->>CLI: Проверка инициализации
    CLI->>Logger: Логирование действия (INFO)
    CLI->>Storage: save_secret("db_pass", "123456")
    Storage->>Storage: _get_master_key()
    alt Ключ отсутствует
        Storage->>Crypto: generate_key()
        Crypto-->>Storage: Возвращает ключ
        Storage->>FS: Сохраняет master.key
    end
    Storage->>Crypto: encrypt_secret("123456", key)
    Crypto-->>Storage: Возвращает зашифрованную строку
    Storage->>Storage: _load_data()
    Storage->>FS: Читает data.json
    FS-->>Storage: Возвращает данные
    alt Ключ уже существует
        Storage->>Storage: Создает новую версию с инкрементом
    else Ключ новый
        Storage->>Storage: Создает запись с version=1
    end
    Storage->>Storage: _save_data()
    Storage->>FS: Записывает обновленный data.json
    FS-->>Storage: Успешно сохранено
    Storage-->>CLI: Операция выполнена
    CLI->>Logger: Логирование успеха (INFO)
    CLI-->>User: ✅ Секрет db_pass добавлен
```

---

# 3. Распределение ролей

| Студент | Роль | Зона ответственности |
|---------|------|----------------------|
| Лесовский Егор Сергеевич | DevOps / Инженер по логированию | Создание структуры проекта, настройка Click CLI, интеграция Loguru, конфигурация линтеров (Flake8/Black), реализация пользовательских команд (init, add, get, list, logs, delete), проверка инициализации проекта, обработка ошибок в CLI |
| Жабенко Илья Алексеевич | Backend-разработчик / Архитектор | Проектирование архитектуры, реализация криптографического ядра, разработка класса SecretStorage, версионирование секретов, безопасное удаление, экспорт/импорт секретов, ротация мастер-ключа |

---

# 4. Чек-лист готовности

- [x] Создан новый публичный репозиторий на GitHub.
- [x] Все участники добавлены в репозиторий как соавторы (Collaborators).
- [x] Каждый участник сделал минимум 3 осмысленных коммита (согласно Git-политике).
- [x] Настроено локальное виртуальное окружение, проект запускается в базовом виде.

---

# 5. Результаты работы (ссылки)

| Тип | Ссылка |
|-----|--------|
| Репозиторий | https://github.com/sqdylove/SecretGuard |
| Коммит Егора | https://github.com/sqdylove/SecretGuard/pull/1 |
| Коммит Ильи | https://github.com/sqdylove/SecretGuard/pull/2 |

---

# 6. Выполненные задачи за день

## ✅ Что сделано (общее):

- ✅ Создан репозиторий и настроена структура проекта
- ✅ Установлены все необходимые библиотеки (Click, Loguru, Cryptography, PyYAML, Flake8, Black, Pytest)
- ✅ Настроены Flake8 и Black с едиными правилами форматирования
- ✅ Создан базовый CLI с командой `secretguard --version`
- ✅ Настроено логирование Loguru (запись в файл с ротацией и цветной вывод в консоль)
- ✅ Создан файл `main.py` для запуска приложения
- ✅ Разработана архитектура криптографического ядра проекта
- ✅ Реализованы функции `generate_key`, `load_key`, `save_key`, `encrypt_secret`, `decrypt_secret`
- ✅ Созданы юнит-тесты для всех криптографических функций
- ✅ Написаны UML-диаграммы: Use Case, Sequence и Class diagrams
- ✅ Спроектирована структура класса `SecretStorage` с методами для работы с секретами
- ✅ Определены кастомные исключения (`NeedConfirmError`, `MergeConflictError`)

---

## 👨‍💻 Что сделал Егор Лесовский:

- ✅ Создал репозиторий и настроил структуру проекта
- ✅ Установил все необходимые библиотеки
- ✅ Настроил Flake8 и Black с едиными правилами форматирования
- ✅ Создал базовый CLI с командой `secretguard --version`
- ✅ Настроил логирование Loguru (запись в файл с ротацией и цветной вывод в консоль)
- ✅ Создал файл `main.py` для запуска приложения

---

## 👨‍💻 Что сделал Илья Жабенко:

- ✅ Разработал архитектуру криптографического ядра проекта
- ✅ Реализовал функции `generate_key`, `load_key`, `save_key`, `encrypt_secret`, `decrypt_secret`
- ✅ Создал юнит-тесты для всех криптографических функций
- ✅ Написал UML-диаграммы: Use Case, Sequence и Class diagrams
- ✅ Спроектировал структуру класса `SecretStorage` с методами для работы с секретами
- ✅ Определил кастомные исключения (`NeedConfirmError`, `MergeConflictError`)

---

# 7. Планы на завтра

## 📋 Планы Егора:

- Реализовать команду `secretguard init` для инициализации проекта
- Создать структуру папок `.secretguard/` с конфигом
- Интегрировать генерацию мастер-ключа

## 📋 Планы Ильи:

- Реализовать базовый класс `SecretStorage` с методами `save_secret` и `get_secret`
- Интегрировать криптографическое ядро в `SecretStorage`
- Написать тесты для `SecretStorage`

---

# 📌 ИТОГИ ДНЯ 1

Оба участника успешно завершили первый день практики. Создана основа проекта:

- ✅ Структура репозитория
- ✅ CLI-фреймворк
- ✅ Система логирования
- ✅ Криптографическое ядро
- ✅ Написаны тесты и документация
- ✅ Разработаны UML-диаграммы

**Ссылка на репозиторий:** https://github.com/sqdylove/SecretGuard
