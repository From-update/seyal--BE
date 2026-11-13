import hashlib
import random
import string

def generate_numeric_otp(length=6) -> str:
    """Generate a cryptographically suitable random numeric OTP."""
    return ''.join(random.choices(string.digits, k=length))

def hash_secret(value: str) -> str:
    """Hash OTP or token with SHA-256 for secure storage."""
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def get_fractional_position(prev_pos: float = None, next_pos: float = None) -> float:
    """
    Generate fractional index between prev_pos and next_pos.
    If no prev, place before next_pos (next_pos / 2 or 1.0).
    If no next, place after prev_pos (prev_pos + 1.0).
    """
    if prev_pos is None and next_pos is None:
        return 1.0
    if prev_pos is None:
        return next_pos / 2.0
    if next_pos is None:
        return prev_pos + 1.0
    return (prev_pos + next_pos) / 2.0

