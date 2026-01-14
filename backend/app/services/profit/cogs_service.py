# =============================================================================
# Stratum AI - COGS Service
# =============================================================================
"""
Service for managing COGS (Cost of Goods Sold) data.

Features:
- COGS data ingestion (CSV, API)
- Product margin management
- Margin rule configuration
- Historical COGS tracking
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import csv
import io

from sqlalchemy import select, and_, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.profit import (
    ProductCatalog,
    ProductMargin,
    MarginRule,
    COGSUpload,
    MarginType,
    COGSSource,
)

logger = get_logger(__name__)


class COGSService:
    """
    Service for COGS and margin management.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # =========================================================================
    # Product Margin Management
    # =========================================================================

    async def set_product_cogs(
        self,
        product_id: UUID,
        cogs_cents: Optional[int] = None,
        cogs_percentage: Optional[float] = None,
        effective_date: Optional[date] = None,
        shipping_cost_cents: int = 0,
        handling_cost_cents: int = 0,
        platform_fee_cents: int = 0,
        payment_processing_cents: int = 0,
        source: COGSSource = COGSSource.MANUAL,
        user_id: Optional[int] = None,
    ) -> ProductMargin:
        """
        Set COGS for a product.

        Args:
            product_id: Product UUID
            cogs_cents: COGS per unit in cents (mutually exclusive with cogs_percentage)
            cogs_percentage: COGS as percentage of revenue
            effective_date: When this COGS becomes effective
            shipping_cost_cents: Shipping cost per unit
            handling_cost_cents: Handling cost per unit
            platform_fee_cents: Marketplace fee per unit
            payment_processing_cents: Payment processing fee
            source: Data source
            user_id: User making the change

        Returns:
            Created ProductMargin
        """
        if effective_date is None:
            effective_date = date.today()

        # End any existing margin that starts before this date
        await self.db.execute(
            update(ProductMargin)
            .where(
                and_(
                    ProductMargin.product_id == product_id,
                    ProductMargin.effective_date < effective_date,
                    or_(
                        ProductMargin.end_date.is_(None),
                        ProductMargin.end_date >= effective_date,
                    ),
                )
            )
            .values(end_date=effective_date - datetime.timedelta(days=1))
        )

        # Calculate total COGS
        total_cogs = (cogs_cents or 0) + shipping_cost_cents + handling_cost_cents + platform_fee_cents + payment_processing_cents

        # Determine margin type
        margin_type = MarginType.PERCENTAGE if cogs_percentage else MarginType.FIXED_AMOUNT

        margin = ProductMargin(
            tenant_id=self.tenant_id,
            product_id=product_id,
            effective_date=effective_date,
            cogs_cents=cogs_cents,
            cogs_percentage=cogs_percentage,
            margin_type=margin_type,
            shipping_cost_cents=shipping_cost_cents,
            handling_cost_cents=handling_cost_cents,
            platform_fee_cents=platform_fee_cents,
            payment_processing_cents=payment_processing_cents,
            total_cogs_cents=total_cogs if cogs_cents else None,
            source=source,
            created_by_user_id=user_id,
        )

        self.db.add(margin)
        await self.db.commit()
        await self.db.refresh(margin)

        logger.info(f"Set COGS for product {product_id}: {cogs_cents} cents or {cogs_percentage}%")
        return margin

    async def get_product_cogs(
        self,
        product_id: UUID,
        as_of_date: Optional[date] = None,
    ) -> Optional[ProductMargin]:
        """Get current COGS for a product."""
        if as_of_date is None:
            as_of_date = date.today()

        result = await self.db.execute(
            select(ProductMargin)
            .where(
                and_(
                    ProductMargin.product_id == product_id,
                    ProductMargin.effective_date <= as_of_date,
                    or_(
                        ProductMargin.end_date.is_(None),
                        ProductMargin.end_date >= as_of_date,
                    ),
                )
            )
            .order_by(ProductMargin.effective_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_cogs_history(
        self,
        product_id: UUID,
    ) -> List[ProductMargin]:
        """Get COGS history for a product."""
        result = await self.db.execute(
            select(ProductMargin)
            .where(ProductMargin.product_id == product_id)
            .order_by(ProductMargin.effective_date.desc())
        )
        return list(result.scalars().all())

    async def bulk_update_cogs(
        self,
        updates: List[Dict[str, Any]],
        effective_date: Optional[date] = None,
        source: COGSSource = COGSSource.CSV_UPLOAD,
        user_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Bulk update COGS for multiple products.

        Args:
            updates: List of {sku, cogs_cents or cogs_percentage, ...}
            effective_date: Effective date for all updates
            source: Data source
            user_id: User making changes

        Returns:
            Count of updated, skipped, failed
        """
        if effective_date is None:
            effective_date = date.today()

        updated = 0
        skipped = 0
        failed = 0

        for update_data in updates:
            try:
                sku = update_data.get("sku")
                if not sku:
                    skipped += 1
                    continue

                # Find product by SKU
                result = await self.db.execute(
                    select(ProductCatalog).where(
                        and_(
                            ProductCatalog.tenant_id == self.tenant_id,
                            ProductCatalog.sku == sku,
                        )
                    )
                )
                product = result.scalar_one_or_none()

                if not product:
                    skipped += 1
                    continue

                await self.set_product_cogs(
                    product_id=product.id,
                    cogs_cents=update_data.get("cogs_cents"),
                    cogs_percentage=update_data.get("cogs_percentage"),
                    effective_date=effective_date,
                    shipping_cost_cents=update_data.get("shipping_cost_cents", 0),
                    handling_cost_cents=update_data.get("handling_cost_cents", 0),
                    platform_fee_cents=update_data.get("platform_fee_cents", 0),
                    payment_processing_cents=update_data.get("payment_processing_cents", 0),
                    source=source,
                    user_id=user_id,
                )
                updated += 1

            except Exception as e:
                logger.error(f"Failed to update COGS for {update_data}: {e}")
                failed += 1

        await self.db.commit()

        return {
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "total": len(updates),
        }

    # =========================================================================
    # Margin Rules
    # =========================================================================

    async def create_margin_rule(
        self,
        name: str,
        margin_type: MarginType = MarginType.PERCENTAGE,
        default_margin_percentage: Optional[float] = None,
        default_cogs_percentage: Optional[float] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
        priority: int = 100,
        description: Optional[str] = None,
    ) -> MarginRule:
        """Create a margin rule."""
        rule = MarginRule(
            tenant_id=self.tenant_id,
            name=name,
            description=description,
            priority=priority,
            category=category,
            subcategory=subcategory,
            platform=platform,
            campaign_id=campaign_id,
            margin_type=margin_type,
            default_margin_percentage=default_margin_percentage,
            default_cogs_percentage=default_cogs_percentage,
        )

        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)

        logger.info(f"Created margin rule: {name}")
        return rule

    async def list_margin_rules(
        self,
        active_only: bool = True,
    ) -> List[MarginRule]:
        """List all margin rules."""
        conditions = [MarginRule.tenant_id == self.tenant_id]
        if active_only:
            conditions.append(MarginRule.is_active == True)

        result = await self.db.execute(
            select(MarginRule)
            .where(and_(*conditions))
            .order_by(MarginRule.priority)
        )
        return list(result.scalars().all())

    async def update_margin_rule(
        self,
        rule_id: UUID,
        **kwargs,
    ) -> Optional[MarginRule]:
        """Update a margin rule."""
        result = await self.db.execute(
            select(MarginRule).where(
                and_(
                    MarginRule.id == rule_id,
                    MarginRule.tenant_id == self.tenant_id,
                )
            )
        )
        rule = result.scalar_one_or_none()

        if not rule:
            return None

        allowed_fields = [
            "name", "description", "priority", "category", "subcategory",
            "platform", "campaign_id", "margin_type", "default_margin_percentage",
            "default_cogs_percentage", "is_active",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(rule, field, value)

        rule.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(rule)

        return rule

    async def delete_margin_rule(self, rule_id: UUID) -> bool:
        """Delete a margin rule."""
        result = await self.db.execute(
            delete(MarginRule).where(
                and_(
                    MarginRule.id == rule_id,
                    MarginRule.tenant_id == self.tenant_id,
                )
            )
        )
        await self.db.commit()
        return result.rowcount > 0


class COGSIngestionService:
    """
    Service for ingesting COGS data from various sources.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.cogs_service = COGSService(db, tenant_id)

    async def ingest_csv(
        self,
        file_content: bytes,
        filename: str,
        effective_date: Optional[date] = None,
        user_id: Optional[int] = None,
    ) -> COGSUpload:
        """
        Ingest COGS data from CSV file.

        Expected columns:
        - sku (required)
        - cogs or cogs_cents or cogs_percentage (one required)
        - shipping_cost (optional)
        - handling_cost (optional)
        - platform_fee (optional)
        - payment_processing (optional)

        Args:
            file_content: CSV file bytes
            filename: Original filename
            effective_date: Effective date for COGS
            user_id: User uploading

        Returns:
            COGSUpload record with results
        """
        if effective_date is None:
            effective_date = date.today()

        # Create upload record
        upload = COGSUpload(
            tenant_id=self.tenant_id,
            filename=filename,
            file_type="csv",
            source=COGSSource.CSV_UPLOAD,
            status="processing",
            effective_date=effective_date,
            uploaded_by_user_id=user_id,
        )
        self.db.add(upload)
        await self.db.commit()

        try:
            # Parse CSV
            content = file_content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(content))

            updates = []
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    update_data = self._parse_csv_row(row)
                    if update_data:
                        updates.append(update_data)
                except Exception as e:
                    errors.append({"row": row_num, "error": str(e)})

            upload.rows_processed = len(updates) + len(errors)

            # Bulk update COGS
            if updates:
                result = await self.cogs_service.bulk_update_cogs(
                    updates=updates,
                    effective_date=effective_date,
                    source=COGSSource.CSV_UPLOAD,
                    user_id=user_id,
                )
                upload.rows_succeeded = result["updated"]
                upload.rows_failed = result["failed"] + result["skipped"]
                upload.products_updated = result["updated"]

            if errors:
                upload.error_details = errors

            upload.status = "completed"
            upload.processed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Failed to process COGS CSV: {e}")
            upload.status = "failed"
            upload.error_details = [{"error": str(e)}]
            upload.processed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(upload)

        logger.info(f"COGS CSV upload {upload.id}: {upload.rows_succeeded} succeeded, {upload.rows_failed} failed")
        return upload

    def _parse_csv_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Parse a CSV row into COGS update data."""
        sku = row.get("sku", "").strip()
        if not sku:
            return None

        data = {"sku": sku}

        # COGS value (check multiple column names)
        if "cogs_cents" in row and row["cogs_cents"]:
            data["cogs_cents"] = int(float(row["cogs_cents"]))
        elif "cogs" in row and row["cogs"]:
            # Assume dollars, convert to cents
            data["cogs_cents"] = int(float(row["cogs"]) * 100)
        elif "cogs_percentage" in row and row["cogs_percentage"]:
            data["cogs_percentage"] = float(row["cogs_percentage"])
        elif "cogs_pct" in row and row["cogs_pct"]:
            data["cogs_percentage"] = float(row["cogs_pct"])
        else:
            return None  # No COGS data

        # Optional costs
        if "shipping_cost" in row and row["shipping_cost"]:
            data["shipping_cost_cents"] = int(float(row["shipping_cost"]) * 100)
        if "shipping_cost_cents" in row and row["shipping_cost_cents"]:
            data["shipping_cost_cents"] = int(float(row["shipping_cost_cents"]))

        if "handling_cost" in row and row["handling_cost"]:
            data["handling_cost_cents"] = int(float(row["handling_cost"]) * 100)
        if "handling_cost_cents" in row and row["handling_cost_cents"]:
            data["handling_cost_cents"] = int(float(row["handling_cost_cents"]))

        if "platform_fee" in row and row["platform_fee"]:
            data["platform_fee_cents"] = int(float(row["platform_fee"]) * 100)
        if "platform_fee_cents" in row and row["platform_fee_cents"]:
            data["platform_fee_cents"] = int(float(row["platform_fee_cents"]))

        if "payment_processing" in row and row["payment_processing"]:
            data["payment_processing_cents"] = int(float(row["payment_processing"]) * 100)
        if "payment_processing_cents" in row and row["payment_processing_cents"]:
            data["payment_processing_cents"] = int(float(row["payment_processing_cents"]))

        return data

    async def get_upload_history(
        self,
        limit: int = 50,
    ) -> List[COGSUpload]:
        """Get COGS upload history."""
        result = await self.db.execute(
            select(COGSUpload)
            .where(COGSUpload.tenant_id == self.tenant_id)
            .order_by(COGSUpload.uploaded_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_upload_status(self, upload_id: UUID) -> Optional[COGSUpload]:
        """Get status of a specific upload."""
        result = await self.db.execute(
            select(COGSUpload).where(
                and_(
                    COGSUpload.id == upload_id,
                    COGSUpload.tenant_id == self.tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()
