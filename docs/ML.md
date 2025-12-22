# Stratum AI - Machine Learning Documentation

## Overview

Stratum AI includes an integrated ML engine for ROAS optimization, conversion prediction, budget simulation, and creative fatigue analysis. The system supports both local models (scikit-learn, XGBoost) and cloud-based inference (Google Vertex AI).

---

## ML Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ML PIPELINE ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Raw Data   │───►│   Feature    │───►│    Model     │───►│  Predictions │
│  (PostgreSQL)│    │  Engineering │    │  Inference   │    │   (Cache)    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                            │                   │
                            ▼                   ▼
                    ┌──────────────┐    ┌──────────────┐
                    │   Training   │    │  ML Models   │
                    │   Pipeline   │    │   Storage    │
                    └──────────────┘    └──────────────┘
```

---

## Module Structure

```
backend/app/ml/
├── __init__.py
├── inference.py           # Model inference wrapper
├── data_loader.py         # Training data preparation
├── train.py               # Model training scripts
├── conversion_predictor.py # Conversion prediction model
├── forecaster.py          # Revenue/performance forecasting
├── roas_optimizer.py      # ROAS optimization engine
└── simulator.py           # Budget & performance simulator

ml_service/models/
├── roas_predictor.joblib      # ROAS forecasting model
├── conversion_predictor.joblib # Conversion prediction
├── anomaly_detector.joblib    # Anomaly detection
└── fatigue_scorer.joblib      # Creative fatigue scoring
```

---

## ML Models

### 1. ROAS Predictor

Forecasts Return on Ad Spend for campaigns.

**Algorithm:** XGBoost Regressor

**Input Features:**
```python
features = [
    'historical_roas_7d',      # 7-day rolling ROAS
    'historical_roas_30d',     # 30-day rolling ROAS
    'spend_velocity',          # Daily spend rate
    'ctr',                     # Click-through rate
    'conversion_rate',         # Conversion rate
    'impressions_growth',      # Impressions trend
    'platform_encoded',        # One-hot encoded platform
    'day_of_week',             # Day of week (0-6)
    'season_encoded',          # Season (Q1-Q4)
    'audience_size',           # Target audience size
    'creative_fatigue_score',  # Asset fatigue
]
```

**Output:**
```python
{
    "predicted_roas": 3.25,
    "confidence_lower": 2.90,
    "confidence_upper": 3.60,
    "trend": "improving",        # improving, stable, declining
    "recommendation": "Increase budget by 15%"
}
```

**Model Code:**
```python
# backend/app/ml/roas_optimizer.py

class ROASOptimizer:
    def __init__(self, model_path: str = None):
        self.model = self._load_model(model_path)
        self.scaler = StandardScaler()

    def _load_model(self, path: str):
        if path and Path(path).exists():
            return joblib.load(path)
        return self._create_default_model()

    def _create_default_model(self):
        return XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='reg:squarederror'
        )

    def predict(self, campaign_data: dict) -> dict:
        features = self._extract_features(campaign_data)
        scaled_features = self.scaler.transform([features])

        prediction = self.model.predict(scaled_features)[0]

        # Calculate confidence interval
        predictions = []
        for estimator in self.model.estimators_:
            pred = estimator.predict(scaled_features)[0]
            predictions.append(pred)

        return {
            "predicted_roas": float(prediction),
            "confidence_lower": float(np.percentile(predictions, 10)),
            "confidence_upper": float(np.percentile(predictions, 90)),
            "trend": self._calculate_trend(campaign_data),
            "recommendation": self._generate_recommendation(prediction, campaign_data)
        }

    def _extract_features(self, data: dict) -> list:
        return [
            data.get('historical_roas_7d', 0),
            data.get('historical_roas_30d', 0),
            data.get('spend_velocity', 0),
            data.get('ctr', 0),
            data.get('conversion_rate', 0),
            data.get('impressions_growth', 0),
            self._encode_platform(data.get('platform', 'meta')),
            data.get('day_of_week', 0),
            self._encode_season(data.get('date')),
            data.get('audience_size', 0),
            data.get('creative_fatigue_score', 0),
        ]
