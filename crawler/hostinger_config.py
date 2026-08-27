"""Hostinger database configuration."""

from __future__ import annotations

import os
from typing import Optional


class HostingerConfig:
    """Configuration for Hostinger MySQL upload."""

    # Default credentials from Hostinger panel
    # You can override these with environment variables:
    # - HOSTINGER_DB_HOST
    # - HOSTINGER_DB_NAME
    # - HOSTINGER_DB_USER
    # - HOSTINGER_DB_PASSWORD

    HOST = os.getenv("HOSTINGER_DB_HOST", "localhost")
    DATABASE = os.getenv("HOSTINGER_DB_NAME", "u230450852_retrocrawler")
    USER = os.getenv("HOSTINGER_DB_USER", "u230450852_retrocrawler")
    PASSWORD = os.getenv("HOSTINGER_DB_PASSWORD", "lQ$cyITcQ5K8PzeyUu5")

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
