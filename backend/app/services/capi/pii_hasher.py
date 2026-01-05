# =============================================================================
# Stratum AI - PII Hasher
# =============================================================================
"""
Automatic PII detection and SHA256 hashing for Conversion APIs.
Ensures compliance with platform requirements and privacy regulations.
"""

import hashlib
import re
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from app.core.logging import get_logger

logger = get_logger(__name__)


class PIIField(str, Enum):
    """Standard PII fields recognized by ad platforms."""
    EMAIL = "em"
    PHONE = "ph"
    FIRST_NAME = "fn"
    LAST_NAME = "ln"
    DATE_OF_BIRTH = "db"
    GENDER = "ge"
    CITY = "ct"
    STATE = "st"
    ZIP_CODE = "zp"
    COUNTRY = "country"
    EXTERNAL_ID = "external_id"
    CLIENT_IP = "client_ip_address"
    CLIENT_USER_AGENT = "client_user_agent"
    FBC = "fbc"  # Facebook click ID
    FBP = "fbp"  # Facebook browser ID
    GCLID = "gclid"  # Google click ID
    TTCLID = "ttclid"  # TikTok click ID


@dataclass
class PIIDetectionResult:
    """Result of PII detection in data."""
    field_name: str
    original_key: str
    detected_type: PIIField
    confidence: float
    needs_hashing: bool
    is_hashed: bool


