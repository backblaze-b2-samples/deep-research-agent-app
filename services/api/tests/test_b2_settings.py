from urllib.parse import urlparse

import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.repo import b2_client


def test_legacy_b2_dotenv_keys_do_not_block_startup(tmp_path, monkeypatch):
    """Legacy rollout vars are ignored while the standard vars drive runtime."""
    for key in (
        "B2_REGION",
        "B2_APPLICATION_KEY_ID",
        "B2_APPLICATION_KEY",
        "B2_BUCKET_NAME",
        "B2_PUBLIC_URL_BASE",
    ):
        monkeypatch.delenv(key, raising=False)

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
            ]
        )
    )

    loaded = Settings(_env_file=env_file)

    assert loaded.b2_endpoint_url == "https://s3.us-west-004.backblazeb2.com"
    assert loaded.b2_public_url_base == ""


@pytest.mark.parametrize(
    "region",
    [
        "us-west-004@attacker.example/",
        "us-west-004/path",
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
