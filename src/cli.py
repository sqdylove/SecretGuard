import os
import shutil
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path

import click
import yaml
from loguru import logger
from src.core.storage import SecretStorage, NeedConfirmError

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"


def configure_logging(debug: bool = False) -> None:
    logger.remove()
    level = "DEBUG" if debug else "INFO"
    logger.add(
        LOG_FILE,
        rotation="00:00",
        retention="7 days",
        level=level,
        format="{time:HH:mm:ss} | {level} | {message}",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )
    logger.add(
        lambda msg: click.echo(msg, err=True),
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
        level=level,
    )


configure_logging(False)


class CustomClickGroup(click.Group):
    command_aliases = {
        "-a": "add",
        "-g": "get",
        "-l": "list",
        "-d": "delete",
    }

    def get_command(self, ctx, cmd_name):
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            return command
        alias = self.command_aliases.get(cmd_name)
        if alias:
            return super().get_command(ctx, alias)
        return None

    def main(self, *args, **kwargs):
        try:
            return super().main(*args, **kwargs)
        except Exception as exc:
            logger.exception("Unhandled exception")
            raise click.ClickException("An error occurred. Check logs for details.") from exc


def load_config() -> Path:
    config_path = Path.cwd() / ".secretguard" / "config.yaml"
    if not config_path.exists():
        click.echo(
            "Проект не инициализирован. Запустите secretguard init",
            err=True,
            color=True,
        )
        sys.exit(1)

    try:
        with config_path.open("r", encoding="utf-8") as f:
            yaml.safe_load(f)
        logger.info("Конфигурация загружена из .secretguard/config.yaml")
        return config_path
    except Exception as exc:
        logger.error(f"Не удалось загрузить конфигурацию: {exc}")
        raise click.ClickException("Ошибка при загрузке конфигурации.") from exc


def require_init(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        load_config()
        return func(*args, **kwargs)

    return wrapper


@click.group(cls=CustomClickGroup)
@click.option("--debug", is_flag=True, help="Включить режим отладки")
@click.version_option(
    version="0.1.0",
    prog_name="SecretGuard",
    message="%(prog)s v%(version)s",
)
@click.pass_context
def cli(ctx, debug: bool) -> None:
    """SecretGuard CLI."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    configure_logging(debug)


@cli.command(name="add")
@require_init
@click.argument("key")
@click.argument("value")
def add(key: str, value: str) -> None:
    """Добавляет секрет с версионированием."""
    try:
        config_path = load_config()
        storage = SecretStorage(config_path)
        storage.save_secret(key, value)
        try:
            username = os.getlogin()
        except OSError:
            username = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"

        logger.info(f"Секрет {key} добавлен пользователем {username}")
        click.echo(f"Секрет '{key}' успешно добавлен.")
    except Exception as exc:
        logger.error(f"Не удалось добавить секрет {key}: {exc}", exc_info=True)
        raise click.ClickException(
            "Не удалось добавить секрет. Проверьте журналы и повторите попытку."
        ) from exc


@cli.command(name="get")
@require_init
@click.argument("key")
def get(key: str) -> None:
    """Получает секрет по ключу."""
    try:
        config_path = load_config()
        storage = SecretStorage(config_path)
        secret = storage.get_secret(key)
        if secret is None:
            logger.error("Секрет %s не найден", key)
            click.echo(click.style("Секрет не найден", fg="red"), err=True)
            return

        click.echo(secret)
    except Exception as exc:
        logger.error(f"Ошибка при получении секрета {key}: {exc}", exc_info=True)
        raise click.ClickException(
            "Не удалось получить секрет. Проверьте журналы и повторите попытку."
        ) from exc


@cli.command(name="list")
@require_init
def list_secrets() -> None:
    """Выводит список сохраненных ключей."""
    try:
        config_path = load_config()
        storage = SecretStorage(config_path)
        secrets = storage.list_secrets()

        for index, secret_key in enumerate(secrets, start=1):
            click.echo(f"{index}. {secret_key}")
    except Exception as exc:
        logger.error(f"Ошибка при выводе списка секретов: {exc}", exc_info=True)
        raise click.ClickException(
            "Не удалось получить список секретов. Проверьте журналы и повторите попытку."
        ) from exc


@cli.command(name="logs")
def logs() -> None:
    """Показывает последние 20 строк журнала."""
    try:
        if not LOG_FILE.exists():
            click.echo("Файл журнала не найден.")
            return

        content = LOG_FILE.read_text(encoding="utf-8")
        lines = content.splitlines()
        for line in lines[-20:]:
            click.echo(line)
    except Exception as exc:
        logger.error(f"Ошибка при чтении журнала: {exc}", exc_info=True)
        raise click.ClickException(
            "Не удалось прочитать журналы. Проверьте файлы и повторите попытку."
        ) from exc


@cli.command(name="delete")
@require_init
@click.argument("key")
def delete(key: str) -> None:
    """Удаляет секрет по ключу."""
    try:
        config_path = load_config()
        storage = SecretStorage(config_path)
        try:
            storage.delete_secret(key)
            click.echo(f"Секрет '{key}' удален.")
        except NeedConfirmError:
            confirm = click.confirm("Это критичный секрет. Удалить?")
            if confirm:
                storage.delete_secret(key)
                click.echo(f"Секрет '{key}' удален.")
            else:
                click.echo("Удаление отменено")
    except Exception as exc:
        if isinstance(exc, click.ClickException):
            raise
        logger.error(f"Ошибка при удалении секрета {key}: {exc}", exc_info=True)
        raise click.ClickException(
            "Не удалось удалить секрет. Проверьте журналы и повторите попытку."
        ) from exc


@cli.command()
def init() -> None:
    """Инициализирует проект SecretGuard в текущей директории."""
    project_dir = Path.cwd()
    secret_dir = project_dir / ".secretguard"
    config_file = secret_dir / "config.yaml"
    keys_dir = secret_dir / "keys"
    data_file = secret_dir / "data.json"

    logger.info("Запуск инициализации SecretGuard")

    if secret_dir.exists():
        logger.info("Папка .secretguard уже существует")
        overwrite = click.confirm("Папка уже существует. Перезаписать?", default=False)
        if not overwrite:
            logger.info("Инициализация отменена пользователем")
            raise click.ClickException("Инициализация отменена")
        logger.info("Перезапись существующей папки .secretguard")
        if secret_dir.is_dir():
            shutil.rmtree(secret_dir)
        else:
            secret_dir.unlink()

    try:
        secret_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Создана директория .secretguard")

        keys_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Создана директория .secretguard/keys")

        config_content = (
            "storage_type: local\n"
            "encryption_enabled: true\n"
            "versioning_enabled: true\n"
            f"created_at: {datetime.utcnow().isoformat()}\n"
        )
        config_file.write_text(config_content, encoding="utf-8")
        logger.info("Создан файл .secretguard/config.yaml")

        data_file.write_text("{}", encoding="utf-8")
        logger.info("Создан файл .secretguard/data.json")

        logger.info("Инициализация SecretGuard завершена успешно")
    except Exception as exc:
        logger.error(f"Ошибка при инициализации: {exc}")
        raise click.ClickException("Ошибка при инициализации. Проверьте логи.") from exc


if __name__ == "__main__":
    cli()
