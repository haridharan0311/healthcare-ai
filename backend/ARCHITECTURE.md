# Healthcare Analytics Platform - Layered Architecture

## Overview

This document describes the new layered architecture implemented for the Healthcare Analytics Platform. The architecture transforms the system from a transactional database application into a comprehensive analytical platform with predictive capabilities, decision support, and continuous learning.

## Architecture Layers

The platform is organized into five distinct layers, each with specific responsibilities:

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (Views)                        │
│  RESTful endpoints exposing insights through standardized APIs  │
├─────────────────────────────────────────────────────────────────┤
│                    Decision Engine (Layer 4)                    │
│  Business rule evaluation, alert generation, recommendations    │
├─────────────────────────────────────────────────────────────────┤
│                   Prediction Engine (Layer 3)                   │
│  ML-based forecasting, demand prediction, trend analysis        │
├─────────────────────────────────────────────────────────────────┤
│                   Analytics Engine (Layer 2)                    │
│  Centralized analytics, time-series analysis, pattern recognition│
├─────────────────────────────────────────────────────────────────┤
│                  Data Aggregation (Layer 1)                     │
│  Pure ORM queries for data retrieval, no business logic         │
├─────────────────────────────────────────────────────────────────┤
│                         Database                                │
│  Django models: Appointment, Disease, DrugMaster, etc.          │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Details

### Layer 1: Data Aggregation (`aggregation.py`)

**Purpose**: Pure data access layer with no business logic.

**Key Functions**:
- `aggregate_disease_counts()` - Count appointments per disease
- `aggregate_daily_counts()` - Group counts by date and disease
- `aggregate_medicine_usage()` - Sum medicine quantities by disease
- `compare_disease_trends()` - Compare trends between periods
- `aggregate_top_medicines()` - Top medicines by usage
- `aggregate_seasonality()` - Disease patterns by season
- `aggregate_doctor_wise()` - Disease data by doctor
- `aggregate_weekly()` / `aggregate_monthly()` - Time-based aggregation

**For New Users**: This layer handles all database queries. Think of it as the "data retrieval" layer that gets raw numbers from the database.

### Layer 2: Analytics Engine (`analytics_engine.py`)

**Purpose**: Centralized analytics computations and pattern recognition.

**Key Classes**:
- `AnalyticsEngine` - Main analytics engine

**Key Methods**:
- `analyze_disease_trends()` - Comprehensive disease analysis with trends
- `analyze_medicine_usage()` - Medicine consumption patterns
- `get_health_dashboard()` - Complete health system overview

**For New Users**: This engine takes raw data and computes meaningful metrics like trends, patterns, and statistical summaries.

### Layer 3: Prediction Engine (`prediction_engine.py`)

**Purpose**: ML-based forecasting and demand prediction.

**Key Classes**:
- `PredictionEngine` - Main prediction engine

**Key Methods**:
- `predict_disease_outbreaks()` - Forecast potential disease spikes
- `predict_medicine_demand()` - Predict medicine requirements
- `predict_clinic_resource_needs()` - Forecast resource requirements
- `get_forecast_dashboard()` - Comprehensive forecast overview

**For New Users**: This engine uses historical data to predict future events, helping with proactive planning.

### Layer 4: Decision Engine (`decision_engine.py`)

**Purpose**: Business rule evaluation and actionable recommendations.

**Key Classes**:
- `DecisionEngine` - Main decision engine

**Key Methods**:
- `generate_decisions()` - Comprehensive decision set
- `make_restock_decisions()` - Inventory restock recommendations
- `make_outbreak_response_decisions()` - Disease outbreak actions
- `make_resource_allocation_decisions()` - Resource distribution
- `make_risk_mitigation_decisions()` - Risk prevention actions

**For New Users**: This engine converts predictions into specific, prioritized actions with deadlines and assigned responsibilities.

### Layer 5: Feedback Engine (`feedback_engine.py`)

**Purpose**: Continuous learning and system improvement.

**Key Classes**:
- `FeedbackEngine` - Main feedback engine

**Key Methods**:
- `track_prediction_accuracy()` - Monitor prediction performance
- `monitor_decision_outcomes()` - Track decision effectiveness
- `get_improvement_recommendations()` - System enhancement suggestions

**For New Users**: This engine ensures the system gets smarter over time by learning from past performance.

## API Endpoints

### Analytics Engine Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/insights/health-dashboard/` | Comprehensive health system dashboard |
| `GET /api/insights/disease-trends/analysis/` | Detailed disease trend analysis |
| `GET /api/insights/medicine-usage/analysis/` | Medicine usage patterns |

