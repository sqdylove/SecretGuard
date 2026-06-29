import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import shutil

import pyzipper

from src.core.crypto import decrypt_secret, encrypt_secret, generate_key, load_key, save_key


logger = logging.getLogger(__name__)


class NeedConfirmError(Exception):
    """Исключение, выбрасываемое при попытке удалить критичный секрет без подтверждения."""
    pass


class MergeConflictError(Exception):
    """Исключение, выбрасываемое при конфликте ключей при импорте секретов."""

    def __init__(self, conflicts: List[str]):
        self.conflicts = conflicts
        message = f"Merge conflict for keys: {', '.join(conflicts)}"
        super().__init__(message)


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

    def export_secrets(self, password: str, export_path: Path) -> None:
        """Экспортирует все секреты в ZIP-архив в открытом виде и защищает паролем.

        В архиве будут два файла: `secrets.json` и `metadata.json`.
        """
        master_key = self._get_master_key()
        data = self._load_data()

        secrets_plain = {}
        metadata = {}

        for key, versions in data.items():
            if not isinstance(versions, list) or len(versions) == 0:
                continue

            # Последняя версия как открытое значение
            latest = versions[-1]
            if not isinstance(latest, dict):
                continue

            plain_value = decrypt_secret(latest["value"], master_key)
            secrets_plain[key] = plain_value

            # metadata: список версий и дат
            meta_versions = []
            for v in versions:
                if isinstance(v, dict):
                    meta_versions.append({
                        "version": v.get("version"),
                        "updated_at": v.get("updated_at"),
                    })

            metadata[key] = meta_versions

        export_path.parent.mkdir(parents=True, exist_ok=True)

        # Используем pyzipper для AES-шифрования архива
        with pyzipper.AESZipFile(str(export_path), 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode('utf-8'))
            zf.writestr('secrets.json', json.dumps(secrets_plain, ensure_ascii=False, indent=2).encode('utf-8'))
            zf.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False, indent=2).encode('utf-8'))

    def import_secrets(self, import_path: Path, password: str) -> None:
        """Импортирует секреты из защищённого ZIP-архива и мержит с текущими.

        При конфликте ключей бросает `MergeConflictError`.
        """
        master_key = self._get_master_key()

        if not import_path.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")

        with pyzipper.AESZipFile(str(import_path), 'r') as zf:
            zf.setpassword(password.encode('utf-8'))
            try:
                secrets_bytes = zf.read('secrets.json')
            except KeyError as exc:
                raise ValueError('secrets.json not found in archive') from exc

            try:
                secrets_to_import = json.loads(secrets_bytes.decode('utf-8'))
            except Exception as exc:
                raise ValueError('Invalid secrets.json content') from exc

        if not isinstance(secrets_to_import, dict):
            raise ValueError('secrets.json must contain an object')

        existing = self._load_data()
        conflicts = [k for k in secrets_to_import.keys() if k in existing]
        if conflicts:
            raise MergeConflictError(conflicts)

        # Добавляем новые ключи как первая версия
        for key, plain_value in secrets_to_import.items():
            encrypted_value = encrypt_secret(plain_value, master_key)
            existing[key] = [{
                'version': 1,
                'value': encrypted_value,
                'updated_at': datetime.now().isoformat()
            }]

        self._save_data(existing)

    def rotate_master_key(self, new_key: Optional[bytes] = None) -> None:
        """Ротация мастер-ключа: генерирует/принимает новый ключ и перешифровывает все секреты.

        Сохраняет новый ключ в `keys/master.key` и делает бэкап старого `data.json` как `data.json.bak`.
        """
        # Получаем старый ключ (если его нет — будет создан, но тогда данных скорее всего нет)
        old_key = self._get_master_key()

        if new_key is None:
            new_key = generate_key()

        # Загружаем существующие данные
        data = self._load_data()

        new_data = {}

        for key, versions in data.items():
            if not isinstance(versions, list):
                continue

            new_versions = []
            for v in versions:
                if not isinstance(v, dict):
                    continue
                # Декодируем старое значение и зашифровываем новым ключом
                plain = decrypt_secret(v['value'], old_key)
                new_encrypted = encrypt_secret(plain, new_key)
                new_versions.append({
                    'version': v.get('version'),
                    'value': new_encrypted,
                    'updated_at': v.get('updated_at')
                })

            new_data[key] = new_versions

        # Бэкап текущего data.json
        if self.data_path.exists():
            bak_path = self.data_path.with_suffix(self.data_path.suffix + '.bak')
            shutil.copy(str(self.data_path), str(bak_path))

        # Сохраняем новый ключ
        self.keys_path.mkdir(parents=True, exist_ok=True)
        master_key_path = self.keys_path / 'master.key'
        save_key(new_key, str(master_key_path))

        # Записываем перешифрованные данные
        self._save_data(new_data)
