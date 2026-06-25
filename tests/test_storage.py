import json
from pathlib import Path

import pytest

from src.core.storage import SecretStorage


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
