"""
QUICK START GUIDE - AgriPredictX System

Get the system up and running in 10 minutes!
"""

# ============================================================================
# PREREQUISITES
# ============================================================================
"""
Before you start, ensure you have:
- Python 3.8+ installed
- PostgreSQL 12+ installed and running
- Internet connection (for API access)
- API keys from OpenWeatherMap (optional)
"""

# ============================================================================
# STEP 1: Install Python Dependencies (2 minutes)
# ============================================================================
"""
Open terminal/command prompt and run:

pip install -r requirements.txt

This installs:
- sqlalchemy (database ORM)
- psycopg2-binary (PostgreSQL adapter)
- shap (explainability)
- xgboost (ML model)
- sentinelsat (satellite data)
- pandas, numpy, scikit-learn (data science)
- flask (web API)
"""

# ============================================================================
# STEP 2: Setup PostgreSQL Database (3 minutes)
# ============================================================================
"""
Option A: Local PostgreSQL (Linux/Mac/Windows)

1. Start PostgreSQL service
   Windows: Services → PostgreSQL
   Mac: brew services start postgresql
   Linux: sudo systemctl start postgresql

2. Create database and user
   psql -U postgres
   
   Inside psql:
   CREATE USER agripredictx WITH PASSWORD 'agripredict123';
   CREATE DATABASE agripredictx OWNER agripredictx;
   GRANT ALL PRIVILEGES ON DATABASE agripredictx TO agripredictx;
   \\q (exit)

Option B: Docker (if you have Docker installed)

docker run --name agripredictx-db \\
  -e POSTGRES_USER=agripredictx \\
  -e POSTGRES_PASSWORD=agripredict123 \\
  -e POSTGRES_DB=agripredictx \\
  -p 5432:5432 \\
  -d postgres:13
"""

# ============================================================================
# STEP 3: Configure Environment (2 minutes)
# ============================================================================
"""
Create .env file in project root:

DATABASE_URL=postgresql://agripredictx:agripredict123@localhost:5432/agripredictx
OPENWEATHER_API_KEY=your_api_key_here (optional)
SENTINEL_USERNAME=your_username (optional)
SENTINEL_PASSWORD=your_password (optional)

Getting API Keys:
- OpenWeatherMap: Register at https://openweathermap.org/api
- Sentinel-2: Register at https://dataspace.copernicus.eu/
"""

# ============================================================================
# STEP 4: Initialize Database (1 minute)
# ============================================================================
"""
Python code:

from ingestion_layer import DatabaseConnector

db = DatabaseConnector()
db.create_tables()

Or from command line:
python -c "from ingestion_layer import DatabaseConnector; DatabaseConnector().create_tables()"
"""

# ============================================================================
# STEP 5: Test the System (2 minutes)
# ============================================================================
"""
Run the complete demo:

python main_system.py

This will:
1. Initialize the database
2. Create all tables
3. Demonstrate feature engineering
4. Show a complete prediction example
"""

# ============================================================================
# FULL WORKING EXAMPLE
# ============================================================================
"""
Here's a complete minimal example to get started:
"""

import pandas as pd
import numpy as np
from system_integration import initialize_system, PredictionPipeline
from data_preparation import get_feature_columns

# 1. Initialize the system
print("Initializing AgriPredictX System...")
system = initialize_system()
print("✓ System initialized\n")

# 2. Create dummy trained model (or load your own)
from model import train_model_from_scratch
print("Training model...")
model = train_model_from_scratch()
print("✓ Model trained\n")

# 3. Setup explainability
print("Setting up SHAP explainability...")
X_train = np.random.randn(100, len(get_feature_columns()))
system.setup_explainability(
    model=model,
    X_train=X_train,
    feature_names=get_feature_columns(),
    model_type='tree'
)
print("✓ Explainability configured\n")

# 4. Create prediction pipeline
pipeline = PredictionPipeline(system, model)

# 5. Prepare input data
print("Preparing input data...")
weather_data = pd.DataFrame({
    'temp_max': [32, 31, 30, 29, 31] * 20,
    'temp_min': [18, 17, 16, 15, 17] * 20,
    'rainfall': [5, 10, 8, 15, 12] * 20
})

soil_params = {
    'nitrogen': 150,
    'phosphorus': 80,
    'potassium': 120
}

ndvi_data = pd.Series(np.linspace(0.2, 0.8, 100))
print("✓ Input data prepared\n")

# 6. Make prediction with full explanation
print("Making prediction with SHAP explanation...")
result = pipeline.predict_from_raw_data(
    state='Punjab',
    district='Ludhiana',
    crop='wheat',
    weather_df=weather_data,
    soil_params=soil_params,
    ndvi_series=ndvi_data,
    feature_names=get_feature_columns(),
    baseline_yield=3.5
)
print("✓ Prediction complete\n")