```

---

### 2. Conversion Predictor

Predicts probability of conversion based on user signals.

**Algorithm:** Gradient Boosting Classifier

**Input Features:**
```python
features = [
    'session_duration',        # Time on site
    'pages_viewed',            # Number of pages
    'cart_value',              # Cart total
    'items_in_cart',           # Number of items
    'time_since_last_visit',   # Days since last visit
    'previous_purchases',      # Historical purchase count
    'device_type',             # mobile, desktop, tablet
    'traffic_source',          # organic, paid, direct, social
    'user_segment',            # new, returning, high_value
]
```

**Output:**
```python
{
    "conversion_probability": 0.72,
    "confidence": 0.85,
    "top_factors": [
        {"factor": "cart_value", "impact": 0.35},
        {"factor": "previous_purchases", "impact": 0.25},
        {"factor": "session_duration", "impact": 0.20}
    ]
}
```

**Model Code:**
```python
# backend/app/ml/conversion_predictor.py

class ConversionPredictor:
    def __init__(self):
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1
        )
        self.feature_names = [
            'session_duration', 'pages_viewed', 'cart_value',
            'items_in_cart', 'time_since_last_visit',
            'previous_purchases', 'device_type_encoded',
            'traffic_source_encoded', 'user_segment_encoded'
        ]

    def predict(self, user_data: dict) -> dict:
        features = self._prepare_features(user_data)

        # Get probability
        probabilities = self.model.predict_proba([features])[0]
        conversion_prob = probabilities[1]

        # Get feature importances
        importances = self.model.feature_importances_
        top_factors = self._get_top_factors(features, importances)

        return {
            "conversion_probability": float(conversion_prob),
            "confidence": float(max(probabilities)),
            "top_factors": top_factors
        }

    def _get_top_factors(self, features: list, importances: list) -> list:
        factors = []
        for i, (name, imp) in enumerate(zip(self.feature_names, importances)):
            factors.append({
                "factor": name,
                "impact": float(imp),
                "value": features[i]
            })

        factors.sort(key=lambda x: x['impact'], reverse=True)
        return factors[:5]
```

---

### 3. Budget Simulator

Simulates campaign performance under different budget scenarios.

**Algorithm:** Monte Carlo Simulation + Linear Regression

**Input:**
```python
{
    "campaign_id": 123,
    "base_budget": 10000,
    "scenarios": [
        {"name": "+20% Budget", "budget_change_percent": 20},
        {"name": "-20% Budget", "budget_change_percent": -20},
        {"name": "+50% Budget", "budget_change_percent": 50}
    ],
    "time_horizon_days": 30,
    "simulations": 1000  # Monte Carlo iterations
}
```

**Output:**
```python
{
    "baseline": {
        "spend": 10000,
        "revenue": 32000,
        "roas": 3.2,
        "conversions": 400
    },
    "scenarios": [
        {
            "name": "+20% Budget",
            "spend": 12000,
            "revenue": 37200,
            "roas": 3.1,
            "conversions": 465,
            "marginal_roas": 2.6,
            "confidence_interval": [34500, 39900]
        },
        {
            "name": "-20% Budget",
            "spend": 8000,
            "revenue": 27200,
            "roas": 3.4,
            "conversions": 340,
            "marginal_roas": 2.4,
            "confidence_interval": [25000, 29400]
        }
    ]
}
```

**Model Logic:**
```python
# backend/app/ml/simulator.py

