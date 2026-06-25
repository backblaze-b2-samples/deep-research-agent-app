from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible API) ---
    b2_region: str = ""
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_public_url_base: str = ""

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def b2_endpoint_url(self) -> str:
        if not self.b2_region:
            return ""
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


settings = Settings()
