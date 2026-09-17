"""
Main execution module for AgriPredictX system
Coordinates data ingestion, feature engineering, model training, and explainability
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

from ingestion_layer import DatabaseConnector, IngestionOrchestrator
from system_integration import initialize_system, PredictionPipeline
from feature_engineering import FeatureEngineer
from model import CropPredictionModel, train_model_from_scratch
from data_preparation import get_feature_columns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_database():
    """Initialize PostgreSQL database with all required tables"""
    logger.info("Setting up database...")
    
    try:
        # Initialize database connector
        db = DatabaseConnector()
        db.create_tables()
        logger.info("Database tables created successfully")
        return db
        
    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        sys.exit(1)


def ingest_weather_data(orchestrator: IngestionOrchestrator, 
                        state: str, 
                        district: str,
                        latitude: float,
                        longitude: float) -> int:
    """
    Fetch and ingest weather data from OpenWeatherMap API.
    
    Args:
        orchestrator: IngestionOrchestrator instance
        state: State name
        district: District name
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        Number of records ingested
    """
    logger.info(f"Ingesting weather data for {state}, {district}...")
    
    start_time = datetime.utcnow()
    
    try:
        # Fetch weather data
        response = orchestrator.weather.fetch_weather(latitude, longitude, state, district)
        
        if response:
            # Parse and store
            records = orchestrator.weather.parse_and_store_weather(response, state, district)
            
            # Log operation
            orchestrator.log_ingestion(
                source_type='weather',
                operation='fetch_and_store',
                status='success',
                records_processed=records,
                start_time=start_time
            )
            
            logger.info(f"Successfully ingested {records} weather records")
            return records
        else:
            orchestrator.log_ingestion(
                source_type='weather',
                operation='fetch_and_store',
                status='failure',
                records_processed=0,
                error_message='Failed to fetch weather data',
                start_time=start_time
            )
            return 0
            
    except Exception as e:
        logger.error(f"Weather ingestion failed: {str(e)}")
        orchestrator.log_ingestion(
            source_type='weather',
            operation='fetch_and_store',
            status='failure',
            records_processed=0,
            error_message=str(e),
            start_time=start_time
        )
        return 0


def ingest_crop_yield_data(orchestrator: IngestionOrchestrator,
                           csv_path: str,
                           state: str) -> int:
    """
    Load and ingest historical crop yield data.
    
    Args:
        orchestrator: IngestionOrchestrator instance
        csv_path: Path to CSV file from data.gov.in
        state: State name
        
    Returns:
        Number of records ingested
    """
    logger.info(f"Ingesting crop yield data for {state}...")
    
    start_time = datetime.utcnow()
    
    try:
        # Load CSV
        df = orchestrator.yield_data.load_from_csv(csv_path, state)
        
        if not df.empty:
            # Parse and store
            records = orchestrator.yield_data.parse_and_store_yield(df, state)
            
            # Log operation
            orchestrator.log_ingestion(
                source_type='yield',
                operation='load_from_csv',
                status='success',
                records_processed=records,
                start_time=start_time
            )
            
            logger.info(f"Successfully ingested {records} yield records")
            return records
        else:
            orchestrator.log_ingestion(
                source_type='yield',
                operation='load_from_csv',
                status='failure',
                records_processed=0,
                error_message='CSV file empty or not found',
                start_time=start_time
            )
            return 0
            
    except Exception as e:
        logger.error(f"Crop yield ingestion failed: {str(e)}")
        orchestrator.log_ingestion(
            source_type='yield',
            operation='load_from_csv',
            status='failure',
            records_processed=0,
            error_message=str(e),
            start_time=start_time
        )
        return 0


def ingest_soil_fertility_data(orchestrator: IngestionOrchestrator,
                               state: str,
                               district: str,
                               nitrogen: float,
                               phosphorus: float,
                               potassium: float) -> bool:
    """
    Ingest soil fertility measurements.
    
    Args:
        orchestrator: IngestionOrchestrator instance
        state: State name
        district: District name
        nitrogen: N content (kg/hectare)
        phosphorus: P content (kg/hectare)
        potassium: K content (kg/hectare)
        
    Returns:
        True if successful
    """
    logger.info(f"Ingesting soil fertility data for {state}, {district}...")
    
    try:
        success = orchestrator.soil.store_soil_fertility(
            state=state,
            district=district,
            nitrogen=nitrogen,
            phosphorus=phosphorus,
            potassium=potassium
        )
        
        if success:
            orchestrator.log_ingestion(
                source_type='soil',
                operation='store',
                status='success',
                records_processed=1,
                start_time=datetime.utcnow()
            )
        else:
            orchestrator.log_ingestion(
                source_type='soil',
                operation='store',
                status='failure',
                records_processed=0,
                error_message='Failed to store soil data',
                start_time=datetime.utcnow()
            )
        
        return success
        
    except Exception as e:
        logger.error(f"Soil fertility ingestion failed: {str(e)}")
        return False


def demonstrate_prediction_pipeline():
    """
    Demonstrate complete prediction pipeline with explanation.
    
    This shows how the system:
    1. Acquires data from multiple sources
    2. Engineers agronomically significant features
    3. Makes predictions with ML model
    4. Generates SHAP-based explanations
    5. Logs predictions for audit and monitoring
    """
    logger.info("\n" + "="*60)
    logger.info("DEMONSTRATING PREDICTION PIPELINE")
    logger.info("="*60 + "\n")
    
    try:
        # Initialize system
        system = initialize_system()
        
        # Initialize or load model
        model = train_model_from_scratch()
        
        # Setup explainability (requires training data)
        X_train = np.random.randn(100, len(get_feature_columns()))
        system.setup_explainability(
            model=model,
            X_train=X_train,
            feature_names=get_feature_columns(),
            model_type='tree'
        )
        
        # Create prediction pipeline
        pipeline = PredictionPipeline(system, model)
        
        # Simulate input data
        weather_data = pd.DataFrame({
            'temp_max': np.random.uniform(25, 35, 100),
            'temp_min': np.random.uniform(15, 25, 100),
            'rainfall': np.random.uniform(0, 50, 100)
        })
        
        soil_params = {
            'nitrogen': 150,
            'phosphorus': 80,
            'potassium': 120
        }
        
        ndvi_data = pd.Series(np.random.uniform(0.3, 0.8, 100))
        
        # Make prediction
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
        
        # Display results
        logger.info("\nPREDICTION RESULT:")
        logger.info(f"  Prediction ID: {result['prediction_id']}")
        logger.info(f"  Location: {result['state']}, {result['district']}")
        logger.info(f"  Crop: {result['crop']}")
        logger.info(f"  Predicted Yield: {result['predicted_yield']:.2f} t/ha")
        logger.info(f"  Baseline Yield: {result['baseline_yield']:.2f} t/ha")
        
        if 'top_positive_features' in result:
            logger.info(f"  Top positive factors: {', '.join(result['top_positive_features'][:3])}")
        if 'top_negative_features' in result:
            logger.info(f"  Top negative factors: {', '.join(result['top_negative_features'][:3])}")
        
        logger.info("\n" + "="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Prediction pipeline error: {str(e)}")


def main():
    """Main entry point for system initialization and demonstration"""
    logger.info("Starting AgriPredictX System Initialization")
    logger.info("="*60)
    
    try:
        # Step 1: Setup database
        logger.info("\n[STEP 1] Setting up database...")
        db = setup_database()
        
        # Step 2: Initialize ingestion orchestrator
        logger.info("\n[STEP 2] Initializing data ingestion...")
        orchestrator = IngestionOrchestrator(db)
        
        # Step 3: Demonstrate feature engineering
        logger.info("\n[STEP 3] Demonstrating feature engineering...")
        
        # Calculate GDD
        weather_data = pd.DataFrame({
            'temp_max': [30, 32, 31, 29, 28],
            'temp_min': [15, 17, 16, 14, 13]
        })
        gdd = FeatureEngineer.calculate_growing_degree_days(weather_data, 'wheat')
        logger.info(f"  Cumulative GDD for wheat: {gdd:.1f}°C-days")
        
        # Calculate rainfall statistics
        rainfall_data = pd.Series([5, 10, 15, 8, 20, 12, 18])
        rainfall_stats = FeatureEngineer.calculate_rainfall_statistics(rainfall_data)
        logger.info(f"  Total rainfall: {rainfall_stats['total_rainfall']:.1f} mm")
        logger.info(f"  7-day mean: {rainfall_stats['rainfall_7day_mean']:.1f} mm")
        
        # Calculate SFI
        sfi = FeatureEngineer.calculate_soil_fertility_index(150, 80, 120)
        logger.info(f"  Soil Fertility Index: {sfi:.3f}")
        
        # Step 4: Demonstrate complete prediction pipeline
        logger.info("\n[STEP 4] Demonstrating prediction pipeline with explanations...")
        demonstrate_prediction_pipeline()
        
        logger.info("\n" + "="*60)
        logger.info("AgriPredictX System Initialization Complete!")
        logger.info("="*60)
        logger.info("\nNext steps:")
        logger.info("1. Configure OpenWeatherMap API key in environment")
        logger.info("2. Load historical crop yield data from data.gov.in")
        logger.info("3. Configure Sentinel-2 credentials for NDVI data")
        logger.info("4. Start API server: python api_server.py")
        logger.info("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"System initialization failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