class BudgetSimulator:
    def __init__(self):
        self.diminishing_returns_factor = 0.85  # Budget efficiency decay

    def simulate(
        self,
        campaign: Campaign,
        scenarios: list[dict],
        days: int = 30,
        iterations: int = 1000
    ) -> dict:
        baseline = self._calculate_baseline(campaign, days)

        results = []
        for scenario in scenarios:
            change = scenario['budget_change_percent'] / 100
            new_budget = baseline['spend'] * (1 + change)

            # Monte Carlo simulation
            simulated_revenues = []
            for _ in range(iterations):
                revenue = self._simulate_revenue(
                    campaign, new_budget, days
                )
                simulated_revenues.append(revenue)

            avg_revenue = np.mean(simulated_revenues)
            marginal_spend = new_budget - baseline['spend']
            marginal_revenue = avg_revenue - baseline['revenue']

            results.append({
                "name": scenario['name'],
                "spend": new_budget,
                "revenue": avg_revenue,
                "roas": avg_revenue / new_budget,
                "conversions": int(avg_revenue / campaign.avg_order_value),
                "marginal_roas": marginal_revenue / marginal_spend if marginal_spend > 0 else 0,
                "confidence_interval": [
                    np.percentile(simulated_revenues, 5),
                    np.percentile(simulated_revenues, 95)
                ]
            })

        return {"baseline": baseline, "scenarios": results}

    def _simulate_revenue(self, campaign, budget, days):
        """Single simulation run with stochastic elements."""
        # Base conversion rate with noise
        base_cvr = campaign.conversion_rate * (1 + np.random.normal(0, 0.1))

        # Diminishing returns on budget increase
        budget_ratio = budget / campaign.current_daily_budget
        efficiency = budget_ratio ** self.diminishing_returns_factor

        # Calculate expected revenue
        expected_conversions = (
            (budget / campaign.cpc) *  # Clicks from budget
            base_cvr *                  # Conversion rate
            efficiency                   # Diminishing returns
        )

        revenue = expected_conversions * campaign.avg_order_value
        return revenue * days
```

---

### 4. Creative Fatigue Scorer

Detects when creative assets become less effective.

**Algorithm:** Time-series analysis + Performance decay detection

**Input Features:**
```python
features = [
    'days_in_rotation',        # Days since first use
    'total_impressions',       # Cumulative impressions
    'frequency',               # Average frequency per user
    'ctr_trend_7d',            # CTR change over 7 days
    'ctr_trend_30d',           # CTR change over 30 days
    'engagement_decay_rate',   # Rate of engagement decline
]
```

**Output:**
```python
{
    "fatigue_score": 72,           # 0-100 (higher = more fatigued)
    "fatigue_level": "high",       # low, medium, high, critical
    "days_until_critical": 5,
    "recommendation": "Replace creative within 5 days",
    "suggested_actions": [
        "Rotate to new creative",
        "Reduce frequency cap",
        "Narrow audience targeting"
    ]
}
```

**Scoring Logic:**
```python
# backend/app/ml/fatigue_scorer.py

class FatigueScorer:
    def __init__(self):
        self.thresholds = {
            'low': 30,
            'medium': 50,
            'high': 70,
            'critical': 85
        }

    def calculate_score(self, asset: CreativeAsset) -> dict:
        # Component scores
        age_score = self._age_score(asset.days_in_rotation)
        frequency_score = self._frequency_score(asset.avg_frequency)
        ctr_decay_score = self._ctr_decay_score(asset)
        engagement_score = self._engagement_decay_score(asset)

        # Weighted combination
        fatigue_score = (
            age_score * 0.2 +
            frequency_score * 0.25 +
            ctr_decay_score * 0.35 +
            engagement_score * 0.2
        )

        fatigue_level = self._get_level(fatigue_score)
        days_until_critical = self._estimate_critical_days(asset, fatigue_score)

        return {
            "fatigue_score": round(fatigue_score, 1),
            "fatigue_level": fatigue_level,
            "days_until_critical": days_until_critical,
            "recommendation": self._get_recommendation(fatigue_level),
            "suggested_actions": self._get_actions(fatigue_level, asset)
        }

    def _ctr_decay_score(self, asset) -> float:
        """Calculate score based on CTR decline."""
        if asset.initial_ctr == 0:
            return 50

        decline = (asset.initial_ctr - asset.current_ctr) / asset.initial_ctr
        return min(100, max(0, decline * 200))

    def _frequency_score(self, frequency: float) -> float:
        """Higher frequency = higher fatigue."""
        if frequency < 2:
            return 10
        elif frequency < 4:
            return 30
        elif frequency < 6:
            return 60
        elif frequency < 8:
            return 80
        else:
            return 95
```

---

## Data Quality & EMQ

### Event Matching Quality (EMQ)

Scores the quality of conversion events for attribution.

```python
# backend/app/services/capi/data_quality.py

