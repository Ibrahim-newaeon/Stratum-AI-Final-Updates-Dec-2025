# =============================================================================
# Stratum AI - Add ML Prediction Columns
# =============================================================================
"""
Add missing columns to ml_predictions table.

Revision ID: 012_add_ml_prediction_columns
Revises: 011_add_usp_layer_tables
Create Date: 2026-01-05 00:00:00.000000

This migration adds:
- prediction_type: Type of prediction (portfolio_analysis, roas_alerts, etc.)
- input_data: JSONB for complex input data
- prediction_result: JSONB for complex prediction results
- confidence_score: Confidence score for the prediction
- created_at: Timestamp when prediction was created
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012_add_ml_prediction_columns'
down_revision = '011_add_usp_layer_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add prediction_type column (required)
    op.add_column('ml_predictions', sa.Column('prediction_type', sa.String(50), nullable=True))

    # Add input_data JSONB column
    op.add_column('ml_predictions', sa.Column('input_data', postgresql.JSONB(), nullable=True))

    # Add prediction_result JSONB column
    op.add_column('ml_predictions', sa.Column('prediction_result', postgresql.JSONB(), nullable=True))

    # Add confidence_score column
    op.add_column('ml_predictions', sa.Column('confidence_score', sa.Float(), nullable=True))

    # Add created_at column if not exists
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'ml_predictions' AND column_name = 'created_at'
            ) THEN
                ALTER TABLE ml_predictions ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
            END IF;
        END $$;
    """)

    # Update existing rows to have a default prediction_type
    op.execute("UPDATE ml_predictions SET prediction_type = 'campaign_prediction' WHERE prediction_type IS NULL")

    # Make prediction_type required after setting defaults
    op.alter_column('ml_predictions', 'prediction_type', nullable=False)

    # Create index on prediction_type
    op.create_index('ix_predictions_type', 'ml_predictions', ['tenant_id', 'prediction_type'])


def downgrade() -> None:
    op.drop_index('ix_predictions_type')
    op.drop_column('ml_predictions', 'prediction_type')
    op.drop_column('ml_predictions', 'input_data')
    op.drop_column('ml_predictions', 'prediction_result')
    op.drop_column('ml_predictions', 'confidence_score')
