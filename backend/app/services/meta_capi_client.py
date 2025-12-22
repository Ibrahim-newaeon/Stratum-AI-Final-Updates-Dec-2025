# =============================================================================
# Stratum AI - Meta CAPI Client
# =============================================================================
"""
Async HTTP client for Meta Conversion API.
"""

import httpx
from typing import Any


class MetaCapiClient:
    """
    Async client for sending events to Meta Conversion API.
    """

    def __init__(self, access_token: str):
        self.access_token = access_token

    async def send(self, pixel_id: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """
        Send events to Meta CAPI.

        Args:
            pixel_id: Meta Pixel ID
            payload: Event payload with 'data' array and optional 'test_event_code'

        Returns:
            Tuple of (status_code, response_data)
        """
        url = f"https://graph.facebook.com/v20.0/{pixel_id}/events"
        params = {"access_token": self.access_token}

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, params=params, json=payload)
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text}
            return r.status_code, data
