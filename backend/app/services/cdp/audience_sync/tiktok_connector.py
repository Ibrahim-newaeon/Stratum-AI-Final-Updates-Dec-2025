# =============================================================================
# Stratum AI - TikTok Custom Audience Connector
# =============================================================================
"""
TikTok Marketing API Custom Audience Connector.

Implements the TikTok Marketing API for Custom Audience operations:
- Create DMP audiences (Data Management Platform)
- Upload customer file audiences
- Support for email, phone, and advertising IDs

API Reference: https://business-api.tiktok.com/portal/docs?id=1739940504185857
"""

import time
import json
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


class TikTokAudienceConnector(BaseAudienceConnector):
    """
    TikTok Custom Audience connector.

    Uses TikTok Marketing API to manage custom audiences.
    Supports customer file uploads with hashed identifiers.
    """

    PLATFORM_NAME = "tiktok"
    BATCH_SIZE = 50000  # TikTok supports up to 50k per batch
    API_VERSION = "v1.3"
    BASE_URL = "https://business-api.tiktok.com/open_api"

    def __init__(
        self,
        access_token: str,
        ad_account_id: str,  # TikTok Advertiser ID
        **kwargs
    ):
        super().__init__(access_token, ad_account_id, **kwargs)
        self.advertiser_id = self.ad_account_id

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for TikTok API requests."""
        return {
            "Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    async def create_audience(
        self,
        config: AudienceConfig,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Create a new TikTok Custom Audience with initial users.
        """
        start_time = time.time()

        try:
            # Step 1: Create the custom audience
            create_url = f"{self.BASE_URL}/{self.API_VERSION}/dmp/custom_audience/create/"

            create_payload = {
                "advertiser_id": self.advertiser_id,
                "custom_audience_name": config.name,
                "calculate_type": "MULTIPLE_TYPES",  # Support multiple identifier types
                "file_paths": [],  # Will be populated after upload
            }

            # TikTok requires creating audience first, then uploading
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    create_url,
                    json=create_payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                create_result = response.json()

            if create_result.get("code") != 0:
                return AudienceSyncResult(
                    success=False,
                    operation="create",
                    error_message=create_result.get("message", "Unknown error"),
                    error_code=str(create_result.get("code")),
                    platform_response=create_result,
                )

            audience_id = create_result.get("data", {}).get("custom_audience_id")
            if not audience_id:
                return AudienceSyncResult(
                    success=False,
                    operation="create",
                    error_message="No audience ID returned",
                    platform_response=create_result,
                )

            self.logger.info(
                "tiktok_audience_created",
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
                "tiktok_audience_create_failed",
                error=str(e),
                response=error_body,
            )
            return AudienceSyncResult(
                success=False,
                operation="create",
                error_message=str(error_body.get("message", str(e))),
                error_details=error_body,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            self.logger.error("tiktok_audience_create_error", error=str(e))
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
        Add users to a TikTok Custom Audience.
        """
        start_time = time.time()
        total_sent = 0
        total_added = 0
        total_failed = 0

        try:
            # Prepare user data by identifier type
            email_hashes = []
            phone_hashes = []
            device_ids = []

            for user in users:
                for identifier in user.identifiers:
                    hashed = identifier.get_hashed()
                    if not hashed:
                        continue

                    if identifier.identifier_type == IdentifierType.EMAIL:
                        email_hashes.append(hashed)
                    elif identifier.identifier_type == IdentifierType.PHONE:
                        phone_hashes.append(hashed)
                    elif identifier.identifier_type == IdentifierType.MOBILE_ADVERTISER_ID:
                        device_ids.append(hashed)

            # Upload each identifier type
            async with httpx.AsyncClient(timeout=300) as client:
                uploads = []

                if email_hashes:
                    uploads.append(("EMAIL_SHA256", email_hashes))
                if phone_hashes:
                    uploads.append(("PHONE_SHA256", phone_hashes))
                if device_ids:
                    uploads.append(("IDFA_SHA256", device_ids))  # Also works for GAID

                for id_type, hashes in uploads:
                    # Upload in batches
                    batches = self._chunk_list(hashes, self.BATCH_SIZE)

                    for batch in batches:
                        upload_url = f"{self.BASE_URL}/{self.API_VERSION}/dmp/custom_audience/update/"

                        upload_payload = {
                            "advertiser_id": self.advertiser_id,
                            "custom_audience_id": audience_id,
                            "action": "APPEND",
                            "id_type": id_type,
                            "id_list": batch,
                        }

                        response = await client.post(
                            upload_url,
                            json=upload_payload,
                            headers=self._get_headers(),
                        )
                        response.raise_for_status()
                        result = response.json()

                        if result.get("code") == 0:
                            total_sent += len(batch)
                            total_added += len(batch)
                        else:
                            total_failed += len(batch)
                            self.logger.warning(
                                "tiktok_batch_upload_error",
                                code=result.get("code"),
                                message=result.get("message"),
                            )

            duration_ms = int((time.time() - start_time) * 1000)

            self.logger.info(
                "tiktok_audience_users_added",
                audience_id=audience_id,
                total_sent=total_sent,
                total_added=total_added,
            )

            return AudienceSyncResult(
                success=total_failed == 0,
                operation="add",
                platform_audience_id=audience_id,
                users_sent=total_sent,
                users_added=total_added,
                users_failed=total_failed,
                duration_ms=duration_ms,
            )

        except Exception as e:
            self.logger.error("tiktok_audience_add_error", error=str(e))
            return AudienceSyncResult(
                success=False,
                operation="add",
                platform_audience_id=audience_id,
                users_sent=total_sent,
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def remove_users(
        self,
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Remove users from a TikTok Custom Audience.
        """
        start_time = time.time()
        total_sent = 0
        total_removed = 0

        try:
            # Prepare user data by identifier type
            email_hashes = []
            phone_hashes = []
            device_ids = []

            for user in users:
                for identifier in user.identifiers:
                    hashed = identifier.get_hashed()
                    if not hashed:
                        continue

                    if identifier.identifier_type == IdentifierType.EMAIL:
                        email_hashes.append(hashed)
                    elif identifier.identifier_type == IdentifierType.PHONE:
                        phone_hashes.append(hashed)
                    elif identifier.identifier_type == IdentifierType.MOBILE_ADVERTISER_ID:
                        device_ids.append(hashed)

            async with httpx.AsyncClient(timeout=300) as client:
                uploads = []

                if email_hashes:
                    uploads.append(("EMAIL_SHA256", email_hashes))
                if phone_hashes:
                    uploads.append(("PHONE_SHA256", phone_hashes))
                if device_ids:
                    uploads.append(("IDFA_SHA256", device_ids))

                for id_type, hashes in uploads:
                    upload_url = f"{self.BASE_URL}/{self.API_VERSION}/dmp/custom_audience/update/"

                    upload_payload = {
                        "advertiser_id": self.advertiser_id,
                        "custom_audience_id": audience_id,
                        "action": "DELETE",
                        "id_type": id_type,
                        "id_list": hashes,
                    }

                    response = await client.post(
                        upload_url,
                        json=upload_payload,
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()
                    result = response.json()

                    if result.get("code") == 0:
                        total_sent += len(hashes)
                        total_removed += len(hashes)

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
            self.logger.error("tiktok_audience_remove_error", error=str(e))
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
        Replace entire TikTok audience using OVERRIDE action.
        """
        start_time = time.time()
        total_sent = 0

        try:
            # Prepare user data by identifier type
            email_hashes = []
            phone_hashes = []

            for user in users:
                for identifier in user.identifiers:
                    hashed = identifier.get_hashed()
                    if not hashed:
                        continue

                    if identifier.identifier_type == IdentifierType.EMAIL:
                        email_hashes.append(hashed)
                    elif identifier.identifier_type == IdentifierType.PHONE:
                        phone_hashes.append(hashed)

            async with httpx.AsyncClient(timeout=300) as client:
                uploads = []

                if email_hashes:
                    uploads.append(("EMAIL_SHA256", email_hashes))
                if phone_hashes:
                    uploads.append(("PHONE_SHA256", phone_hashes))

                for id_type, hashes in uploads:
                    upload_url = f"{self.BASE_URL}/{self.API_VERSION}/dmp/custom_audience/update/"

                    upload_payload = {
                        "advertiser_id": self.advertiser_id,
                        "custom_audience_id": audience_id,
                        "action": "OVERRIDE",
                        "id_type": id_type,
                        "id_list": hashes,
                    }

                    response = await client.post(
                        upload_url,
                        json=upload_payload,
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()
                    result = response.json()

                    if result.get("code") == 0:
                        total_sent += len(hashes)

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
            self.logger.error("tiktok_audience_replace_error", error=str(e))
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
        Delete a TikTok Custom Audience.
        """
        start_time = time.time()

        try:
            url = f"{self.BASE_URL}/{self.API_VERSION}/dmp/custom_audience/delete/"

            payload = {
                "advertiser_id": self.advertiser_id,
                "custom_audience_ids": [audience_id],
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                result = response.json()

            duration_ms = int((time.time() - start_time) * 1000)

            success = result.get("code") == 0

            return AudienceSyncResult(
                success=success,
                operation="delete",
                platform_audience_id=audience_id,
                error_message=None if success else result.get("message"),
                duration_ms=duration_ms,
                platform_response=result,
            )

        except Exception as e:
            self.logger.error("tiktok_audience_delete_error", error=str(e))
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
        Get TikTok Custom Audience information.
        """
        try:
            url = f"{self.BASE_URL}/{self.API_VERSION}/dmp/custom_audience/get/"

            params = {
                "advertiser_id": self.advertiser_id,
                "custom_audience_ids": json.dumps([audience_id]),
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                result = response.json()

            if result.get("code") == 0:
                audiences = result.get("data", {}).get("list", [])
                if audiences:
                    audience = audiences[0]
                    return {
                        "id": audience.get("custom_audience_id"),
                        "name": audience.get("custom_audience_name"),
                        "size": audience.get("audience_size"),
                        "status": audience.get("is_valid"),
                        "create_time": audience.get("create_time"),
                    }

            return {"error": result.get("message", "Not found")}

        except Exception as e:
            self.logger.error("tiktok_audience_info_error", error=str(e))
            return {"error": str(e)}
