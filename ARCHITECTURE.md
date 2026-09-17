# AgriPredictX System Architecture

## System Overview

AgriPredictX is a comprehensive agricultural yield prediction system that integrates data ingestion from multiple sources, advanced feature engineering, machine learning, and explainability to provide farmers with accurate crop yield predictions and actionable insights.

### Key Features

1. **Multi-Source Data Ingestion** - Acquires and validates data from 4 sources
2. **Robust Error Handling** - Handles API anomalies and missing data
3. **Advanced Feature Engineering** - Calculates agronomically significant features
4. **Tree-Based ML Models** - XGBoost/RandomForest for yield prediction
5. **SHAP Explainability** - Per-prediction explanations with Shapley values
6. **Comprehensive Logging** - Audit trail and monitoring capabilities

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  OpenWeatherMap  │  │  data.gov.in     │  │  Sentinel-2      │          │
│  │  5-day Forecast  │  │  Historical      │  │  Satellite       │          │
│  │  (3-hr intervals)│  │  Crop Yield      │  │  NDVI Data       │          │
│  │                  │  │  (20 states,     │  │                  │          │
│  │  ✓ Error handling│  │   15 crops,      │  │  ✓ Geospatial    │          │
│  │    KeyError fix  │  │   1990-2022)     │  │    processing    │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│           │                    │                      │                     │
│           └─────────────────────┼──────────────────────┘                     │
│                                 │                                            │
│           ┌─────────────────────▼──────────────────────┐                    │
│           │    Data Validation & Anomaly Detection    │                    │
│           │  - Response structure validation          │                    │
│           │  - Missing key handling                   │                    │
│           │  - Data type coercion                     │                    │
│           └─────────────────────┬──────────────────────┘                    │
│                                 │                                            │
│           ┌─────────────────────▼──────────────────────┐                    │
│           │     Soil Fertility Ingestion              │                    │
│           │  - N, P, K measurements                   │                    │
│           │  - SFI calculation                        │                    │
│           └─────────────────────┬──────────────────────┘                    │
│                                 │                                            │
│                         IngestionLog Table                                   │
│                   (source, operation, status)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  PostgreSQL Database       │
                    ├────────────────────────────┤
                    │ ✓ CropYieldRecord          │
                    │ ✓ WeatherObservation       │
                    │ ✓ SatelliteNDVIData        │
                    │ ✓ SoilFertilityRecord      │
                    │ ✓ IngestionLog             │
                    └────────┬────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────────┐ ┌─────────────────┐ ┌───────────────────┐
│  Weather Data    │ │  Yield Data     │ │  NDVI Data        │
│  (3-hr values)   │ │  (historical    │ │  (Sentinel-2)     │
│                  │ │   20 states)    │ │                   │
└──────────────────┘ └─────────────────┘ └───────────────────┘
```

---

## Component Details

### 1. Ingestion Layer (`ingestion_layer.py`)

#### DatabaseConnector
- Manages PostgreSQL connections via SQLAlchemy
- Creates all required tables on initialization
- Provides session management for ORM operations

#### WeatherIngestion
- **Source**: OpenWeatherMap 5-day forecast API
- **Frequency**: 3-hour intervals
- **Error Handling**: Robust validation for API response structure
  - Detects missing 'list' key (resolved KeyError: 'list' bug)
  - Validates nested 'main' and 'weather' structures
  - Type coercion for temperature/humidity values

**Example API Response Validation**:
```python
# Prevents KeyError: 'list' bug
if 'list' not in response:
    logger.warning("Missing 'list' key - invalid response")
    return False

# Validates nested structure before access
if not all(k in record['main'] for k in ['temp', 'humidity', 'pressure']):
    logger.warning("Invalid 'main' structure")
    return False
