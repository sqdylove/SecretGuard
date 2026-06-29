import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.core.crypto import decrypt_secret, encrypt_secret, generate_key, load_key, save_key


logger = logging.getLogger(__name__)


class NeedConfirmError(Exception):
    """Исключение, выбрасываемое при попытке удалить критичный секрет без подтверждения."""
    pass


class SecretStorage:
    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
        self.data_path = self.config_path.parent / "data.json"
        self.keys_path = self.config_path.parent / "keys"

    def _get_master_key(self) -> bytes:
        self.keys_path.mkdir(parents=True, exist_ok=True)
        master_key_path = self.keys_path / "master.key"

        if master_key_path.exists():
            return load_key(str(master_key_path))

        master_key = generate_key()
        save_key(master_key, str(master_key_path))
        return master_key

    def save_secret(self, key: str, value: str) -> None:
        master_key = self._get_master_key()
        encrypted_value = encrypt_secret(value, master_key)

        secrets = self._load_data()
        existing_versions = secrets.get(key)

        if isinstance(existing_versions, list):
            versions = existing_versions
            next_version = 1
            for version_entry in versions:
                if isinstance(version_entry, dict) and isinstance(version_entry.get("version"), int):
                    next_version = max(next_version, version_entry["version"] + 1)
        elif existing_versions is None:
            versions = []
            next_version = 1
        else:
            versions = [{"version": 1, "value": existing_versions, "updated_at": datetime.now().isoformat()}]
            next_version = 2

        versions.append(
            {"version": next_version, "value": encrypted_value, "updated_at": datetime.now().isoformat()}
        )
        secrets[key] = versions
        self._save_data(secrets)

    def get_secret(self, key: str) -> Optional[str]:
        master_key = self._get_master_key()
        secrets = self._load_data()

        versions = secrets.get(key)
        if not isinstance(versions, list) or not versions:
            return None

        latest_entry = versions[-1]
        if not isinstance(latest_entry, dict):
            return None

        return decrypt_secret(latest_entry["value"], master_key)

    def get_secret_version(self, key: str, version: int) -> Optional[str]:
        master_key = self._get_master_key()
        secrets = self._load_data()

        versions = secrets.get(key)
        if not isinstance(versions, list):
            return None

        for version_entry in versions:
            if isinstance(version_entry, dict) and version_entry.get("version") == version:
                return decrypt_secret(version_entry["value"], master_key)

        return None

    def list_secrets(self) -> List[str]:
        secrets = self._load_data()
        return sorted([
            key for key, value in secrets.items()
            if isinstance(value, list) and len(value) > 0
        ])

    def _is_critical_secret(self, key: str) -> bool:
        """Проверяет, содержит ли ключ критичные слова."""
        key_lower = key.lower()
        return 'password' in key_lower or 'token' in key_lower

    def delete_secret(self, key: str) -> None:
        """Удаляет все версии секрета."""
        if self._is_critical_secret(key):
            raise NeedConfirmError('Это критичный секрет.\n\nТребуется подтверждение удаления')

        secrets = self._load_data()
        if key in secrets:
            del secrets[key]
            self._save_data(secrets)

    def delete_version(self, key: str, version: int) -> None:
        """Удаляет конкретную версию секрета."""
        if self._is_critical_secret(key):
            raise NeedConfirmError('Это критичный секрет.\n\nТребуется подтверждение удаления')

        secrets = self._load_data()
        if key not in secrets:
            return

        versions = secrets[key]
        if not isinstance(versions, list):
            return

        # Фильтруем версии, исключая нужную
        filtered_versions = [v for v in versions if not (isinstance(v, dict) and v.get("version") == version)]

        if len(filtered_versions) == 0:
            # Если версий не осталось, удаляем весь ключ
            del secrets[key]
        else:
            # Иначе обновляем список версий
            secrets[key] = filtered_versions

        self._save_data(secrets)

    def get_secret_history(self, key: str) -> List[dict]:
        """Возвращает историю всех версий для ключа."""
        secrets = self._load_data()
        versions = secrets.get(key)

        if not isinstance(versions, list):
            return []

        history = []
        for version_entry in versions:
            if isinstance(version_entry, dict):
                history.append({
                    "version": version_entry.get("version"),
                    "updated_at": version_entry.get("updated_at")
                })

        return history

    def _load_data(self) -> dict:
        if not self.data_path.exists():
            return {}

        try:
            with self.data_path.open("r", encoding="utf-8") as data_file:
                data = json.load(data_file)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Corrupted data storage at %s", self.data_path)
            raise ValueError("Corrupted data storage") from exc

        if not isinstance(data, dict):
            logger.error("Corrupted data storage at %s", self.data_path)
            raise ValueError("Corrupted data storage")

        return data

    def _save_data(self, data: dict) -> None:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        with self.data_path.open("w", encoding="utf-8") as data_file:
            json.dump(data, data_file, indent=2, ensure_ascii=False)
