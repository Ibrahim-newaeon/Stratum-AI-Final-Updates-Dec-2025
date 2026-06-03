# =============================================================================
# Stratum AI — doc_index tests (Copilot RAG foundation)
# =============================================================================
"""
Pure-Python tests for the chunker + helpers. The OpenAI and pgvector
integrations are mocked — these tests run without OPENAI_API_KEY and
without a Postgres connection.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services.agents.doc_index import (
    CURATED_GLOBS,
    DocChunk,
    RagDisabledError,
    _heading_path_for_offset,
    _vector_literal,
    _walk_headings,
    chunk_markdown,
    embed_texts,
    find_corpus_files,
)

# =============================================================================
# Chunking
# =============================================================================


class TestChunkMarkdown:
    def test_empty_input_returns_empty_list(self) -> None:
        assert chunk_markdown("docs/x.md", "") == []
        assert chunk_markdown("docs/x.md", "   \n\n   ") == []

    def test_single_short_paragraph_is_one_chunk(self) -> None:
        chunks = chunk_markdown(
            "docs/x.md",
            "# Title\n\nHello world. This is a short paragraph.",
            target_chars=500,
        )
        assert len(chunks) == 1
        assert chunks[0].source_path == "docs/x.md"
        assert chunks[0].chunk_index == 0
        assert "Hello world" in chunks[0].content

    def test_long_doc_splits_at_paragraph_boundaries(self) -> None:
        para = "Lorem ipsum dolor sit amet. " * 30  # ~810 chars
        text = f"# Title\n\n{para}\n\n{para}\n\n{para}"
        chunks = chunk_markdown("docs/x.md", text, target_chars=900)
        # 3 paragraphs of ~810 chars each, target 900 → can't pair them.
        assert len(chunks) >= 3
        # No chunk crosses the target by more than one paragraph.
        for c in chunks:
            assert len(c.content) < 1800

    def test_chunk_index_is_zero_based_and_sequential(self) -> None:
        text = "\n\n".join(f"Paragraph number {i}." for i in range(20))
        chunks = chunk_markdown("docs/x.md", text, target_chars=80)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_metadata_records_heading_path(self) -> None:
        text = (
            "# Top Level\n\n"
            "Intro paragraph.\n\n"
            "## Subsection A\n\n"
            "Subsection paragraph.\n\n"
            "## Subsection B\n\n"
            "Another paragraph here that is intentionally longer to land in its own chunk because target is small.\n"
        )
        chunks = chunk_markdown("docs/x.md", text, target_chars=80)
        # Find the chunk that starts inside Subsection B.
        b_chunks = [c for c in chunks if "Another paragraph here" in c.content]
        assert b_chunks, "expected to find a chunk for Subsection B"
        assert b_chunks[0].metadata["title"] == "Subsection B"
        assert b_chunks[0].metadata["heading_path"][-1] == "Subsection B"

    def test_code_fences_are_not_split(self) -> None:
        text = (
            "# Title\n\n"
            "Some intro.\n\n"
            "```python\n"
            "def hello():\n"
            "    print('a' * 200)\n"
            "    print('b' * 200)\n"
            "    print('c' * 200)\n"
            "```\n\n"
            "Some outro.\n"
        )
        chunks = chunk_markdown("docs/x.md", text, target_chars=200)
        # The code fence is a single paragraph; whichever chunk it lands in
        # contains the whole fence intact.
        fence_chunks = [c for c in chunks if "```python" in c.content]
        assert len(fence_chunks) == 1
        assert "```python" in fence_chunks[0].content
        assert (
            "```"
            in fence_chunks[0].content[
                fence_chunks[0].content.rindex("```python") + 1 :
            ]
        )

    def test_chunk_content_is_stripped(self) -> None:
        chunks = chunk_markdown(
            "docs/x.md", "\n\n  Hello.  \n\n  World.  \n\n", target_chars=500
        )
        assert len(chunks) == 1
        assert chunks[0].content.strip() == chunks[0].content

    def test_target_chars_packs_multiple_paragraphs(self) -> None:
        # Each paragraph is 40 chars + 2 chars for the "\n\n" join.
        # Target 100 → two paragraphs (40+2+40=82) fit; a third (122) does not.
        # Expect ~5 chunks for 10 paragraphs.
        text = "\n\n".join(["x" * 40] * 10)
        chunks = chunk_markdown("docs/x.md", text, target_chars=100)
        assert 4 <= len(chunks) <= 6  # tolerance for boundary handling


# =============================================================================
# Heading walker
# =============================================================================


class TestWalkHeadings:
    def test_picks_up_all_levels(self) -> None:
        text = "# A\n\n## B\n\n### C\n\nbody\n"
        headings = _walk_headings(text)
        levels = [h["level"] for h in headings]
        titles = [h["title"] for h in headings]
        assert levels == [1, 2, 3]
        assert titles == ["A", "B", "C"]

    def test_offset_path_pops_siblings(self) -> None:
        text = "# A\n\n## B\n\n## C\n\nbody"
        headings = _walk_headings(text)
        offset = text.index("body")
        path = _heading_path_for_offset(headings, offset)
        # B is a sibling of C; only the most recent ## stays.
        assert path == ["A", "C"]

    def test_offset_before_first_heading_is_empty(self) -> None:
        text = "preface\n\n# A"
        headings = _walk_headings(text)
        assert _heading_path_for_offset(headings, 0) == []


# =============================================================================
# Vector literal
# =============================================================================


class TestVectorLiteral:
    def test_round_trip_format(self) -> None:
        out = _vector_literal([0.1, 0.2, 0.3])
        assert out.startswith("[") and out.endswith("]")
        # 6 decimal places per element, comma separated, no spaces.
        assert out == "[0.100000,0.200000,0.300000]"

    def test_handles_negative_and_large_values(self) -> None:
        out = _vector_literal([-1.234567, 1000.5])
        assert out == "[-1.234567,1000.500000]"

    def test_empty_vector(self) -> None:
        assert _vector_literal([]) == "[]"


# =============================================================================
# Embedding gate
# =============================================================================


class TestEmbedTexts:
    @pytest.mark.asyncio
    async def test_raises_when_api_key_missing(self) -> None:
        with patch("app.services.agents.doc_index.settings") as mock_settings:
            mock_settings.openai_api_key = None
            with pytest.raises(RagDisabledError):
                await embed_texts(["hello"])

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_empty_input(self) -> None:
        with patch("app.services.agents.doc_index.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"
            assert await embed_texts([]) == []

    @pytest.mark.asyncio
    async def test_calls_openai_with_configured_model(self) -> None:
        fake_response = type(
            "X", (), {"data": [type("R", (), {"embedding": [0.1] * 1536})()]}
        )()
        fake_client = type(
            "C",
            (),
            {
                "embeddings": type(
                    "E",
                    (),
                    {"create": AsyncMock(return_value=fake_response)},
                )()
            },
        )()
        with (
            patch("app.services.agents.doc_index.settings") as mock_settings,
            patch("openai.AsyncOpenAI", return_value=fake_client) as mock_factory,
        ):
            mock_settings.openai_api_key = "sk-test"
            mock_settings.copilot_rag_embedding_model = "text-embedding-3-small"
            result = await embed_texts(["hello"])
            assert mock_factory.called
            assert len(result) == 1
            assert len(result[0]) == 1536


# =============================================================================
# Corpus discovery
# =============================================================================


class TestFindCorpusFiles:
    def test_returns_only_existing_md_files(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "00-overview").mkdir()
        (tmp_path / "docs" / "00-overview" / "vision.md").write_text("# Vision")
        (tmp_path / "docs" / "00-overview" / "ignore.txt").write_text("nope")
        (tmp_path / "docs" / "04-features").mkdir()
        (tmp_path / "docs" / "04-features" / "cdp.md").write_text("# CDP")

        files = find_corpus_files(tmp_path)
        rel = sorted(str(f.relative_to(tmp_path)) for f in files)
        assert "docs/00-overview/vision.md" in rel
        assert "docs/04-features/cdp.md" in rel
        assert all(".md" in f for f in rel)

    def test_curated_globs_are_documented(self) -> None:
        # Sanity: the constant the indexer falls back to is non-empty
        # and points at locations that exist in this repo (smoke).
        assert len(CURATED_GLOBS) >= 5
        # Globs all start with docs/ so they're confined to the corpus.
        assert all(g.startswith("docs/") for g in CURATED_GLOBS)


# =============================================================================
# DocChunk dataclass
# =============================================================================


class TestDocChunk:
    def test_default_metadata_is_dict(self) -> None:
        c = DocChunk(source_path="x.md", chunk_index=0, content="hi")
        assert c.metadata == {}

    def test_is_frozen(self) -> None:
        c = DocChunk(source_path="x.md", chunk_index=0, content="hi")
        with pytest.raises(Exception):
            c.content = "no"  # type: ignore[misc]
