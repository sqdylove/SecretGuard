import os
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


if __name__ == "__main__":
    cli()
