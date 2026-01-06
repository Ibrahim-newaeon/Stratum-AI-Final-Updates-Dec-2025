# =============================================================================
# Stratum AI - Offline Conversion Upload Service
# =============================================================================
"""
Service for uploading offline conversions to ad platforms.

Offline conversions include:
- In-store purchases
- Phone orders
- CRM conversions
- Lead qualification events
- Post-purchase events (returns, upsells)

Supports:
- Meta (Facebook) Offline Conversions API
- Google Ads Offline Conversion Import
- TikTok Events API (offline mode)
- LinkedIn Offline Conversions
"""

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import asyncio
import httpx

from app.core.logging import get_logger
from app.services.capi.pii_hasher import PIIHasher

logger = get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class OfflineConversionStatus(str, Enum):
    """Status of an offline conversion upload."""
    PENDING = "pending"
    PROCESSING = "processing"
    UPLOADED = "uploaded"
    FAILED = "failed"
    PARTIAL = "partial"  # Some records failed


class OfflineConversionSource(str, Enum):
    """Source of offline conversion data."""
    CRM = "crm"
    POS = "pos"  # Point of Sale
    CALL_CENTER = "call_center"
    MANUAL = "manual"
    CSV_UPLOAD = "csv_upload"
    API = "api"


@dataclass
class OfflineConversion:
    """Single offline conversion record."""
    # Identifiers
    conversion_id: str
    platform: str

    # User identification (at least one required)
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    external_id: Optional[str] = None
    click_id: Optional[str] = None  # gclid, fbclid, ttclid, etc.

    # Conversion details
    event_name: str = "Purchase"
    event_time: Optional[datetime] = None
    conversion_value: float = 0.0
    currency: str = "USD"

    # Attribution
    order_id: Optional[str] = None
    item_count: int = 0
    source: OfflineConversionSource = OfflineConversionSource.MANUAL

    # Processing status
    status: OfflineConversionStatus = OfflineConversionStatus.PENDING
    error_message: Optional[str] = None
    platform_response: Optional[Dict] = None


@dataclass
class OfflineConversionBatch:
    """Batch of offline conversions for upload."""
    batch_id: str
    platform: str
    conversions: List[OfflineConversion]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: OfflineConversionStatus = OfflineConversionStatus.PENDING
    total_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    error_summary: Optional[str] = None


@dataclass
class UploadResult:
    """Result of an offline conversion upload."""
    batch_id: str
    platform: str
    success: bool
    total_records: int
    successful_records: int
    failed_records: int
    errors: List[Dict[str, Any]]
    platform_response: Optional[Dict] = None


# =============================================================================
# Platform-Specific Uploaders
# =============================================================================

class BaseOfflineUploader:
    """Base class for platform-specific offline uploaders."""

    PLATFORM_NAME = "base"

    def __init__(self):
        self.hasher = PIIHasher()
        self._credentials: Dict[str, str] = {}

    def set_credentials(self, credentials: Dict[str, str]):
        """Set platform credentials."""
        self._credentials = credentials

    async def upload(self, conversions: List[OfflineConversion]) -> UploadResult:
        """Upload conversions. Override in subclasses."""
        raise NotImplementedError

    def _hash_email(self, email: Optional[str]) -> Optional[str]:
        """Hash email for privacy."""
        if not email:
            return None
        return hashlib.sha256(email.lower().strip().encode()).hexdigest()

    def _hash_phone(self, phone: Optional[str]) -> Optional[str]:
        """Hash phone for privacy."""
        if not phone:
            return None
        # Normalize: remove spaces, dashes, and leading +
        normalized = phone.replace(" ", "").replace("-", "").replace("+", "")
        return hashlib.sha256(normalized.encode()).hexdigest()


