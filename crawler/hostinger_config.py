"""Hostinger database configuration."""

from __future__ import annotations

import os
from typing import Optional

try:
    # Untracked, git-ignored file for local dev convenience (see .gitignore).
    # Never commit real credentials here or as hardcoded defaults below -
    # this file previously had a real password checked into git history.
    from crawler import local_secrets  # type: ignore
except ImportError:
    local_secrets = None


def _secret(env_var: str, local_attr: str) -> str:
    value = os.getenv(env_var)
    if value:
        return value
    if local_secrets is not None:
        return getattr(local_secrets, local_attr, "")
    return ""


class HostingerConfig:
    """Configuration for MariaDB upload (now hosted on Synology NAS).

    Credentials come from environment variables, or from an untracked
    crawler/local_secrets.py for local dev convenience. Set the following
    env vars (or create crawler/local_secrets.py with matching attributes)
    before running: HOSTINGER_DB_HOST, HOSTINGER_DB_NAME, HOSTINGER_DB_USER,
    HOSTINGER_DB_PASSWORD.
    """

    HOST = _secret("HOSTINGER_DB_HOST", "HOSTINGER_DB_HOST")
    DATABASE = _secret("HOSTINGER_DB_NAME", "HOSTINGER_DB_NAME")
    USER = _secret("HOSTINGER_DB_USER", "HOSTINGER_DB_USER")
    PASSWORD = _secret("HOSTINGER_DB_PASSWORD", "HOSTINGER_DB_PASSWORD")

    # Upload settings
    ENABLE_UPLOAD = os.getenv("HOSTINGER_ENABLE_UPLOAD", "true").lower() == "true"
    BATCH_SIZE = int(os.getenv("HOSTINGER_BATCH_SIZE", "10"))
    CONNECTION_TIMEOUT = int(os.getenv("HOSTINGER_CONNECTION_TIMEOUT", "10"))

    @classmethod
    def get_uploader_kwargs(cls) -> dict:
        """Get kwargs for HostingerUploader initialization."""
        return {
            "host": cls.HOST,
            "database": cls.DATABASE,
            "user": cls.USER,
            "password": cls.PASSWORD,
        }

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """Validate configuration.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        if not cls.HOST:
            errors.append("HOSTINGER_DB_HOST not set")
        if not cls.DATABASE:
            errors.append("HOSTINGER_DB_NAME not set")
        if not cls.USER:
            errors.append("HOSTINGER_DB_USER not set")
        if not cls.PASSWORD:
            errors.append("HOSTINGER_DB_PASSWORD not set")

        return len(errors) == 0, errors

    @classmethod
    def print_config(cls) -> None:
        """Print current configuration (safely, without exposing password)."""
        print("Hostinger Configuration:")
        print(f"  Host: {cls.HOST}")
        print(f"  Database: {cls.DATABASE}")
        print(f"  User: {cls.USER}")
        print(f"  Password: {'*' * len(cls.PASSWORD)}")
        print(f"  Upload enabled: {cls.ENABLE_UPLOAD}")
        print(f"  Batch size: {cls.BATCH_SIZE}")
