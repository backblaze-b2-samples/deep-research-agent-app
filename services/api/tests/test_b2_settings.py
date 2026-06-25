from urllib.parse import urlparse

import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.repo import b2_client

B2_ENV_KEYS = (
    "B2_REGION",
    "B2_APPLICATION_KEY_ID",
    "B2_APPLICATION_KEY",
    "B2_BUCKET_NAME",
    "B2_PUBLIC_URL_BASE",
    "B2_ENDPOINT",
    "B2_PUBLIC_URL",
)


class FakeS3Client:
    def __init__(self):
        self.put_object_kwargs = {}

    def put_object(self, **kwargs):
        self.put_object_kwargs = kwargs


def clear_b2_env(monkeypatch):
    for key in B2_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_legacy_b2_dotenv_keys_do_not_block_startup(tmp_path, monkeypatch):
    """Legacy rollout vars are ignored while the standard vars drive runtime."""
    clear_b2_env(monkeypatch)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "B2_REGION=us-west-004",
                "B2_APPLICATION_KEY_ID=key-id",
                "B2_APPLICATION_KEY=application-key",
                "B2_BUCKET_NAME=bucket-name",
                "B2_ENDPOINT=https://legacy.example.test",
                "B2_PUBLIC_URL=https://legacy-public.example.test",
                "B2_PUBLIC_URL_BASE=https://public.example.test",
            ]
        )
    )

    loaded = Settings(_env_file=env_file)

    assert loaded.b2_endpoint_url == "https://s3.us-west-004.backblazeb2.com"
    assert loaded.effective_b2_public_url_base == "https://public.example.test"


def test_legacy_public_url_falls_back_when_standard_name_missing(
    tmp_path, monkeypatch
):
    clear_b2_env(monkeypatch)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "B2_REGION=us-west-004",
                "B2_APPLICATION_KEY_ID=key-id",
                "B2_APPLICATION_KEY=application-key",
                "B2_BUCKET_NAME=bucket-name",
                "B2_PUBLIC_URL=https://legacy-public.example.test",
            ]
        )
    )

    loaded = Settings(_env_file=env_file)

    assert loaded.b2_public_url_base == ""
    assert (
        loaded.effective_b2_public_url_base
        == "https://legacy-public.example.test"
    )


def test_unknown_b2_dotenv_key_is_rejected(tmp_path, monkeypatch):
    clear_b2_env(monkeypatch)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "B2_REGION=us-west-004",
                "B2_APPLICATION_KEY_ID=key-id",
                "B2_APPLICATION_KEY=application-key",
                "B2_BUCKET_NAME=bucket-name",
                "B2_UNKNOWN_SETTING=value",
            ]
        )
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=env_file)


@pytest.mark.parametrize(
    "region",
    [
        "us-west-004@attacker.example/",
        "us-west-004.attacker.com#",
        "us-west-004/path",
        "us-west-004?x=",
        "us-west-004:443@attacker.com",
        "us-west-004#fragment",
        "us-west-004:443",
        "us-west-004\\path",
        "us-west-004 path",
        "us-west-004\n",
        "us-west-004\x00",
    ],
)
def test_b2_region_rejects_unsafe_endpoint_tokens(region):
    with pytest.raises(ValidationError, match="B2_REGION"):
        Settings(_env_file=None, b2_region=region)


def test_b2_endpoint_host_stays_on_backblaze_domain():
    loaded = Settings(_env_file=None, b2_region="us-west-004")

    parsed = urlparse(loaded.b2_endpoint_url)

    assert parsed.scheme == "https"
    assert parsed.hostname == "s3.us-west-004.backblazeb2.com"
    assert parsed.hostname.endswith(".backblazeb2.com")


def test_b2_client_uses_s3_endpoint_and_sample_user_agent(monkeypatch):
    captured = {}
    sentinel = object()

    def fake_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured["kwargs"] = kwargs
        return sentinel

    b2_client.get_s3_client.cache_clear()
    monkeypatch.setattr(settings, "b2_region", "us-west-004")
    monkeypatch.setattr(settings, "b2_application_key_id", "key-id")
    monkeypatch.setattr(settings, "b2_application_key", "application-key")
    monkeypatch.setattr(b2_client.boto3, "client", fake_client)

    try:
        assert b2_client.get_s3_client() is sentinel
    finally:
        b2_client.get_s3_client.cache_clear()

    kwargs = captured["kwargs"]
    config = kwargs["config"]

    assert captured["service_name"] == "s3"
    assert kwargs["endpoint_url"] == "https://s3.us-west-004.backblazeb2.com"
    assert kwargs["region_name"] == "us-west-004"
    assert kwargs["aws_access_key_id"] == "key-id"
    assert kwargs["aws_secret_access_key"] == "application-key"
    assert config.signature_version == "s3v4"
    assert "(backblaze-b2-samples)" in config.user_agent_extra


def test_upload_file_public_url_strips_trailing_base_slash(monkeypatch):
    fake_client = FakeS3Client()
    monkeypatch.setattr(
        settings,
        "b2_public_url_base",
        "https://bucket.s3.us-west-004.backblazeb2.com/",
    )
    monkeypatch.setattr(settings, "b2_public_url", "")
    monkeypatch.setattr(settings, "b2_bucket_name", "bucket-name")
    monkeypatch.setattr(b2_client, "get_s3_client", lambda: fake_client)

    metadata = b2_client.upload_file(
        b"page",
        "research/thread/source page.md",
        "text/markdown",
    )

    assert fake_client.put_object_kwargs["Bucket"] == "bucket-name"
    assert fake_client.put_object_kwargs["Key"] == (
        "research/thread/source page.md"
    )
    assert metadata.url == (
        "https://bucket.s3.us-west-004.backblazeb2.com/"
        "research/thread/source%20page.md"
    )


def test_upload_file_public_url_falls_back_to_legacy_name(monkeypatch):
    fake_client = FakeS3Client()
    monkeypatch.setattr(settings, "b2_public_url_base", "")
    monkeypatch.setattr(
        settings,
        "b2_public_url",
        "https://legacy-public.example.test/",
    )
    monkeypatch.setattr(settings, "b2_bucket_name", "bucket-name")
    monkeypatch.setattr(b2_client, "get_s3_client", lambda: fake_client)

    metadata = b2_client.upload_file(
        b"page",
        "research/thread/source page.md",
        "text/markdown",
    )

    assert metadata.url == (
        "https://legacy-public.example.test/"
        "research/thread/source%20page.md"
    )
