# =============================================================================
# Stratum AI - Embed Token Service
# =============================================================================
"""
Secure token management for embed widgets.

Security Features:
- Cryptographically secure token generation
- Domain binding with wildcard support
- Short-lived tokens with refresh rotation
- Rate limiting per token
- Token hashing (never store plaintext)
- Suspicious activity detection
"""

import hashlib
import hmac
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tiers import (
    SubscriptionTier,
    get_tier_limit,
)
from app.models.embed_widgets import (
    EmbedDomainWhitelist,
    EmbedToken,
    EmbedWidget,
    TokenStatus,
)


class EmbedTokenService:
    """Service for managing embed tokens with security."""

    # Token configuration
    DEFAULT_TOKEN_EXPIRY_DAYS = 30
    DEFAULT_REFRESH_EXPIRY_DAYS = 90
    MAX_TOKENS_PER_WIDGET = 5

    def __init__(self, db: Session):
        self.db = db
        # Secret key for HMAC signatures (should be in settings)
        self._signing_key = getattr(settings, "EMBED_SIGNING_KEY", "stratum-embed-secret-key")

    # =========================================================================
    # Token Generation
    # =========================================================================

    def create_token(
        self,
        tenant_id: int,
        widget_id: UUID,
        allowed_domains: list[str],
        tier: SubscriptionTier,
        expires_in_days: int = DEFAULT_TOKEN_EXPIRY_DAYS,
    ) -> tuple[EmbedToken, str, str]:
        """
        Create a new embed token for a widget.

        Args:
            tenant_id: Tenant ID
            widget_id: Widget ID
            allowed_domains: List of allowed domains (supports wildcards)
            tier: Current subscription tier
            expires_in_days: Token expiration in days

        Returns:
            Tuple of (token_model, plaintext_token, refresh_token)
            Note: Plaintext tokens are only returned once at creation!

        Raises:
            HTTPException: If limits exceeded or validation fails
        """
        # Validate widget exists and belongs to tenant
        widget = (
            self.db.query(EmbedWidget)
            .filter(
                EmbedWidget.id == widget_id,
                EmbedWidget.tenant_id == tenant_id,
            )
            .first()
        )

        if not widget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

        # Check token limit per widget
        existing_tokens = (
            self.db.query(EmbedToken)
            .filter(
                EmbedToken.widget_id == widget_id,
                EmbedToken.status == TokenStatus.ACTIVE.value,
            )
            .count()
        )

        if existing_tokens >= self.MAX_TOKENS_PER_WIDGET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {self.MAX_TOKENS_PER_WIDGET} active tokens per widget",
            )

        # Validate domains against whitelist
        self._validate_domains(tenant_id, allowed_domains, tier)

        # Generate tokens
        full_token, token_prefix, token_hash = EmbedToken.generate_token()
        refresh_token, refresh_hash = EmbedToken.generate_refresh_token()

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        refresh_expires_at = datetime.utcnow() + timedelta(days=self.DEFAULT_REFRESH_EXPIRY_DAYS)

        # Determine rate limit based on tier
        rate_limit = self._get_rate_limit_for_tier(tier)

        # Create token record
        token = EmbedToken(
            tenant_id=tenant_id,
            widget_id=widget_id,
            token_prefix=token_prefix,
            token_hash=token_hash,
            allowed_domains=allowed_domains,
            expires_at=expires_at,
            refresh_token_hash=refresh_hash,
            refresh_expires_at=refresh_expires_at,
            rate_limit_per_minute=rate_limit,
        )

        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)

        # Return token with plaintext (only time it's available!)
        return token, full_token, refresh_token

    def refresh_token(
        self,
        token_id: UUID,
        refresh_token: str,
    ) -> tuple[str, str, datetime]:
        """
        Refresh an embed token using the refresh token.

        Args:
            token_id: Token ID
            refresh_token: Plaintext refresh token

        Returns:
            Tuple of (new_token, new_refresh_token, new_expiry)

        Raises:
            HTTPException: If refresh fails
        """
        token = (
            self.db.query(EmbedToken)
            .filter(
                EmbedToken.id == token_id,
            )
            .first()
        )

        if not token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")

        # Verify refresh token
        refresh_hash = EmbedToken.hash_token(refresh_token)
        if token.refresh_token_hash != refresh_hash:
            # Potential token theft - mark as suspicious
            token.suspicious_activity = True
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # Check refresh token expiry
        if token.refresh_expires_at and token.refresh_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
            )

        # Generate new tokens
        new_full_token, new_prefix, new_hash = EmbedToken.generate_token()
        new_refresh, new_refresh_hash = EmbedToken.generate_refresh_token()

        # Update token record
        token.token_prefix = new_prefix
        token.token_hash = new_hash
        token.refresh_token_hash = new_refresh_hash
        token.expires_at = datetime.utcnow() + timedelta(days=self.DEFAULT_TOKEN_EXPIRY_DAYS)
        token.refresh_expires_at = datetime.utcnow() + timedelta(
            days=self.DEFAULT_REFRESH_EXPIRY_DAYS
        )

        self.db.commit()

        return new_full_token, new_refresh, token.expires_at

    # =========================================================================
    # Token Validation
    # =========================================================================

    def validate_token(
        self,
        token: str,
        origin: str,
    ) -> tuple[EmbedToken, EmbedWidget]:
        """
        Validate an embed token for a request.

        Args:
            token: Plaintext embed token
            origin: Request origin header

        Returns:
            Tuple of (token_model, widget_model)

        Raises:
            HTTPException: If validation fails
        """
        # Hash the provided token
        token_hash = EmbedToken.hash_token(token)

        # Look up token by hash
        db_token = (
            self.db.query(EmbedToken)
            .filter(
                EmbedToken.token_hash == token_hash,
            )
            .first()
        )

        if not db_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # Check token status
        if db_token.status != TokenStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token is {db_token.status}"
            )

        # Check expiration
        if db_token.expires_at < datetime.utcnow():
            db_token.status = TokenStatus.EXPIRED.value
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

        # Validate origin against allowed domains
        if not self._validate_origin(origin, db_token.allowed_domains):
            db_token.suspicious_activity = True
            db_token.total_errors += 1
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed for this token"
            )

        # Check rate limit
        if not self._check_rate_limit(db_token):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
            )

        # Update usage stats
        db_token.last_used_at = datetime.utcnow()
        db_token.last_origin = origin
        db_token.total_requests += 1

        # Get associated widget
        widget = (
            self.db.query(EmbedWidget)
            .filter(
                EmbedWidget.id == db_token.widget_id,
                EmbedWidget.is_active == True,
            )
            .first()
        )

        if not widget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found or inactive"
            )

        # Update widget stats
        widget.total_views += 1
        widget.last_viewed_at = datetime.utcnow()

        self.db.commit()

        return db_token, widget

    def revoke_token(self, tenant_id: int, token_id: UUID) -> None:
        """Revoke an embed token."""
        token = (
            self.db.query(EmbedToken)
            .filter(
                EmbedToken.id == token_id,
                EmbedToken.tenant_id == tenant_id,
            )
            .first()
        )

        if not token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")

        token.status = TokenStatus.REVOKED.value
        self.db.commit()

    # =========================================================================
    # Domain Validation
    # =========================================================================

    def _validate_domains(
        self,
        tenant_id: int,
        domains: list[str],
        tier: SubscriptionTier,
    ) -> None:
        """Validate domains against whitelist and tier limits."""
        # Check domain count limit
        max_domains = get_tier_limit(tier, "max_embed_domains")
        if len(domains) > max_domains:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_domains} domains allowed for {tier.value} tier",
            )

        # Get whitelisted domains for tenant
        whitelist = (
            self.db.query(EmbedDomainWhitelist)
            .filter(
                EmbedDomainWhitelist.tenant_id == tenant_id,
                EmbedDomainWhitelist.is_active == True,
            )
            .all()
        )

        whitelist_patterns = [w.domain_pattern for w in whitelist]

        # Check each domain against whitelist
        for domain in domains:
            domain = domain.lower()
            matched = False

            for pattern in whitelist_patterns:
                if self._domain_matches_pattern(domain, pattern):
                    matched = True
                    break

            if not matched:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Domain '{domain}' is not in your whitelist. Add it first.",
                )

    def _validate_origin(self, origin: str, allowed_domains: list[str]) -> bool:
        """Check if origin matches any allowed domain pattern."""
        if not origin:
            return False

        # Extract hostname from origin
        # Origin format: https://example.com or http://localhost:3000
        try:
            # Remove protocol
            if "://" in origin:
                hostname = origin.split("://")[1]
            else:
                hostname = origin

            # Remove port if present
            if ":" in hostname:
                hostname = hostname.split(":")[0]

            # Remove path if present
            if "/" in hostname:
                hostname = hostname.split("/")[0]

            hostname = hostname.lower()
        except Exception:
            return False

        # Check against allowed domains
        return any(self._domain_matches_pattern(hostname, pattern) for pattern in allowed_domains)

    def _domain_matches_pattern(self, domain: str, pattern: str) -> bool:
        """Check if domain matches a pattern (supports wildcards)."""
        pattern = pattern.lower()
        domain = domain.lower()

        # Direct match
        if domain == pattern:
            return True

        # Wildcard match (*.example.com)
        if pattern.startswith("*."):
            base_domain = pattern[2:]  # Remove *.
            # Match exact subdomain or any deeper subdomain
            if domain == base_domain or domain.endswith("." + base_domain):
                return True

        return False

    # =========================================================================
    # Rate Limiting
    # =========================================================================

    def _check_rate_limit(self, token: EmbedToken) -> bool:
        """Check and update rate limit for token."""
        now = datetime.utcnow()

        # Reset counter if minute has passed
        if (
            token.current_minute_start is None
            or (now - token.current_minute_start).total_seconds() >= 60
        ):
            token.current_minute_start = now
            token.current_minute_requests = 1
            return True

        # Check if under limit
        if token.current_minute_requests < token.rate_limit_per_minute:
            token.current_minute_requests += 1
            return True

        return False

    def _get_rate_limit_for_tier(self, tier: SubscriptionTier) -> int:
        """Get rate limit per minute for tier."""
        limits = {
            SubscriptionTier.STARTER: 60,
            SubscriptionTier.PROFESSIONAL: 300,
            SubscriptionTier.ENTERPRISE: 1000,
        }
        return limits.get(tier, 60)

    # =========================================================================
    # Data Signing
    # =========================================================================

    def sign_data(self, data: dict, token_id: str) -> str:
        """
        Sign widget data with HMAC for integrity verification.

        Args:
            data: Data dictionary to sign
            token_id: Token ID for binding

        Returns:
            HMAC signature
        """
        import json

        # Create canonical representation
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        message = f"{token_id}:{canonical}".encode()

        # Create HMAC signature
        signature = hmac.new(self._signing_key.encode(), message, hashlib.sha256).hexdigest()

        return signature

    def verify_signature(self, data: dict, token_id: str, signature: str) -> bool:
        """Verify data signature."""
        expected = self.sign_data(data, token_id)
        return hmac.compare_digest(expected, signature)
