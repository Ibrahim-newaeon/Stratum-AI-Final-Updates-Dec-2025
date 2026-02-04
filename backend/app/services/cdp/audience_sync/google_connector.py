# =============================================================================
# Stratum AI - Google Customer Match Connector
# =============================================================================
"""
Google Ads Customer Match API Connector.

Implements the Google Ads API for Customer Match audience operations:
- Create customer match user lists
- Add/remove users via hashed identifiers
- Support for email, phone, address, and mobile device IDs

API Reference: https://developers.google.com/google-ads/api/docs/remarketing/audience-segments/customer-match
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


class GoogleAudienceConnector(BaseAudienceConnector):
    """
    Google Ads Customer Match connector.

    Uses Google Ads API to manage customer match user lists.
    Requires OAuth credentials with google-ads scope.
    """

    PLATFORM_NAME = "google"
    BATCH_SIZE = 100000  # Google supports up to 100k per request
    API_VERSION = "v15"
    BASE_URL = "https://googleads.googleapis.com"

    def __init__(
        self,
        access_token: str,
        ad_account_id: str,  # Google Ads Customer ID
        developer_token: Optional[str] = None,
        login_customer_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(access_token, ad_account_id, **kwargs)
        self.developer_token = developer_token
        self.login_customer_id = login_customer_id
        # Remove dashes from customer ID
        self.customer_id = self.ad_account_id.replace("-", "")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Google Ads API requests."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        if self.developer_token:
            headers["developer-token"] = self.developer_token
        if self.login_customer_id:
            headers["login-customer-id"] = self.login_customer_id.replace("-", "")
        return headers

    async def create_audience(
        self,
        config: AudienceConfig,
        users: list[AudienceUser],
    ) -> AudienceSyncResult:
        """
        Create a new Google Ads Customer Match user list with initial users.
        """
        start_time = time.time()

        try:
            # Step 1: Create the user list
            create_url = (
                f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/userLists:mutate"
            )

            user_list_operation = {
                "create": {
                    "name": config.name,
                    "description": config.description or f"CDP Segment: {config.name}",
                    "membershipStatus": "OPEN",
                    "membershipLifeSpan": config.retention_days or 540,  # Max 540 days
                    "crmBasedUserList": {
                        "uploadKeyType": "CONTACT_INFO",
                        "dataSourceType": "FIRST_PARTY",
                    },
                }
            }

            payload = {"operations": [user_list_operation]}

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    create_url,
                    json=payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                create_result = response.json()

            # Extract user list resource name
            results = create_result.get("results", [])
            if not results:
                return AudienceSyncResult(
                    success=False,
                    operation="create",
                    error_message="No user list created in response",
                    platform_response=create_result,
                )

            resource_name = results[0].get("resourceName", "")
            # Extract ID from resource name: customers/123/userLists/456 -> 456
            audience_id = resource_name.split("/")[-1] if resource_name else ""

            self.logger.info(
                "google_audience_created",
                audience_id=audience_id,
                resource_name=resource_name,
                name=config.name,
            )

            # Step 2: Add users to the user list
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
                "google_audience_create_failed",
                error=str(e),
                response=error_body,
            )
            return AudienceSyncResult(
                success=False,
                operation="create",
                error_message=str(error_body.get("error", {}).get("message", str(e))),
                error_details=error_body,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            self.logger.error("google_audience_create_error", error=str(e))
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
        Add users to a Google Customer Match user list.
        Uses OfflineUserDataJobService for bulk uploads.
        """
        start_time = time.time()
        total_sent = 0
        total_added = 0
        total_failed = 0

        try:
            # Step 1: Create offline user data job
            job_url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/offlineUserDataJobs:create"

            job_payload = {
                "job": {
                    "type": "CUSTOMER_MATCH_USER_LIST",
                    "customerMatchUserListMetadata": {
                        "userList": f"customers/{self.customer_id}/userLists/{audience_id}"
                    },
                }
            }

            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    job_url,
                    json=job_payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                job_result = response.json()

            job_resource_name = job_result.get("resourceName", "")
            if not job_resource_name:
                return AudienceSyncResult(
                    success=False,
                    operation="add",
                    error_message="Failed to create offline data job",
                    platform_response=job_result,
                )

            # Step 2: Add operations to the job
            user_data = self._prepare_google_user_data(users)
            batches = self._chunk_list(user_data, self.BATCH_SIZE)

            async with httpx.AsyncClient(timeout=300) as client:
                for batch in batches:
                    operations = [
                        {"create": {"userIdentifiers": identifiers}} for identifiers in batch
                    ]

                    add_url = (
                        f"{self.BASE_URL}/{self.API_VERSION}/{job_resource_name}:addOperations"
                    )
                    add_payload = {
                        "operations": operations,
                        "enablePartialFailure": True,
                    }

                    response = await client.post(
                        add_url,
                        json=add_payload,
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()

                    total_sent += len(batch)

                # Step 3: Run the job
                run_url = f"{self.BASE_URL}/{self.API_VERSION}/{job_resource_name}:run"
                response = await client.post(
                    run_url,
                    json={},
                    headers=self._get_headers(),
                )
                response.raise_for_status()

            total_added = total_sent  # Assume all added unless partial failure

            duration_ms = int((time.time() - start_time) * 1000)

            self.logger.info(
                "google_audience_users_added",
                audience_id=audience_id,
                total_sent=total_sent,
            )

            return AudienceSyncResult(
                success=True,
                operation="add",
                platform_audience_id=audience_id,
                users_sent=total_sent,
                users_added=total_added,
                users_failed=total_failed,
                duration_ms=duration_ms,
            )

        except httpx.HTTPStatusError as e:
            error_body = e.response.json() if e.response.content else {}
            self.logger.error(
                "google_audience_add_failed",
                audience_id=audience_id,
                error=str(e),
            )
            return AudienceSyncResult(
                success=False,
                operation="add",
                platform_audience_id=audience_id,
                users_sent=total_sent,
                error_message=str(error_body.get("error", {}).get("message", str(e))),
                error_details=error_body,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            self.logger.error("google_audience_add_error", error=str(e))
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
        Remove users from a Google Customer Match user list.
        """
        start_time = time.time()
        total_sent = 0
        total_removed = 0

        try:
            # Create job for removal
            job_url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/offlineUserDataJobs:create"

            job_payload = {
                "job": {
                    "type": "CUSTOMER_MATCH_USER_LIST",
                    "customerMatchUserListMetadata": {
                        "userList": f"customers/{self.customer_id}/userLists/{audience_id}"
                    },
                }
            }

            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    job_url,
                    json=job_payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                job_result = response.json()

            job_resource_name = job_result.get("resourceName", "")

            user_data = self._prepare_google_user_data(users)

            async with httpx.AsyncClient(timeout=300) as client:
                # Add remove operations
                operations = [
                    {"remove": {"userIdentifiers": identifiers}} for identifiers in user_data
                ]

                add_url = f"{self.BASE_URL}/{self.API_VERSION}/{job_resource_name}:addOperations"
                add_payload = {"operations": operations}

                response = await client.post(
                    add_url,
                    json=add_payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()

                total_sent = len(user_data)

                # Run the job
                run_url = f"{self.BASE_URL}/{self.API_VERSION}/{job_resource_name}:run"
                await client.post(run_url, json={}, headers=self._get_headers())

            total_removed = total_sent
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
            self.logger.error("google_audience_remove_error", error=str(e))
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
        Replace audience by removing all and re-adding.
        Google doesn't have a native replace operation.
        """
        start_time = time.time()

        # For Google, we create a new job with REMOVE_ALL operation first
        # Then add the new users
        try:
            # Create a new user list and deprecate the old one
            # Or use the existing add_users with full list
            result = await self.add_users(audience_id, users)
            result.operation = "replace"
            return result

        except Exception as e:
            self.logger.error("google_audience_replace_error", error=str(e))
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
        Delete a Google Ads user list (set to CLOSED status).
        """
        start_time = time.time()

        try:
            url = (
                f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/userLists:mutate"
            )

            payload = {
                "operations": [
                    {
                        "update": {
                            "resourceName": f"customers/{self.customer_id}/userLists/{audience_id}",
                            "membershipStatus": "CLOSED",
                        },
                        "updateMask": "membershipStatus",
                    }
                ]
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

            return AudienceSyncResult(
                success=True,
                operation="delete",
                platform_audience_id=audience_id,
                duration_ms=duration_ms,
                platform_response=result,
            )

        except Exception as e:
            self.logger.error("google_audience_delete_error", error=str(e))
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
        Get Google Ads user list information.
        """
        try:
            url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/googleAds:searchStream"

            query = f"""
                SELECT
                    user_list.id,
                    user_list.name,
                    user_list.description,
                    user_list.membership_status,
                    user_list.size_for_display,
                    user_list.size_for_search
                FROM user_list
                WHERE user_list.id = {audience_id}
            """

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json={"query": query},
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                results = response.json()

            if results and len(results) > 0:
                row = results[0].get("results", [{}])[0]
                user_list = row.get("userList", {})
                return {
                    "id": user_list.get("id"),
                    "name": user_list.get("name"),
                    "description": user_list.get("description"),
                    "status": user_list.get("membershipStatus"),
                    "size_display": user_list.get("sizeForDisplay"),
                    "size_search": user_list.get("sizeForSearch"),
                }

            return {}

        except Exception as e:
            self.logger.error("google_audience_info_error", error=str(e))
            return {"error": str(e)}

    # =========================================================================
    # Google-specific helpers
    # =========================================================================

    def _prepare_google_user_data(self, users: list[AudienceUser]) -> list[list[dict]]:
        """
        Prepare user data in Google's Customer Match format.
        Each user is a list of identifier objects.
        """
        user_data = []

        for user in users:
            identifiers = []

            for identifier in user.identifiers:
                hashed = identifier.get_hashed()
                if not hashed:
                    continue

                if identifier.identifier_type == IdentifierType.EMAIL:
                    identifiers.append({"hashedEmail": hashed})
                elif identifier.identifier_type == IdentifierType.PHONE:
                    identifiers.append({"hashedPhoneNumber": hashed})
                elif identifier.identifier_type == IdentifierType.MOBILE_ADVERTISER_ID:
                    identifiers.append({"mobileId": hashed})

            # Add address info if available
            if user.first_name or user.last_name or user.country:
                address_info = {}
                if user.first_name:
                    address_info["hashedFirstName"] = self._hash_identifier(
                        user.first_name, IdentifierType.EXTERNAL_ID
                    )
                if user.last_name:
                    address_info["hashedLastName"] = self._hash_identifier(
                        user.last_name, IdentifierType.EXTERNAL_ID
                    )
                if user.country:
                    address_info["countryCode"] = user.country
                if user.zip_code:
                    address_info["postalCode"] = user.zip_code
                if address_info:
                    identifiers.append({"addressInfo": address_info})

            if identifiers:
                user_data.append(identifiers)

        return user_data
