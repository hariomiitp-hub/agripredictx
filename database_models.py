"""SQLAlchemy ORM models for the agricultural prediction system"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class CropYieldRecord(Base):
    """Historical crop yield records from data.gov.in"""
    __tablename__ = 'crop_yield_records'
    
    id = Column(Integer, primary_key=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    crop = Column(String(100), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    season = Column(String(20), nullable=False)  # kharif, rabi, zaid
    area_harvested = Column(Float)  # hectares
    production = Column(Float)  # tonnes
    yield_per_hectare = Column(Float, nullable=False)  # target variable: tonnes/hectare
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_crop_state_year', 'crop', 'state', 'year'),
        Index('idx_season_year', 'season', 'year'),
    )


class WeatherObservation(Base):
    """Weather data from OpenWeatherMap API"""
    __tablename__ = 'weather_observations'
    
    id = Column(Integer, primary_key=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    observation_date = Column(DateTime, nullable=False, index=True)
    
    temperature_max = Column(Float, nullable=False)  # Celsius
    temperature_min = Column(Float, nullable=False)
    temperature_avg = Column(Float)
    humidity = Column(Float)  # percentage
    rainfall = Column(Float, default=0)  # mm
    wind_speed = Column(Float)  # km/h
    pressure = Column(Float)  # hPa
    cloud_cover = Column(Float)  # percentage
    
    # API response metadata
    api_response = Column(JSON)  # Raw response from OpenWeatherMap
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_weather_location_date', 'state', 'district', 'observation_date'),
    )


class SatelliteNDVIData(Base):
    """Normalized Difference Vegetation Index from Sentinel-2"""
    __tablename__ = 'satellite_ndvi_data'
    
    id = Column(Integer, primary_key=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    crop = Column(String(100), nullable=False)
    observation_date = Column(DateTime, nullable=False, index=True)
    
    ndvi_value = Column(Float, nullable=False)  # Range: -1 to 1
    cloud_coverage = Column(Float)  # percentage
    sentinel_tile = Column(String(50))  # Sentinel-2 tile identifier
    processing_level = Column(String(20))  # L1C, L2A
    
    # Geospatial info
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Metadata
    acquisition_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_ndvi_location_date', 'state', 'district', 'observation_date'),
        Index('idx_ndvi_crop_date', 'crop', 'observation_date'),
    )


class SoilFertilityRecord(Base):
    """Soil fertility measurements"""
    __tablename__ = 'soil_fertility_records'
    
    id = Column(Integer, primary_key=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    measurement_date = Column(DateTime, nullable=False, index=True)
    
    nitrogen = Column(Float, nullable=False)  # kg/hectare
    phosphorus = Column(Float, nullable=False)  # kg/hectare
    potassium = Column(Float, nullable=False)  # kg/hectare
    soil_fertility_index = Column(Float, nullable=False)  # Computed: N(0.4) + P(0.3) + K(0.3), normalized
    
    # Additional soil parameters
    ph = Column(Float)
    organic_carbon = Column(Float)  # percentage
    electrical_conductivity = Column(Float)  # dS/m
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_soil_location_date', 'state', 'district', 'measurement_date'),
    )


class PredictionExplanability(Base):
    """SHAP-based explainability logs for each prediction"""
    __tablename__ = 'prediction_explainability'
    
    id = Column(Integer, primary_key=True)
    prediction_id = Column(String(50), nullable=False, index=True, unique=True)
    
    # Prediction context
    state = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    crop = Column(String(100), nullable=False)
    predicted_yield = Column(Float, nullable=False)  # tonnes/hectare
    baseline_yield = Column(Float)  # Expected baseline from SHAP
    
    # SHAP values for each feature (stored as JSON for flexibility)
    shap_values = Column(JSON, nullable=False)  # {feature_name: shap_value}
    feature_values = Column(JSON, nullable=False)  # {feature_name: actual_value}
    
    # Explanation summary
    top_positive_features = Column(JSON)  # List of top 5 features increasing prediction
    top_negative_features = Column(JSON)  # List of top 5 features decreasing prediction
    
    # Waterfall plot data (for visualization)
    waterfall_data = Column(JSON)  # Structured data for waterfall visualization
    
    # Audit trail
    model_version = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(100))  # Optional: farmer/user who received prediction
    feedback = Column(Text)  # Optional: farmer feedback on prediction accuracy
    
    __table_args__ = (
        Index('idx_explanation_crop', 'crop'),
        Index('idx_explanation_date', 'created_at'),
    )


class IngestionLog(Base):
    """Log of data ingestion operations"""
    __tablename__ = 'ingestion_logs'
    
    id = Column(Integer, primary_key=True)
    source_type = Column(String(50), nullable=False)  # 'weather', 'yield', 'ndvi', 'soil'
    operation = Column(String(100))  # 'fetch', 'validate', 'load'
    status = Column(String(20))  # 'success', 'failure', 'partial'
    
    # Data details
    records_processed = Column(Integer)
    records_failed = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Timestamps
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_ingestion_source_date', 'source_type', 'created_at'),
    )


class FarmRecord(Base):
    """Registered farm identity and the context used by assurance services."""
    __tablename__ = 'farms'

    id = Column(Integer, primary_key=True)
    farm_id = Column(String(100), nullable=False, unique=True, index=True)
    state = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    crop = Column(String(100), nullable=False)
    season = Column(String(20))
    area_hectares = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)
    profile = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class FarmLossScore(Base):
    """Timestamped loss verification snapshot; it is supporting evidence only."""
    __tablename__ = 'farm_loss_scores'

    id = Column(Integer, primary_key=True)
    farm_id = Column(String(100), nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    score = Column(Float, nullable=False)
    yield_delta_pct = Column(Float, nullable=False)
    data_quality = Column(Text)
    model_version = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_loss_score_farm_date', 'farm_id', 'snapshot_date'),
    )


class LossEvent(Base):
    """Immutable-ish evidentiary record for an automatically detected loss signal."""
    __tablename__ = 'loss_events'

    id = Column(Integer, primary_key=True)
    farm_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    detected_at = Column(DateTime, nullable=False, index=True)
    raw_sensor_snapshot = Column(JSON, nullable=False)
    severity = Column(String(20), nullable=False)
    source = Column(String(30), nullable=False, default='auto-detected')
    claim_draft = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_loss_event_farm_type_date', 'farm_id', 'event_type', 'detected_at'),
    )


class EnrollmentValidationResult(Base):
    """Audit log for non-blocking enrollment sanity checks."""
    __tablename__ = 'enrollment_validation_results'

    id = Column(Integer, primary_key=True)
    farm_id = Column(String(100), nullable=False, index=True)
    declared_data = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClaimRecord(Base):
    """Farmer/FPO-maintained claim timeline; status is not an insurer decision."""
    __tablename__ = 'claims'

    id = Column(Integer, primary_key=True)
    farm_id = Column(String(100), nullable=False, index=True)
    claim_id = Column(String(100), index=True)
    status = Column(String(30), nullable=False, default='enrolled')
    status_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expected_next_action = Column(Text)
    last_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_claim_farm_status', 'farm_id', 'status'),
    )
