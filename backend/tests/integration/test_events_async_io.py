# =============================================================================
# Stratum AI - Events senders: async I/O contract
# =============================================================================
"""Proves the event senders never block the event loop.

A synchronous HTTP client inside ``async def`` holds the loop for the whole
request. These senders sit on the CAPI path — the highest-volume operation in
the product — so one slow platform endpoint would stall every other tenant's
request on the same worker.

Asserting the returned dict is not enough to catch that: a blocking client
returns the right value too. These tests assert the call is *awaited*, and that
two concurrent sends genuinely overlap.
"""

import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.stratum.events import MetaEventsSender, ServerEvent, StandardEvent

pytestmark = [pytest.mark.integration]

MODULE = "app.stratum.events"


@contextmanager
def patch_httpx(module: str, verb: str, handler: AsyncMock):
    """Patch httpx.AsyncClient so ``async with ... as c`` yields a mock.

    MagicMock supplies the async context-manager protocol, so ``__aenter__`` is
    already an AsyncMock. ``__aexit__`` is pinned to False explicitly — a truthy
    value would swallow the transport errors the failure-path tests rely on.
    """
    with patch(f"{module}.httpx.AsyncClient") as mock_cls:
        setattr(mock_cls.return_value.__aenter__.return_value, verb, handler)
        mock_cls.return_value.__aexit__.return_value = False
        yield mock_cls


def http_response(status_code: int = 200, payload: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload if payload is not None else {}
    r.raise_for_status.return_value = None
    return r


def an_event() -> ServerEvent:
    return ServerEvent(event_name=StandardEvent.VIEW_CONTENT)


class TestMetaEventsSenderIsAsync:
    async def test_send_awaits_an_httpx_call(self):
        post = AsyncMock(return_value=http_response(200, {"events_received": 1}))
        sender = MetaEventsSender("px-1", "tok-1")

        with patch_httpx(MODULE, "post", post):
            result = await sender.send([an_event()])

        assert post.await_count == 1
        assert result == {"events_received": 1}

    async def test_send_does_not_block_the_event_loop(self):
        """Two concurrent sends must overlap.

        Each stubbed call parks until both have started. Sequential execution
        can never satisfy that, so a blocking client fails here by timeout
        rather than by assertion — which is the point: this is a structural
        check, not a timing threshold that goes flaky on a loaded runner.
        """
        started = 0
        both_started = asyncio.Event()

        async def handler(*args, **kwargs):
            nonlocal started
            started += 1
            if started == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=5)
            return http_response(200, {"events_received": 1})

        sender = MetaEventsSender("px-1", "tok-1")
        with patch_httpx(MODULE, "post", AsyncMock(side_effect=handler)):
            await asyncio.gather(
                sender.send([an_event()]),
                sender.send([an_event()]),
            )

        assert started == 2

    async def test_transport_failure_raises_an_httpx_error(self):
        post = AsyncMock(side_effect=httpx.ConnectError("dns fail"))
        sender = MetaEventsSender("px-1", "tok-1")

        with patch_httpx(MODULE, "post", post):
            with pytest.raises(httpx.HTTPError):
                await sender.send([an_event()])

    async def test_get_emq_scores_awaits_an_httpx_call(self):
        get = AsyncMock(return_value=http_response(200, {"data": []}))
        sender = MetaEventsSender("px-1", "tok-1")

        with patch_httpx(MODULE, "get", get):
            result = await sender.get_emq_scores()

        assert get.await_count == 1
        assert result == {"data": []}
