import json
from pathlib import Path

import pytest

from src.core.storage import SecretStorage, NeedConfirmError


def test_storage_creates_master_key_and_round_trips_secret(tmp_path: Path):
    config_path = tmp_path / "config.json"
    storage = SecretStorage(config_path)

    assert storage.data_path == tmp_path / "data.json"
    assert storage.keys_path == tmp_path / "keys"

    storage.save_secret("api-key", "super-secret")

    master_key_path = storage.keys_path / "master.key"
    assert master_key_path.exists()

    restored = storage.get_secret("api-key")
    assert restored == "super-secret"


def test_storage_returns_none_for_missing_secret(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    assert storage.get_secret("missing") is None


def test_storage_raises_on_corrupt_data_file(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    storage = SecretStorage(tmp_path / "config.json")
    storage.data_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Corrupted data storage"):
        storage.get_secret("any")

    assert "Corrupted data storage" in caplog.text


def test_storage_creates_new_versions_for_existing_secret(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    storage.save_secret("api-key", "first-value")
    storage.save_secret("api-key", "second-value")

    data = json.loads(storage.data_path.read_text(encoding="utf-8"))
    versions = data["api-key"]

    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert versions[1]["version"] == 2
    assert isinstance(versions[0]["updated_at"], str)
    assert isinstance(versions[1]["updated_at"], str)

    assert storage.get_secret("api-key") == "second-value"
    assert storage.get_secret_version("api-key", 1) == "first-value"
    assert storage.get_secret_version("api-key", 99) is None
    assert storage.list_secrets() == ["api-key"]


def test_delete_secret_removes_all_versions(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    storage.save_secret("api-key", "value1")
    storage.save_secret("api-key", "value2")
    storage.save_secret("other-key", "other-value")

    assert "api-key" in storage.list_secrets()
    assert "other-key" in storage.list_secrets()

    storage.delete_secret("api-key")

    assert "api-key" not in storage.list_secrets()
    assert "other-key" in storage.list_secrets()
    assert storage.get_secret("api-key") is None


def test_delete_secret_raises_for_critical_key(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    storage.save_secret("db_password", "secret")
    storage.save_secret("api_token", "token123")

    with pytest.raises(NeedConfirmError, match="Это критичный секрет"):
        storage.delete_secret("db_password")

    with pytest.raises(NeedConfirmError, match="Это критичный секрет"):
        storage.delete_secret("api_token")

    # Они должны остаться в хранилище
    assert "db_password" in storage.list_secrets()
    assert "api_token" in storage.list_secrets()


def test_delete_version_removes_specific_version(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    storage.save_secret("api-key", "value1")
    storage.save_secret("api-key", "value2")
    storage.save_secret("api-key", "value3")

    history = storage.get_secret_history("api-key")
    assert len(history) == 3

    storage.delete_version("api-key", 2)

    history = storage.get_secret_history("api-key")
    assert len(history) == 2
    assert all(v["version"] != 2 for v in history)

    # Текущая версия должна остаться третьей
    assert storage.get_secret("api-key") == "value3"


def test_delete_version_removes_key_when_no_versions_left(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    storage.save_secret("api-key", "value")
    assert "api-key" in storage.list_secrets()

    storage.delete_version("api-key", 1)

    assert "api-key" not in storage.list_secrets()
    assert storage.get_secret("api-key") is None


def test_delete_version_raises_for_critical_key(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    storage.save_secret("admin_password", "secret")
    storage.save_secret("admin_password", "new-secret")

    with pytest.raises(NeedConfirmError, match="Это критичный секрет"):
        storage.delete_version("admin_password", 1)

    # Версии должны остаться
    history = storage.get_secret_history("admin_password")
    assert len(history) == 2


def test_get_secret_history_returns_all_versions(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    storage.save_secret("api-key", "value1")
    storage.save_secret("api-key", "value2")
    storage.save_secret("api-key", "value3")

    history = storage.get_secret_history("api-key")

    assert len(history) == 3
    assert history[0]["version"] == 1
    assert history[1]["version"] == 2
    assert history[2]["version"] == 3
    assert all("updated_at" in v for v in history)


def test_get_secret_history_returns_empty_for_missing_key(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    history = storage.get_secret_history("missing")
    assert history == []


def test_list_secrets_only_returns_keys_with_versions(tmp_path: Path):
    storage = SecretStorage(tmp_path / "config.json")

    # Вручную добавим некорректные записи
    data = {
        "valid_key": [{"version": 1, "value": "encrypted", "updated_at": "2024-01-01T00:00:00"}],
        "empty_list": [],
        "corrupted_key": "not_a_list",
    }
    storage.data_path.parent.mkdir(parents=True, exist_ok=True)
    storage.data_path.write_text(json.dumps(data), encoding="utf-8")

    # list_secrets должен вернуть только valid_key
    secrets = storage.list_secrets()
    assert secrets == ["valid_key"]
    assert "empty_list" not in secrets
    assert "corrupted_key" not in secrets