class DataQualityAnalyzer:
    """Analyzes event data quality for CAPI."""

    FIELD_WEIGHTS = {
        'meta': {
            'email': 0.25,
            'phone': 0.20,
            'click_id': 0.20,
            'ip_address': 0.15,
            'user_agent': 0.10,
            'external_id': 0.10,
        },
        'google': {
            'email': 0.25,
            'phone': 0.20,
            'gclid': 0.25,
            'ip_address': 0.10,
            'user_agent': 0.10,
            'external_id': 0.10,
        },
    }

    QUALITY_LEVELS = {
        'excellent': (80, 100),
        'good': (60, 79),
        'fair': (40, 59),
        'poor': (0, 39),
    }

    def analyze(self, event: dict, platform: str) -> dict:
        weights = self.FIELD_WEIGHTS.get(platform, self.FIELD_WEIGHTS['meta'])
        score = 0
        missing_fields = []

        for field, weight in weights.items():
            if self._has_valid_value(event, field):
                score += weight * 100
            else:
                missing_fields.append(field)

        level = self._get_quality_level(score)
        roas_impact = self._estimate_roas_impact(score)

        return {
            "score": round(score, 1),
            "level": level,
            "missing_fields": missing_fields,
            "roas_impact_estimate": roas_impact,
            "recommendations": self._get_recommendations(missing_fields)
        }

    def _estimate_roas_impact(self, score: float) -> str:
        if score >= 80:
            return "~95% attribution accuracy"
        elif score >= 60:
            return "~80% attribution accuracy"
        elif score >= 40:
            return "~60% attribution accuracy"
        else:
            return "<40% attribution accuracy - significant loss"
```

---

## Training Pipeline

### Training Workflow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Data Export │───►│  Feature     │───►│   Model      │
│  (Celery)    │    │  Engineering │    │   Training   │
└──────────────┘    └──────────────┘    └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Validation  │
                                        │  & Metrics   │
                                        └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Model       │
                                        │  Deployment  │
                                        └──────────────┘
```

### Training Script

```python
# backend/app/ml/train.py

class ModelTrainer:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.models_path = Path(settings.ml_models_path)

    async def train_roas_model(self, tenant_id: int) -> dict:
        """Train ROAS prediction model for a tenant."""

        # 1. Load training data
        data = await self._load_campaign_data(tenant_id)

        if len(data) < 100:
            raise ValueError("Insufficient data for training (min 100 campaigns)")

        # 2. Feature engineering
        X, y = self._prepare_features(data)

        # 3. Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # 4. Train model
        model = XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='reg:squarederror'
        )
        model.fit(X_train, y_train)

        # 5. Evaluate
        y_pred = model.predict(X_test)
        metrics = {
            "mae": mean_absolute_error(y_test, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
            "r2": r2_score(y_test, y_pred)
        }

        # 6. Save model
        model_path = self.models_path / f"roas_predictor_t{tenant_id}.joblib"
        joblib.dump(model, model_path)

        return {
            "status": "success",
            "model_path": str(model_path),
            "metrics": metrics,
            "training_samples": len(X_train),
            "test_samples": len(X_test)
        }
```

---

## Model Serving

### Inference Service

```python
# backend/app/ml/inference.py

class InferenceService:
    def __init__(self):
        self.models = {}
        self.cache = Redis(settings.redis_url)
        self.cache_ttl = 1800  # 30 minutes

    async def get_prediction(
        self,
        model_type: str,
        input_data: dict,
        tenant_id: int
    ) -> dict:
        # Check cache first
        cache_key = self._make_cache_key(model_type, input_data)
        cached = await self.cache.get(cache_key)
        if cached:
            return json.loads(cached)

        # Load model
        model = self._get_model(model_type, tenant_id)

        # Make prediction
        if model_type == 'roas':
            predictor = ROASOptimizer(model)
            result = predictor.predict(input_data)
        elif model_type == 'conversion':
            predictor = ConversionPredictor(model)
            result = predictor.predict(input_data)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Cache result
        await self.cache.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(result)
        )

        return result

    def _get_model(self, model_type: str, tenant_id: int):
        key = f"{model_type}_{tenant_id}"

        if key not in self.models:
            path = Path(settings.ml_models_path) / f"{model_type}_t{tenant_id}.joblib"
            if not path.exists():
                # Fall back to default model
                path = Path(settings.ml_models_path) / f"{model_type}_default.joblib"

            self.models[key] = joblib.load(path)

        return self.models[key]
```

---

## Celery Tasks

### ML Background Tasks

