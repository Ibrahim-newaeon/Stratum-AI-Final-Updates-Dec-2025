"""Add indexes on unindexed foreign-key columns (DB-003).

PostgreSQL does not auto-index foreign keys, so an unindexed FK forces a
sequential scan for every join and every ON DELETE cascade check when the
parent row is removed. This adds a btree index to each FK column that lacked
one (introspected from the live schema). CREATE INDEX IF NOT EXISTS keeps it
idempotent.

Revision ID: 060_add_fk_indexes
Revises: 059_add_autopilot_frozen
"""

from alembic import op

revision = "060_add_fk_indexes"
down_revision = "059_add_autopilot_frozen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_user_id ON api_keys (user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_campaign_draft_ad_account_id ON campaign_draft (ad_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_campaign_draft_approved_by_user_id ON campaign_draft (approved_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_campaign_draft_created_by_user_id ON campaign_draft (created_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_campaign_draft_rejected_by_user_id ON campaign_draft (rejected_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_campaign_draft_submitted_by_user_id ON campaign_draft (submitted_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_campaign_publish_log_published_by_user_id ON campaign_publish_log (published_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cdp_canonical_identities_canonical_identifier_id ON cdp_canonical_identities (canonical_identifier_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_changelog_read_status_changelog_id ON changelog_read_status (changelog_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_assignments_assigned_by ON client_assignments (assigned_by)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_requests_requested_by ON client_requests (requested_by)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_requests_reviewed_by ON client_requests (reviewed_by)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cms_posts_approved_by_id ON cms_posts (approved_by_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cms_posts_locked_by_id ON cms_posts (locked_by_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cms_posts_rejected_by_id ON cms_posts (rejected_by_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cms_posts_reviewed_by_id ON cms_posts (reviewed_by_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cms_posts_submitted_by_id ON cms_posts (submitted_by_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cms_post_tags_tag_id ON cms_post_tags (tag_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cms_post_versions_created_by_id ON cms_post_versions (created_by_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cogs_uploads_uploaded_by_user_id ON cogs_uploads (uploaded_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_creative_assets_campaign_id ON creative_assets (campaign_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_crm_deals_attributed_touchpoint_id ON crm_deals (attributed_touchpoint_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_crm_deals_contact_id ON crm_deals (contact_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_crm_writeback_syncs_triggered_by_user_id ON crm_writeback_syncs (triggered_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_profit_metrics_margin_rule_id ON daily_profit_metrics (margin_rule_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_profit_metrics_product_id ON daily_profit_metrics (product_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_enforcement_audit_logs_user_id ON enforcement_audit_logs (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_actions_queue_applied_by_user_id ON fact_actions_queue (applied_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_actions_queue_approved_by_user_id ON fact_actions_queue (approved_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_actions_queue_created_by_user_id ON fact_actions_queue (created_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_actions_queue_enforcement_confirmed_by_user_id ON fact_actions_queue (enforcement_confirmed_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_invoices_subscription_id ON invoices (subscription_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_landing_pages_published_by_user_id ON landing_pages (published_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_landing_pages_template_id ON landing_pages (template_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_landing_page_subscribers_converted_to_tenant_id ON landing_page_subscribers (converted_to_tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_landing_page_subscribers_reviewed_by_user_id ON landing_page_subscribers (reviewed_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_launch_readiness_events_user_id ON launch_readiness_events (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_launch_readiness_item_state_checked_by_user_id ON launch_readiness_item_state (checked_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ml_predictions_campaign_id ON ml_predictions (campaign_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_model_training_runs_model_id ON model_training_runs (model_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_model_training_runs_triggered_by_user_id ON model_training_runs (triggered_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_newsletter_campaigns_created_by_user_id ON newsletter_campaigns (created_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_newsletter_campaigns_template_id ON newsletter_campaigns (template_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_newsletter_templates_created_by_user_id ON newsletter_templates (created_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pacing_alerts_resolved_by_user_id ON pacing_alerts (resolved_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_product_margins_created_by_user_id ON product_margins (created_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_profit_roas_reports_generated_by_user_id ON profit_roas_reports (generated_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_report_executions_template_id ON report_executions (template_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_report_executions_triggered_by_user_id ON report_executions (triggered_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_report_templates_created_by_user_id ON report_templates (created_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_report_templates_last_modified_by_user_id ON report_templates (last_modified_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_rule_executions_campaign_id ON rule_executions (campaign_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scheduled_reports_created_by_user_id ON scheduled_reports (created_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_subscriptions_plan_id ON subscriptions (plan_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_targets_created_by_user_id ON targets (created_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenant_ad_account_connection_id ON tenant_ad_account (connection_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenant_onboarding_completed_by_user_id ON tenant_onboarding (completed_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenant_platform_connection_granted_by_user_id ON tenant_platform_connection (granted_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_touchpoints_contact_id ON touchpoints (contact_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_trained_attribution_models_created_by_user_id ON trained_attribution_models (created_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_template_id ON whatsapp_messages (template_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_api_keys_user_id")
    op.execute("DROP INDEX IF EXISTS ix_campaign_draft_ad_account_id")
    op.execute("DROP INDEX IF EXISTS ix_campaign_draft_approved_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_campaign_draft_created_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_campaign_draft_rejected_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_campaign_draft_submitted_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_campaign_publish_log_published_by_user_id")
    op.execute(
        "DROP INDEX IF EXISTS ix_cdp_canonical_identities_canonical_identifier_id"
    )
    op.execute("DROP INDEX IF EXISTS ix_changelog_read_status_changelog_id")
    op.execute("DROP INDEX IF EXISTS ix_client_assignments_assigned_by")
    op.execute("DROP INDEX IF EXISTS ix_client_requests_requested_by")
    op.execute("DROP INDEX IF EXISTS ix_client_requests_reviewed_by")
    op.execute("DROP INDEX IF EXISTS ix_cms_posts_approved_by_id")
    op.execute("DROP INDEX IF EXISTS ix_cms_posts_locked_by_id")
    op.execute("DROP INDEX IF EXISTS ix_cms_posts_rejected_by_id")
    op.execute("DROP INDEX IF EXISTS ix_cms_posts_reviewed_by_id")
    op.execute("DROP INDEX IF EXISTS ix_cms_posts_submitted_by_id")
    op.execute("DROP INDEX IF EXISTS ix_cms_post_tags_tag_id")
    op.execute("DROP INDEX IF EXISTS ix_cms_post_versions_created_by_id")
    op.execute("DROP INDEX IF EXISTS ix_cogs_uploads_uploaded_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_creative_assets_campaign_id")
    op.execute("DROP INDEX IF EXISTS ix_crm_deals_attributed_touchpoint_id")
    op.execute("DROP INDEX IF EXISTS ix_crm_deals_contact_id")
    op.execute("DROP INDEX IF EXISTS ix_crm_writeback_syncs_triggered_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_daily_profit_metrics_margin_rule_id")
    op.execute("DROP INDEX IF EXISTS ix_daily_profit_metrics_product_id")
    op.execute("DROP INDEX IF EXISTS ix_enforcement_audit_logs_user_id")
    op.execute("DROP INDEX IF EXISTS ix_fact_actions_queue_applied_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_fact_actions_queue_approved_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_fact_actions_queue_created_by_user_id")
    op.execute(
        "DROP INDEX IF EXISTS ix_fact_actions_queue_enforcement_confirmed_by_user_id"
    )
    op.execute("DROP INDEX IF EXISTS ix_invoices_subscription_id")
    op.execute("DROP INDEX IF EXISTS ix_landing_pages_published_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_landing_pages_template_id")
    op.execute(
        "DROP INDEX IF EXISTS ix_landing_page_subscribers_converted_to_tenant_id"
    )
    op.execute("DROP INDEX IF EXISTS ix_landing_page_subscribers_reviewed_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_launch_readiness_events_user_id")
    op.execute("DROP INDEX IF EXISTS ix_launch_readiness_item_state_checked_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_ml_predictions_campaign_id")
    op.execute("DROP INDEX IF EXISTS ix_model_training_runs_model_id")
    op.execute("DROP INDEX IF EXISTS ix_model_training_runs_triggered_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_newsletter_campaigns_created_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_newsletter_campaigns_template_id")
    op.execute("DROP INDEX IF EXISTS ix_newsletter_templates_created_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_pacing_alerts_resolved_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_product_margins_created_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_profit_roas_reports_generated_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_report_executions_template_id")
    op.execute("DROP INDEX IF EXISTS ix_report_executions_triggered_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_report_templates_created_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_report_templates_last_modified_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_rule_executions_campaign_id")
    op.execute("DROP INDEX IF EXISTS ix_scheduled_reports_created_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_subscriptions_plan_id")
    op.execute("DROP INDEX IF EXISTS ix_targets_created_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_tenant_ad_account_connection_id")
    op.execute("DROP INDEX IF EXISTS ix_tenant_onboarding_completed_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_tenant_platform_connection_granted_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_touchpoints_contact_id")
    op.execute("DROP INDEX IF EXISTS ix_trained_attribution_models_created_by_user_id")
    op.execute("DROP INDEX IF EXISTS ix_whatsapp_messages_template_id")