```

#### CropYieldIngestion
- **Source**: Historical data from data.gov.in
- **Coverage**: 20 Indian states, 15 major crops, 1990-2022
- **Storage**: PostgreSQL via SQLAlchemy ORM
- **Features**: State, district, crop, year, season, area, production, yield

#### SatelliteNDVIIngestion
- **Source**: Sentinel-2 public archives
- **Data**: Normalized Difference Vegetation Index (NDVI)
- **Processing**: Sentinelsat library integration
- **Storage**: Geospatial metadata with NDVI values

#### SoilFertilityIngestion
- **Parameters**: Nitrogen, Phosphorus, Potassium (NPK)
- **Computation**: Soil Fertility Index (SFI) normalization
- **Formula**: SFI = (N_norm × 0.40) + (P_norm × 0.30) + (K_norm × 0.30)
  - N normalized to 0-200 kg/ha range
  - P normalized to 0-150 kg/ha range
  - K normalized to 0-200 kg/ha range
  - Final SFI: 0-1 scale for comparability

---

### 2. Feature Engineering (`feature_engineering.py`)

#### Growing Degree Days (GDD)
**Agronomic Significance**: Measures thermal units accumulated during growing season

**Formula**:
```
GDD = Σ max((T_max + T_min)/2 - base_temp, 0)
```

**Base Temperatures by Crop**:
- Wheat, Rice, Maize: 10°C
- Cotton, Sugarcane: 15°C
- Potato: 7°C
- Chickpea, Lentil: 8°C

**Application**: Predicts crop maturity and yield potential

#### Rolling Rainfall Analysis
**Metrics Computed**:
- 7-day rolling total (critical growth stage)
- 14-day rolling total (mid-season dynamics)
- Mean daily rainfall
- Peak rainfall events
- Rainy days count (>2.5mm threshold)

**Agronomic Significance**: Captures moisture availability during critical phenological stages

#### Soil Fertility Index (SFI)
**Components**:
1. **Nitrogen (40% weight)**
   - Primary for vegetative growth
   - Typical range: 0-200 kg/hectare

2. **Phosphorus (30% weight)**
   - Root development and energy metabolism
   - Typical range: 0-150 kg/hectare

3. **Potassium (30% weight)**
   - Water retention and disease resistance
   - Typical range: 0-200 kg/hectare

**Normalization**: Each component scaled to 0-1, then weighted composite computed

**Output**: Single 0-1 score for soil fertility comparison across regions

#### NDVI Features
**Indicators of Canopy Health**:
1. **NDVI Peak**: Maximum vegetation index (best canopy condition)
2. **NDVI Mean**: Average health throughout season
3. **NDVI at 60 DAS**: Vegetation index at critical growth stage (60 days after sowing)
4. **NDVI Gain**: Change from sowing to peak (growth trajectory)

**Range**: -1 (water) to +1 (dense vegetation)
**Typical Crop Values**:
- Growing crops: 0.4-0.8
- Sparse vegetation: 0.2-0.4
- Non-vegetated: <0.2

#### Categorical Encodings
- **Crop variety**: Encoded based on training data mappings
- **State**: Region identifier (20 states covered)
- **District**: Sub-region identifier within state

---

### 3. Feature Engineering Pipeline (`FeatureEngineer` class)

```python
features = FeatureEngineer.create_comprehensive_features(
    weather_data=weather_df,           # temp_max, temp_min, rainfall
    soil_data={'N': 150, 'P': 80, 'K': 120},
    ndvi_data=ndvi_series,             # Sentinel-2 observations
    crop='wheat',
    state='Punjab',
    district='Ludhiana'
)

