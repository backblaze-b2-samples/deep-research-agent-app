import re
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Backblaze regions are lower-case location tokens such as us-west-004 and
# eu-central-003. Keeping the grammar tight prevents URL authority injection
# when deriving the S3 endpoint.
_B2_REGION_PATTERN = re.compile(r"^[a-z]{2}(?:-[a-z]+)+-\d{3}$")


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible API) ---
    b2_region: str = ""
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_public_url_base: str = ""
    # Migration-only legacy names. Keep these explicit so old dotenv files do
    # not fail validation, while unrelated unknown keys still fail.
    b2_endpoint: str = Field(default="", exclude=True, repr=False)
    b2_public_url: str = Field(default="", exclude=True, repr=False)

    # --- Anthropic / research agent ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    # Depth bounds for a single research run. Lower these to cut cost.
    research_max_searches: int = 8
    research_max_sources: int = 8
    # Adaptive-thinking effort passed to the model: "low" | "medium" | "high".
    research_effort: str = "medium"
    # Browser fetch limits (Playwright). Keep small — fetched pages are
    # untrusted input and we cap size/time to bound cost and SSRF blast radius.
    fetch_timeout_ms: int = 30_000
    screenshot_timeout_ms: int = 15_000
    fetch_max_bytes: int = 5 * 1024 * 1024  # 5MB of rendered HTML
    screenshot_viewport_width: int = 1280
    screenshot_viewport_height: int = 1024

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "forbid",
    }

    @field_validator("b2_region")
    @classmethod
    def validate_b2_region(cls, value: str) -> str:
        if not value:
            return value
        if not _B2_REGION_PATTERN.fullmatch(value):
            raise ValueError(
                "B2_REGION must be a Backblaze region token like us-west-004"
            )
        return value

    @property
    def b2_endpoint_url(self) -> str:
        if not self.b2_region:
            return ""
        endpoint = f"https://s3.{self.b2_region}.backblazeb2.com"
        host = urlparse(endpoint).hostname
        if host is None or not host.endswith(".backblazeb2.com"):
            raise ValueError("Derived B2 endpoint must target backblazeb2.com")
        return endpoint

    @property
    def effective_b2_public_url_base(self) -> str:
        return self.b2_public_url_base or self.b2_public_url

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


settings = Settings()
