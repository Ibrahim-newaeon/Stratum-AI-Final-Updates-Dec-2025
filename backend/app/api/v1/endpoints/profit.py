# =============================================================================
# Stratum AI - Profit ROAS API Endpoints
# =============================================================================
"""
API endpoints for Profit ROAS calculations and COGS management.

Endpoints:
- Products: Product catalog management
- COGS: Cost of goods sold data
- Profit: Profit ROAS calculations and reports
- Margin Rules: Default margin configuration
"""

from datetime import date
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.tenancy.deps import get_current_user, get_db
from app.core.logging import get_logger
from app.models import User
from app.models.profit import (
    MarginType,
    ProductStatus,
    COGSSource,
)
from app.services.profit import (
    ProfitCalculationService,
    COGSService,
    COGSIngestionService,
    ProductCatalogService,
)

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ProductCreate(BaseModel):
    """Schema for creating a product."""
    sku: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    product_type: Optional[str] = None
    base_price: Optional[float] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=3)
    external_ids: Optional[Dict[str, str]] = None
    attributes: Optional[Dict[str, Any]] = None


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    product_type: Optional[str] = None
    base_price: Optional[float] = Field(None, ge=0)
    status: Optional[ProductStatus] = None


class COGSSet(BaseModel):
    """Schema for setting product COGS."""
    cogs: Optional[float] = Field(None, ge=0, description="COGS per unit in dollars")
    cogs_percentage: Optional[float] = Field(None, ge=0, le=100, description="COGS as % of revenue")
    effective_date: Optional[date] = None
    shipping_cost: float = Field(default=0, ge=0)
    handling_cost: float = Field(default=0, ge=0)
    platform_fee: float = Field(default=0, ge=0)
    payment_processing: float = Field(default=0, ge=0)


class MarginRuleCreate(BaseModel):
    """Schema for creating a margin rule."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    margin_type: MarginType = MarginType.PERCENTAGE
    default_margin_percentage: Optional[float] = Field(None, ge=0, le=100)
    default_cogs_percentage: Optional[float] = Field(None, ge=0, le=100)
    category: Optional[str] = None
    subcategory: Optional[str] = None
    platform: Optional[str] = None
    campaign_id: Optional[str] = None
    priority: int = Field(default=100, ge=1, le=1000)


class MarginRuleUpdate(BaseModel):
    """Schema for updating a margin rule."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    default_margin_percentage: Optional[float] = Field(None, ge=0, le=100)
    default_cogs_percentage: Optional[float] = Field(None, ge=0, le=100)
    priority: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None


# =============================================================================
# Product Endpoints
# =============================================================================

@router.post("/products", response_model=Dict[str, Any])
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new product in the catalog."""
    service = ProductCatalogService(db, current_user.tenant_id)

    product = await service.create_product(
        sku=product_data.sku,
        name=product_data.name,
        description=product_data.description,
        category=product_data.category,
        subcategory=product_data.subcategory,
        brand=product_data.brand,
        product_type=product_data.product_type,
        base_price_cents=int(product_data.base_price * 100) if product_data.base_price else None,
        currency=product_data.currency,
        external_ids=product_data.external_ids,
        attributes=product_data.attributes,
    )

    return {
        "status": "success",
        "message": "Product created successfully",
        "product": {
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
        },
    }


@router.get("/products", response_model=Dict[str, Any])
async def list_products(
    status: Optional[ProductStatus] = Query(None),
    category: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List products with optional filters."""
    service = ProductCatalogService(db, current_user.tenant_id)

    result = await service.list_products(
        status=status,
        category=category,
        brand=brand,
        search=search,
        limit=limit,
        offset=offset,
    )

    return {
        "status": "success",
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
        "products": [
            {
                "id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "brand": p.brand,
                "status": p.status.value,
                "base_price": p.base_price_cents / 100 if p.base_price_cents else None,
            }
            for p in result["products"]
        ],
    }