class PIIHasher:
    """
    Automatically detects and hashes PII data for Conversion APIs.

    Features:
    - Pattern-based PII detection
    - SHA256 hashing with normalization
    - Platform-specific formatting
    - Confidence scoring
    """

    # Field name patterns for PII detection
    FIELD_PATTERNS = {
        PIIField.EMAIL: [
            r"email", r"e[-_]?mail", r"user[-_]?email", r"customer[-_]?email",
            r"contact[-_]?email", r"mail"
        ],
        PIIField.PHONE: [
            r"phone", r"tel", r"mobile", r"cell", r"phone[-_]?number",
            r"contact[-_]?number", r"telephone"
        ],
        PIIField.FIRST_NAME: [
            r"first[-_]?name", r"fname", r"given[-_]?name", r"forename"
        ],
        PIIField.LAST_NAME: [
            r"last[-_]?name", r"lname", r"surname", r"family[-_]?name"
        ],
        PIIField.DATE_OF_BIRTH: [
            r"dob", r"date[-_]?of[-_]?birth", r"birth[-_]?date", r"birthday"
        ],
        PIIField.GENDER: [
            r"gender", r"sex"
        ],
        PIIField.CITY: [
            r"city", r"town", r"locality"
        ],
        PIIField.STATE: [
            r"state", r"province", r"region"
        ],
        PIIField.ZIP_CODE: [
            r"zip", r"zip[-_]?code", r"postal", r"postal[-_]?code", r"postcode"
        ],
        PIIField.COUNTRY: [
            r"country", r"country[-_]?code", r"nation"
        ],
        PIIField.EXTERNAL_ID: [
            r"external[-_]?id", r"user[-_]?id", r"customer[-_]?id", r"client[-_]?id"
        ],
        PIIField.CLIENT_IP: [
            r"ip", r"ip[-_]?address", r"client[-_]?ip", r"user[-_]?ip"
        ],
        PIIField.CLIENT_USER_AGENT: [
            r"user[-_]?agent", r"ua", r"browser"
        ],
        PIIField.FBC: [r"fbc", r"fb[-_]?click[-_]?id"],
        PIIField.FBP: [r"fbp", r"fb[-_]?browser[-_]?id"],
        PIIField.GCLID: [r"gclid", r"google[-_]?click[-_]?id"],
        PIIField.TTCLID: [r"ttclid", r"tiktok[-_]?click[-_]?id"],
    }

    # Value patterns for validation
    VALUE_PATTERNS = {
        PIIField.EMAIL: r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        PIIField.PHONE: r"^[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,}$",
        PIIField.ZIP_CODE: r"^\d{5}(-\d{4})?$|^[A-Z]\d[A-Z]\s?\d[A-Z]\d$",
    }

    # Fields that require hashing
    HASHABLE_FIELDS = {
        PIIField.EMAIL, PIIField.PHONE, PIIField.FIRST_NAME, PIIField.LAST_NAME,
        PIIField.DATE_OF_BIRTH, PIIField.GENDER, PIIField.CITY, PIIField.STATE,
        PIIField.ZIP_CODE, PIIField.COUNTRY, PIIField.EXTERNAL_ID
    }

    # Fields that should NOT be hashed
    NON_HASHABLE_FIELDS = {
        PIIField.CLIENT_IP, PIIField.CLIENT_USER_AGENT,
        PIIField.FBC, PIIField.FBP, PIIField.GCLID, PIIField.TTCLID
    }

    def __init__(self):
        """Initialize the PII hasher."""
        self._compiled_patterns: Dict[PIIField, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        for field, patterns in self.FIELD_PATTERNS.items():
            self._compiled_patterns[field] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def detect_pii_fields(self, data: Dict[str, Any]) -> List[PIIDetectionResult]:
        """
        Detect PII fields in the given data dictionary.

        Args:
            data: Dictionary of field names to values

        Returns:
            List of PII detection results
        """
        results = []

        for key, value in data.items():
            detection = self._detect_field(key, value)
            if detection:
                results.append(detection)

        return results

    def _detect_field(self, key: str, value: Any) -> Optional[PIIDetectionResult]:
        """Detect if a field contains PII."""
        if value is None or value == "":
            return None

        # Check if already hashed (64 char hex string)
        is_hashed = self._is_hashed(value)

        # Try to match field name patterns
        best_match = None
        best_confidence = 0.0

        for pii_field, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(key):
                    confidence = self._calculate_confidence(key, value, pii_field, pattern)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = pii_field

        if best_match:
            return PIIDetectionResult(
                field_name=best_match.value,
                original_key=key,
                detected_type=best_match,
                confidence=best_confidence,
                needs_hashing=best_match in self.HASHABLE_FIELDS and not is_hashed,
                is_hashed=is_hashed,
            )

        return None

    def _calculate_confidence(
        self, key: str, value: Any, pii_field: PIIField, pattern: re.Pattern
    ) -> float:
        """Calculate confidence score for PII detection."""
        confidence = 0.5  # Base confidence for pattern match

        # Exact match gets higher confidence
        if pattern.fullmatch(key):
            confidence += 0.3

        # Value pattern validation
        if pii_field in self.VALUE_PATTERNS:
            value_pattern = self.VALUE_PATTERNS[pii_field]
            if re.match(value_pattern, str(value)):
                confidence += 0.2

        return min(confidence, 1.0)

    def _is_hashed(self, value: Any) -> bool:
        """Check if a value appears to be already hashed."""
        if not isinstance(value, str):
            return False
        return bool(re.match(r"^[a-f0-9]{64}$", value.lower()))

    def hash_value(self, value: str, pii_type: PIIField) -> str:
        """
        Hash a PII value using SHA256 with proper normalization.

        Args:
            value: The value to hash
            pii_type: The type of PII for normalization rules

        Returns:
            SHA256 hash of normalized value
        """
        normalized = self._normalize_value(value, pii_type)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _normalize_value(self, value: str, pii_type: PIIField) -> str:
        """Normalize a value before hashing based on PII type."""
        value = str(value).strip()

        if pii_type == PIIField.EMAIL:
            # Lowercase, trim whitespace
            return value.lower().strip()

        elif pii_type == PIIField.PHONE:
            # Remove all non-numeric characters except +
            cleaned = re.sub(r"[^\d+]", "", value)
            # Remove leading + if present, keep digits only
            return cleaned.lstrip("+")

        elif pii_type in (PIIField.FIRST_NAME, PIIField.LAST_NAME, PIIField.CITY):
            # Lowercase, remove special characters
            return re.sub(r"[^a-z]", "", value.lower())

        elif pii_type == PIIField.STATE:
            # Lowercase, 2-letter abbreviation
            return value.lower()[:2] if len(value) >= 2 else value.lower()

        elif pii_type == PIIField.ZIP_CODE:
            # Remove spaces and hyphens, keep first 5 digits for US
            cleaned = re.sub(r"[\s-]", "", value)
            return cleaned[:5] if cleaned.isdigit() else cleaned.lower()

        elif pii_type == PIIField.COUNTRY:
            # 2-letter country code, lowercase
            return value.lower()[:2]

        elif pii_type == PIIField.GENDER:
            # Single letter: m or f
            return value.lower()[0] if value else ""

        elif pii_type == PIIField.DATE_OF_BIRTH:
            # YYYYMMDD format
            digits = re.sub(r"\D", "", value)
            return digits[:8] if len(digits) >= 8 else digits

        else:
            return value.lower().strip()

    def hash_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically detect and hash all PII fields in the data.

        Args:
            data: Original data dictionary

        Returns:
            Data dictionary with PII fields hashed
        """
        result = data.copy()
        detections = self.detect_pii_fields(data)

        for detection in detections:
            if detection.needs_hashing:
                original_value = data.get(detection.original_key)
                if original_value:
                    hashed = self.hash_value(str(original_value), detection.detected_type)
                    # Use platform-standard field name
                    result[detection.field_name] = hashed
                    # Keep original if key is different
                    if detection.original_key != detection.field_name:
                        del result[detection.original_key]

        return result

    def get_missing_fields(
        self, data: Dict[str, Any], required_fields: Set[PIIField]
    ) -> List[PIIField]:
        """
        Identify which required PII fields are missing from the data.

        Args:
            data: Data dictionary to check
            required_fields: Set of required PII fields

        Returns:
            List of missing PII fields
        """
        detections = self.detect_pii_fields(data)
        detected_types = {d.detected_type for d in detections}

        return [f for f in required_fields if f not in detected_types]

    def calculate_data_completeness(
        self, data: Dict[str, Any], platform: str = "meta"
    ) -> Dict[str, Any]:
        """
        Calculate data completeness score for a platform.

        Args:
            data: Data dictionary to analyze
            platform: Target platform (meta, google, tiktok, snapchat, linkedin)

        Returns:
            Completeness analysis with score and missing fields
        """
        # Platform-specific required and optional fields
        platform_fields = {
            "meta": {
                "required": {PIIField.EMAIL},
                "optional": {
                    PIIField.PHONE, PIIField.FIRST_NAME, PIIField.LAST_NAME,
                    PIIField.CITY, PIIField.STATE, PIIField.ZIP_CODE,
                    PIIField.COUNTRY, PIIField.EXTERNAL_ID, PIIField.FBC, PIIField.FBP
                },
                "weights": {
                    PIIField.EMAIL: 30, PIIField.PHONE: 20, PIIField.EXTERNAL_ID: 15,
                    PIIField.FIRST_NAME: 10, PIIField.LAST_NAME: 10,
                    PIIField.FBC: 5, PIIField.FBP: 5, PIIField.CLIENT_IP: 5
                }
            },
            "google": {
                "required": set(),
                "optional": {
                    PIIField.EMAIL, PIIField.PHONE, PIIField.FIRST_NAME,
                    PIIField.LAST_NAME, PIIField.CITY, PIIField.STATE,
                    PIIField.ZIP_CODE, PIIField.COUNTRY, PIIField.GCLID
                },
                "weights": {
                    PIIField.EMAIL: 25, PIIField.PHONE: 20, PIIField.GCLID: 20,
                    PIIField.FIRST_NAME: 10, PIIField.LAST_NAME: 10,
                    PIIField.ZIP_CODE: 10, PIIField.COUNTRY: 5
                }
            },
            "tiktok": {
                "required": set(),
                "optional": {
                    PIIField.EMAIL, PIIField.PHONE, PIIField.EXTERNAL_ID,
                    PIIField.TTCLID, PIIField.CLIENT_IP, PIIField.CLIENT_USER_AGENT
                },
                "weights": {
                    PIIField.EMAIL: 30, PIIField.PHONE: 25, PIIField.TTCLID: 20,
                    PIIField.EXTERNAL_ID: 15, PIIField.CLIENT_IP: 10
                }
            },
            "snapchat": {
                "required": set(),
                "optional": {
                    PIIField.EMAIL, PIIField.PHONE, PIIField.EXTERNAL_ID,
                    PIIField.CLIENT_IP
                },
                "weights": {
                    PIIField.EMAIL: 35, PIIField.PHONE: 30,
                    PIIField.EXTERNAL_ID: 20, PIIField.CLIENT_IP: 15
                }
            },
            "linkedin": {
                "required": set(),
                "optional": {
                    PIIField.EMAIL, PIIField.FIRST_NAME, PIIField.LAST_NAME,
                    PIIField.EXTERNAL_ID
                },
                "weights": {
                    PIIField.EMAIL: 40, PIIField.FIRST_NAME: 20,
                    PIIField.LAST_NAME: 20, PIIField.EXTERNAL_ID: 20
                }
            },
        }

        config = platform_fields.get(platform, platform_fields["meta"])
        detections = self.detect_pii_fields(data)
        detected_types = {d.detected_type for d in detections}

        # Calculate score
        total_weight = sum(config["weights"].values())
        achieved_weight = sum(
            config["weights"].get(field, 0)
            for field in detected_types
            if field in config["weights"]
        )

        score = (achieved_weight / total_weight * 100) if total_weight > 0 else 0

        # Identify missing fields
        all_fields = config["required"] | config["optional"]
        missing = all_fields - detected_types
        missing_with_weights = [
            {"field": f.value, "weight": config["weights"].get(f, 0), "impact": "high" if f in config["required"] else "medium"}
            for f in missing
            if f in config["weights"]
        ]
        missing_with_weights.sort(key=lambda x: x["weight"], reverse=True)

        return {
            "platform": platform,
            "score": round(score, 1),
            "detected_fields": [d.field_name for d in detections],
            "missing_fields": missing_with_weights[:5],  # Top 5 missing
            "total_fields_detected": len(detections),
            "recommendation": self._get_recommendation(score, missing_with_weights),
        }

    def _get_recommendation(
        self, score: float, missing_fields: List[Dict]
    ) -> str:
        """Generate recommendation based on completeness score."""
        if score >= 90:
            return "Excellent! Your data is well-matched for high ROAS."
        elif score >= 70:
            top_missing = missing_fields[0]["field"] if missing_fields else "phone"
            return f"Good match rate. Add '{top_missing}' to improve by ~{missing_fields[0]['weight'] if missing_fields else 10}%."
        elif score >= 50:
            return f"Fair match rate. Add {len(missing_fields[:3])} more fields to significantly boost ROAS."
        else:
            return "Low match rate. Critical data gaps are reducing your ad performance."