# 7. Display results
print("=" * 60)
print("PREDICTION RESULTS")
print("=" * 60)
print(f"Prediction ID: {result['prediction_id']}")
print(f"Location: {result['state']}, {result['district']}")
print(f"Crop: {result['crop']}")
print(f"Predicted Yield: {result['predicted_yield']:.2f} t/ha")
print(f"Baseline Yield: {result['baseline_yield']:.2f} t/ha")
print(f"Difference: {result['predicted_yield'] - result['baseline_yield']:+.2f} t/ha")

if 'top_positive_features' in result:
    print(f"\nPositive Factors:")
    for feature in result['top_positive_features'][:3]:
        print(f"  ✓ {feature}")

if 'top_negative_features' in result:
    print(f"\nNegative Factors:")
    for feature in result['top_negative_features'][:3]:
        print(f"  ✗ {feature}")

print("=" * 60)

# 8. Check database
print("\nVerifying data persisted to database...")
from database_models import PredictionExplanability
from ingestion_layer import DatabaseConnector

session = DatabaseConnector().get_session()
prediction_log = session.query(PredictionExplanability).filter_by(
    prediction_id=result['prediction_id']
).first()

if prediction_log:
    print(f"✓ Prediction explanation saved to database (ID: {prediction_log.id})")
else:
    print("⚠ Prediction not found in database (SHAP not available)")

session.close()

# ============================================================================
# WORKING WITH REAL DATA
# ============================================================================
"""
Once you have the system running, use real data:

1. INGESTION FROM OPENWEATHERMAP
   
   from ingestion_layer import IngestionOrchestrator, DatabaseConnector
   
   db = DatabaseConnector()
   orchestrator = IngestionOrchestrator(db)
   
   # Fetch weather for specific location
   response = orchestrator.weather.fetch_weather(
       latitude=31.6295,      # Ludhiana, Punjab
       longitude=74.8765,
       state='Punjab',
       district='Ludhiana'
   )
   
   if response:
       records = orchestrator.weather.parse_and_store_weather(
           response, 'Punjab', 'Ludhiana'
       )
       print(f"Stored {records} weather observations")

2. LOAD CROP YIELD DATA FROM CSV
   
   df = pd.read_csv('yield_data.csv')  # From data.gov.in
   records = orchestrator.yield_data.parse_and_store_yield(df, 'Punjab')
   print(f"Stored {records} historical yield records")

3. ADD SOIL FERTILITY MEASUREMENTS
   
   success = orchestrator.soil.store_soil_fertility(
       state='Punjab',
       district='Ludhiana',
       nitrogen=150,
       phosphorus=80,
       potassium=120
   )
   print("Soil data stored" if success else "Error storing soil data")

4. RETRIEVE DATA FOR PREDICTION
   
   from database_models import WeatherObservation, SoilFertilityRecord
   from datetime import datetime, timedelta
   
   session = db.get_session()
   
   # Get recent weather data
   one_week_ago = datetime.utcnow() - timedelta(days=7)
   weather_records = session.query(WeatherObservation).filter(
       WeatherObservation.state == 'Punjab',
       WeatherObservation.district == 'Ludhiana',
       WeatherObservation.observation_date >= one_week_ago
   ).all()
   
   # Convert to DataFrame for feature engineering
   weather_df = pd.DataFrame([
       {
           'temp_max': r.temperature_max,
           'temp_min': r.temperature_min,
           'rainfall': r.rainfall
       } for r in weather_records
   ])
"""

