"""Configuration and environment setup guide for AgriPredictX system"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
# PostgreSQL database URL format:
# postgresql://username:password@host:port/database_name
#
# Example local setup:
# PostgreSQL database URL. Defaults to local PostgreSQL if not set.
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://agripredictx:password@localhost:5432/agripredictx'
)

# ============================================================================
# OPENWEATHERMAP API CONFIGURATION
# ============================================================================
# Get API key from: https://openweathermap.org/api
#
# Free tier includes:
# - 5 Day / 3 Hour Forecast API (used for weather data ingestion)
# - 1000 calls/day
#
# Set in environment variable OPENWEATHER_API_KEY or .env file
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')

# API endpoint for 5-day forecast
OPENWEATHER_FORECAST_API = 'https://api.openweathermap.org/data/2.5/forecast'

# ============================================================================
# SENTINEL-2 SATELLITE DATA CONFIGURATION
# ============================================================================
# For NDVI data from Sentinel-2, you can use sentinelsat
# 
# Copernicus Data Space Ecosystem credentials:
# https://dataspace.copernicus.eu/
#
# Set in environment variables SENTINEL_USERNAME and SENTINEL_PASSWORD
SENTINEL_USERNAME = os.getenv('SENTINEL_USERNAME', '')
SENTINEL_PASSWORD = os.getenv('SENTINEL_PASSWORD', '')

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
MODEL_CONFIG = {
    # XGBoost parameters
    'xgb_max_depth': 8,
    'xgb_learning_rate': 0.1,
    'xgb_n_estimators': 100,
    'xgb_subsample': 0.8,
    'xgb_colsample_bytree': 0.8,
    
    # RandomForest parameters
    'rf_n_estimators': 100,
    'rf_max_depth': 15,
    
    # Training parameters
    'test_size': 0.2,
    'random_state': 42,
    'batch_size': 32,
    'epochs': 50,
}

# ============================================================================
# FEATURE ENGINEERING CONFIGURATION
# ============================================================================
# Base temperatures for GDD calculation (Celsius)
# Different crops have different base temperatures for thermal unit accumulation
GDD_BASE_TEMPERATURES = {
    'wheat': 10,      # 10°C threshold
    'rice': 10,       # 10°C threshold
    'maize': 10,      # 10°C threshold
    'cotton': 15.6,   # 15.6°C threshold
    'sugarcane': 15,  # 15°C threshold
    'potato': 7,      # 7°C threshold
    'tomato': 10,     # 10°C threshold
    'chilli': 15,     # 15°C threshold
}

# Soil Fertility Index (SFI) weights and normalization ranges
SFI_CONFIG = {
    'weights': {
        'nitrogen': 0.40,       # 40% weight
        'phosphorus': 0.30,     # 30% weight
        'potassium': 0.30,      # 30% weight
    },
    'normalization_ranges': {
        'nitrogen': {'min': 0, 'max': 200},      # kg/hectare
        'phosphorus': {'min': 0, 'max': 150},    # kg/hectare
        'potassium': {'min': 0, 'max': 200},     # kg/hectare
    }
}

# NDVI thresholds for crop health classification
NDVI_THRESHOLDS = {
    'poor': 0.2,          # NDVI < 0.2: Poor vegetation
    'fair': 0.4,          # 0.2 <= NDVI < 0.4: Fair
    'good': 0.6,          # 0.4 <= NDVI < 0.6: Good
    'excellent': 1.0,     # NDVI >= 0.6: Excellent
}

# ============================================================================
# DATA INGESTION CONFIGURATION
# ============================================================================
# Ingestion intervals and batch sizes
INGESTION_CONFIG = {
    'weather_fetch_interval_hours': 3,      # Fetch weather every 3 hours
    'satellite_fetch_interval_days': 5,     # Fetch satellite data every 5 days
    'max_api_retries': 3,                   # Retry API calls up to 3 times
    'api_timeout_seconds': 30,              # API request timeout
    'batch_size_database': 1000,            # Batch insert size for database
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'handlers': {
        'file': 'logs/agripredictx.log',
        'level': 'INFO',
    }
}

# ============================================================================
# SETUP INSTRUCTIONS
# ============================================================================
"""
INITIAL SETUP GUIDE:

1. DATABASE SETUP (PostgreSQL)
   ============================
   
   a) Install PostgreSQL:
      - Windows: https://www.postgresql.org/download/windows/
      - macOS: brew install postgresql
      - Linux: sudo apt-get install postgresql postgresql-contrib
   
   b) Create database and user:
      psql -U postgres
      CREATE USER agripredictx WITH PASSWORD 'password';
      CREATE DATABASE agripredictx OWNER agripredictx;
      GRANT ALL PRIVILEGES ON DATABASE agripredictx TO agripredictx;
   
   c) Set DATABASE_URL in .env file or environment