### Prediction Engine Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/insights/predictions/disease-outbreaks/` | Disease outbreak forecasts |
| `GET /api/insights/predictions/medicine-demand/` | Medicine demand predictions |
| `GET /api/insights/predictions/resource-needs/` | Clinic resource forecasts |
| `GET /api/insights/predictions/dashboard/` | Complete forecast dashboard |

### Decision Engine Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/insights/decisions/dashboard/` | All recommended decisions |
| `GET /api/insights/decisions/restock/` | Restock recommendations |
| `GET /api/insights/decisions/outbreak-response/` | Outbreak response actions |
| `GET /api/insights/decisions/resource-allocation/` | Resource allocation decisions |
| `GET /api/insights/decisions/risk-mitigation/` | Risk mitigation actions |

### Feedback Engine Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/insights/feedback/prediction-accuracy/` | Prediction accuracy metrics |
| `GET /api/insights/feedback/decision-outcomes/` | Decision effectiveness |
| `GET /api/insights/feedback/improvement-recommendations/` | System improvement suggestions |

### Unified Platform Endpoint

| Endpoint | Description |
|----------|-------------|
| `GET /api/insights/platform-dashboard/` | Complete platform overview (all engines) |

## Usage Examples

### Basic Usage

```python
from analytics.services import (
    AnalyticsEngine,
    PredictionEngine,
    DecisionEngine,
    FeedbackEngine
)

# Analytics
analytics = AnalyticsEngine()
disease_trends = analytics.analyze_disease_trends(days=30)

# Predictions
predictions = PredictionEngine()
outbreak_forecast = predictions.predict_disease_outbreaks(days_ahead=14)

# Decisions
decisions = DecisionEngine()
restock_recommendations = decisions.make_restock_decisions()

# Feedback
feedback = FeedbackEngine()
accuracy_report = feedback.track_prediction_accuracy()
```

### Comprehensive Dashboard

```python
# Single call for complete platform overview
from analytics.services import (
    AnalyticsEngine,
    PredictionEngine,
    DecisionEngine,
    FeedbackEngine
)

# Get everything in one call
dashboard = AnalyticsPlatformDashboardView.as_view()(request)
```

## Key Features

### 1. Centralized Analytics Logic
All analytics computations are now centralized in the Analytics Engine, eliminating duplication and ensuring consistency.

### 2. Predictive Capabilities
The Prediction Engine uses statistical methods to forecast:
- Disease outbreaks
- Medicine demand
- Resource needs

### 3. Decision Support
The Decision Engine provides:
- Prioritized action items
- Specific recommendations with deadlines
- Assigned responsibilities

### 4. Continuous Learning
The Feedback Engine enables:
- Prediction accuracy tracking
- Decision outcome monitoring
- System improvement recommendations

### 5. Time-Series Analysis
Comprehensive temporal analysis including:
- Daily, weekly, monthly aggregations
- Trend detection and comparison
- Seasonal pattern recognition

### 6. Alert Generation
Automated alerts for:
- Disease outbreaks
- Stock shortages
- Resource constraints
- Quality issues

## Migration from Old Architecture

The new architecture maintains backward compatibility with existing endpoints while adding new capabilities:

| Old Endpoint | New Equivalent |
|--------------|----------------|
| `/api/disease-trends/` | `/api/insights/disease-trends/analysis/` |
| `/api/spike-alerts/` | `/api/insights/predictions/disease-outbreaks/` |
| `/api/restock-suggestions/` | `/api/insights/decisions/restock/` |
| N/A (new) | `/api/insights/platform-dashboard/` |

## Best Practices

1. **Use the appropriate layer**: Don't bypass layers - use Analytics Engine for analysis, Prediction Engine for forecasts, etc.

2. **Cache appropriately**: Use the built-in caching for frequently accessed data.

3. **Monitor accuracy**: Regularly check the Feedback Engine to ensure predictions remain accurate.

4. **Act on decisions**: The Decision Engine provides prioritized actions - implement a system to track action completion.

5. **Review recommendations**: The Feedback Engine provides improvement suggestions - review and implement them regularly.

## Future Enhancements

Potential future improvements:
- Integration with external data sources (weather, demographics)
- Advanced ML algorithms (neural networks, ensemble methods)
- Real-time streaming analytics
- Automated decision execution
- Multi-tenant support
- Advanced visualization dashboards

## Support

For questions or issues with the layered architecture, refer to:
- `backend/analytics/services/` - Service implementations
- `backend/analytics/views/insight_views.py` - API endpoints
- `backend/analytics/utils/` - Utility functions and validators