# =============================================================================
# Stratum AI - Embed Security Service
# =============================================================================
"""
Security utilities for embed widgets.

Implements:
- Content Security Policy (CSP) headers
- X-Frame-Options for clickjacking protection
- CORS configuration for embed endpoints
- Request validation and sanitization
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import re

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse


class EmbedSecurityService:
    """Security service for embed widgets."""

    def __init__(self, signing_key: str):
        self._signing_key = signing_key

    # =========================================================================
    # CSP Headers
    # =========================================================================

    def get_csp_headers(
        self,
        allowed_domains: List[str],
        widget_type: str,
    ) -> Dict[str, str]:
        """
        Generate Content Security Policy headers for embed.

        These headers restrict what the embedded content can do,
        preventing XSS and other injection attacks.
        """
        # Convert domain patterns to CSP format
        frame_ancestors = self._domains_to_csp(allowed_domains)

        # Base CSP directives
        csp_parts = [
            "default-src 'self'",
            f"frame-ancestors {frame_ancestors}",
            "script-src 'self' 'unsafe-inline'",  # Needed for inline widget scripts
            "style-src 'self' 'unsafe-inline'",   # Needed for inline styles
            "img-src 'self' data: https:",        # Allow images from HTTPS
            "font-src 'self' https://fonts.gstatic.com",
            "connect-src 'self'",                  # API calls to self only
            "object-src 'none'",                   # No plugins
            "base-uri 'self'",
            "form-action 'none'",                  # No form submissions
        ]

        csp = "; ".join(csp_parts)

        return {
            "Content-Security-Policy": csp,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": f"ALLOW-FROM {frame_ancestors.split()[0]}",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    def _domains_to_csp(self, domains: List[str]) -> str:
        """Convert domain patterns to CSP frame-ancestors format."""
        csp_domains = []

        for domain in domains:
            # Handle wildcards
            if domain.startswith("*."):
                # *.example.com -> https://*.example.com
                csp_domains.append(f"https://{domain}")
                csp_domains.append(f"http://{domain}")  # Also allow HTTP for dev
            else:
                csp_domains.append(f"https://{domain}")
                csp_domains.append(f"http://{domain}")

        # Always include self
        csp_domains.append("'self'")

        return " ".join(csp_domains)

    # =========================================================================
    # CORS Headers for Embed
    # =========================================================================

    def get_cors_headers(
        self,
        origin: str,
        allowed_domains: List[str],
    ) -> Optional[Dict[str, str]]:
        """
        Generate CORS headers for embed requests.

        Returns None if origin is not allowed.
        """
        # Validate origin against allowed domains
        if not self._is_origin_allowed(origin, allowed_domains):
            return None

        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Embed-Token",
            "Access-Control-Max-Age": "86400",  # 24 hours
            "Access-Control-Allow-Credentials": "false",
        }

    def _is_origin_allowed(self, origin: str, allowed_domains: List[str]) -> bool:
        """Check if origin is in allowed domains list."""
        if not origin:
            return False

        # Extract hostname from origin
        try:
            if "://" in origin:
                hostname = origin.split("://")[1]
            else:
                hostname = origin

            if ":" in hostname:
                hostname = hostname.split(":")[0]

            if "/" in hostname:
                hostname = hostname.split("/")[0]

            hostname = hostname.lower()
        except Exception:
            return False

        # Check against allowed domains
        for pattern in allowed_domains:
            pattern = pattern.lower()

            if hostname == pattern:
                return True

            if pattern.startswith("*."):
                base = pattern[2:]
                if hostname == base or hostname.endswith("." + base):
                    return True

        return False

    # =========================================================================
    # Request Validation
    # =========================================================================

    def validate_embed_request(self, request: Request) -> Dict[str, Any]:
        """
        Validate an incoming embed request.

        Returns validation result with origin and other metadata.
        """
        # Get origin header
        origin = request.headers.get("origin", "")
        referer = request.headers.get("referer", "")

        # If no origin, try to extract from referer
        if not origin and referer:
            try:
                parts = referer.split("/")
                if len(parts) >= 3:
                    origin = f"{parts[0]}//{parts[2]}"
            except Exception:
                pass

        # Get token from header or query param
        token = request.headers.get("X-Embed-Token", "")
        if not token:
            token = request.query_params.get("token", "")

        # Get user agent for analytics
        user_agent = request.headers.get("user-agent", "")
        device_type = self._detect_device_type(user_agent)

        return {
            "origin": origin,
            "token": token,
            "user_agent": user_agent,
            "device_type": device_type,
            "ip": self._get_client_ip(request),
        }

    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent."""
        ua_lower = user_agent.lower()

        if "mobile" in ua_lower or "android" in ua_lower:
            if "tablet" in ua_lower or "ipad" in ua_lower:
                return "tablet"
            return "mobile"

        return "desktop"

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get client IP address, handling proxies."""
        # Check X-Forwarded-For header
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Get first IP (client IP)
            return forwarded.split(",")[0].strip()

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return None

    # =========================================================================
    # Data Signing and Verification
    # =========================================================================

    def sign_widget_data(
        self,
        data: Dict[str, Any],
        token_id: str,
        timestamp: datetime,
    ) -> str:
        """
        Sign widget data for integrity verification.

        The signature ensures data hasn't been tampered with in transit.
        """
        # Create canonical representation
        canonical = json.dumps({
            "data": data,
            "token_id": token_id,
            "timestamp": timestamp.isoformat(),
        }, sort_keys=True, separators=(',', ':'))

        # Create HMAC-SHA256 signature
        signature = hmac.new(
            self._signing_key.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def create_signed_response(
        self,
        data: Dict[str, Any],
        token_id: str,
        ttl_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Create a signed response with expiration.

        The response includes:
        - The actual data
        - Signature for verification
        - Expiration timestamp
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)

        signature = self.sign_widget_data(data, token_id, now)

        return {
            "data": data,
            "signature": signature,
            "signed_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

    # =========================================================================
    # Sanitization
    # =========================================================================

    def sanitize_widget_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize widget configuration before rendering.

        Prevents injection attacks through config values.
        """
        sanitized = {}

        for key, value in config.items():
            if isinstance(value, str):
                # Remove potential script tags and event handlers
                sanitized[key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_widget_config(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_string(v) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_string(self, value: str) -> str:
        """Sanitize a string value."""
        # Remove script tags
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)

        # Remove event handlers
        value = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', value, flags=re.IGNORECASE)

        # Remove javascript: URLs
        value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)

        # Escape HTML entities
        value = value.replace('&', '&amp;')
        value = value.replace('<', '&lt;')
        value = value.replace('>', '&gt;')
        value = value.replace('"', '&quot;')
        value = value.replace("'", '&#x27;')

        return value

    # =========================================================================
    # Response Helpers
    # =========================================================================

    def create_embed_response(
        self,
        data: Dict[str, Any],
        token_id: str,
        allowed_domains: List[str],
        widget_type: str,
        origin: str,
    ) -> Response:
        """
        Create a secure response for embed requests.

        Applies all security headers and signs the data.
        """
        # Create signed response
        signed_data = self.create_signed_response(data, token_id)

        # Get security headers
        csp_headers = self.get_csp_headers(allowed_domains, widget_type)
        cors_headers = self.get_cors_headers(origin, allowed_domains)

        if cors_headers is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin not allowed"
            )

        # Combine headers
        headers = {**csp_headers, **cors_headers}

        # Create response
        response = JSONResponse(
            content=signed_data,
            headers=headers,
        )

        return response
