"""
Stratum AI - ML Dataset Generator
=================================
Generates synthetic datasets for machine learning models:
1. Churn Prediction
2. Customer LTV Prediction
3. Campaign Performance Prediction
4. Signal Health Prediction
5. Anomaly Detection

Usage:
    python generate_ml_datasets.py
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Configuration
NUM_CUSTOMERS = 10000
NUM_CAMPAIGNS = 500
NUM_DAYS = 365
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def generate_churn_prediction_dataset():
    """
    Generate dataset for customer churn prediction.

    Features:
    - Customer demographics and account info
    - Behavioral metrics (engagement, activity)
    - Transaction history
    - Support interactions
    - Product usage

    Target: churned (0/1)
    """
    print("Generating Churn Prediction Dataset...")

    data = []

    for i in range(NUM_CUSTOMERS):
        # Customer ID
        customer_id = f"CUST_{i+1:06d}"

        # Account age (days)
        account_age_days = np.random.randint(30, 1500)

        # Subscription tier
        tier = np.random.choice(["starter", "professional", "enterprise"], p=[0.5, 0.35, 0.15])
        tier_value = {"starter": 299, "professional": 799, "enterprise": 2500}[tier]

        # Monthly recurring revenue
        mrr = tier_value * np.random.uniform(0.8, 1.2)

        # Contract type
        contract_type = np.random.choice(["monthly", "annual"], p=[0.6, 0.4])

        # Days until contract renewal
        days_to_renewal = (
            np.random.randint(1, 365) if contract_type == "annual" else np.random.randint(1, 30)
        )

        # Engagement metrics (last 30 days)
        login_frequency = np.random.poisson(15)  # Avg logins per month
        session_duration_avg = np.random.exponential(25)  # Minutes
        pages_viewed = np.random.poisson(50)
        features_used = np.random.randint(1, 20)

        # Activity trends (negative = declining)
        login_trend_30d = np.random.normal(0, 0.3)  # % change
        usage_trend_30d = np.random.normal(0, 0.25)

        # Transaction history
        total_transactions = np.random.poisson(20)
        total_spend = mrr * account_age_days / 30 * np.random.uniform(0.8, 1.1)
        avg_transaction_value = total_spend / max(total_transactions, 1)
        days_since_last_transaction = np.random.exponential(30)

        # Support interactions
        support_tickets_90d = np.random.poisson(2)
        open_tickets = np.random.choice(
            [0, 0, 0, 1, 1, 2, 3], p=[0.5, 0.15, 0.1, 0.1, 0.08, 0.05, 0.02]
        )
        avg_ticket_resolution_hours = np.random.exponential(24) if support_tickets_90d > 0 else 0
        nps_score = np.random.choice(
            range(0, 11), p=[0.02, 0.02, 0.03, 0.03, 0.05, 0.1, 0.15, 0.2, 0.2, 0.12, 0.08]
        )

        # Product usage
        api_calls_30d = np.random.poisson(1000) if tier != "starter" else np.random.poisson(200)
        integrations_active = np.random.randint(1, 8)
        team_members = np.random.randint(1, 15) if tier == "enterprise" else np.random.randint(1, 5)

        # Email engagement
        email_open_rate = np.random.beta(2, 5) * 100  # 0-100%
        email_click_rate = email_open_rate * np.random.uniform(0.1, 0.3)

        # Feature adoption
        onboarding_completed = np.random.choice([0, 1], p=[0.1, 0.9])
        training_sessions_attended = np.random.poisson(1)

        # Billing issues
        failed_payments_90d = np.random.choice(
            [0, 0, 0, 0, 1, 1, 2], p=[0.7, 0.1, 0.05, 0.05, 0.05, 0.03, 0.02]
        )

        # Calculate churn probability based on features
        churn_score = 0

        # High risk factors
        if days_since_last_transaction > 60:
            churn_score += 0.3
        if login_trend_30d < -0.3:
            churn_score += 0.25
        if open_tickets >= 2:
            churn_score += 0.2
        if nps_score <= 5:
            churn_score += 0.15
        if failed_payments_90d >= 1:
            churn_score += 0.2
        if days_to_renewal < 30 and contract_type == "annual":
            churn_score += 0.1
        if usage_trend_30d < -0.4:
            churn_score += 0.2
        if email_open_rate < 10:
            churn_score += 0.1

        # Protective factors
        if tier == "enterprise":
            churn_score -= 0.15
        if account_age_days > 365:
            churn_score -= 0.1
        if integrations_active >= 3:
            churn_score -= 0.15
        if training_sessions_attended >= 2:
            churn_score -= 0.1
        if team_members >= 5:
            churn_score -= 0.1

        # Add noise and clamp
        churn_score = np.clip(churn_score + np.random.normal(0, 0.1), 0, 1)

        # Determine churn (with some randomness)
        churned = 1 if np.random.random() < churn_score else 0

        # Churn date (if churned)
        churn_date = (
            (datetime.now() - timedelta(days=np.random.randint(1, 90))).strftime("%Y-%m-%d")
            if churned
            else None
        )

        data.append(
            {
                "customer_id": customer_id,
                "account_age_days": account_age_days,
                "subscription_tier": tier,
                "mrr": round(mrr, 2),
                "contract_type": contract_type,
                "days_to_renewal": days_to_renewal,
                "login_frequency_30d": login_frequency,
                "avg_session_duration_min": round(session_duration_avg, 2),
                "pages_viewed_30d": pages_viewed,
                "features_used_30d": features_used,
                "login_trend_30d": round(login_trend_30d, 4),
                "usage_trend_30d": round(usage_trend_30d, 4),
                "total_transactions": total_transactions,
                "total_spend": round(total_spend, 2),
                "avg_transaction_value": round(avg_transaction_value, 2),
                "days_since_last_transaction": round(days_since_last_transaction, 1),
                "support_tickets_90d": support_tickets_90d,
                "open_tickets": open_tickets,
                "avg_ticket_resolution_hours": round(avg_ticket_resolution_hours, 2),
                "nps_score": nps_score,
                "api_calls_30d": api_calls_30d,
                "integrations_active": integrations_active,
                "team_members": team_members,
                "email_open_rate": round(email_open_rate, 2),
                "email_click_rate": round(email_click_rate, 2),
                "onboarding_completed": onboarding_completed,
                "training_sessions_attended": training_sessions_attended,
                "failed_payments_90d": failed_payments_90d,
                "churn_probability": round(churn_score, 4),
                "churned": churned,
                "churn_date": churn_date,
            }
        )

    df = pd.DataFrame(data)
    output_path = os.path.join(OUTPUT_DIR, "churn_prediction_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"  Saved: {output_path}")
    print(f"  Records: {len(df)}, Churn Rate: {df['churned'].mean()*100:.1f}%")

    return df


def generate_ltv_prediction_dataset():
    """
    Generate dataset for Customer Lifetime Value prediction.

    Features:
    - Customer attributes
    - Historical purchase behavior
    - Engagement metrics
    - RFM scores

    Target: ltv_12_months (continuous)
    """
    print("Generating LTV Prediction Dataset...")

    data = []

    for i in range(NUM_CUSTOMERS):
        customer_id = f"CUST_{i+1:06d}"

        # Customer type
        customer_type = np.random.choice(["b2b", "b2c"], p=[0.3, 0.7])

        # Acquisition channel
        acquisition_channel = np.random.choice(
            ["organic", "paid_search", "paid_social", "referral", "direct", "email"],
            p=[0.2, 0.25, 0.2, 0.15, 0.1, 0.1],
        )

        # Acquisition cost
        channel_cac = {
            "organic": 0,
            "paid_search": 150,
            "paid_social": 120,
            "referral": 50,
            "direct": 0,
            "email": 30,
        }
        cac = channel_cac[acquisition_channel] * np.random.uniform(0.5, 1.5)

        # Account age
        account_age_days = np.random.randint(90, 1000)

        # RFM Scores
        recency_days = np.random.exponential(30)
        frequency = np.random.poisson(8)
        monetary_avg = np.random.lognormal(5, 1)

        # RFM scoring (1-5 scale)
        recency_score = 5 - min(int(recency_days / 30), 4)
        frequency_score = min(int(frequency / 3) + 1, 5)
        monetary_score = min(int(np.log(monetary_avg + 1) / 2) + 1, 5)

        # First purchase value
        first_purchase_value = monetary_avg * np.random.uniform(0.3, 1.0)

        # Purchase patterns
        total_orders = max(1, frequency + np.random.randint(-2, 5))
        total_revenue = total_orders * monetary_avg * np.random.uniform(0.8, 1.2)
        avg_order_value = total_revenue / total_orders
        max_order_value = avg_order_value * np.random.uniform(1.5, 3.0)

        # Time between purchases
        avg_days_between_orders = account_age_days / max(total_orders, 1)

        # Product diversity
        unique_products_purchased = min(total_orders * np.random.uniform(0.5, 2.0), 50)
        unique_categories = min(unique_products_purchased / 3, 10)

        # Engagement
        website_visits_30d = np.random.poisson(10)
        email_opens_30d = np.random.poisson(5)
        cart_abandonment_rate = np.random.beta(2, 5)

        # Discount usage
        discount_orders_pct = np.random.beta(2, 5)
        avg_discount_amount = monetary_avg * discount_orders_pct * 0.2

        # Returns
        return_rate = np.random.beta(1, 10)

        # Calculate LTV
        # Base on historical behavior and predictive factors
        base_monthly_value = total_revenue / max(account_age_days / 30, 1)

        # Adjust for engagement and trends
        engagement_factor = 1 + (website_visits_30d / 20) * 0.1
        retention_factor = 1 - (recency_days / 100) * 0.05
        frequency_factor = 1 + (frequency / 10) * 0.1

        # 12-month LTV prediction
        ltv_12_months = (
            base_monthly_value * 12 * engagement_factor * retention_factor * frequency_factor
        )
        ltv_12_months *= np.random.uniform(0.8, 1.2)  # Add noise
        ltv_12_months = max(0, ltv_12_months)

        data.append(
            {
                "customer_id": customer_id,
                "customer_type": customer_type,
                "acquisition_channel": acquisition_channel,
                "customer_acquisition_cost": round(cac, 2),
                "account_age_days": account_age_days,
                "recency_days": round(recency_days, 1),
                "frequency": frequency,
                "monetary_avg": round(monetary_avg, 2),
                "recency_score": recency_score,
                "frequency_score": frequency_score,
                "monetary_score": monetary_score,
                "rfm_score": recency_score + frequency_score + monetary_score,
                "first_purchase_value": round(first_purchase_value, 2),
                "total_orders": total_orders,
                "total_revenue": round(total_revenue, 2),
                "avg_order_value": round(avg_order_value, 2),
                "max_order_value": round(max_order_value, 2),
                "avg_days_between_orders": round(avg_days_between_orders, 1),
                "unique_products_purchased": int(unique_products_purchased),
                "unique_categories": int(unique_categories),
                "website_visits_30d": website_visits_30d,
                "email_opens_30d": email_opens_30d,
                "cart_abandonment_rate": round(cart_abandonment_rate, 4),
                "discount_orders_pct": round(discount_orders_pct, 4),
                "avg_discount_amount": round(avg_discount_amount, 2),
                "return_rate": round(return_rate, 4),
                "ltv_12_months": round(ltv_12_months, 2),
            }
        )

    df = pd.DataFrame(data)
    output_path = os.path.join(OUTPUT_DIR, "ltv_prediction_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"  Saved: {output_path}")
    print(f"  Records: {len(df)}, Avg LTV: ${df['ltv_12_months'].mean():,.2f}")

    return df


def generate_campaign_performance_dataset():
    """
    Generate dataset for campaign performance prediction.

    Features:
    - Campaign configuration
    - Audience targeting
    - Creative attributes
    - Historical performance

    Target: roas, conversions, cpa
    """
    print("Generating Campaign Performance Dataset...")

    data = []

    platforms = ["meta", "google", "tiktok", "snapchat"]
    objectives = ["conversions", "traffic", "awareness", "app_installs", "lead_gen"]

    for i in range(NUM_CAMPAIGNS * 30):  # 30 days per campaign
        campaign_id = f"CAMP_{(i // 30) + 1:05d}"
        day_num = i % 30 + 1
        date = (datetime.now() - timedelta(days=30 - day_num)).strftime("%Y-%m-%d")

        # Campaign attributes (consistent within campaign)
        np.random.seed(hash(campaign_id) % (2**32))

        platform = np.random.choice(platforms, p=[0.4, 0.3, 0.2, 0.1])
        objective = np.random.choice(objectives, p=[0.4, 0.2, 0.15, 0.15, 0.1])

        # Budget
        daily_budget = np.random.choice(
            [50, 100, 250, 500, 1000, 2500], p=[0.2, 0.25, 0.25, 0.15, 0.1, 0.05]
        )

        # Bid strategy
        bid_strategy = np.random.choice(
            ["lowest_cost", "cost_cap", "bid_cap", "target_cost"], p=[0.4, 0.3, 0.2, 0.1]
        )

        # Audience size
        audience_size = np.random.lognormal(14, 1.5)  # Log-normal distribution

        # Targeting attributes
        geo_regions = np.random.randint(1, 10)
        age_range_width = np.random.choice([10, 20, 30, 40], p=[0.2, 0.4, 0.3, 0.1])
        interests_count = np.random.randint(0, 15)
        lookalike_used = np.random.choice([0, 1], p=[0.6, 0.4])
        retargeting = np.random.choice([0, 1], p=[0.7, 0.3])

        # Creative attributes
        creative_count = np.random.randint(1, 10)
        video_creative = np.random.choice([0, 1], p=[0.4, 0.6])
        creative_age_days = np.random.randint(1, 60)

        # Reset seed for daily variation
        np.random.seed(42 + i)

        # Daily performance (with variation)
        day_of_week = datetime.strptime(date, "%Y-%m-%d").weekday()
        weekend_factor = 1.1 if day_of_week >= 5 else 1.0

        # Spend
        spend = daily_budget * np.random.uniform(0.7, 1.0) * weekend_factor

        # Platform-specific base CPM
        platform_cpm = {"meta": 12, "google": 8, "tiktok": 6, "snapchat": 10}
        cpm = platform_cpm[platform] * np.random.uniform(0.6, 1.8)

        # Impressions
        impressions = (spend / cpm) * 1000

        # CTR (varies by platform and creative)
        base_ctr = {"meta": 1.2, "google": 3.5, "tiktok": 0.8, "snapchat": 0.5}
        ctr = base_ctr[platform] * np.random.uniform(0.5, 2.0)
        if video_creative:
            ctr *= 1.2

        # Clicks
        clicks = impressions * (ctr / 100)

        # CPC
        cpc = spend / max(clicks, 1)

        # Conversion rate (varies by objective and targeting)
        base_cvr = {
            "conversions": 3.0,
            "traffic": 0.5,
            "awareness": 0.2,
            "app_installs": 5.0,
            "lead_gen": 8.0,
        }
        cvr = base_cvr[objective] * np.random.uniform(0.3, 2.5)
        if retargeting:
            cvr *= 2.0
        if lookalike_used:
            cvr *= 1.3

        # Conversions
        conversions = clicks * (cvr / 100)

        # Revenue (for ROAS calculation)
        avg_order_value = np.random.lognormal(4, 0.8)
        revenue = conversions * avg_order_value

        # ROAS
        roas = revenue / max(spend, 1)

        # CPA
        cpa = spend / max(conversions, 0.1)

        # Quality metrics
        landing_page_score = np.random.uniform(5, 10)
        relevance_score = np.random.uniform(4, 10)

        data.append(
            {
                "campaign_id": campaign_id,
                "date": date,
                "day_of_week": day_of_week,
                "platform": platform,
                "objective": objective,
                "daily_budget": daily_budget,
                "bid_strategy": bid_strategy,
                "audience_size": int(audience_size),
                "geo_regions": geo_regions,
                "age_range_width": age_range_width,
                "interests_count": interests_count,
                "lookalike_used": lookalike_used,
                "retargeting": retargeting,
                "creative_count": creative_count,
                "video_creative": video_creative,
                "creative_age_days": creative_age_days,
                "spend": round(spend, 2),
                "impressions": int(impressions),
                "clicks": int(clicks),
                "ctr": round(ctr, 4),
                "cpc": round(cpc, 2),
                "conversions": round(conversions, 2),
                "cvr": round(cvr, 4),
                "revenue": round(revenue, 2),
                "roas": round(roas, 4),
                "cpa": round(cpa, 2),
                "cpm": round(cpm, 2),
                "landing_page_score": round(landing_page_score, 2),
                "relevance_score": round(relevance_score, 2),
            }
        )

    # Reset seed
    np.random.seed(42)

    df = pd.DataFrame(data)
    output_path = os.path.join(OUTPUT_DIR, "campaign_performance_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"  Saved: {output_path}")
    print(f"  Records: {len(df)}, Avg ROAS: {df['roas'].mean():.2f}")

    return df


def generate_signal_health_dataset():
    """
    Generate dataset for signal health prediction.

    Features:
    - Data source metrics
    - API health indicators
    - Event volume patterns

    Target: health_status (healthy/risk/degraded/critical), health_score
    """
    print("Generating Signal Health Dataset...")

    data = []

    sources = ["meta_capi", "google_analytics", "segment", "shopify", "stripe"]

    for day in range(NUM_DAYS):
        date = (datetime.now() - timedelta(days=NUM_DAYS - day)).strftime("%Y-%m-%d")

        for source in sources:
            # Base metrics vary by source
            source_config = {
                "meta_capi": {"base_emq": 8.5, "base_volume": 50000, "api_stability": 0.98},
                "google_analytics": {"base_emq": 7.5, "base_volume": 100000, "api_stability": 0.99},
                "segment": {"base_emq": 9.0, "base_volume": 30000, "api_stability": 0.97},
                "shopify": {"base_emq": 8.0, "base_volume": 20000, "api_stability": 0.99},
                "stripe": {"base_emq": 9.5, "base_volume": 5000, "api_stability": 0.995},
            }

            config = source_config[source]

            # Time-based patterns
            day_of_week = datetime.strptime(date, "%Y-%m-%d").weekday()
            is_weekend = day_of_week >= 5

            # Simulate occasional issues
            has_incident = np.random.random() < 0.03  # 3% chance of incident
            incident_severity = (
                np.random.choice([1, 2, 3], p=[0.6, 0.3, 0.1]) if has_incident else 0
            )

            # EMQ Score
            emq_score = config["base_emq"] + np.random.normal(0, 0.5)
            if has_incident:
                emq_score -= incident_severity * 1.5
            emq_score = np.clip(emq_score, 0, 10)

            # Event volume
            volume_factor = 0.7 if is_weekend else 1.0
            event_volume = int(config["base_volume"] * volume_factor * np.random.uniform(0.8, 1.2))
            if has_incident:
                event_volume = int(event_volume * (1 - incident_severity * 0.2))

            # Event loss rate
            base_loss_rate = 0.02
            event_loss_rate = base_loss_rate + np.random.exponential(0.01)
            if has_incident:
                event_loss_rate += incident_severity * 0.05
            event_loss_rate = min(event_loss_rate, 0.5)

            # Data freshness (minutes since last sync)
            data_freshness = np.random.exponential(15)
            if has_incident:
                data_freshness += incident_severity * 60

            # API metrics
            api_success_rate = config["api_stability"] - np.random.exponential(0.005)
            if has_incident:
                api_success_rate -= incident_severity * 0.1
            api_success_rate = np.clip(api_success_rate, 0.5, 1.0)

            api_latency_ms = np.random.exponential(100)
            if has_incident:
                api_latency_ms += incident_severity * 500

            api_errors_count = np.random.poisson(5)
            if has_incident:
                api_errors_count += incident_severity * 50

            # Match rate
            match_rate = 0.85 + np.random.normal(0, 0.05)
            if has_incident:
                match_rate -= incident_severity * 0.1
            match_rate = np.clip(match_rate, 0.3, 1.0)

            # Calculate health score (0-100)
            health_score = 100
            health_score -= max(0, (10 - emq_score) * 5)  # EMQ impact
            health_score -= event_loss_rate * 100  # Loss rate impact
            health_score -= max(0, (data_freshness - 60) / 10)  # Freshness impact
            health_score -= (1 - api_success_rate) * 50  # API health impact
            health_score -= min(api_errors_count / 10, 20)  # Error count impact
            health_score = np.clip(health_score, 0, 100)

            # Determine status
            if health_score >= 70:
                health_status = "healthy"
            elif health_score >= 50:
                health_status = "risk"
            elif health_score >= 30:
                health_status = "degraded"
            else:
                health_status = "critical"

            data.append(
                {
                    "date": date,
                    "source": source,
                    "day_of_week": day_of_week,
                    "is_weekend": int(is_weekend),
                    "emq_score": round(emq_score, 2),
                    "event_volume": event_volume,
                    "event_loss_rate": round(event_loss_rate, 4),
                    "data_freshness_min": round(data_freshness, 2),
                    "api_success_rate": round(api_success_rate, 4),
                    "api_latency_ms": round(api_latency_ms, 2),
                    "api_errors_count": api_errors_count,
                    "match_rate": round(match_rate, 4),
                    "has_incident": int(has_incident),
                    "incident_severity": incident_severity,
                    "health_score": round(health_score, 2),
                    "health_status": health_status,
                }
            )

    df = pd.DataFrame(data)
    output_path = os.path.join(OUTPUT_DIR, "signal_health_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"  Saved: {output_path}")
    print(f"  Records: {len(df)}")
    print(f"  Status Distribution: {df['health_status'].value_counts().to_dict()}")

    return df


def generate_anomaly_detection_dataset():
    """
    Generate time series dataset for anomaly detection.

    Features:
    - Multiple metric time series
    - Injected anomalies (spikes, drops, trend changes)

    Target: is_anomaly (0/1), anomaly_type
    """
    print("Generating Anomaly Detection Dataset...")

    data = []

    metrics = ["spend", "impressions", "clicks", "conversions", "revenue", "cpa", "roas"]

    for day in range(NUM_DAYS):
        date = (datetime.now() - timedelta(days=NUM_DAYS - day)).strftime("%Y-%m-%d")
        day_of_week = datetime.strptime(date, "%Y-%m-%d").weekday()

        # Base values with weekly seasonality
        weekend_factor = 0.8 if day_of_week >= 5 else 1.0

        # Add trend
        trend_factor = 1 + (day / NUM_DAYS) * 0.2  # 20% growth over period

        # Base metrics
        base_spend = 5000 * weekend_factor * trend_factor
        base_impressions = 500000 * weekend_factor * trend_factor
        base_clicks = 15000 * weekend_factor * trend_factor
        base_conversions = 300 * weekend_factor * trend_factor
        base_revenue = 15000 * weekend_factor * trend_factor

        # Add normal noise
        spend = base_spend * np.random.uniform(0.85, 1.15)
        impressions = base_impressions * np.random.uniform(0.9, 1.1)
        clicks = base_clicks * np.random.uniform(0.85, 1.15)
        conversions = base_conversions * np.random.uniform(0.8, 1.2)
        revenue = base_revenue * np.random.uniform(0.8, 1.2)

        # Derived metrics
        ctr = (clicks / impressions) * 100
        cvr = (conversions / clicks) * 100
        cpa = spend / max(conversions, 1)
        roas = revenue / spend
        cpm = (spend / impressions) * 1000

        # Inject anomalies (5% of days)
        is_anomaly = 0
        anomaly_type = "none"
        anomaly_metric = None
        anomaly_severity = 0

        if np.random.random() < 0.05:
            is_anomaly = 1
            anomaly_type = np.random.choice(["spike", "drop", "trend_break"])
            anomaly_metric = np.random.choice(metrics)
            anomaly_severity = np.random.choice([1, 2, 3], p=[0.5, 0.35, 0.15])

            multiplier = (
                1 + anomaly_severity * 0.5
                if anomaly_type == "spike"
                else 1 - anomaly_severity * 0.3
            )

            if anomaly_metric == "spend":
                spend *= multiplier
            elif anomaly_metric == "impressions":
                impressions *= multiplier
            elif anomaly_metric == "clicks":
                clicks *= multiplier
            elif anomaly_metric == "conversions":
                conversions *= multiplier
            elif anomaly_metric == "revenue":
                revenue *= multiplier
            elif anomaly_metric == "cpa":
                cpa *= multiplier
            elif anomaly_metric == "roas":
                roas *= multiplier

            # Recalculate derived metrics
            if anomaly_metric in ["impressions", "clicks"]:
                ctr = (clicks / impressions) * 100
            if anomaly_metric in ["clicks", "conversions"]:
                cvr = (conversions / max(clicks, 1)) * 100
            if anomaly_metric in ["spend", "conversions"]:
                cpa = spend / max(conversions, 1)
            if anomaly_metric in ["spend", "revenue"]:
                roas = revenue / max(spend, 1)

        # Calculate z-scores (would normally use rolling window)
        # Simplified: using expected values
        spend_zscore = (spend - base_spend) / (base_spend * 0.1)
        impressions_zscore = (impressions - base_impressions) / (base_impressions * 0.1)
        clicks_zscore = (clicks - base_clicks) / (base_clicks * 0.1)
        conversions_zscore = (conversions - base_conversions) / (base_conversions * 0.15)
        revenue_zscore = (revenue - base_revenue) / (base_revenue * 0.15)

        data.append(
            {
                "date": date,
                "day_of_week": day_of_week,
                "spend": round(spend, 2),
                "impressions": int(impressions),
                "clicks": int(clicks),
                "conversions": round(conversions, 2),
                "revenue": round(revenue, 2),
                "ctr": round(ctr, 4),
                "cvr": round(cvr, 4),
                "cpa": round(cpa, 2),
                "roas": round(roas, 4),
                "cpm": round(cpm, 2),
                "spend_zscore": round(spend_zscore, 4),
                "impressions_zscore": round(impressions_zscore, 4),
                "clicks_zscore": round(clicks_zscore, 4),
                "conversions_zscore": round(conversions_zscore, 4),
                "revenue_zscore": round(revenue_zscore, 4),
                "is_anomaly": is_anomaly,
                "anomaly_type": anomaly_type,
                "anomaly_metric": anomaly_metric if anomaly_metric else "",
                "anomaly_severity": anomaly_severity,
            }
        )

    df = pd.DataFrame(data)
    output_path = os.path.join(OUTPUT_DIR, "anomaly_detection_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"  Saved: {output_path}")
    print(f"  Records: {len(df)}, Anomaly Rate: {df['is_anomaly'].mean()*100:.1f}%")

    return df


def generate_data_dictionary():
    """Generate data dictionary for all datasets."""
    print("Generating Data Dictionary...")

    dictionary = [
        # Churn Prediction
        {
            "dataset": "churn_prediction",
            "field": "customer_id",
            "type": "string",
            "description": "Unique customer identifier",
        },
        {
            "dataset": "churn_prediction",
            "field": "account_age_days",
            "type": "int",
            "description": "Days since account creation",
        },
        {
            "dataset": "churn_prediction",
            "field": "subscription_tier",
            "type": "categorical",
            "description": "Subscription plan: starter, professional, enterprise",
        },
        {
            "dataset": "churn_prediction",
            "field": "mrr",
            "type": "float",
            "description": "Monthly recurring revenue",
        },
        {
            "dataset": "churn_prediction",
            "field": "login_frequency_30d",
            "type": "int",
            "description": "Number of logins in last 30 days",
        },
        {
            "dataset": "churn_prediction",
            "field": "login_trend_30d",
            "type": "float",
            "description": "Login frequency change rate",
        },
        {
            "dataset": "churn_prediction",
            "field": "nps_score",
            "type": "int",
            "description": "Net Promoter Score (0-10)",
        },
        {
            "dataset": "churn_prediction",
            "field": "churned",
            "type": "binary",
            "description": "Target: 1 if churned, 0 otherwise",
        },
        # LTV Prediction
        {
            "dataset": "ltv_prediction",
            "field": "customer_id",
            "type": "string",
            "description": "Unique customer identifier",
        },
        {
            "dataset": "ltv_prediction",
            "field": "rfm_score",
            "type": "int",
            "description": "Combined RFM score (3-15)",
        },
        {
            "dataset": "ltv_prediction",
            "field": "total_revenue",
            "type": "float",
            "description": "Total historical revenue",
        },
        {
            "dataset": "ltv_prediction",
            "field": "ltv_12_months",
            "type": "float",
            "description": "Target: Predicted 12-month LTV",
        },
        # Campaign Performance
        {
            "dataset": "campaign_performance",
            "field": "campaign_id",
            "type": "string",
            "description": "Unique campaign identifier",
        },
        {
            "dataset": "campaign_performance",
            "field": "platform",
            "type": "categorical",
            "description": "Ad platform: meta, google, tiktok, snapchat",
        },
        {
            "dataset": "campaign_performance",
            "field": "objective",
            "type": "categorical",
            "description": "Campaign objective",
        },
        {
            "dataset": "campaign_performance",
            "field": "roas",
            "type": "float",
            "description": "Target: Return on Ad Spend",
        },
        {
            "dataset": "campaign_performance",
            "field": "cpa",
            "type": "float",
            "description": "Target: Cost per Acquisition",
        },
        # Signal Health
        {
            "dataset": "signal_health",
            "field": "source",
            "type": "categorical",
            "description": "Data source name",
        },
        {
            "dataset": "signal_health",
            "field": "emq_score",
            "type": "float",
            "description": "Event Match Quality score (0-10)",
        },
        {
            "dataset": "signal_health",
            "field": "health_score",
            "type": "float",
            "description": "Overall health score (0-100)",
        },
        {
            "dataset": "signal_health",
            "field": "health_status",
            "type": "categorical",
            "description": "Target: healthy, risk, degraded, critical",
        },
        # Anomaly Detection
        {
            "dataset": "anomaly_detection",
            "field": "date",
            "type": "date",
            "description": "Date of observation",
        },
        {
            "dataset": "anomaly_detection",
            "field": "spend_zscore",
            "type": "float",
            "description": "Z-score of spend metric",
        },
        {
            "dataset": "anomaly_detection",
            "field": "is_anomaly",
            "type": "binary",
            "description": "Target: 1 if anomaly detected",
        },
        {
            "dataset": "anomaly_detection",
            "field": "anomaly_type",
            "type": "categorical",
            "description": "Type: spike, drop, trend_break",
        },
    ]

    df = pd.DataFrame(dictionary)
    output_path = os.path.join(OUTPUT_DIR, "data_dictionary.csv")
    df.to_csv(output_path, index=False)
    print(f"  Saved: {output_path}")

    return df


def main():
    """Generate all ML datasets."""
    print("=" * 60)
    print("Stratum AI - ML Dataset Generator")
    print("=" * 60)
    print()

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate all datasets
    generate_churn_prediction_dataset()
    print()

    generate_ltv_prediction_dataset()
    print()

    generate_campaign_performance_dataset()
    print()

    generate_signal_health_dataset()
    print()

    generate_anomaly_detection_dataset()
    print()

    generate_data_dictionary()
    print()

    print("=" * 60)
    print("All datasets generated successfully!")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