class MetaOfflineUploader(BaseOfflineUploader):
    """
    Meta (Facebook) Offline Conversions API uploader.

    Uses the Offline Events API to upload offline conversions
    that can be matched back to ad impressions/clicks.
    """

    PLATFORM_NAME = "meta"
    BASE_URL = "https://graph.facebook.com"
    API_VERSION = "v18.0"

    async def upload(self, conversions: List[OfflineConversion]) -> UploadResult:
        """Upload conversions to Meta Offline Events API."""
        offline_event_set_id = self._credentials.get("offline_event_set_id")
        access_token = self._credentials.get("access_token")

        if not offline_event_set_id or not access_token:
            return UploadResult(
                batch_id="",
                platform=self.PLATFORM_NAME,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": "Missing offline_event_set_id or access_token"}],
            )

        # Format conversions for Meta
        formatted_events = []
        for conv in conversions:
            event = self._format_conversion(conv)
            formatted_events.append(event)

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/{self.API_VERSION}/{offline_event_set_id}/events"

                # Meta accepts up to 1000 events per request
                batch_size = 1000
                all_results = []

                for i in range(0, len(formatted_events), batch_size):
                    batch = formatted_events[i:i + batch_size]

                    response = await client.post(
                        url,
                        params={"access_token": access_token},
                        json={"data": batch, "upload_tag": f"stratum_offline_{datetime.now().strftime('%Y%m%d')}"},
                        timeout=60.0,
                    )

                    result = response.json()
                    all_results.append(result)

                # Aggregate results
                total_received = sum(r.get("num_processed_entries", 0) for r in all_results if "error" not in r)
                errors = [r.get("error", {}) for r in all_results if "error" in r]

                return UploadResult(
                    batch_id=f"meta_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    platform=self.PLATFORM_NAME,
                    success=len(errors) == 0,
                    total_records=len(conversions),
                    successful_records=total_received,
                    failed_records=len(conversions) - total_received,
                    errors=errors,
                    platform_response=all_results[0] if all_results else None,
                )

        except Exception as e:
            logger.error(f"Meta offline upload error: {e}")
            return UploadResult(
                batch_id="",
                platform=self.PLATFORM_NAME,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": str(e)}],
            )

    def _format_conversion(self, conv: OfflineConversion) -> Dict[str, Any]:
        """Format conversion for Meta Offline Events API."""
        # Build match keys (user identifiers)
        match_keys = {}
        if conv.email:
            match_keys["em"] = [self._hash_email(conv.email)]
        if conv.phone:
            match_keys["ph"] = [self._hash_phone(conv.phone)]
        if conv.first_name:
            match_keys["fn"] = [hashlib.sha256(conv.first_name.lower().encode()).hexdigest()]
        if conv.last_name:
            match_keys["ln"] = [hashlib.sha256(conv.last_name.lower().encode()).hexdigest()]
        if conv.external_id:
            match_keys["external_id"] = [conv.external_id]

        # Event time (Unix timestamp)
        event_time = conv.event_time or datetime.now(timezone.utc)
        if isinstance(event_time, datetime):
            event_time = int(event_time.timestamp())

        event = {
            "match_keys": match_keys,
            "event_name": conv.event_name,
            "event_time": event_time,
            "currency": conv.currency,
            "value": conv.conversion_value,
        }

        # Add optional fields
        if conv.order_id:
            event["order_id"] = conv.order_id
        if conv.item_count:
            event["contents"] = [{"quantity": conv.item_count}]

        return event