@router.get("/products/categories", response_model=Dict[str, Any])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get all product categories."""
    service = ProductCatalogService(db, current_user.tenant_id)
    categories = await service.get_categories()

    return {
        "status": "success",
        "categories": categories,
    }


@router.get("/products/coverage", response_model=Dict[str, Any])
async def get_cogs_coverage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get COGS data coverage statistics."""
    service = ProductCatalogService(db, current_user.tenant_id)
    coverage = await service.get_cogs_coverage()

    return {
        "status": "success",
        **coverage,
    }


@router.get("/products/missing-cogs", response_model=Dict[str, Any])
async def get_products_missing_cogs(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get products that don't have COGS data."""
    service = ProductCatalogService(db, current_user.tenant_id)
    products = await service.get_products_missing_cogs(limit=limit)

    return {
        "status": "success",
        "count": len(products),
        "products": [
            {
                "id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
            }
            for p in products
        ],
    }


@router.get("/products/{product_id}", response_model=Dict[str, Any])
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get product details with COGS data."""
    service = ProductCatalogService(db, current_user.tenant_id)
    product = await service.get_product_with_cogs(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "status": "success",
        "product": product,
    }


@router.patch("/products/{product_id}", response_model=Dict[str, Any])
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a product."""
    service = ProductCatalogService(db, current_user.tenant_id)

    update_dict = product_data.model_dump(exclude_unset=True)
    if "base_price" in update_dict:
        update_dict["base_price_cents"] = int(update_dict.pop("base_price") * 100) if update_dict["base_price"] else None

    product = await service.update_product(product_id, **update_dict)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "status": "success",
        "message": "Product updated",
    }


@router.delete("/products/{product_id}", response_model=Dict[str, Any])
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete (discontinue) a product."""
    service = ProductCatalogService(db, current_user.tenant_id)
    success = await service.delete_product(product_id)

    if not success:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "status": "success",
        "message": "Product discontinued",
    }


@router.post("/products/import", response_model=Dict[str, Any])
async def import_products(
    file: UploadFile = File(...),
    update_existing: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Import products from CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    service = ProductCatalogService(db, current_user.tenant_id)

    result = await service.import_from_csv(
        file_content=content,
        update_existing=update_existing,
    )

    return {
        "status": "success",
        "message": f"Imported {result['created']} products, updated {result['updated']}",
        **result,
    }


# =============================================================================
# COGS Endpoints
# =============================================================================

@router.post("/products/{product_id}/cogs", response_model=Dict[str, Any])
async def set_product_cogs(
    product_id: UUID,
    cogs_data: COGSSet,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Set COGS for a product."""
    if not cogs_data.cogs and not cogs_data.cogs_percentage:
        raise HTTPException(status_code=400, detail="Must provide either cogs or cogs_percentage")

    service = COGSService(db, current_user.tenant_id)

    margin = await service.set_product_cogs(
        product_id=product_id,
        cogs_cents=int(cogs_data.cogs * 100) if cogs_data.cogs else None,
        cogs_percentage=cogs_data.cogs_percentage,
        effective_date=cogs_data.effective_date,
        shipping_cost_cents=int(cogs_data.shipping_cost * 100),
        handling_cost_cents=int(cogs_data.handling_cost * 100),
        platform_fee_cents=int(cogs_data.platform_fee * 100),
        payment_processing_cents=int(cogs_data.payment_processing * 100),
        source=COGSSource.MANUAL,
        user_id=current_user.id,
    )

    return {
        "status": "success",
        "message": "COGS set successfully",
        "margin_id": str(margin.id),
        "effective_date": margin.effective_date.isoformat(),
    }


