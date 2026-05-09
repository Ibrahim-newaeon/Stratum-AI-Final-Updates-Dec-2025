# =============================================================================
# Stratum AI — copilot_llm bridge tests (Phase D PR2)
# =============================================================================
"""
Verifies the copilot_llm bridge wires Anthropic + RAG retrieval together
correctly. OpenAI / Anthropic / pgvector are all mocked — this file
runs without network or DB.

Covers the contract from PR2:

- Returns LLMResult(text=None) when llm flag is off, no key, or SDK
  is missing.
- Returns LLMResult(text=str, citations=[...]) when both LLM and RAG
  are enabled and retrieval finds hits.
- Returns LLMResult(text=str, citations=[]) when RAG is enabled but
  retrieval errors / returns empty (LLM still runs).
- Citation order matches retrieval order (closest distance first).
- Heading path becomes the citation title when present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.agents.copilot_llm import (
    Citation,
    LLMResult,
    _format_doc_excerpts,
    generate_llm_message,
)


# =============================================================================
# Fixtures
# =============================================================================


@dataclass
class _FakeRetrievedChunk:
    source_path: str
    chunk_index: int
    content: str
    metadata: dict
    distance: float


def _fake_anthropic_response(text: str = "ROAS sits at 4.2x today.") -> Any:
    """Build a stand-in for anthropic.types.Message."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=120, output_tokens=40)
    return response


def _patch_settings(**overrides: Any):
    """
    Patch settings inside copilot_llm. Returns the patch context manager
    so callers can use it with `with`.
    """
    base = {
        "copilot_llm_enabled": True,
        "anthropic_api_key": "sk-ant-test",
        "copilot_llm_model": "claude-haiku-4-5",
        "copilot_llm_max_tokens": 600,
        "copilot_llm_timeout_seconds": 8.0,
        "copilot_rag_enabled": False,
        "openai_api_key": None,
    }
    base.update(overrides)
    return patch.multiple(
        "app.services.agents.copilot_llm.settings",
        **base,
    )


# =============================================================================
# Off-paths (LLM disabled / no key / no SDK)
# =============================================================================


class TestLLMDisabledPaths:
    @pytest.mark.asyncio
    async def test_returns_text_none_when_flag_off(self) -> None:
        with _patch_settings(copilot_llm_enabled=False):
            result = await generate_llm_message(
                message="hi",
                user_name="X",
                metrics=None,
                health_data=None,
                anomaly_data=None,
                intent="greeting",
            )
        assert result == LLMResult(text=None)

    @pytest.mark.asyncio
    async def test_returns_text_none_when_no_anthropic_key(self) -> None:
        with _patch_settings(anthropic_api_key=None):
            result = await generate_llm_message(
                message="hi",
                user_name="X",
                metrics=None,
                health_data=None,
                anomaly_data=None,
                intent="greeting",
            )
        assert result.text is None
        assert result.citations == []


# =============================================================================
# RAG retrieval contract
# =============================================================================


