import base64
import os


class Fernet:
    def __init__(self, key: bytes):
        if not isinstance(key, bytes):
            raise TypeError("key must be bytes")
        self.key = key

    @staticmethod
    def generate_key() -> bytes:
        return base64.urlsafe_b64encode(os.urandom(32))

    def encrypt(self, data: bytes) -> bytes:
        nonce = os.urandom(8)
        payload = b"v1:" + nonce + b":" + data
        return base64.urlsafe_b64encode(payload)

    def decrypt(self, token: bytes) -> bytes:
        try:
            raw = base64.urlsafe_b64decode(token)
        except Exception as exc:
            raise ValueError("invalid token") from exc

        if not raw.startswith(b"v1:"):
            raise ValueError("invalid token")

        parts = raw.split(b":", 2)
        if len(parts) != 3:
            raise ValueError("invalid token")

        return parts[2]
