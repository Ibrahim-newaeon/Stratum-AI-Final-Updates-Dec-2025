# =============================================================================
# Stratum AI - Embed Widget Service
# =============================================================================
"""
Service for managing embed widgets with tier-based branding.

Tier Alignment:
- Starter: Full Stratum branding, 3 widgets, 2 domains
- Professional: Minimal branding, 10 widgets, 10 domains
- Enterprise: White-label (no branding), unlimited
"""

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.tiers import (
    Feature,
    SubscriptionTier,
    get_tier_limit,
    has_feature,
)
from app.models.embed_widgets import (
    BrandingLevel,
    EmbedDomainWhitelist,
    EmbedWidget,
    WidgetSize,
    WidgetType,
)
from app.schemas.embed_widgets import (
    WidgetCreate,
    WidgetUpdate,
)

# Widget size dimensions
WIDGET_DIMENSIONS = {
    WidgetSize.BADGE.value: (120, 40),
    WidgetSize.COMPACT.value: (200, 100),
    WidgetSize.STANDARD.value: (300, 200),
    WidgetSize.LARGE.value: (400, 300),
}


class EmbedWidgetService:
    """Service for managing embed widgets."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # Branding Level Determination
    # =========================================================================

    def get_branding_level_for_tier(self, tier: SubscriptionTier) -> BrandingLevel:
        """Determine branding level based on subscription tier."""
        if has_feature(tier, Feature.EMBED_WIDGETS_WHITELABEL):
            return BrandingLevel.NONE
        elif has_feature(tier, Feature.EMBED_WIDGETS_MINIMAL):
            return BrandingLevel.MINIMAL
        else:
            return BrandingLevel.FULL

    # =========================================================================
    # Widget CRUD
    # =========================================================================

    def create_widget(
        self,
        tenant_id: int,
        data: WidgetCreate,
        tier: SubscriptionTier,
    ) -> EmbedWidget:
        """
        Create a new embed widget.

        Args:
            tenant_id: Tenant ID
            data: Widget creation data
            tier: Current subscription tier

        Returns:
            Created widget

        Raises:
            HTTPException: If limits exceeded or validation fails
        """
        # Check widget limit
        max_widgets = get_tier_limit(tier, "max_embed_widgets")
        current_count = (
            self.db.query(EmbedWidget)
            .filter(
                EmbedWidget.tenant_id == tenant_id,
                EmbedWidget.is_active == True,
            )
            .count()
        )

        if current_count >= max_widgets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_widgets} widgets allowed for {tier.value} tier",
            )

        # Validate custom branding (Enterprise only)
        if data.custom_branding and not has_feature(tier, Feature.EMBED_WIDGETS_WHITELABEL):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Custom branding requires Enterprise tier",
            )

        # Determine branding level
        branding_level = self.get_branding_level_for_tier(tier)

        # Get dimensions
        if data.widget_size == WidgetSize.CUSTOM:
            width = data.custom_width
            height = data.custom_height
        else:
            width, height = WIDGET_DIMENSIONS.get(
                data.widget_size.value, WIDGET_DIMENSIONS[WidgetSize.STANDARD.value]
            )

        # Create widget
        widget = EmbedWidget(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            widget_type=data.widget_type.value,
            widget_size=data.widget_size.value,
            custom_width=width if data.widget_size == WidgetSize.CUSTOM else None,
            custom_height=height if data.widget_size == WidgetSize.CUSTOM else None,
            branding_level=branding_level.value,
            data_scope=data.data_scope.dict() if data.data_scope else {},
            refresh_interval_seconds=data.refresh_interval_seconds,
        )

        # Apply custom branding if Enterprise
        if data.custom_branding and branding_level == BrandingLevel.NONE:
            widget.custom_logo_url = data.custom_branding.custom_logo_url
            widget.custom_accent_color = data.custom_branding.custom_accent_color
            widget.custom_background_color = data.custom_branding.custom_background_color
            widget.custom_text_color = data.custom_branding.custom_text_color

        self.db.add(widget)
        self.db.commit()
        self.db.refresh(widget)

        return widget

    def get_widget(self, tenant_id: int, widget_id: UUID) -> Optional[EmbedWidget]:
        """Get a widget by ID."""
        return (
            self.db.query(EmbedWidget)
            .filter(
                EmbedWidget.id == widget_id,
                EmbedWidget.tenant_id == tenant_id,
            )
            .first()
        )

    def list_widgets(
        self,
        tenant_id: int,
        widget_type: Optional[WidgetType] = None,
        is_active: Optional[bool] = None,
    ) -> list[EmbedWidget]:
        """List widgets for a tenant."""
        query = self.db.query(EmbedWidget).filter(
            EmbedWidget.tenant_id == tenant_id,
        )

        if widget_type:
            query = query.filter(EmbedWidget.widget_type == widget_type.value)

        if is_active is not None:
            query = query.filter(EmbedWidget.is_active == is_active)

        return query.order_by(EmbedWidget.created_at.desc()).all()

    def update_widget(
        self,
        tenant_id: int,
        widget_id: UUID,
        data: WidgetUpdate,
        tier: SubscriptionTier,
    ) -> EmbedWidget:
        """Update an existing widget."""
        widget = self.get_widget(tenant_id, widget_id)

        if not widget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

        # Update fields
        if data.name is not None:
            widget.name = data.name

        if data.description is not None:
            widget.description = data.description

        if data.widget_size is not None:
            widget.widget_size = data.widget_size.value
            if data.widget_size == WidgetSize.CUSTOM:
                widget.custom_width = data.custom_width
                widget.custom_height = data.custom_height

        if data.data_scope is not None:
            widget.data_scope = data.data_scope.dict()

        if data.refresh_interval_seconds is not None:
            widget.refresh_interval_seconds = data.refresh_interval_seconds

        if data.is_active is not None:
            widget.is_active = data.is_active

        # Update custom branding (Enterprise only)
        if data.custom_branding:
            if not has_feature(tier, Feature.EMBED_WIDGETS_WHITELABEL):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Custom branding requires Enterprise tier",
                )

            widget.custom_logo_url = data.custom_branding.custom_logo_url
            widget.custom_accent_color = data.custom_branding.custom_accent_color
            widget.custom_background_color = data.custom_branding.custom_background_color
            widget.custom_text_color = data.custom_branding.custom_text_color

        self.db.commit()
        self.db.refresh(widget)

        return widget

    def delete_widget(self, tenant_id: int, widget_id: UUID) -> None:
        """Delete a widget and its tokens."""
        widget = self.get_widget(tenant_id, widget_id)

        if not widget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

        self.db.delete(widget)
        self.db.commit()

    # =========================================================================
    # Domain Whitelist Management
    # =========================================================================

    def add_domain_to_whitelist(
        self,
        tenant_id: int,
        domain_pattern: str,
        description: Optional[str],
        tier: SubscriptionTier,
    ) -> EmbedDomainWhitelist:
        """Add a domain to the whitelist."""
        # Check domain limit
        max_domains = get_tier_limit(tier, "max_embed_domains")
        current_count = (
            self.db.query(EmbedDomainWhitelist)
            .filter(
                EmbedDomainWhitelist.tenant_id == tenant_id,
                EmbedDomainWhitelist.is_active == True,
            )
            .count()
        )

        if current_count >= max_domains:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_domains} domains allowed for {tier.value} tier",
            )

        # Check if already exists
        existing = (
            self.db.query(EmbedDomainWhitelist)
            .filter(
                EmbedDomainWhitelist.tenant_id == tenant_id,
                EmbedDomainWhitelist.domain_pattern == domain_pattern.lower(),
            )
            .first()
        )

        if existing:
            if existing.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Domain already in whitelist"
                )
            else:
                # Reactivate
                existing.is_active = True
                existing.description = description
                self.db.commit()
                self.db.refresh(existing)
                return existing

        # Create new whitelist entry
        whitelist = EmbedDomainWhitelist(
            tenant_id=tenant_id,
            domain_pattern=domain_pattern.lower(),
            description=description,
        )

        self.db.add(whitelist)
        self.db.commit()
        self.db.refresh(whitelist)

        return whitelist

    def list_whitelisted_domains(self, tenant_id: int) -> list[EmbedDomainWhitelist]:
        """List all whitelisted domains for a tenant."""
        return (
            self.db.query(EmbedDomainWhitelist)
            .filter(
                EmbedDomainWhitelist.tenant_id == tenant_id,
                EmbedDomainWhitelist.is_active == True,
            )
            .order_by(EmbedDomainWhitelist.domain_pattern)
            .all()
        )

    def remove_domain_from_whitelist(
        self,
        tenant_id: int,
        domain_id: UUID,
    ) -> None:
        """Remove a domain from the whitelist."""
        domain = (
            self.db.query(EmbedDomainWhitelist)
            .filter(
                EmbedDomainWhitelist.id == domain_id,
                EmbedDomainWhitelist.tenant_id == tenant_id,
            )
            .first()
        )

        if not domain:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

        # Soft delete
        domain.is_active = False
        self.db.commit()

    # =========================================================================
    # Embed Code Generation
    # =========================================================================

    def generate_embed_code(
        self,
        widget: EmbedWidget,
        token: str,
        base_url: str,
    ) -> dict[str, str]:
        """
        Generate embed code snippets for a widget.

        Returns both iframe and script embed options.
        """
        widget_id = str(widget.id)

        # Get dimensions
        if widget.widget_size == WidgetSize.CUSTOM.value:
            width = widget.custom_width
            height = widget.custom_height
        else:
            width, height = WIDGET_DIMENSIONS.get(
                widget.widget_size, WIDGET_DIMENSIONS[WidgetSize.STANDARD.value]
            )

        # Embed URL
        embed_url = f"{base_url}/embed/v1/widget/{widget_id}"

        # Iframe embed code
        iframe_code = f"""<iframe
  src="{embed_url}?token={token}"
  width="{width}"
  height="{height}"
  frameborder="0"
  sandbox="allow-scripts allow-same-origin"
  loading="lazy"
  title="{widget.name}"
></iframe>"""

        # Script embed code (more flexible)
        script_code = f"""<div id="stratum-widget-{widget_id}"></div>
<script>
(function() {{
  var w = document.createElement('script');
  w.src = '{base_url}/embed/v1/loader.js';
  w.async = true;
  w.dataset.widgetId = '{widget_id}';
  w.dataset.token = '{token}';
  document.head.appendChild(w);
}})();
</script>"""

        # Preview URL (for testing in dashboard)
        preview_url = f"{base_url}/embed/v1/preview/{widget_id}?token={token}"

        # Documentation URL
        docs_url = f"{base_url}/docs/embed-widgets"

        return {
            "iframe_code": iframe_code,
            "script_code": script_code,
            "preview_url": preview_url,
            "documentation_url": docs_url,
        }