# Returns comprehensive feature dictionary:
{
    'gdd_cumulative': 850.5,           # Growing Degree Days
    'rainfall_7day_mean': 12.3,        # 7-day rolling average
    'rainfall_14day_mean': 15.7,       # 14-day rolling average
    'soil_fertility_index': 0.72,      # SFI (0-1)
    'ndvi_peak': 0.78,                 # Peak canopy health
    'ndvi_at_60das': 0.65,             # 60-day stage NDVI
    'crop_encoded': 5,                 # Crop ID
    'state_encoded': 3,                # State ID
    'district_encoded': 12             # District ID
}
```

---

### 4. Explainability Module (`explainability.py`)

#### ModelExplainer (SHAP Integration)

**Explainer Types**:
- **TreeExplainer**: For XGBoost/RandomForest models (exact SHAP values)
- **LinearExplainer**: For linear models
- **KernelExplainer**: Model-agnostic (slow but general)

**Shapley Values**: Per-prediction explanation showing each feature's contribution

#### Prediction Explanation Example
```
Input Features:
  - GDD Cumulative: 850.5 → +0.7 t/ha contribution
  - Soil Fertility Index: 0.72 → -0.5 t/ha impact
  - NDVI Peak: 0.78 → +0.3 t/ha contribution
  - Rainfall 7-day: 12.3mm → +0.2 t/ha

Expected Baseline: 3.0 t/ha
Feature Contributions: +0.7 -0.5 +0.3 +0.2 = +0.7
Final Prediction: 3.7 t/ha
```

#### Waterfall Visualization
```
Visualization shows:
1. Baseline (expected yield)
2. Each feature's additive contribution
3. Final prediction value
4. Color coding: Green (positive), Red (negative)
```

#### Farmer-Friendly Report Example
```
============================================================
CROP YIELD PREDICTION REPORT
============================================================

Predicted Yield: 3.7 t/ha
Baseline Expected: 3.0 t/ha

FACTORS INCREASING YIELD:
  ✓ High cumulative GDD
  ✓ Good NDVI peak canopy
  ✓ Adequate rainfall

FACTORS DECREASING YIELD:
  ✗ Low soil fertility index
