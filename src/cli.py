import os
from datetime import datetime
from pathlib import Path

import click
from loguru import logger

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

logger.remove()
logger.add(
    LOG_FILE,
    rotation="00:00",
    retention="7 days",
    level="INFO",
    format="{time:HH:mm:ss} | {level} | {message}",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)
logger.add(
    lambda msg: click.echo(msg, err=True),
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
    level="INFO",
)

class CustomClickGroup(click.Group):
    def main(self, *args, **kwargs):
        try:
            return super().main(*args, **kwargs)
        except Exception as exc:
            logger.exception("Unhandled exception")
            raise click.ClickException("An error occurred. Check logs for details.") from exc


@click.group(cls=CustomClickGroup)
@click.version_option(
    version="0.1.0",
    prog_name="SecretGuard",
    message="%(prog)s v%(version)s",
)
def cli() -> None:
    """SecretGuard CLI."""
    pass


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

    try:
        if secret_dir.exists() and secret_dir.is_dir():
            for item in secret_dir.iterdir():
                if item.is_dir():
                    for sub_item in item.iterdir():
                        if sub_item.is_file():
                            sub_item.unlink()
                    item.rmdir()
                else:
                    item.unlink()
            secret_dir.rmdir()

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