@router.get("/products/{product_id}/cogs/history", response_model=Dict[str, Any])
async def get_cogs_history(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get COGS history for a product."""
    service = COGSService(db, current_user.tenant_id)
    history = await service.get_cogs_history(product_id)

    return {
        "status": "success",
        "product_id": str(product_id),
        "history": [
            {
                "id": str(m.id),
                "effective_date": m.effective_date.isoformat(),
                "end_date": m.end_date.isoformat() if m.end_date else None,
                "cogs_cents": m.cogs_cents,
                "cogs_percentage": m.cogs_percentage,
                "total_cogs_cents": m.total_cogs_cents,
                "source": m.source.value,
                "created_at": m.created_at.isoformat(),
            }
            for m in history
        ],
    }


@router.post("/cogs/upload", response_model=Dict[str, Any])
async def upload_cogs(
    file: UploadFile = File(...),
    effective_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Upload COGS data from CSV file.

    Expected columns:
    - sku (required)
    - cogs or cogs_cents or cogs_percentage (one required)
    - shipping_cost (optional)
    - handling_cost (optional)
    - platform_fee (optional)
    - payment_processing (optional)
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    service = COGSIngestionService(db, current_user.tenant_id)

    upload = await service.ingest_csv(
        file_content=content,
        filename=file.filename,
        effective_date=effective_date,
        user_id=current_user.id,
    )

    return {
        "status": "success" if upload.status == "completed" else "error",
        "upload_id": str(upload.id),
        "rows_processed": upload.rows_processed,
        "rows_succeeded": upload.rows_succeeded,
        "rows_failed": upload.rows_failed,
        "products_updated": upload.products_updated,
        "errors": upload.error_details,
    }


@router.get("/cogs/uploads", response_model=Dict[str, Any])
async def get_cogs_uploads(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get COGS upload history."""
    service = COGSIngestionService(db, current_user.tenant_id)
    uploads = await service.get_upload_history(limit=limit)

    return {
        "status": "success",
        "uploads": [
            {
                "id": str(u.id),
                "filename": u.filename,
                "status": u.status,
                "rows_processed": u.rows_processed,
                "rows_succeeded": u.rows_succeeded,
                "rows_failed": u.rows_failed,
                "products_updated": u.products_updated,
                "uploaded_at": u.uploaded_at.isoformat(),
                "processed_at": u.processed_at.isoformat() if u.processed_at else None,
            }
            for u in uploads
        ],
    }


# =============================================================================
# Margin Rules Endpoints
# =============================================================================

@router.post("/margin-rules", response_model=Dict[str, Any])
async def create_margin_rule(
    rule_data: MarginRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a margin rule."""
    if not rule_data.default_margin_percentage and not rule_data.default_cogs_percentage:
        raise HTTPException(
            status_code=400,
            detail="Must provide either default_margin_percentage or default_cogs_percentage"
        )

    service = COGSService(db, current_user.tenant_id)

    rule = await service.create_margin_rule(
        name=rule_data.name,
        description=rule_data.description,
        margin_type=rule_data.margin_type,
        default_margin_percentage=rule_data.default_margin_percentage,
        default_cogs_percentage=rule_data.default_cogs_percentage,
        category=rule_data.category,
        subcategory=rule_data.subcategory,
        platform=rule_data.platform,
        campaign_id=rule_data.campaign_id,
        priority=rule_data.priority,
    )

    return {
        "status": "success",
        "message": "Margin rule created",
        "rule_id": str(rule.id),
    }


@router.get("/margin-rules", response_model=Dict[str, Any])
async def list_margin_rules(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all margin rules."""
    service = COGSService(db, current_user.tenant_id)
    rules = await service.list_margin_rules(active_only=active_only)

    return {
        "status": "success",
        "rules": [
            {
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "priority": r.priority,
                "category": r.category,
                "platform": r.platform,
                "campaign_id": r.campaign_id,
                "margin_type": r.margin_type.value,
                "default_margin_percentage": r.default_margin_percentage,
                "default_cogs_percentage": r.default_cogs_percentage,
                "is_active": r.is_active,
            }
            for r in rules
        ],
    }


@router.patch("/margin-rules/{rule_id}", response_model=Dict[str, Any])
async def update_margin_rule(
    rule_id: UUID,
    rule_data: MarginRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a margin rule."""
    service = COGSService(db, current_user.tenant_id)

    rule = await service.update_margin_rule(
        rule_id,
        **rule_data.model_dump(exclude_unset=True),
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Margin rule not found")

    return {
        "status": "success",
        "message": "Margin rule updated",
    }


@router.delete("/margin-rules/{rule_id}", response_model=Dict[str, Any])
async def delete_margin_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a margin rule."""
    service = COGSService(db, current_user.tenant_id)
    success = await service.delete_margin_rule(rule_id)

    if not success:
        raise HTTPException(status_code=404, detail="Margin rule not found")

    return {
        "status": "success",
        "message": "Margin rule deleted",
    }


# =============================================================================
# Profit ROAS Endpoints
# =============================================================================

@router.get("/profit/roas", response_model=Dict[str, Any])
async def get_profit_roas(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    platform: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    product_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Calculate Profit ROAS for a date range.

    Returns:
    - Revenue ROAS (traditional)
    - Gross Profit ROAS
    - Net Profit ROAS
    - Breakeven analysis
    """
    service = ProfitCalculationService(db, current_user.tenant_id)

    return await service.calculate_profit_roas(
        start_date=start_date,
        end_date=end_date,
        platform=platform,
        campaign_id=campaign_id,
        product_id=product_id,
    )


@router.get("/profit/trend", response_model=Dict[str, Any])
async def get_profit_trend(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    platform: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    granularity: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get Profit ROAS trend over time."""
    service = ProfitCalculationService(db, current_user.tenant_id)

    return await service.get_profit_trend(
        start_date=start_date,
        end_date=end_date,
        platform=platform,
        campaign_id=campaign_id,
        granularity=granularity,
    )


@router.get("/profit/by-product", response_model=Dict[str, Any])
async def get_product_profitability(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    platform: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("gross_profit", regex="^(gross_profit|net_profit|gross_profit_roas)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get profitability breakdown by product."""
    service = ProfitCalculationService(db, current_user.tenant_id)

    return await service.get_product_profitability(
        start_date=start_date,
        end_date=end_date,
        platform=platform,
        limit=limit,
        sort_by=sort_by,
    )


@router.get("/profit/by-campaign", response_model=Dict[str, Any])
async def get_campaign_profitability(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get profitability breakdown by campaign."""
    service = ProfitCalculationService(db, current_user.tenant_id)

    return await service.get_campaign_profitability(
        start_date=start_date,
        end_date=end_date,
        platform=platform,
    )


@router.post("/profit/report", response_model=Dict[str, Any])
async def generate_profit_report(
    start_date: date = Query(..., description="Report start date"),
    end_date: date = Query(..., description="Report end date"),
    report_type: str = Query("custom", regex="^(daily|weekly|monthly|custom)$"),
    platform: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generate and save a profit ROAS report."""
    service = ProfitCalculationService(db, current_user.tenant_id)

    report = await service.generate_profit_report(
        start_date=start_date,
        end_date=end_date,
        report_type=report_type,
        platform=platform,
        campaign_id=campaign_id,
        category=category,
        user_id=current_user.id,
    )

    return {
        "status": "success",
        "report_id": str(report.id),
        "period": {
            "start": report.period_start.isoformat(),
            "end": report.period_end.isoformat(),
        },
        "summary": {
            "total_revenue": report.total_revenue_cents / 100 if report.total_revenue_cents else 0,
            "total_cogs": report.total_cogs_cents / 100 if report.total_cogs_cents else 0,
            "total_gross_profit": report.total_gross_profit_cents / 100 if report.total_gross_profit_cents else 0,
            "total_ad_spend": report.total_ad_spend_cents / 100 if report.total_ad_spend_cents else 0,
            "revenue_roas": report.revenue_roas,
            "gross_profit_roas": report.gross_profit_roas,
            "net_profit_roas": report.net_profit_roas,
            "breakeven_roas": report.breakeven_roas,
            "above_breakeven": report.above_breakeven,
        },
    }
