import base64
from cryptography.fernet import Fernet


def generate_key() -> bytes:
    return Fernet.generate_key()


def load_key(key_path: str) -> bytes:
    with open(key_path, "rb") as key_file:
        return key_file.read()


def save_key(key: bytes, key_path: str) -> None:
    with open(key_path, "wb") as key_file:
        key_file.write(key)


def encrypt_secret(data: str, key: bytes) -> str:
    token = Fernet(key).encrypt(data.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(token: str, key: bytes) -> str:
    decoded_token = token.encode("utf-8")
    return Fernet(key).decrypt(decoded_token).decode("utf-8")
