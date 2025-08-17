from __future__ import annotations

import os
from typing import List

from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator


class Settings(BaseSettings):
    """
    Strongly-typed environment.
    ENV: "dev" | "prod" | "staging"
    ENFORCE_HTTPS: reject non-HTTPS when true
    CSP_REPORT_ONLY: send CSP in report-only mode when true
    ALLOWED_ORIGINS: comma-separated list for CORS
    """

    ENV: str = os.getenv("ENV", "dev")
    ENFORCE_HTTPS: bool = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"
    CSP_REPORT_ONLY: bool = os.getenv("CSP_REPORT_ONLY", "false").lower() == "true"
    ALLOWED_ORIGINS: List[AnyHttpUrl] | None = None

    @validator("ALLOWED_ORIGINS", pre=True)
    def _parse_allowed_origins(cls, v, values):
        if v:
            if isinstance(v, list):
                return v
            return [o.strip() for o in str(v).split(",") if o.strip()]

        if values.get("ENV", "dev") == "dev":
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
            ]
        return [
            "https://recoveryos.org",
            "https://www.recoveryos.org",
        ]

    class Config:
        env_file = ".env"
        case_sensitive = True
