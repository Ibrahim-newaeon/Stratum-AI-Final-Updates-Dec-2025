# =============================================================================
# Stratum AI - Snapchat Audience Match Connector
# =============================================================================
"""
Snapchat Marketing API Audience Match Connector.

Implements the Snapchat Marketing API for SAM (Snapchat Audience Match) operations:
- Create SAM Lookalike audiences
- Upload customer segments
- Support for email, phone, and mobile advertiser IDs

API Reference: https://marketingapi.snapchat.com/docs/#snap-audience-match
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    BaseAudienceConnector,
    AudienceConfig,
    AudienceUser,
    AudienceSyncResult,
    IdentifierType,
)


class SnapchatAudienceConnector(BaseAudienceConnector):
    """
    Snapchat Audience Match (SAM) connector.

    Uses Snapchat Marketing API to manage custom audiences.
    Supports customer file uploads with hashed identifiers.
    """

    PLATFORM_NAME = "snapchat"
    BATCH_SIZE = 100000  # Snapchat supports large batches
    API_VERSION = "v1"
    BASE_URL = "https://adsapi.snapchat.com"

    def __init__(
        self,
        access_token: str,
        ad_account_id: str,  # Snapchat Ad Account ID
        organization_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(access_token, ad_account_id, **kwargs)
        self.organization_id = organization_id

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Snapchat API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def create_audience(
        self,
        config: AudienceConfig,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Create a new Snapchat Audience Match segment with initial users.
        """
        start_time = time.time()

        try:
            # Step 1: Create the SAM segment
            create_url = f"{self.BASE_URL}/{self.API_VERSION}/adaccounts/{self.ad_account_id}/segments"

            # Determine source type based on identifiers available
            source_type = "FIRST_PARTY"  # Customer list

            create_payload = {
                "segments": [{
                    "name": config.name,
                    "description": config.description or f"CDP Segment: {config.name}",
                    "source_type": source_type,
                    "ad_account_id": self.ad_account_id,
                    "retention_in_days": config.retention_days or 180,
                }]
            }

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    create_url,
                    json=create_payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                create_result = response.json()

            segments = create_result.get("segments", [])
            if not segments:
                return AudienceSyncResult(
                    success=False,
                    operation="create",
                    error_message="No segment returned from Snapchat",
                    platform_response=create_result,
                )

            segment = segments[0].get("segment", {})
            audience_id = segment.get("id")

            if not audience_id:
                return AudienceSyncResult(
                    success=False,
                    operation="create",
                    error_message="No segment ID in response",
                    platform_response=create_result,
                )

            self.logger.info(
                "snapchat_audience_created",
                audience_id=audience_id,
                name=config.name,
            )

            # Step 2: Upload users if provided
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
                "snapchat_audience_create_failed",
                error=str(e),
                response=error_body,
            )
            return AudienceSyncResult(
                success=False,
                operation="create",
                error_message=str(error_body.get("error_message", str(e))),
                error_details=error_body,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            self.logger.error("snapchat_audience_create_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="create",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def add_users(
        self,
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Add users to a Snapchat SAM segment.
        """
        start_time = time.time()
        total_sent = 0
        total_added = 0
        total_failed = 0

        try:
            # Prepare user data - Snapchat uses schema-based uploads
            user_data = self._prepare_snapchat_user_data(users)

            if not user_data:
                return AudienceSyncResult(
                    success=True,
                    operation="add",
                    platform_audience_id=audience_id,
                    users_sent=0,
                    users_added=0,
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Upload in batches
            batches = self._chunk_list(user_data, self.BATCH_SIZE)

            async with httpx.AsyncClient(timeout=300) as client:
                for batch in batches:
                    upload_url = f"{self.BASE_URL}/{self.API_VERSION}/segments/{audience_id}/users"

                    # Build the upload payload
                    upload_payload = {
                        "users": [{
                            "schema": ["EMAIL_SHA256", "PHONE_SHA256", "MOBILE_AD_ID_SHA256"],
                            "data": batch,
                        }]
                    }

                    response = await client.post(
                        upload_url,
                        json=upload_payload,
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()
                    result = response.json()

                    # Parse response
                    users_result = result.get("users", [{}])[0]
                    num_uploaded = users_result.get("number_uploaded_users", len(batch))

                    total_sent += len(batch)
                    total_added += num_uploaded

                    self.logger.info(
                        "snapchat_batch_uploaded",
                        audience_id=audience_id,
                        batch_size=len(batch),
                        uploaded=num_uploaded,
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
                audience_size=audience_info.get("approximate_number_users"),
                duration_ms=duration_ms,
            )

        except httpx.HTTPStatusError as e:
            error_body = e.response.json() if e.response.content else {}
            self.logger.error(
                "snapchat_audience_add_failed",
                audience_id=audience_id,
                error=str(e),
            )
            return AudienceSyncResult(
                success=False,
                operation="add",
                platform_audience_id=audience_id,
                users_sent=total_sent,
                users_added=total_added,
                error_message=str(error_body.get("error_message", str(e))),
                error_details=error_body,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            self.logger.error("snapchat_audience_add_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="add",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def remove_users(
        self,
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Remove users from a Snapchat SAM segment.
        """
        start_time = time.time()
        total_sent = 0
        total_removed = 0

        try:
            user_data = self._prepare_snapchat_user_data(users)

            if not user_data:
                return AudienceSyncResult(
                    success=True,
                    operation="remove",
                    platform_audience_id=audience_id,
                    users_sent=0,
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            async with httpx.AsyncClient(timeout=300) as client:
                delete_url = f"{self.BASE_URL}/{self.API_VERSION}/segments/{audience_id}/users"

                delete_payload = {
                    "users": [{
                        "schema": ["EMAIL_SHA256", "PHONE_SHA256", "MOBILE_AD_ID_SHA256"],
                        "data": user_data,
                    }]
                }

                response = await client.request(
                    "DELETE",
                    delete_url,
                    json=delete_payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                result = response.json()

                users_result = result.get("users", [{}])[0]
                total_removed = users_result.get("number_uploaded_users", len(user_data))
                total_sent = len(user_data)

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
            self.logger.error("snapchat_audience_remove_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="remove",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def replace_audience(
        self,
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Replace entire Snapchat audience.
        Snapchat doesn't have native replace, so we add with a new upload.
        """
        start_time = time.time()

        try:
            # For Snapchat, we just do a fresh add (overwrites previous data)
            result = await self.add_users(audience_id, users)
            result.operation = "replace"
            return result

        except Exception as e:
            self.logger.error("snapchat_audience_replace_error", error=str(e))
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
        Delete a Snapchat SAM segment.
        """
        start_time = time.time()

        try:
            url = f"{self.BASE_URL}/{self.API_VERSION}/segments/{audience_id}"

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.delete(
                    url,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                result = response.json()

            duration_ms = int((time.time() - start_time) * 1000)

            return AudienceSyncResult(
                success=True,
                operation="delete",
                platform_audience_id=audience_id,
                duration_ms=duration_ms,
                platform_response=result,
            )

        except Exception as e:
            self.logger.error("snapchat_audience_delete_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="delete",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def get_audience_info(
        self,
        audience_id: str,
    ) -> Dict[str, Any]:
        """
        Get Snapchat SAM segment information.
        """
        try:
            url = f"{self.BASE_URL}/{self.API_VERSION}/segments/{audience_id}"

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                result = response.json()

            segments = result.get("segments", [])
            if segments:
                segment = segments[0].get("segment", {})
                return {
                    "id": segment.get("id"),
                    "name": segment.get("name"),
                    "description": segment.get("description"),
                    "status": segment.get("status"),
                    "source_type": segment.get("source_type"),
                    "approximate_number_users": segment.get("approximate_number_users"),
                    "targetable_status": segment.get("targetable_status"),
                    "upload_status": segment.get("upload_status"),
                    "retention_in_days": segment.get("retention_in_days"),
                }

            return {}

        except Exception as e:
            self.logger.error("snapchat_audience_info_error", error=str(e))
            return {"error": str(e)}

    # =========================================================================
    # Snapchat-specific helpers
    # =========================================================================

    def _prepare_snapchat_user_data(self, users: List[AudienceUser]) -> List[List[str]]:
        """
        Prepare user data in Snapchat's format.
        Returns list of [email_hash, phone_hash, mobile_id_hash] arrays.
        """
        data_rows = []

        for user in users:
            email_hash = ""
            phone_hash = ""
            mobile_id_hash = ""

            for identifier in user.identifiers:
                hashed = identifier.get_hashed()
                if not hashed:
                    continue

                if identifier.identifier_type == IdentifierType.EMAIL:
                    email_hash = hashed
                elif identifier.identifier_type == IdentifierType.PHONE:
                    phone_hash = hashed
                elif identifier.identifier_type == IdentifierType.MOBILE_ADVERTISER_ID:
                    mobile_id_hash = hashed

            # Only add if at least one identifier exists
            if email_hash or phone_hash or mobile_id_hash:
                data_rows.append([email_hash, phone_hash, mobile_id_hash])

        return data_rows