2. DEPENDENCIES INSTALLATION
   ==========================
   
   pip install -r requirements.txt
   
   Required packages:
   - sqlalchemy: ORM for database operations
   - psycopg2-binary: PostgreSQL adapter
   - shap: Model explainability
   - sentinelsat: Satellite data access
   - xgboost, scikit-learn: ML models

3. ENVIRONMENT VARIABLES (.env)
   =============================
   
   Create .env file with:
   DATABASE_URL=postgresql://agripredictx:password@localhost:5432/agripredictx
   OPENWEATHER_API_KEY=your_api_key_here
   SENTINEL_USERNAME=your_username_here
   SENTINEL_PASSWORD=your_password_here

4. API KEY SETUP
   ==============
   
   a) OpenWeatherMap:
      - Register at https://openweathermap.org/api
      - Free tier: 1000 calls/day, 5-day forecast
      - Get API key and add to .env
   
   b) Sentinel-2 (optional):
      - Register at https://dataspace.copernicus.eu/
      - Get credentials and add to .env

5. DATA INGESTION
   ===============
   
   a) Weather data:
      - Automatically fetched via OpenWeatherMap API
      - Run: python main_system.py
   
   b) Historical crop yield data:
      - Download from https://data.gov.in/
      - Place CSV files in data/ directory
      - Run ingestion_layer.py to load
   
   c) Satellite NDVI data:
      - Fetched via Sentinel-2 archives
      - Requires authentication (see above)

6. MODEL TRAINING
   ===============
   
   python model.py train
   
   Generates:
   - crop_model.pkl: Trained XGBoost/RandomForest model
   - feature_scaler.pkl: Feature normalization scaler

7. START API SERVER
   =================
   
   python api_server.py
   
   API endpoints:
   - GET /: Dashboard
   - POST /predict: Make prediction
   - GET /health: Health check

SYSTEM COMPONENTS:
==================

1. Ingestion Layer (ingestion_layer.py)
   - WeatherIngestion: OpenWeatherMap API integration
   - CropYieldIngestion: Historical data from data.gov.in
   - SatelliteNDVIIngestion: Sentinel-2 NDVI data
   - SoilFertilityIngestion: Soil measurements
   - Error handling for API anomalies (KeyError: 'list' bug fix)

2. Feature Engineering (feature_engineering.py)
   - Cumulative Growing Degree Days (GDD)
   - 7-day and 14-day rolling rainfall totals
   - Soil Fertility Index (SFI) calculation
   - NDVI features (peak, mean, 60-day value)
   - Categorical encoding (crop, state, district)

3. Explainability (explainability.py)
   - SHAP TreeExplainer integration
   - Shapley value computation
   - Waterfall plot visualization
   - Per-prediction logging to database
   - Farmer-friendly reports

4. Database Models (database_models.py)
   - CropYieldRecord: Historical yield data (20 states, 15 crops, 1990-2022)
   - WeatherObservation: 3-hour interval weather data
   - SatelliteNDVIData: Sentinel-2 NDVI values
   - SoilFertilityRecord: NPK measurements
   - PredictionExplanability: SHAP audit logs
   - IngestionLog: Data ingestion tracking

5. System Integration (system_integration.py)
   - AgriPredictXSystem: Unified interface
   - PredictionPipeline: End-to-end workflow
   - Feature engineering coordination
   - Model explainability setup

EXAMPLE WORKFLOW:
=================

# 1. Initialize system
system = initialize_system()

# 2. Fetch weather data
weather_response = system.ingestion.weather.fetch_weather(lat, lon, state, district)

# 3. Engineer features
features = FeatureEngineer.create_comprehensive_features(
    weather_data=weather_df,
    soil_data={'nitrogen': 150, 'phosphorus': 80, 'potassium': 120},
    ndvi_data=ndvi_series,
    crop='wheat',
    state='Punjab',
    district='Ludhiana'
)

# 4. Make prediction with explanation
result = pipeline.predict_from_raw_data(
    state='Punjab',
    district='Ludhiana',
    crop='wheat',
    weather_df=weather_df,
    soil_params=soil_params,
    ndvi_series=ndvi_series
)

# 5. Access explanation
print(f"Predicted Yield: {result['predicted_yield']} t/ha")
print(f"Top positive factors: {result['top_positive_features']}")
print(f"Top negative factors: {result['top_negative_features']}")
"""

# ============================================================================
# VALIDATION
# ============================================================================

def validate_configuration():
    """Validate that all required configurations are set"""
    import logging
    logger = logging.getLogger(__name__)
    
    warnings = []
    
    if not OPENWEATHER_API_KEY:
        warnings.append("OPENWEATHER_API_KEY not set - weather data ingestion will fail")
    
    if not SENTINEL_USERNAME or not SENTINEL_PASSWORD:
        warnings.append("Sentinel-2 credentials not set - satellite NDVI data ingestion will fail")
    
    if warnings:
        logger.warning("Configuration warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    logger.info("Configuration validated")


if __name__ == '__main__':
    # Print configuration guide
    print(__doc__)
    validate_configuration()
