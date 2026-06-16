"""Tests for the research agent service.

These exercise the real orchestration in ``service/research.py`` and the real
B2-prefix logic in ``repo/b2_research.py`` against an in-memory fake S3 client,
with the external boundaries (``llm_client`` + ``browser``) mocked. The point
is to prove that a run writes the expected artifacts under
``research/<id>/`` — i.e. that B2 really is the agent's memory — without making
network calls or spending tokens.
"""

import json
from datetime import UTC, datetime

import pytest

from app.repo import b2_research
from app.repo.browser import FetchedPage
from app.service import library, report, research, research_search


class FakeS3:
    """Minimal in-memory stand-in for the boto3 S3 client used by b2_research."""

    def __init__(self):
        self.store: dict[str, bytes] = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.store[Key] = Body if isinstance(Body, bytes) else Body.encode()

    def get_object(self, Bucket, Key):
        if Key not in self.store:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

        class _Body:
            def __init__(self, data):
                self._data = data

            def read(self):
                return self._data

        return {"Body": _Body(self.store[Key])}

    def head_object(self, Bucket, Key):
        if Key not in self.store:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {"ContentLength": len(self.store[Key])}

    def list_objects_v2(self, Bucket, Prefix="", Delimiter="", MaxKeys=1000, **kw):
        keys = [k for k in self.store if k.startswith(Prefix)]
        if Delimiter:
            prefixes = set()
            for k in keys:
                rest = k[len(Prefix):]
                if Delimiter in rest:
                    prefixes.add(Prefix + rest.split(Delimiter)[0] + Delimiter)
            return {"CommonPrefixes": [{"Prefix": p} for p in sorted(prefixes)]}
        return {
            "Contents": [{"Key": k, "Size": len(self.store[k])} for k in keys],
            "IsTruncated": False,
        }

    def delete_objects(self, Bucket, Delete):
        for obj in Delete["Objects"]:
            self.store.pop(obj["Key"], None)


