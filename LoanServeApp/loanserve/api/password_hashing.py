"""Salted password hashes; plaintext passwords are never stored."""

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError


class PasswordVault:
    def __init__(self):
        self.password_hasher = PasswordHasher()

    def hash_password(self, plain_password):
        return self.password_hasher.hash(plain_password)

    def matches_stored_hash(self, plain_password, stored_hash):
        try:
            return self.password_hasher.verify(stored_hash, plain_password)
        except VerificationError:
            return False