```

#### Explainability Logging
**Persisted to Database**:
- SHAP values for each feature
- Actual feature values
- Top positive/negative contributors
- Waterfall plot data
- Baseline vs predicted values
- Model version and timestamp
- Optional farmer feedback

---

### 5. Database Schema (`database_models.py`)

#### CropYieldRecord
```sql
CREATE TABLE crop_yield_records (
  id SERIAL PRIMARY KEY,
  state VARCHAR(100) NOT NULL,
  district VARCHAR(100) NOT NULL,
  crop VARCHAR(100) NOT NULL,
  year INTEGER NOT NULL,
  season VARCHAR(20) NOT NULL,  -- kharif, rabi, zaid
  area_harvested FLOAT,
  production FLOAT,
  yield_per_hectare FLOAT NOT NULL,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  INDEX: (crop, state, year)
);
```

#### WeatherObservation (3-hour intervals)
```sql
CREATE TABLE weather_observations (
  id SERIAL PRIMARY KEY,
  state VARCHAR(100),
  district VARCHAR(100),
  observation_date TIMESTAMP NOT NULL,
  temperature_max FLOAT,
  temperature_min FLOAT,
  temperature_avg FLOAT,
  humidity FLOAT,
  rainfall FLOAT DEFAULT 0,
  wind_speed FLOAT,
  pressure FLOAT,
  cloud_cover FLOAT,
  api_response JSON,  -- Raw OpenWeatherMap response
  created_at TIMESTAMP,
  INDEX: (state, district, observation_date)
);
```

#### SatelliteNDVIData (Sentinel-2)
```sql
CREATE TABLE satellite_ndvi_data (
  id SERIAL PRIMARY KEY,
  state VARCHAR(100),
  district VARCHAR(100),
  crop VARCHAR(100),
  observation_date TIMESTAMP NOT NULL,
  ndvi_value FLOAT NOT NULL,  -- Range: -1 to 1
  cloud_coverage FLOAT,
  sentinel_tile VARCHAR(50),
  latitude FLOAT,
  longitude FLOAT,
  acquisition_date TIMESTAMP,
  created_at TIMESTAMP,
  INDEX: (state, district, observation_date),
  INDEX: (crop, observation_date)
);
```

#### SoilFertilityRecord
```sql
CREATE TABLE soil_fertility_records (
  id SERIAL PRIMARY KEY,
  state VARCHAR(100),
  district VARCHAR(100),
  measurement_date TIMESTAMP NOT NULL,
  nitrogen FLOAT NOT NULL,
  phosphorus FLOAT NOT NULL,
  potassium FLOAT NOT NULL,
  soil_fertility_index FLOAT NOT NULL,  -- Normalized 0-1
  ph FLOAT,
  organic_carbon FLOAT,
  electrical_conductivity FLOAT,
  created_at TIMESTAMP,
  INDEX: (state, district, measurement_date)
);
```

#### PredictionExplanability (SHAP Audit Log)
```sql
CREATE TABLE prediction_explainability (
  id SERIAL PRIMARY KEY,
  prediction_id VARCHAR(50) NOT NULL UNIQUE,
  state VARCHAR(100),
  district VARCHAR(100),
  crop VARCHAR(100),
  predicted_yield FLOAT,
  baseline_yield FLOAT,
  shap_values JSON,        -- {feature: value}
  feature_values JSON,     -- {feature: value}
  top_positive_features JSON,
  top_negative_features JSON,
  waterfall_data JSON,     -- Visualization data
  model_version VARCHAR(50),
  user_id VARCHAR(100),    -- Optional farmer ID
  feedback TEXT,           -- Optional farmer feedback
  created_at TIMESTAMP,
  INDEX: (crop),
  INDEX: (created_at)
);
```

#### IngestionLog (Audit Trail)
```sql
CREATE TABLE ingestion_logs (
  id SERIAL PRIMARY KEY,
  source_type VARCHAR(50),  -- weather, yield, ndvi, soil
  operation VARCHAR(100),   -- fetch, validate, load
  status VARCHAR(20),       -- success, failure, partial
  records_processed INTEGER,
  records_failed INTEGER,
  error_message TEXT,
  error_details JSON,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  duration_seconds FLOAT,
  created_at TIMESTAMP,
  INDEX: (source_type, created_at)
);
```

---

### 6. System Integration (`system_integration.py`)

#### AgriPredictXSystem
Central interface coordinating all components:

```python
system = AgriPredictXSystem(db_url='postgresql://...')

# Setup explainability
system.setup_explainability(
    model=trained_model,
    X_train=training_data,
    feature_names=get_feature_columns(),
    model_type='tree'
)

# Get comprehensive features
features = system.get_comprehensive_features(
    state='Punjab',
    district='Ludhiana',
    crop='wheat',
    weather_data=weather_df,
    soil_data={'nitrogen': 150, 'phosphorus': 80, 'potassium': 120},
    ndvi_data=ndvi_series
)

# Make prediction with explanation
result = system.make_prediction_with_explanation(
    model=model,
    X=feature_vector,
    feature_names=feature_names,
    prediction_id='pred_12345',
    state='Punjab',
    district='Ludhiana',
    crop='wheat',
    baseline_yield=3.0
)

print(result)
# {
#   'prediction_id': 'pred_12345',
#   'predicted_yield': 3.7,
#   'baseline_yield': 3.0,
#   'top_positive_features': ['gdd_cumulative', 'ndvi_peak'],
#   'top_negative_features': ['soil_fertility_index'],
#   'shap_values': {feature: value, ...},
#   'explanation': {...}
# }
```

#### PredictionPipeline
End-to-end workflow from raw data to explanation:

```python
pipeline = PredictionPipeline(system, model)

