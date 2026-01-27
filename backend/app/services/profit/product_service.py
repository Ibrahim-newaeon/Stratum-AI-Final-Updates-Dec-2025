# =============================================================================
# Stratum AI - Product Catalog Service
# =============================================================================
"""
Service for managing product catalog.

Features:
- Product CRUD operations
- Bulk import from CSV
- Category management
- External ID mapping
"""

import csv
import io
from datetime import UTC, date, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.profit import (
    ProductCatalog,
    ProductMargin,
    ProductStatus,
)

logger = get_logger(__name__)


class ProductCatalogService:
    """
    Service for managing product catalog.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def create_product(
        self,
        sku: str,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        brand: Optional[str] = None,
        product_type: Optional[str] = None,
        base_price_cents: Optional[int] = None,
        currency: str = "USD",
        external_ids: Optional[dict[str, str]] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> ProductCatalog:
        """Create a new product."""
        product = ProductCatalog(
            tenant_id=self.tenant_id,
            sku=sku,
            name=name,
            description=description,
            category=category,
            subcategory=subcategory,
            brand=brand,
            product_type=product_type,
            base_price_cents=base_price_cents,
            currency=currency,
            external_ids=external_ids,
            attributes=attributes,
            status=ProductStatus.ACTIVE,
        )

        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)

        logger.info(f"Created product: {sku} - {name}")
        return product

    async def get_product(self, product_id: UUID) -> Optional[ProductCatalog]:
        """Get a product by ID."""
        result = await self.db.execute(
            select(ProductCatalog).where(
                and_(
                    ProductCatalog.id == product_id,
                    ProductCatalog.tenant_id == self.tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_product_by_sku(self, sku: str) -> Optional[ProductCatalog]:
        """Get a product by SKU."""
        result = await self.db.execute(
            select(ProductCatalog).where(
                and_(
                    ProductCatalog.sku == sku,
                    ProductCatalog.tenant_id == self.tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_products(
        self,
        status: Optional[ProductStatus] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List products with filters."""
        conditions = [ProductCatalog.tenant_id == self.tenant_id]

        if status:
            conditions.append(ProductCatalog.status == status)
        else:
            conditions.append(ProductCatalog.status != ProductStatus.DISCONTINUED)

        if category:
            conditions.append(ProductCatalog.category == category)

        if brand:
            conditions.append(ProductCatalog.brand == brand)

        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    ProductCatalog.sku.ilike(search_pattern),
                    ProductCatalog.name.ilike(search_pattern),
                )
            )

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(ProductCatalog).where(and_(*conditions))
        )
        total = count_result.scalar()

        # Get products
        result = await self.db.execute(
            select(ProductCatalog)
            .where(and_(*conditions))
            .order_by(ProductCatalog.name)
            .limit(limit)
            .offset(offset)
        )
        products = result.scalars().all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "products": list(products),
        }

    async def update_product(
        self,
        product_id: UUID,
        **kwargs,
    ) -> Optional[ProductCatalog]:
        """Update a product."""
        product = await self.get_product(product_id)
        if not product:
            return None

        allowed_fields = [
            "name",
            "description",
            "category",
            "subcategory",
            "brand",
            "product_type",
            "base_price_cents",
            "currency",
            "status",
            "external_ids",
            "attributes",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(product, field, value)

        product.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(product)

        return product

    async def delete_product(self, product_id: UUID) -> bool:
        """Soft delete a product (set status to discontinued)."""
        product = await self.get_product(product_id)
        if not product:
            return False

        product.status = ProductStatus.DISCONTINUED
        product.updated_at = datetime.now(UTC)
        await self.db.commit()

        return True

    async def get_categories(self) -> list[dict[str, Any]]:
        """Get all product categories with counts."""
        result = await self.db.execute(
            select(
                ProductCatalog.category,
                func.count().label("count"),
            )
            .where(
                and_(
                    ProductCatalog.tenant_id == self.tenant_id,
                    ProductCatalog.status != ProductStatus.DISCONTINUED,
                    ProductCatalog.category.isnot(None),
                )
            )
            .group_by(ProductCatalog.category)
            .order_by(ProductCatalog.category)
        )
        rows = result.fetchall()

        return [{"category": r.category, "count": r.count} for r in rows]

    async def get_brands(self) -> list[dict[str, Any]]:
        """Get all brands with counts."""
        result = await self.db.execute(
            select(
                ProductCatalog.brand,
                func.count().label("count"),
            )
            .where(
                and_(
                    ProductCatalog.tenant_id == self.tenant_id,
                    ProductCatalog.status != ProductStatus.DISCONTINUED,
                    ProductCatalog.brand.isnot(None),
                )
            )
            .group_by(ProductCatalog.brand)
            .order_by(ProductCatalog.brand)
        )
        rows = result.fetchall()

        return [{"brand": r.brand, "count": r.count} for r in rows]

    async def import_from_csv(
        self,
        file_content: bytes,
        update_existing: bool = True,
    ) -> dict[str, int]:
        """
        Import products from CSV.

        Expected columns:
        - sku (required)
        - name (required)
        - description (optional)
        - category (optional)
        - subcategory (optional)
        - brand (optional)
        - product_type (optional)
        - price (optional, in dollars)

        Args:
            file_content: CSV file bytes
            update_existing: Whether to update existing products

        Returns:
            Count of created, updated, skipped, failed
        """
        content = file_content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        created = 0
        updated = 0
        skipped = 0
        failed = 0

        for row in reader:
            try:
                sku = row.get("sku", "").strip()
                name = row.get("name", "").strip()

                if not sku or not name:
                    skipped += 1
                    continue

                # Check if exists
                existing = await self.get_product_by_sku(sku)

                if existing:
                    if update_existing:
                        await self.update_product(
                            existing.id,
                            name=name,
                            description=row.get("description"),
                            category=row.get("category"),
                            subcategory=row.get("subcategory"),
                            brand=row.get("brand"),
                            product_type=row.get("product_type"),
                            base_price_cents=int(float(row["price"]) * 100)
                            if row.get("price")
                            else None,
                        )
                        updated += 1
                    else:
                        skipped += 1
                else:
                    await self.create_product(
                        sku=sku,
                        name=name,
                        description=row.get("description"),
                        category=row.get("category"),
                        subcategory=row.get("subcategory"),
                        brand=row.get("brand"),
                        product_type=row.get("product_type"),
                        base_price_cents=int(float(row["price"]) * 100)
                        if row.get("price")
                        else None,
                    )
                    created += 1

            except Exception as e:
                logger.error(f"Failed to import product: {e}")
                failed += 1

        await self.db.commit()

        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
        }

    async def get_product_with_cogs(
        self,
        product_id: UUID,
        as_of_date: Optional[date] = None,
    ) -> Optional[dict[str, Any]]:
        """Get product with current COGS data."""
        if as_of_date is None:
            as_of_date = datetime.now(UTC).date()

        product = await self.get_product(product_id)
        if not product:
            return None

        # Get current margin
        margin_result = await self.db.execute(
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
        margin = margin_result.scalar_one_or_none()

        return {
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "subcategory": product.subcategory,
            "brand": product.brand,
            "product_type": product.product_type,
            "base_price": product.base_price_cents / 100 if product.base_price_cents else None,
            "currency": product.currency,
            "status": product.status.value,
            "cogs": {
                "cogs_cents": margin.cogs_cents if margin else None,
                "cogs_percentage": margin.cogs_percentage if margin else None,
                "total_cogs_cents": margin.total_cogs_cents if margin else None,
                "margin_type": margin.margin_type.value if margin else None,
                "effective_date": margin.effective_date.isoformat() if margin else None,
                "source": margin.source.value if margin else None,
            }
            if margin
            else None,
        }

    async def get_products_missing_cogs(
        self,
        limit: int = 100,
    ) -> list[ProductCatalog]:
        """Get products that don't have COGS data."""
        # Get products with margins
        products_with_margins = select(ProductMargin.product_id).distinct()

        result = await self.db.execute(
            select(ProductCatalog)
            .where(
                and_(
                    ProductCatalog.tenant_id == self.tenant_id,
                    ProductCatalog.status == ProductStatus.ACTIVE,
                    ~ProductCatalog.id.in_(products_with_margins),
                )
            )
            .order_by(ProductCatalog.name)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_cogs_coverage(self) -> dict[str, Any]:
        """Get COGS data coverage statistics."""
        # Total active products
        total_result = await self.db.execute(
            select(func.count())
            .select_from(ProductCatalog)
            .where(
                and_(
                    ProductCatalog.tenant_id == self.tenant_id,
                    ProductCatalog.status == ProductStatus.ACTIVE,
                )
            )
        )
        total = total_result.scalar()

        # Products with COGS
        today = datetime.now(UTC).date()
        with_cogs_result = await self.db.execute(
            select(func.count(func.distinct(ProductMargin.product_id))).where(
                and_(
                    ProductMargin.tenant_id == self.tenant_id,
                    ProductMargin.effective_date <= today,
                    or_(
                        ProductMargin.end_date.is_(None),
                        ProductMargin.end_date >= today,
                    ),
                )
            )
        )
        with_cogs = with_cogs_result.scalar()

        coverage_pct = (with_cogs / total * 100) if total > 0 else 0

        return {
            "total_products": total,
            "products_with_cogs": with_cogs,
            "products_missing_cogs": total - with_cogs,
            "coverage_percentage": round(coverage_pct, 1),
        }