```python
# backend/app/workers/tasks.py

@celery_app.task(queue='ml')
def generate_daily_forecasts(tenant_id: int = None):
    """Generate ROAS forecasts for all active campaigns."""
    async def _run():
        async with get_db_session() as db:
            if tenant_id:
                tenants = [await db.get(Tenant, tenant_id)]
            else:
                tenants = await get_all_tenants(db)

            for tenant in tenants:
                campaigns = await get_active_campaigns(db, tenant.id)

                for campaign in campaigns:
                    try:
                        prediction = await inference_service.get_prediction(
                            'roas',
                            campaign.to_dict(),
                            tenant.id
                        )

                        # Store prediction
                        await store_prediction(db, campaign.id, prediction)

                    except Exception as e:
                        logger.error(f"Prediction failed: {campaign.id}", error=str(e))

    asyncio.run(_run())


@celery_app.task(queue='ml')
def calculate_all_fatigue_scores():
    """Calculate creative fatigue scores for all assets."""
    async def _run():
        async with get_db_session() as db:
            assets = await get_active_assets(db)
            scorer = FatigueScorer()

            for asset in assets:
                score_data = scorer.calculate_score(asset)
                asset.fatigue_score = score_data['fatigue_score']
                await db.commit()

    asyncio.run(_run())
```

### Beat Schedule

```python
# backend/app/workers/celery_app.py

celery_app.conf.beat_schedule = {
    'generate-daily-forecasts': {
        'task': 'app.workers.tasks.generate_daily_forecasts',
        'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM UTC
    },
    'calculate-fatigue-scores': {
        'task': 'app.workers.tasks.calculate_all_fatigue_scores',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM UTC
    },
    'run-live-predictions': {
        'task': 'app.workers.tasks.run_all_tenant_predictions',
        'schedule': timedelta(minutes=30),  # Every 30 minutes
    },
}
```

---

## Configuration

### Environment Variables

```env
# ML Provider: 'local' or 'vertex'
ML_PROVIDER=local
ML_MODELS_PATH=/app/ml_service/models

# Google Vertex AI (if ML_PROVIDER=vertex)
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_ENDPOINT=your-endpoint
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Model Configuration

```python
# backend/app/core/config.py

class Settings:
    ml_provider: str = "local"
    ml_models_path: str = "/app/ml_service/models"

    # Vertex AI settings
    google_cloud_project: Optional[str] = None
    vertex_ai_endpoint: Optional[str] = None

    @property
    def use_vertex_ai(self) -> bool:
        return self.ml_provider == "vertex"
```

---

## Performance Metrics

### Model Evaluation

| Model | Metric | Target | Current |
|-------|--------|--------|---------|
| ROAS Predictor | MAE | < 0.3 | 0.25 |
| ROAS Predictor | R² | > 0.8 | 0.82 |
| Conversion Predictor | AUC | > 0.85 | 0.87 |
| Conversion Predictor | Precision | > 0.8 | 0.83 |
| Fatigue Scorer | Accuracy | > 0.9 | 0.91 |

### Inference Latency

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| ROAS Prediction | 12ms | 35ms | 85ms |
| Conversion Prediction | 8ms | 25ms | 60ms |
| Budget Simulation (1k runs) | 180ms | 350ms | 500ms |
| Fatigue Score | 5ms | 15ms | 30ms |

---

## Best Practices

### Data Quality

1. **Minimum data requirements:**
   - ROAS model: 100+ campaigns with 30+ days history
   - Conversion model: 10,000+ events
   - Fatigue model: 50+ creatives with performance data

2. **Feature engineering:**
   - Normalize numerical features
   - Handle missing values appropriately
   - Encode categorical variables consistently

### Model Maintenance

1. **Retraining frequency:**
   - Monthly for stable models
   - Weekly during high-change periods
   - Triggered by performance degradation

2. **Monitoring:**
   - Track prediction accuracy over time
   - Alert on model drift
   - Log feature distributions

### Caching Strategy

1. **Cache predictions for:**
   - 30 minutes for ROAS predictions
   - 15 minutes for real-time predictions
   - 24 hours for fatigue scores

2. **Invalidate cache when:**
   - New campaign data arrives
   - Model is retrained
   - User requests refresh
