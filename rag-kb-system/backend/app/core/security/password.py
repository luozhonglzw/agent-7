"""Password hashing and verification utilities.

Uses bcrypt via passlib for secure password storage.
Never stores passwords in plain text.

Usage:
    from app.core.security.password import get_password_hash, verify_password

    hashed = get_password_hash("user_password")
    is_valid = verify_password("user_password", hashed)
"""

from passlib.context import CryptContext

# ── Password Context ───────────────────────────────────────────
# Configure bcrypt with automatic rounds detection
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password to hash.

    Returns:
        Bcrypt hashed password string.

    Example:
        >>> hashed = get_password_hash("my_secure_password")
        >>> hashed.startswith("$2b$")
        True
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Previously hashed password to compare against.

    Returns:
        True if password matches the hash, False otherwise.

    Example:
        >>> hashed = get_password_hash("test123")
        >>> verify_password("test123", hashed)
        True
        >>> verify_password("wrong", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)
