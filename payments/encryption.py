import hashlib
from cryptography.fernet import Fernet
from django.conf import settings


def _fernet() -> Fernet:
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    """Encrypt a plaintext string with Fernet (AES-128-CBC + HMAC-SHA256)."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decrypt a Fernet-encrypted string back to plaintext."""
    return _fernet().decrypt(value.encode()).decode()


def hash_identifier(value: str) -> str:
    """One-way SHA-256 hash used only for duplicate detection.
    The hash is never reversible — the identifier is separately encrypted."""
    return hashlib.sha256(value.encode()).hexdigest()


def mask_identifier(value: str, visible: int = 4) -> str:
    if len(value) <= visible:
        return '*' * len(value)
    return '*' * (len(value) - visible) + value[-visible:]


def luhn_check(number: str) -> bool:
    """Validate a credit/debit card number with the Luhn algorithm."""
    digits = [int(d) for d in number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits) + sum(sum(divmod(d * 2, 10)) for d in even_digits)
    return total % 10 == 0