class GoogleOfflineUploader(BaseOfflineUploader):
    """
    Google Ads Offline Conversion Import uploader.

    Uses the Google Ads API to upload offline conversions
    that can be attributed to ad clicks via GCLID.
    """

    PLATFORM_NAME = "google"
    BASE_URL = "https://googleads.googleapis.com"
    API_VERSION = "v15"

    async def upload(self, conversions: List[OfflineConversion]) -> UploadResult:
        """Upload conversions to Google Ads Offline Conversion Import."""
        customer_id = self._credentials.get("customer_id", "").replace("-", "")
        conversion_action_id = self._credentials.get("conversion_action_id")
        developer_token = self._credentials.get("developer_token")
        access_token = self._credentials.get("access_token")

        if not all([customer_id, conversion_action_id, developer_token]):
            return UploadResult(
                batch_id="",
                platform=self.PLATFORM_NAME,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": "Missing required credentials"}],
            )

        # Format conversions for Google
        formatted_conversions = []
        for conv in conversions:
            formatted = self._format_conversion(conv, customer_id, conversion_action_id)
            if formatted:
                formatted_conversions.append(formatted)

        if not formatted_conversions:
            return UploadResult(
                batch_id="",
                platform=self.PLATFORM_NAME,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": "No valid conversions to upload (GCLID required)"}],
            )

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{customer_id}:uploadClickConversions"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": developer_token,
                    "Content-Type": "application/json",
                }

                payload = {
                    "conversions": formatted_conversions,
                    "partialFailure": True,
                }

                response = await client.post(url, json=payload, headers=headers, timeout=60.0)
                result = response.json()

                if response.status_code == 200:
                    # Check for partial failures
                    partial_errors = result.get("partialFailureError", {})
                    failed_count = len(partial_errors.get("details", []))

                    return UploadResult(
                        batch_id=f"google_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        platform=self.PLATFORM_NAME,
                        success=failed_count == 0,
                        total_records=len(conversions),
                        successful_records=len(formatted_conversions) - failed_count,
                        failed_records=failed_count + (len(conversions) - len(formatted_conversions)),
                        errors=[partial_errors] if partial_errors else [],
                        platform_response=result,
                    )
                else:
                    return UploadResult(
                        batch_id="",
                        platform=self.PLATFORM_NAME,
                        success=False,
                        total_records=len(conversions),
                        successful_records=0,
                        failed_records=len(conversions),
                        errors=[result.get("error", {"message": "Upload failed"})],
                    )

        except Exception as e:
            logger.error(f"Google offline upload error: {e}")
            return UploadResult(
                batch_id="",
                platform=self.PLATFORM_NAME,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": str(e)}],
            )

    def _format_conversion(
        self,
        conv: OfflineConversion,
        customer_id: str,
        conversion_action_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Format conversion for Google Ads API."""
        # Google requires GCLID for click-based attribution
        gclid = conv.click_id
        if not gclid and conv.external_id and conv.external_id.startswith("gclid:"):
            gclid = conv.external_id.replace("gclid:", "")

        if not gclid:
            # Cannot upload without GCLID
            logger.warning(f"Skipping conversion {conv.conversion_id}: no GCLID")
            return None

        # Format timestamp
        event_time = conv.event_time or datetime.now(timezone.utc)
        if isinstance(event_time, datetime):
            conversion_datetime = event_time.strftime("%Y-%m-%d %H:%M:%S%z")
        else:
            conversion_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")

        formatted = {
            "conversionAction": f"customers/{customer_id}/conversionActions/{conversion_action_id}",
            "gclid": gclid,
            "conversionDateTime": conversion_datetime,
        }

        if conv.conversion_value > 0:
            formatted["conversionValue"] = conv.conversion_value
            formatted["currencyCode"] = conv.currency

        if conv.order_id:
            formatted["orderId"] = conv.order_id

        return formatted


class TikTokOfflineUploader(BaseOfflineUploader):
    """TikTok Events API uploader for offline conversions."""

    PLATFORM_NAME = "tiktok"
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"

    async def upload(self, conversions: List[OfflineConversion]) -> UploadResult:
        """Upload conversions to TikTok Events API."""
        pixel_code = self._credentials.get("pixel_code")
        access_token = self._credentials.get("access_token")

        if not pixel_code or not access_token:
            return UploadResult(
                batch_id="",
                platform=self.PLATFORM_NAME,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": "Missing pixel_code or access_token"}],
            )

        # Format conversions
        formatted_events = [self._format_conversion(conv) for conv in conversions]

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/pixel/track/"
                headers = {"Access-Token": access_token}

                payload = {
                    "pixel_code": pixel_code,
                    "event": formatted_events,
                    "event_source": "offline",
                }

                response = await client.post(url, json=payload, headers=headers, timeout=60.0)
                result = response.json()

                if result.get("code") == 0:
                    return UploadResult(
                        batch_id=f"tiktok_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        platform=self.PLATFORM_NAME,
                        success=True,
                        total_records=len(conversions),
                        successful_records=len(conversions),
                        failed_records=0,
                        errors=[],
                        platform_response=result,
                    )
                else:
                    return UploadResult(
                        batch_id="",
                        platform=self.PLATFORM_NAME,
                        success=False,
                        total_records=len(conversions),
                        successful_records=0,
                        failed_records=len(conversions),
                        errors=[{"message": result.get("message", "Upload failed"), "code": result.get("code")}],
                    )

        except Exception as e:
            logger.error(f"TikTok offline upload error: {e}")
            return UploadResult(
                batch_id="",
                platform=self.PLATFORM_NAME,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": str(e)}],
            )

    def _format_conversion(self, conv: OfflineConversion) -> Dict[str, Any]:
        """Format conversion for TikTok Events API."""
        event_time = conv.event_time or datetime.now(timezone.utc)
        if isinstance(event_time, datetime):
            event_time = int(event_time.timestamp())

        return {
            "event": conv.event_name,
            "event_time": event_time,
            "user": {
                "email": self._hash_email(conv.email),
                "phone": self._hash_phone(conv.phone),
                "external_id": conv.external_id,
            },
            "properties": {
                "value": conv.conversion_value,
                "currency": conv.currency,
                "order_id": conv.order_id,
            },
        }


class LinkedInOfflineUploader(BaseOfflineUploader):
    """LinkedIn Conversions API uploader for offline conversions."""

    PLATFORM_NAME = "linkedin"
    BASE_URL = "https://api.linkedin.com/rest"
    API_VERSION = "202401"

    async def upload(self, conversions: List[OfflineConversion]) -> UploadResult:
        """Upload conversions to LinkedIn Conversions API."""
        conversion_id = self._credentials.get("conversion_id")
        access_token = self._credentials.get("access_token")

        if not conversion_id or not access_token:
            return UploadResult(
                batch_id="",
                platform=self.PLATFORM_NAME,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": "Missing conversion_id or access_token"}],
            )

        # Format conversions
        formatted_events = [self._format_conversion(conv, conversion_id) for conv in conversions]

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/conversionEvents"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "LinkedIn-Version": self.API_VERSION,
                    "Content-Type": "application/json",
                }

                payload = {"elements": formatted_events}

                response = await client.post(url, json=payload, headers=headers, timeout=60.0)

                if response.status_code in [200, 201]:
                    return UploadResult(
                        batch_id=f"linkedin_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        platform=self.PLATFORM_NAME,
                        success=True,
                        total_records=len(conversions),
                        successful_records=len(conversions),
                        failed_records=0,
                        errors=[],
                        platform_response=response.json() if response.text else None,
                    )
                else:
                    return UploadResult(
                        batch_id="",
                        platform=self.PLATFORM_NAME,
                        success=False,
                        total_records=len(conversions),
                        successful_records=0,
                        failed_records=len(conversions),
                        errors=[{"message": f"HTTP {response.status_code}", "body": response.text}],
                    )

        except Exception as e:
            logger.error(f"LinkedIn offline upload error: {e}")
            return UploadResult(
                batch_id="",
                platform=self.PLATFORM_NAME,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": str(e)}],
            )

    def _format_conversion(self, conv: OfflineConversion, conversion_id: str) -> Dict[str, Any]:
        """Format conversion for LinkedIn API."""
        event_time = conv.event_time or datetime.now(timezone.utc)
        if isinstance(event_time, datetime):
            event_time_ms = int(event_time.timestamp() * 1000)
        else:
            event_time_ms = int(event_time * 1000)

        user_ids = []
        if conv.email:
            user_ids.append({"idType": "SHA256_EMAIL", "idValue": self._hash_email(conv.email)})
        if conv.phone:
            user_ids.append({"idType": "SHA256_PHONE_NUMBER", "idValue": self._hash_phone(conv.phone)})

        return {
            "conversion": f"urn:li:conversion:{conversion_id}",
            "conversionHappenedAt": event_time_ms,
            "user": {"userIds": user_ids},
            "conversionValue": {
                "currencyCode": conv.currency,
                "amount": str(conv.conversion_value),
            },
        }


# =============================================================================
# Offline Conversion Service
# =============================================================================

class OfflineConversionService:
    """
    Service for managing offline conversion uploads across platforms.

    Features:
    - CSV file parsing and validation
    - Multi-platform upload support
    - Batch processing with retry
    - Upload history tracking
    """

    def __init__(self):
        self._uploaders: Dict[str, BaseOfflineUploader] = {
            "meta": MetaOfflineUploader(),
            "google": GoogleOfflineUploader(),
            "tiktok": TikTokOfflineUploader(),
            "linkedin": LinkedInOfflineUploader(),
        }
        self._batches: Dict[str, OfflineConversionBatch] = {}

    def set_platform_credentials(self, platform: str, credentials: Dict[str, str]):
        """Set credentials for a platform uploader."""
        if platform in self._uploaders:
            self._uploaders[platform].set_credentials(credentials)

    def parse_csv(
        self,
        csv_content: str,
        platform: str,
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> List[OfflineConversion]:
        """
        Parse CSV content into OfflineConversion objects.

        Args:
            csv_content: CSV file content as string
            platform: Target platform
            column_mapping: Optional mapping of CSV columns to conversion fields

        Returns:
            List of parsed OfflineConversion objects
        """
        # Default column mapping
        default_mapping = {
            "email": ["email", "user_email", "customer_email"],
            "phone": ["phone", "phone_number", "mobile"],
            "first_name": ["first_name", "firstname", "fname"],
            "last_name": ["last_name", "lastname", "lname"],
            "conversion_value": ["value", "amount", "revenue", "conversion_value", "order_value"],
            "currency": ["currency", "currency_code"],
            "event_time": ["event_time", "timestamp", "date", "conversion_time"],
            "order_id": ["order_id", "transaction_id", "reference"],
            "click_id": ["click_id", "gclid", "fbclid", "ttclid"],
            "event_name": ["event_name", "event", "action"],
        }

        if column_mapping:
            default_mapping.update(column_mapping)

        conversions = []
        reader = csv.DictReader(io.StringIO(csv_content))

        for i, row in enumerate(reader):
            try:
                conv = self._parse_row(row, platform, default_mapping, i)
                if conv:
                    conversions.append(conv)
            except Exception as e:
                logger.warning(f"Error parsing row {i}: {e}")

        return conversions

    def _parse_row(
        self,
        row: Dict[str, str],
        platform: str,
        mapping: Dict[str, List[str]],
        row_index: int,
    ) -> Optional[OfflineConversion]:
        """Parse a single CSV row into an OfflineConversion."""

        def get_value(field: str) -> Optional[str]:
            """Get value from row using mapping."""
            for col_name in mapping.get(field, [field]):
                if col_name.lower() in {k.lower(): k for k in row}:
                    actual_key = {k.lower(): k for k in row}[col_name.lower()]
                    val = row.get(actual_key, "").strip()
                    if val:
                        return val
            return None

        email = get_value("email")
        phone = get_value("phone")

        # At least one identifier required
        if not email and not phone and not get_value("click_id"):
            logger.warning(f"Row {row_index}: No user identifiers found")
            return None

        # Parse event time
        event_time_str = get_value("event_time")
        event_time = None
        if event_time_str:
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                try:
                    event_time = datetime.strptime(event_time_str, fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue

        # Parse value
        value_str = get_value("conversion_value")
        conversion_value = 0.0
        if value_str:
            try:
                conversion_value = float(value_str.replace(",", "").replace("$", ""))
            except ValueError:
                pass

        return OfflineConversion(
            conversion_id=f"{platform}_{row_index}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            platform=platform,
            email=email,
            phone=phone,
            first_name=get_value("first_name"),
            last_name=get_value("last_name"),
            click_id=get_value("click_id"),
            external_id=get_value("external_id"),
            event_name=get_value("event_name") or "Purchase",
            event_time=event_time,
            conversion_value=conversion_value,
            currency=get_value("currency") or "USD",
            order_id=get_value("order_id"),
            source=OfflineConversionSource.CSV_UPLOAD,
        )

    async def upload_conversions(
        self,
        conversions: List[OfflineConversion],
        platform: str,
    ) -> UploadResult:
        """
        Upload offline conversions to a platform.

        Args:
            conversions: List of conversions to upload
            platform: Target platform

        Returns:
            UploadResult with success/failure details
        """
        if platform not in self._uploaders:
            return UploadResult(
                batch_id="",
                platform=platform,
                success=False,
                total_records=len(conversions),
                successful_records=0,
                failed_records=len(conversions),
                errors=[{"message": f"Unknown platform: {platform}"}],
            )

        uploader = self._uploaders[platform]

        # Create batch record
        batch_id = f"{platform}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        batch = OfflineConversionBatch(
            batch_id=batch_id,
            platform=platform,
            conversions=conversions,
            total_records=len(conversions),
            status=OfflineConversionStatus.PROCESSING,
        )
        self._batches[batch_id] = batch

        # Upload
        result = await uploader.upload(conversions)
        result.batch_id = batch_id

        # Update batch status
        batch.successful_records = result.successful_records
        batch.failed_records = result.failed_records
        batch.status = (
            OfflineConversionStatus.UPLOADED if result.success
            else OfflineConversionStatus.PARTIAL if result.successful_records > 0
            else OfflineConversionStatus.FAILED
        )
        if result.errors:
            batch.error_summary = "; ".join(str(e.get("message", "")) for e in result.errors[:3])

        logger.info(f"Offline upload {batch_id}: {result.successful_records}/{result.total_records} succeeded")

        return result

    async def upload_csv(
        self,
        csv_content: str,
        platform: str,
        credentials: Dict[str, str],
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> UploadResult:
        """
        Parse CSV and upload conversions to a platform.

        Args:
            csv_content: CSV file content
            platform: Target platform
            credentials: Platform credentials
            column_mapping: Optional column mapping

        Returns:
            UploadResult
        """
        # Set credentials
        self.set_platform_credentials(platform, credentials)

        # Parse CSV
        conversions = self.parse_csv(csv_content, platform, column_mapping)

        if not conversions:
            return UploadResult(
                batch_id="",
                platform=platform,
                success=False,
                total_records=0,
                successful_records=0,
                failed_records=0,
                errors=[{"message": "No valid conversions found in CSV"}],
            )

        # Upload
        return await self.upload_conversions(conversions, platform)

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an upload batch."""
        batch = self._batches.get(batch_id)
        if not batch:
            return None

        return {
            "batch_id": batch.batch_id,
            "platform": batch.platform,
            "status": batch.status.value,
            "created_at": batch.created_at.isoformat(),
            "total_records": batch.total_records,
            "successful_records": batch.successful_records,
            "failed_records": batch.failed_records,
            "error_summary": batch.error_summary,
        }

    def get_upload_history(
        self,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get recent upload history."""
        batches = list(self._batches.values())

        if platform:
            batches = [b for b in batches if b.platform == platform]

        # Sort by created_at descending
        batches.sort(key=lambda b: b.created_at, reverse=True)

        return [
            {
                "batch_id": b.batch_id,
                "platform": b.platform,
                "status": b.status.value,
                "created_at": b.created_at.isoformat(),
                "total_records": b.total_records,
                "successful_records": b.successful_records,
                "failed_records": b.failed_records,
            }
            for b in batches[:limit]
        ]


# Create singleton instance
offline_conversion_service = OfflineConversionService()