# ============================================================================
# COMMON TASKS
# ============================================================================
"""
TASK 1: Make a Prediction
─────────────────────────

from system_integration import PredictionPipeline, initialize_system
from model import train_model_from_scratch

system = initialize_system()
model = train_model_from_scratch()
system.setup_explainability(model, X_train, feature_names)
pipeline = PredictionPipeline(system, model)

result = pipeline.predict_from_raw_data(
    state='Punjab',
    district='Ludhiana',
    crop='wheat',
    weather_df=weather_data,
    soil_params=soil_params,
    ndvi_series=ndvi_data
)


TASK 2: View Prediction History
────────────────────────────────

from database_models import PredictionExplanability
from ingestion_layer import DatabaseConnector
import json

db = DatabaseConnector()
session = db.get_session()

predictions = session.query(PredictionExplanability).filter(
    PredictionExplanability.crop == 'wheat'
).order_by(PredictionExplanability.created_at.desc()).limit(10)

for pred in predictions:
    print(f"{pred.created_at}: {pred.predicted_yield:.2f} t/ha")
    top_features = json.loads(pred.top_positive_features)
    print(f"  Factors: {', '.join(top_features[:3])}")

session.close()


TASK 3: Analyze Feature Importance
──────────────────────────────────

from database_models import PredictionExplanability
from ingestion_layer import DatabaseConnector
import json
from collections import Counter

db = DatabaseConnector()
session = db.get_session()

# Get all predictions for wheat crop
predictions = session.query(PredictionExplanability).filter(
    PredictionExplanability.crop == 'wheat'
).all()

# Aggregate SHAP values
all_shap_values = {}
for pred in predictions:
    shap_dict = json.loads(pred.shap_values)
    for feature, value in shap_dict.items():
        if feature not in all_shap_values:
            all_shap_values[feature] = []
        all_shap_values[feature].append(abs(float(value)))

# Calculate average importance
avg_importance = {
    feature: sum(vals) / len(vals)
    for feature, vals in all_shap_values.items()
}

# Print top features
for feature, importance in sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"{feature}: {importance:.4f}")

session.close()


TASK 4: Check Ingestion Logs
─────────────────────────────

from database_models import IngestionLog
from ingestion_layer import DatabaseConnector

db = DatabaseConnector()
session = db.get_session()

logs = session.query(IngestionLog).order_by(
    IngestionLog.created_at.desc()
).limit(20)

for log in logs:
    status_symbol = "✓" if log.status == 'success' else "✗"
    print(f"{status_symbol} {log.source_type}: {log.records_processed} records "
          f"({log.duration_seconds:.1f}s)")
    if log.error_message:
        print(f"   Error: {log.error_message}")

session.close()
"""

# ============================================================================
# TROUBLESHOOTING
# ============================================================================
"""
PROBLEM: "ModuleNotFoundError: No module named 'sqlalchemy'"
SOLUTION: Install dependencies
  pip install -r requirements.txt

PROBLEM: "FATAL: password authentication failed for user 'agripredictx'"
SOLUTION: Check database credentials in .env file
  Verify PostgreSQL user and password match

PROBLEM: "psycopg2.OperationalError: could not connect to server"
SOLUTION: PostgreSQL service not running
  Windows: Start PostgreSQL from Services
  Mac: brew services start postgresql
  Linux: sudo systemctl start postgresql

PROBLEM: "KeyError: 'list'" during weather ingestion
SOLUTION: This is now handled! The system validates response structure
  Check ingestion logs for which API request failed

PROBLEM: "SHAP not available" warning
SOLUTION: Install SHAP
  pip install shap>=0.43.0

PROBLEM: Database tables not created
SOLUTION: Run database initialization
  python -c "from ingestion_layer import DatabaseConnector; DatabaseConnector().create_tables()"

PROBLEM: "No matching crop found" when querying
SOLUTION: Check that crop names match training data
  Available crops in config.py: CROP_REQUIREMENTS dictionary
"""

# ============================================================================
# NEXT STEPS
# ============================================================================
"""
1. ✓ Completed: System setup and first prediction
2. → Next: Ingest real weather data from OpenWeatherMap
3. → Next: Load historical crop yield data from data.gov.in
4. → Next: Deploy API server for web access
5. → Next: Integrate with farmer mobile app
6. → Next: Setup continuous model retraining pipeline
7. → Next: Collect farmer feedback for improvement

For detailed documentation, see:
- ARCHITECTURE.md: Complete system architecture
- IMPLEMENTATION_SUMMARY.md: File-by-file breakdown
- system_config.py: Configuration reference
"""

# ============================================================================
# PERFORMANCE TIPS
# ============================================================================
"""
1. BATCH PROCESSING
   Insert data in batches for faster database operations
   Update ingestion_layer.py: BATCH_SIZE setting

2. CACHING
   Cache model predictions to reduce inference time
   Keep X_train in memory for faster SHAP computation

3. DATABASE INDEXES
   Already optimized with composite indexes
   For large datasets (>1M records), consider partitioning

4. API RATE LIMITING
   OpenWeatherMap free tier: 1000 calls/day
   Stagger requests or cache results

5. FEATURE PREPROCESSING
   Pre-compute GDD, rainfall stats during ingestion
   Store as features to skip computation at prediction time
"""

if __name__ == '__main__':
    print(__doc__)
    print("\nTo get started:")
    print("1. pip install -r requirements.txt")
    print("2. Setup PostgreSQL database")
    print("3. Create .env file with DATABASE_URL")
    print("4. python main_system.py")
    print("\nFor detailed setup, see system_config.py")