result = pipeline.predict_from_raw_data(
    state='Punjab',
    district='Ludhiana',
    crop='wheat',
    weather_df=weather_data,
    soil_params={'nitrogen': 150, 'phosphorus': 80, 'potassium': 120},
    ndvi_series=ndvi_data,
    feature_names=feature_columns,
    baseline_yield=3.0
)
```

---

## Data Flow Diagram

```
Raw Data Sources
    ↓
    ├─→ Weather API (OpenWeatherMap)
    ├─→ Historical CSV (data.gov.in)
    ├─→ Satellite Imagery (Sentinel-2)
    └─→ Soil Measurements
         ↓
    Ingestion Layer
    (validation, error handling)
         ↓
    PostgreSQL Database
    (WeatherObservation, CropYieldRecord, etc.)
         ↓
    Data Retrieval
         ↓
    Feature Engineering
    (GDD, rainfall, SFI, NDVI, encodings)
         ↓
    Feature Vector
         ↓
    ML Model Prediction
    (XGBoost/RandomForest)
         ↓
    SHAP Explainability
    (Shapley values, waterfall plots)
         ↓
    PredictionExplanability Log
    (database audit trail)
         ↓
    Farmer Dashboard
    (prediction + explanation)
```

---

## Error Handling & Robustness

### KeyError: 'list' Bug Resolution
**Original Issue**: OpenWeatherMap API occasionally returns responses missing the 'list' key

**Solution Implemented**:
```python
def _validate_weather_response(self, response):
    # Check for required keys BEFORE accessing
    if 'list' not in response:
        logger.warning("Missing 'list' key in weather API response")
        return False
    
    # Validate structure before nested access
    if not isinstance(response['list'], list) or len(response['list']) == 0:
        logger.warning("Weather 'list' is empty or invalid")
        return False
    
    # Validate record structure
    for key in ['dt', 'main', 'weather', 'wind']:
        if key not in first_record:
            logger.warning(f"Missing '{key}' in weather forecast record")
            return False
    
    return True
```

### Ingestion Logging
Every ingestion operation logged for audit:
- Source type (weather, yield, ndvi, soil)
- Operation type (fetch, validate, load)
- Success/failure status
- Records processed/failed counts
- Error messages and stack traces
- Timestamps and duration

---

## Scalability Considerations

1. **Database Indexing**: Composite indexes on frequently queried columns
2. **Batch Processing**: Records inserted in configurable batch sizes
3. **Connection Pooling**: SQLAlchemy manages connection pool
4. **Asynchronous Ingestion**: Can be extended with Celery for async tasks
5. **API Rate Limiting**: Configured timeouts and retry logic

---

## Monitoring & Alerts

**Available Metrics**:
- Ingestion success/failure rates
- API response times
- Database query performance
- Prediction accuracy vs baseline
- Feature importance trends
- Farmer feedback collection

---

## Production Deployment

### Prerequisites
- PostgreSQL 12+ with PostGIS (optional for geospatial)
- Python 3.8+
- Environment variables configured (.env)
- API keys obtained (OpenWeatherMap, Sentinel-2)

### Deployment Steps
1. Install dependencies: `pip install -r requirements.txt`
2. Initialize database: `python main_system.py`
3. Start API server: `python api_server.py`
4. Monitor with: `logs/agripredictx.log`

---

## Future Enhancements

1. **Multi-Model Ensemble**: Combine multiple models for robustness
2. **Temporal SHAP**: Explain predictions across time series
3. **Uncertainty Quantification**: Confidence intervals for predictions
4. **Transfer Learning**: Pre-trained models for under-studied crops
5. **Real-time Alerts**: Notify farmers of adverse weather/soil conditions
6. **Mobile App Integration**: Direct farmer access to predictions
7. **Feedback Loop**: Continuous model improvement from farmer feedback

---

## References

1. **Growing Degree Days**: FAO Agricultural Data
2. **SHAP Explanations**: Lundberg & Lee, 2017
3. **Sentinel-2 NDVI**: ESA Technical Documentation
4. **Soil Fertility Index**: Indian Council of Agricultural Research (ICAR)
