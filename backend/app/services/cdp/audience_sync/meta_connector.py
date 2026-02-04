# =============================================================================
# Stratum AI - Meta Custom Audience Connector
# =============================================================================
"""
Meta (Facebook/Instagram) Custom Audience API Connector.

Implements the Meta Marketing API for Custom Audience operations:
- Create customer list custom audiences
- Add/remove users via hashed identifiers
- Support for email, phone, and mobile advertiser IDs

API Reference: https://developers.facebook.com/docs/marketing-api/audiences/guides/custom-audiences
"""

import time
from typing import Any, Optional

import httpx

from .base import (
    AudienceConfig,
    AudienceSyncResult,
    AudienceUser,
    BaseAudienceConnector,
    IdentifierType,
)


class MetaAudienceConnector(BaseAudienceConnector):
    """
    Meta Custom Audience connector for Facebook/Instagram.

    Uses Meta's Marketing API to manage custom audiences.
    Supports customer file custom audiences with hashed identifiers.
    """

    PLATFORM_NAME = "meta"
    BATCH_SIZE = 10000  # Meta recommends batches of 10,000
    API_VERSION = "v18.0"
    BASE_URL = "https://graph.facebook.com"

    def __init__(
        self, access_token: str, ad_account_id: str, app_secret: Optional[str] = None, **kwargs
    ):
        super().__init__(access_token, ad_account_id, **kwargs)
        self.app_secret = app_secret
        # Meta ad account IDs should be prefixed with "act_"
        if not self.ad_account_id.startswith("act_"):
            self.ad_account_id = f"act_{self.ad_account_id}"

    async def create_audience(
        self,
        config: AudienceConfig,
        users: list[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Create a new Meta Custom Audience with initial users.
        """
        start_time = time.time()

        try:
            # Step 1: Create the custom audience
            create_url = f"{self.BASE_URL}/{self.API_VERSION}/{self.ad_account_id}/customaudiences"

            create_payload = {
                "name": config.name,
                "subtype": "CUSTOM",
                "description": config.description or f"CDP Segment: {config.name}",
                "customer_file_source": config.customer_file_source or "USER_PROVIDED_ONLY",
                "access_token": self.access_token,
            }

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(create_url, data=create_payload)
                response.raise_for_status()
                create_result = response.json()

            audience_id = create_result.get("id")
            if not audience_id:
                return AudienceSyncResult(
                    success=False,
                    operation="create",
                    error_message="No audience ID returned from Meta",
                    platform_response=create_result,
                )

            self.logger.info(
                "meta_audience_created",
                audience_id=audience_id,
                name=config.name,
            )

            # Step 2: Add users to the audience
            if users:
                add_result = await self.add_users(audience_id, users)
                add_result.operation = "create"
                add_result.platform_audience_id = audience_id
                add_result.platform_audience_name = config.name
                return add_result

            duration_ms = int((time.time() - start_time) * 1000)

            return AudienceSyncResult(
                success=True,
                operation="create",
                platform_audience_id=audience_id,
                platform_audience_name=config.name,
                users_sent=0,
                duration_ms=duration_ms,
                platform_response=create_result,
            )

        except httpx.HTTPStatusError as e:
            error_body = e.response.json() if e.response.content else {}
            self.logger.error(
                "meta_audience_create_failed",
                error=str(e),
                response=error_body,
            )
            return AudienceSyncResult(
                success=False,
                operation="create",
                error_message=error_body.get("error", {}).get("message", str(e)),
                error_code=str(error_body.get("error", {}).get("code", "")),
                error_details=error_body,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            self.logger.error("meta_audience_create_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="create",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def add_users(
        self,
        audience_id: str,
        users: list[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Add users to a Meta Custom Audience.
        """
        start_time = time.time()
        total_sent = 0
        total_added = 0
        total_failed = 0

        try:
            # Prepare user data in Meta's format
            schema = ["EMAIL", "PHONE", "MADID"]
            data_rows = self._prepare_meta_user_data(users)

            # Upload in batches
            batches = self._chunk_list(data_rows, self.BATCH_SIZE)

            async with httpx.AsyncClient(timeout=120) as client:
                for batch in batches:
                    payload = {
                        "payload": {
                            "schema": schema,
                            "data": batch,
                        },
                        "access_token": self.access_token,
                    }

                    url = f"{self.BASE_URL}/{self.API_VERSION}/{audience_id}/users"
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    result = response.json()

                    # Parse response
                    num_received = result.get("num_received", len(batch))
                    num_invalid = result.get("num_invalid_entries", 0)

                    total_sent += num_received
                    total_added += num_received - num_invalid
                    total_failed += num_invalid

                    self.logger.info(
                        "meta_audience_batch_uploaded",
                        audience_id=audience_id,
                        batch_size=len(batch),
                        received=num_received,
                        invalid=num_invalid,
                    )

            duration_ms = int((time.time() - start_time) * 1000)

            # Get updated audience info
            audience_info = await self.get_audience_info(audience_id)

            return AudienceSyncResult(
                success=True,
                operation="add",
                platform_audience_id=audience_id,
                users_sent=total_sent,
                users_added=total_added,
                users_failed=total_failed,
                audience_size=audience_info.get("approximate_count"),
                duration_ms=duration_ms,
            )

        except httpx.HTTPStatusError as e:
            error_body = e.response.json() if e.response.content else {}
            self.logger.error(
                "meta_audience_add_failed",
                audience_id=audience_id,
                error=str(e),
            )
            return AudienceSyncResult(
                success=False,
                operation="add",
                platform_audience_id=audience_id,
                users_sent=total_sent,
                users_added=total_added,
                users_failed=total_failed,
                error_message=error_body.get("error", {}).get("message", str(e)),
                error_details=error_body,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            self.logger.error("meta_audience_add_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="add",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def remove_users(
        self,
        audience_id: str,
        users: list[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Remove users from a Meta Custom Audience.
        """
        start_time = time.time()
        total_sent = 0
        total_removed = 0

        try:
            schema = ["EMAIL", "PHONE", "MADID"]
            data_rows = self._prepare_meta_user_data(users)

            batches = self._chunk_list(data_rows, self.BATCH_SIZE)

            async with httpx.AsyncClient(timeout=120) as client:
                for batch in batches:
                    payload = {
                        "payload": {
                            "schema": schema,
                            "data": batch,
                        },
                        "access_token": self.access_token,
                    }

                    url = f"{self.BASE_URL}/{self.API_VERSION}/{audience_id}/users"
                    response = await client.request("DELETE", url, json=payload)
                    response.raise_for_status()
                    result = response.json()

                    num_received = result.get("num_received", len(batch))
                    total_sent += num_received
                    total_removed += num_received

            duration_ms = int((time.time() - start_time) * 1000)

            return AudienceSyncResult(
                success=True,
                operation="remove",
                platform_audience_id=audience_id,
                users_sent=total_sent,
                users_removed=total_removed,
                duration_ms=duration_ms,
            )

        except Exception as e:
            self.logger.error("meta_audience_remove_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="remove",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def replace_audience(
        self,
        audience_id: str,
        users: list[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Replace entire audience by using session-based replace.
        Meta recommends using sessions for full audience replacement.
        """
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                # Step 1: Create a replace session
                session_url = f"{self.BASE_URL}/{self.API_VERSION}/{audience_id}/usersreplace"
                session_payload = {
                    "access_token": self.access_token,
                }
                response = await client.post(session_url, data=session_payload)
                response.raise_for_status()
                session_result = response.json()
                session_id = session_result.get("session_id")

                if not session_id:
                    # Fallback: Delete all and re-add
                    self.logger.warning("meta_replace_session_failed_fallback")
                    return await self.add_users(audience_id, users)

                # Step 2: Upload all users with session
                schema = ["EMAIL", "PHONE", "MADID"]
                data_rows = self._prepare_meta_user_data(users)
                batches = self._chunk_list(data_rows, self.BATCH_SIZE)

                total_sent = 0
                for batch in batches:
                    payload = {
                        "payload": {
                            "schema": schema,
                            "data": batch,
                        },
                        "session": {
                            "session_id": session_id,
                            "batch_seq": batches.index(batch) + 1,
                            "last_batch_flag": batch == batches[-1],
                        },
                        "access_token": self.access_token,
                    }

                    url = f"{self.BASE_URL}/{self.API_VERSION}/{audience_id}/users"
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    total_sent += len(batch)

            duration_ms = int((time.time() - start_time) * 1000)

            return AudienceSyncResult(
                success=True,
                operation="replace",
                platform_audience_id=audience_id,
                users_sent=total_sent,
                users_added=total_sent,
                duration_ms=duration_ms,
            )

        except Exception as e:
            self.logger.error("meta_audience_replace_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="replace",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def delete_audience(
        self,
        audience_id: str,
    ) -> AudienceSyncResult:
        """
        Delete a Meta Custom Audience.
        """
        start_time = time.time()

        try:
            url = f"{self.BASE_URL}/{self.API_VERSION}/{audience_id}"
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.delete(url, params={"access_token": self.access_token})
                response.raise_for_status()
                result = response.json()

            duration_ms = int((time.time() - start_time) * 1000)

            return AudienceSyncResult(
                success=result.get("success", True),
                operation="delete",
                platform_audience_id=audience_id,
                duration_ms=duration_ms,
                platform_response=result,
            )

        except Exception as e:
            self.logger.error("meta_audience_delete_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="delete",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def get_audience_info(
        self,
        audience_id: str,
    ) -> dict[str, Any]:
        """
        Get Meta Custom Audience information.
        """
        try:
            url = f"{self.BASE_URL}/{self.API_VERSION}/{audience_id}"
            fields = "id,name,approximate_count,delivery_status,operation_status,time_created,time_updated"

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    url,
                    params={
                        "access_token": self.access_token,
                        "fields": fields,
                    },
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            self.logger.error("meta_audience_info_error", error=str(e))
            return {"error": str(e)}

    # =========================================================================
    # Meta-specific helpers
    # =========================================================================

    def _prepare_meta_user_data(self, users: list[AudienceUser]) -> list[list[str]]:
        """
        Prepare user data in Meta's multi-key format.
        Returns list of [email_hash, phone_hash, madid_hash] arrays.
        """
        data_rows = []

        for user in users:
            email_hash = ""
            phone_hash = ""
            madid_hash = ""

            for identifier in user.identifiers:
                hashed = identifier.get_hashed()
                if not hashed:
                    continue

                if identifier.identifier_type == IdentifierType.EMAIL:
                    email_hash = hashed
                elif identifier.identifier_type == IdentifierType.PHONE:
                    phone_hash = hashed
                elif identifier.identifier_type == IdentifierType.MOBILE_ADVERTISER_ID:
                    madid_hash = hashed

            # Only add if at least one identifier exists
            if email_hash or phone_hash or madid_hash:
                data_rows.append([email_hash, phone_hash, madid_hash])

        return data_rows
