# SecretGuard

SecretGuard — это Python CLI-проект для безопасного управления секретами и автоматизации.

## Структура проекта

- `main.py` — точка входа для CLI-приложения
- `src/` — пакет с CLI и компонентами приложения
  - `src/cli.py` — команды CLI и настройка логирования
- `core/` — основная логика проекта
- `configs/` — конфигурационные файлы и шаблоны
- `logs/` — сохранённые журналы работы
- `tests/` — юнит- и интеграционные тесты

## Корневые файлы

- `.flake8` — настройки Flake8
- `pyproject.toml` — настройки Black
- `requirements.txt` — зависимости проекта
- `.gitignore` — исключения Git
- `README.md` — документация проекта

## Быстрый старт

1. Создайте виртуальное окружение:
   ```bash
   python -m venv .venv
   ```
2. Активируйте его:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Запустите CLI:
   ```bash
   python main.py --help
   ```

## CLI

Проект предоставляет CLI `SecretGuard` с командой версии:

```bash
python main.py --version
```

## Форматирование и линтинг

- `black` — для форматирования кода
- `flake8` — для статического анализа

