import base64
import tempfile
from pathlib import Path

from src.core.crypto import (
    decrypt_secret,
    encrypt_secret,
    generate_key,
    load_key,
    save_key,
)


def test_generate_key_returns_valid_fernet_key():
    key = generate_key()

    assert isinstance(key, bytes)
    assert len(base64.urlsafe_b64decode(key)) == 32


def test_save_and_load_key_round_trip():
    key = generate_key()

    with tempfile.TemporaryDirectory() as temp_dir:
        key_path = Path(temp_dir) / "test.key"

        save_key(key, str(key_path))

        assert key_path.exists()
        assert load_key(str(key_path)) == key


def test_encrypt_and_decrypt_secret_round_trip():
    key = generate_key()
    original = "super-secret-message"

    token = encrypt_secret(original, key)
    restored = decrypt_secret(token, key)

    assert isinstance(token, str)
    assert restored == original


def test_encrypt_secret_produces_different_token_for_same_input():
    key = generate_key()
    original = "same-message"

    token_one = encrypt_secret(original, key)
    token_two = encrypt_secret(original, key)

    assert token_one != token_two
