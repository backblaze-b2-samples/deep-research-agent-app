"""B2 object operations scoped to the ``research/`` prefix.

This is where the research agent's *memory* lives. Every artifact the agent
touches — raw page HTML, readable-text extractions, full-page screenshots, and
the final report — is written here via the S3-compatible API. Past research is
listed and read back from the same prefix, so a durable research library
accumulates over time.

Layout (see ARCHITECTURE.md / the scaffold plan):

    research/<research_id>/
        report.json                 # ReportMeta (status, sources[], turns[])
        report.md                   # latest long-form Markdown report
        reports/<report_id>.md      # per-turn report (full conversation history)
        thread.json                 # follow-up chain
        sources/<source_id>/
            page.html               # cached rendered HTML
            page.md                 # extracted readable text (Markdown)
            screenshot.png          # Playwright full-page screenshot
            meta.json               # per-source provenance

All access goes through the single S3 client in ``b2_client`` (custom user
agent ``b2ai-deep-research-agent-app``). No b2-native API.
"""

import json
import logging

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client

logger = logging.getLogger(__name__)

# Single source of truth for the app's prefix. Every key this module writes or
# reads is anchored under here, so deletes and listings can never touch data
# belonging to other apps sharing the bucket.
RESEARCH_PREFIX = "research/"


def research_key(research_id: str, *parts: str) -> str:
    """Build a key under ``research/<research_id>/...``."""
    suffix = "/".join(p.strip("/") for p in parts if p)
    base = f"{RESEARCH_PREFIX}{research_id}"
    return f"{base}/{suffix}" if suffix else base


def source_key(research_id: str, source_id: str, name: str) -> str:
    return research_key(research_id, "sources", source_id, name)


def turn_report_key(research_id: str, report_id: str) -> str:
    """Durable per-turn report Markdown: ``research/<id>/reports/<report_id>.md``.

    ``report.md`` always holds the *latest* report (and is the follow-up
    context). This keeps every turn's report so the conversation history can be
    rendered in full instead of only the most recent answer.
    """
    return research_key(research_id, "reports", f"{report_id}.md")


def put_bytes(key: str, data: bytes, content_type: str) -> int:
    """Write raw bytes to B2. Returns the byte count. Raises RuntimeError."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e
    return len(data)


def put_text(key: str, text: str, content_type: str) -> int:
    return put_bytes(key, text.encode("utf-8"), content_type)


def put_json(key: str, obj: dict) -> int:
    return put_text(key, json.dumps(obj, default=str, indent=2), "application/json")


def get_bytes(key: str) -> bytes | None:
    """Read an object body, or None if it doesn't exist."""
    client = get_s3_client()
    try:
        resp = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise
    return resp["Body"].read()


def get_text(key: str) -> str | None:
    data = get_bytes(key)
    return data.decode("utf-8", errors="replace") if data is not None else None


def get_json(key: str) -> dict | None:
    text = get_text(key)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Corrupt JSON at key=%s", key)
        return None


def object_exists(key: str) -> bool:
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.b2_bucket_name, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return False
        raise


def list_keys(prefix: str = RESEARCH_PREFIX, delimiter: str = "") -> list[dict]:
    """List objects under a prefix (always inside ``research/``).

    Returns the raw S3 ``Contents`` dicts (Key/Size/LastModified). Paginates.
    """
    if not prefix.startswith(RESEARCH_PREFIX):
        raise ValueError("b2_research only operates under the research/ prefix")
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    if delimiter:
        kwargs["Delimiter"] = delimiter
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            contents.extend(resp.get("Contents", []))
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return contents


def list_research_ids() -> list[str]:
    """Return the research_id of every thread (top-level subprefix)."""
    client = get_s3_client()
    ids: list[str] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": RESEARCH_PREFIX,
        "Delimiter": "/",
        "MaxKeys": 1000,
    }
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            for cp in resp.get("CommonPrefixes", []):
                # "research/<id>/" -> "<id>"
                ids.append(cp["Prefix"][len(RESEARCH_PREFIX):].rstrip("/"))
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed for research ids: {e}") from e
    return ids


def delete_research(research_id: str) -> int:
    """Delete every object under ``research/<research_id>/``.

    Scoped strictly to this thread's prefix — never wipes shared data.
    Returns the number of objects deleted.
    """
    if not research_id:
        raise ValueError("research_id is required")
    prefix = research_key(research_id) + "/"
    keys = [obj["Key"] for obj in list_keys(prefix)]
    if not keys:
        return 0
    client = get_s3_client()
    deleted = 0
    # delete_objects caps at 1000 keys per request.
    for i in range(0, len(keys), 1000):
        batch = keys[i : i + 1000]
        try:
            client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
            )
        except ClientError as e:
            raise RuntimeError(f"B2 delete failed for '{prefix}': {e}") from e
        deleted += len(batch)
    return deleted


def presign(key: str, filename: str | None = None, expires_in: int = 600) -> str:
    """Presigned GET URL for previewing/downloading a cached artifact."""
    client = get_s3_client()
    params: dict = {"Bucket": settings.b2_bucket_name, "Key": key}
    if filename:
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
    try:
        return client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e
