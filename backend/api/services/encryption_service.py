"""
Encryption service for sensitive data
Uses Fernet (symmetric encryption) for API keys
"""
from cryptography.fernet import Fernet
from backend.api.config import settings
from typing import Optional


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""

    def __init__(self):
        """Initialize encryption service with key from settings"""
        if not settings.ENCRYPTION_KEY:
            raise ValueError(
                "ENCRYPTION_KEY not set in environment. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        self._fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    def encrypt_api_key(self, plain_key: str) -> str:
        """
        Encrypt API key using Fernet symmetric encryption

        Args:
            plain_key: Plain text API key

        Returns:
            Encrypted API key as string
        """
        if not plain_key:
            return ""

        encrypted = self._fernet.encrypt(plain_key.encode())
        return encrypted.decode()

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt API key

        Args:
            encrypted_key: Encrypted API key

        Returns:
            Plain text API key
        """
        if not encrypted_key:
            return ""

        try:
            decrypted = self._fernet.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt API key: {str(e)}")


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create encryption service singleton"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Convenience functions
def encrypt_api_key(plain_key: str) -> str:
    """Encrypt API key (convenience function)"""
    return get_encryption_service().encrypt_api_key(plain_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key (convenience function)"""
    return get_encryption_service().decrypt_api_key(encrypted_key)
