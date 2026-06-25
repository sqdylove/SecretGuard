import json
import logging
from pathlib import Path
from typing import Optional

from src.core.crypto import decrypt_secret, encrypt_secret, generate_key, load_key, save_key


logger = logging.getLogger(__name__)


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

        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        secrets = self._load_data()
        secrets[key] = encrypted_value

        with self.data_path.open("w", encoding="utf-8") as data_file:
            json.dump(secrets, data_file, indent=2, ensure_ascii=False)

    def get_secret(self, key: str) -> Optional[str]:
        master_key = self._get_master_key()
        secrets = self._load_data()

        encrypted_value = secrets.get(key)
        if encrypted_value is None:
            return None

        return decrypt_secret(encrypted_value, master_key)

    def _load_data(self) -> dict:
        if not self.data_path.exists():
            return {}

        try:
            with self.data_path.open("r", encoding="utf-8") as data_file:
                data = json.load(data_file)
        except json.JSONDecodeError as exc:
            logger.error("Corrupted data storage at %s", self.data_path)
            raise ValueError("Corrupted data storage") from exc

        if not isinstance(data, dict):
            logger.error("Corrupted data storage at %s", self.data_path)
            raise ValueError("Corrupted data storage")

        return data