@pytest.fixture
def fake_b2(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(b2_research, "get_s3_client", lambda: fake)
    from app.config import settings

    monkeypatch.setattr(settings, "b2_bucket_name", "test-bucket")
    return fake


class FakeMessage:
    """A stand-in Anthropic Message: content blocks + an optional container.

    ``container`` mirrors the SDK: ``None`` when no server-side tool ran, else
    an object with an ``.id`` (the code-execution container the bundled
    ``web_search`` tool uses).
    """

    def __init__(self, content, container=None):
        self.content = content
        self.container = container


class _Container:
    def __init__(self, container_id):
        self.id = container_id


class _Text:
    type = "text"

    def __init__(self, text):
        self.text = text


class _ToolUse:
    type = "tool_use"

    def __init__(self, tool_id, name, tool_input):
        self.id = tool_id
        self.name = name
        self.input = tool_input


def test_run_research_caches_sources_and_report(fake_b2, monkeypatch):
    """A run that fetches one page then writes a report persists all artifacts."""
    # Turn 1: model asks to fetch a source. Turn 2: model writes the report.
    turns = iter(
        [
            FakeMessage([_ToolUse("t1", "fetch_source", {"url": "https://example.com"})]),
            FakeMessage([_Text("# Findings\n\nGrounded answer [1].\n\n## Sources\n[1] Example")]),
        ]
    )
    monkeypatch.setattr(
        research.llm_client, "create_turn", lambda messages, container=None: next(turns)
    )

    def fake_fetch(url):
        return FetchedPage(
            url=url,
            title="Example Domain",
            html=b"<html><body>Example</body></html>",
            text_markdown="Example readable text.",
            screenshot_png=b"\x89PNG fake",
            sha256="deadbeef",
        )

    monkeypatch.setattr(research.browser, "fetch_page", fake_fetch)

    research_id = research.create_research("What is example.com?")
    research.run_research(research_id)

    # report.json + report.md exist under research/<id>/
    meta = library.get_meta(research_id)
    assert meta.status == "complete"
    assert len(meta.sources) == 1
    src = meta.sources[0]

    keys = set(fake_b2.store.keys())
    assert f"research/{research_id}/report.json" in keys
    assert f"research/{research_id}/report.md" in keys
    assert f"research/{research_id}/sources/{src.source_id}/page.html" in keys
    assert f"research/{research_id}/sources/{src.source_id}/page.md" in keys
    assert f"research/{research_id}/sources/{src.source_id}/screenshot.png" in keys
    assert f"research/{research_id}/sources/{src.source_id}/meta.json" in keys

    detail = report.get_detail(research_id)
    assert detail.report_markdown.startswith("# Findings")


def test_follow_up_preserves_whole_conversation(fake_b2, monkeypatch):
    """A follow-up keeps every turn's report so the full conversation renders.

    The bug this guards against: follow-ups overwrote report.md and meta.question,
    so the detail view could only ever show the latest answer. Each turn's report
    must now persist under reports/<report_id>.md and come back via get_detail.
    """
    replies = iter(
        [
            FakeMessage([_Text("# First report\n\nInitial findings.")]),
            FakeMessage([_Text("# Second report\n\nFollow-up findings.")]),
        ]
    )
    monkeypatch.setattr(
        research.llm_client, "create_turn", lambda m, container=None: next(replies)
    )

    research_id = research.create_research("What is X?")
    research.run_research(research_id)
    research.add_follow_up(research_id, "And how does X compare to Y?")
    research.run_research(research_id)

    meta = library.get_meta(research_id)
    assert len(meta.turns) == 2

    # Both per-turn reports are persisted under reports/<report_id>.md.
    for turn in meta.turns:
        assert f"research/{research_id}/reports/{turn.report_id}.md" in fake_b2.store

    # get_detail returns the whole conversation, oldest first, with both Q&As.
    detail = report.get_detail(research_id)
    assert [t.question for t in detail.turns] == [
        "What is X?",
        "And how does X compare to Y?",
    ]
    assert detail.turns[0].report_markdown.startswith("# First report")
    assert detail.turns[1].report_markdown.startswith("# Second report")
    # report.md still holds the latest report (follow-up context + search).
    assert detail.report_markdown.startswith("# Second report")


def test_legacy_thread_without_per_turn_report_falls_back(fake_b2, monkeypatch):
    """A thread written before per-turn reports existed still shows its latest one.

    Simulates the legacy layout: report.md exists but reports/<report_id>.md does
    not. get_detail must fall back to report.md for the most recent turn.
    """
    monkeypatch.setattr(
        research.llm_client,
        "create_turn",
        lambda m, container=None: FakeMessage([_Text("# Legacy report\n\nText.")]),
    )
    research_id = research.create_research("legacy question")
    research.run_research(research_id)

    # Delete the per-turn copy to mimic a pre-feature thread.
    meta = library.get_meta(research_id)
    fake_b2.store.pop(
        f"research/{research_id}/reports/{meta.turns[0].report_id}.md", None
    )

    detail = report.get_detail(research_id)
    assert len(detail.turns) == 1
    assert detail.turns[0].report_markdown.startswith("# Legacy report")


def test_web_search_container_is_threaded_to_next_turn(fake_b2, monkeypatch):
    """A turn carrying a server-side container id must replay it on later turns.

    The bundled web_search tool runs in a code-execution container. Once a turn
    returns ``message.container``, every subsequent ``create_turn`` call must
    pass that id back — otherwise the API rejects it with 400 "container_id is
    required when there are pending tool uses generated by code execution". This
    is the exact failure the run died on (turns:0, no report).
    """
    # Turn 1: a server-side web_search ran (container present), then the model
    # asks us to fetch a source. Turn 2: writes the report.
    turns = iter(
        [
            FakeMessage(
                [_ToolUse("t1", "fetch_source", {"url": "https://example.com"})],
                container=_Container("cntr_abc123"),
            ),
            FakeMessage([_Text("# Findings\n\nGrounded [1].")]),
        ]
    )
    seen_containers: list[str | None] = []

    def fake_create_turn(messages, container=None):
        seen_containers.append(container)
        return next(turns)

    monkeypatch.setattr(research.llm_client, "create_turn", fake_create_turn)
    monkeypatch.setattr(
        research.browser,
        "fetch_page",
        lambda url: FetchedPage(
            url=url, title="t", html=b"h", text_markdown="x",
            screenshot_png=b"png", sha256="s",
        ),
    )

    research_id = research.create_research("q")
    research.run_research(research_id)

    # First turn starts with no container; the second turn must replay the id
    # surfaced by the first turn's response.
    assert seen_containers == [None, "cntr_abc123"]
    assert library.get_meta(research_id).status == "complete"


def test_unsafe_url_is_skipped_not_fatal(fake_b2, monkeypatch):
    """A blocked (SSRF) fetch returns an error to the model; the run still finishes."""
    turns = iter(
        [
            FakeMessage([_ToolUse("t1", "fetch_source", {"url": "http://169.254.169.254/"})]),
            FakeMessage([_Text("# Report\n\nCould not read that source.")]),
        ]
    )
    monkeypatch.setattr(
        research.llm_client, "create_turn", lambda messages, container=None: next(turns)
    )

    def blocked(url):
        raise research.browser.UnsafeUrlError("private address")

    monkeypatch.setattr(research.browser, "fetch_page", blocked)

    research_id = research.create_research("probe internal")
    research.run_research(research_id)

    meta = library.get_meta(research_id)
    assert meta.status == "complete"
    assert meta.sources == []  # the blocked fetch cached nothing


def test_screenshot_failure_is_non_fatal(fake_b2, monkeypatch):
    """If a page has no screenshot, HTML/text are still cached and the run completes."""
    turns = iter(
        [
            FakeMessage([_ToolUse("t1", "fetch_source", {"url": "https://example.com"})]),
            FakeMessage([_Text("# Report\n\nDone.")]),
        ]
    )
    monkeypatch.setattr(
        research.llm_client, "create_turn", lambda messages, container=None: next(turns)
    )
    monkeypatch.setattr(
        research.browser,
        "fetch_page",
        lambda url: FetchedPage(
            url=url,
            title="No Shot",
            html=b"<html></html>",
            text_markdown="text",
            screenshot_png=None,
            sha256="abc",
        ),
    )

    research_id = research.create_research("q")
    research.run_research(research_id)

    meta = library.get_meta(research_id)
    src = meta.sources[0]
    assert src.has_screenshot is False
    assert f"research/{research_id}/sources/{src.source_id}/page.html" in fake_b2.store
    screenshot_key = f"research/{research_id}/sources/{src.source_id}/screenshot.png"
    assert screenshot_key not in fake_b2.store


def test_run_failure_records_failed_status(fake_b2, monkeypatch):
    """An exception in the loop is recorded as status=failed, not swallowed."""

    def boom(messages, container=None):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(research.llm_client, "create_turn", boom)

    research_id = research.create_research("q")
    research.run_research(research_id)

    meta = library.get_meta(research_id)
    assert meta.status == "failed"
    assert "model exploded" in (meta.error or "")
    assert f"research/{research_id}/.failed" in fake_b2.store


def test_delete_is_scoped_to_prefix(fake_b2, monkeypatch):
    """Deleting one research thread leaves a sibling thread's objects intact."""
    monkeypatch.setattr(
        research.llm_client, "create_turn", lambda m, container=None: FakeMessage([_Text("# R")])
    )

    keep = research.create_research("keep me")
    research.run_research(keep)
    drop = research.create_research("drop me")
    research.run_research(drop)

    # A shared, unrelated key must survive too.
    fake_b2.store["other-app/data.bin"] = b"x"

    library.delete_research(drop)

    assert not any(k.startswith(f"research/{drop}/") for k in fake_b2.store)
    assert any(k.startswith(f"research/{keep}/") for k in fake_b2.store)
    assert "other-app/data.bin" in fake_b2.store


def test_search_finds_by_question(fake_b2, monkeypatch):
    monkeypatch.setattr(
        research.llm_client,
        "create_turn",
        lambda m, container=None: FakeMessage([_Text("# Report on quantum computing")]),
    )
    research_id = research.create_research("Tell me about quantum computing")
    research.run_research(research_id)

    hits = research_search.search("quantum")
    assert any(h.research_id == research_id for h in hits)


def test_stats_counts_research_and_screenshots(fake_b2, monkeypatch):
    turns = iter(
        [
            FakeMessage([_ToolUse("t1", "fetch_source", {"url": "https://example.com"})]),
            FakeMessage([_Text("# R")]),
        ]
    )
    monkeypatch.setattr(
        research.llm_client, "create_turn", lambda m, container=None: next(turns)
    )
    monkeypatch.setattr(
        research.browser,
        "fetch_page",
        lambda url: FetchedPage(
            url=url, title="t", html=b"h", text_markdown="x",
            screenshot_png=b"png", sha256="s",
        ),
    )
    research.run_research(research.create_research("q"))

    stats = library.get_stats()
    assert stats.total_research == 1
    assert stats.total_sources == 1
    assert stats.total_screenshots == 1
    assert stats.total_storage_bytes > 0


def test_meta_roundtrips_through_b2(fake_b2):
    """report.json written by create_research deserializes back to ReportMeta."""
    research_id = research.create_research("roundtrip")
    raw = fake_b2.store[f"research/{research_id}/report.json"]
    data = json.loads(raw)
    assert data["question"] == "roundtrip"
    assert data["status"] == "pending"
    parsed_created = datetime.fromisoformat(data["created_at"])
    assert parsed_created.tzinfo is not None
    assert parsed_created <= datetime.now(UTC)