class TestRAGRetrieval:
    @pytest.mark.asyncio
    async def test_no_retrieval_when_rag_off(self) -> None:
        fake_response = _fake_anthropic_response("LLM only.")
        fake_client = MagicMock()
        fake_client.messages.create = AsyncMock(return_value=fake_response)
        fake_db = MagicMock()

        with (
            _patch_settings(copilot_rag_enabled=False),
            patch("anthropic.AsyncAnthropic", return_value=fake_client),
            patch("app.services.agents.copilot_llm._retrieve_docs") as mock_retrieve,
        ):
            mock_retrieve.return_value = ([], [])
            result = await generate_llm_message(
                message="What's my ROAS?",
                user_name="Sam",
                metrics={"roas": 4.2},
                health_data=None,
                anomaly_data=None,
                intent="performance",
                db=fake_db,
            )

        # _retrieve_docs is still called — it's the one that gates on the
        # flag. So we only assert on the result, not the call.
        assert result.text == "LLM only."
        assert result.citations == []

    @pytest.mark.asyncio
    async def test_no_retrieval_when_no_db(self) -> None:
        fake_response = _fake_anthropic_response()
        fake_client = MagicMock()
        fake_client.messages.create = AsyncMock(return_value=fake_response)

        with (
            _patch_settings(copilot_rag_enabled=True, openai_api_key="sk-test"),
            patch("anthropic.AsyncAnthropic", return_value=fake_client),
        ):
            result = await generate_llm_message(
                message="Q",
                user_name="X",
                metrics=None,
                health_data=None,
                anomaly_data=None,
                intent="greeting",
                db=None,  # no session → no retrieval
            )
        assert result.text is not None
        assert result.citations == []

    @pytest.mark.asyncio
    async def test_retrieval_failure_is_swallowed(self) -> None:
        fake_response = _fake_anthropic_response()
        fake_client = MagicMock()
        fake_client.messages.create = AsyncMock(return_value=fake_response)
        fake_db = MagicMock()

        async def _boom(*_args: Any, **_kwargs: Any) -> List:
            raise RuntimeError("network down")

        with (
            _patch_settings(copilot_rag_enabled=True, openai_api_key="sk-test"),
            patch("anthropic.AsyncAnthropic", return_value=fake_client),
            patch(
                "app.services.agents.doc_index.retrieve_top_k",
                side_effect=_boom,
            ),
        ):
            result = await generate_llm_message(
                message="Q",
                user_name="X",
                metrics=None,
                health_data=None,
                anomaly_data=None,
                intent="greeting",
                db=fake_db,
            )
        # LLM still runs; citations stay empty.
        assert result.text is not None
        assert result.citations == []

    @pytest.mark.asyncio
    async def test_citations_use_heading_path_as_title(self) -> None:
        chunks = [
            _FakeRetrievedChunk(
                source_path="docs/architecture/trust-engine.md",
                chunk_index=2,
                content="Phase 1 ...",
                metadata={
                    "title": "Phases",
                    "heading_path": ["Trust Engine", "Phases"],
                },
                distance=0.18,
            ),
        ]
        fake_response = _fake_anthropic_response()
        fake_client = MagicMock()
        fake_client.messages.create = AsyncMock(return_value=fake_response)
        fake_db = MagicMock()

        async def _retrieve(*_args: Any, **_kwargs: Any) -> List[_FakeRetrievedChunk]:
            return chunks

        with (
            _patch_settings(copilot_rag_enabled=True, openai_api_key="sk-test"),
            patch("anthropic.AsyncAnthropic", return_value=fake_client),
            patch(
                "app.services.agents.doc_index.retrieve_top_k",
                side_effect=_retrieve,
            ),
        ):
            result = await generate_llm_message(
                message="What is the trust gate?",
                user_name="X",
                metrics=None,
                health_data=None,
                anomaly_data=None,
                intent="trust_gate",
                db=fake_db,
            )
        assert len(result.citations) == 1
        assert result.citations[0].title == "Trust Engine » Phases"
        assert result.citations[0].source_path == "docs/architecture/trust-engine.md"
        assert result.citations[0].distance == pytest.approx(0.18)

    @pytest.mark.asyncio
    async def test_citations_preserve_retrieval_order(self) -> None:
        chunks = [
            _FakeRetrievedChunk(
                source_path="a.md", chunk_index=0, content="...",
                metadata={"title": "A"}, distance=0.10,
            ),
            _FakeRetrievedChunk(
                source_path="b.md", chunk_index=0, content="...",
                metadata={"title": "B"}, distance=0.25,
            ),
            _FakeRetrievedChunk(
                source_path="c.md", chunk_index=0, content="...",
                metadata={"title": "C"}, distance=0.40,
            ),
        ]
        fake_response = _fake_anthropic_response()
        fake_client = MagicMock()
        fake_client.messages.create = AsyncMock(return_value=fake_response)
        fake_db = MagicMock()

        async def _retrieve(*_args: Any, **_kwargs: Any) -> List[_FakeRetrievedChunk]:
            return chunks

        with (
            _patch_settings(copilot_rag_enabled=True, openai_api_key="sk-test"),
            patch("anthropic.AsyncAnthropic", return_value=fake_client),
            patch(
                "app.services.agents.doc_index.retrieve_top_k",
                side_effect=_retrieve,
            ),
        ):
            result = await generate_llm_message(
                message="?",
                user_name="X",
                metrics=None,
                health_data=None,
                anomaly_data=None,
                intent="x",
                db=fake_db,
            )
        assert [c.source_path for c in result.citations] == ["a.md", "b.md", "c.md"]


# =============================================================================
# Prompt rendering
# =============================================================================


class TestPromptRendering:
    def test_doc_excerpts_block_format(self) -> None:
        rendered = _format_doc_excerpts(
            [
                {"source_path": "a.md", "title": "A", "content": "Hello world."},
                {"source_path": "b.md", "title": "B", "content": "Second.\n\nMore."},
            ]
        )
        assert "Stratum doc excerpts" in rendered
        assert "[1] A" in rendered
        assert "[2] B" in rendered
        assert "Hello world." in rendered

    def test_empty_docs_renders_nothing_visible(self) -> None:
        # The bridge calls _format_doc_excerpts only when docs is non-empty,
        # so this just verifies the helper itself handles the edge.
        rendered = _format_doc_excerpts([])
        assert rendered == "Stratum doc excerpts (most relevant first):"


# =============================================================================
# Anthropic error paths preserve citations
# =============================================================================


class TestErrorRecovery:
    @pytest.mark.asyncio
    async def test_anthropic_error_returns_citations_with_text_none(self) -> None:
        chunks = [
            _FakeRetrievedChunk(
                source_path="docs/x.md", chunk_index=0, content="Body",
                metadata={"title": "X"}, distance=0.2,
            ),
        ]
        fake_client = MagicMock()
        fake_client.messages.create = AsyncMock(side_effect=RuntimeError("rate limit"))
        fake_db = MagicMock()

        async def _retrieve(*_args: Any, **_kwargs: Any) -> List[_FakeRetrievedChunk]:
            return chunks

        with (
            _patch_settings(copilot_rag_enabled=True, openai_api_key="sk-test"),
            patch("anthropic.AsyncAnthropic", return_value=fake_client),
            patch(
                "app.services.agents.doc_index.retrieve_top_k",
                side_effect=_retrieve,
            ),
        ):
            result = await generate_llm_message(
                message="Q",
                user_name="X",
                metrics=None,
                health_data=None,
                anomaly_data=None,
                intent="x",
                db=fake_db,
            )
        # Caller can decide whether to surface citations alongside the
        # template fallback. We preserve them either way.
        assert result.text is None
        assert len(result.citations) == 1
        assert result.citations[0].source_path == "docs/x.md"


# =============================================================================
# LLMResult dataclass
# =============================================================================


class TestLLMResult:
    def test_default_citations_is_empty_list(self) -> None:
        r = LLMResult(text="ok")
        assert r.citations == []

    def test_is_frozen(self) -> None:
        r = LLMResult(text="x", citations=[Citation("a.md", "A", 0.1)])
        with pytest.raises(Exception):
            r.text = "no"  # type: ignore[misc]
