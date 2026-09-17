"""Data Ingestion Layer - acquires, validates, and persists data from four sources"""
import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from database_models import (
    Base, CropYieldRecord, WeatherObservation, SatelliteNDVIData,
    SoilFertilityRecord, IngestionLog
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnector:
    """Manages database connections and sessions"""
    
    def __init__(self, db_url: str = None):
        """
        Initialize database connector.
        
        Args:
            db_url: PostgreSQL connection string. Falls back to environment variable.
        """
        self.db_url = db_url or os.getenv('DATABASE_URL', 
                                          'postgresql://user:password@localhost:5432/agripredictx')
        self.engine = create_engine(self.db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created/verified")
    
    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()


class WeatherIngestion:
    """Ingest weather data from OpenWeatherMap API"""
    
    def __init__(self, api_key: str = None, db_connector: DatabaseConnector = None):
        """
        Initialize weather ingestion.
        
        Args:
            api_key: OpenWeatherMap API key. Falls back to environment variable.
            db_connector: Database connector instance.
        """
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY', '')
        self.db = db_connector
        self.base_url = "https://api.openweathermap.org/data/2.5/forecast"
        
    def fetch_weather(self, latitude: float, longitude: float, 
                      state: str, district: str) -> Optional[Dict]:
        """
        Fetch 5-day weather forecast from OpenWeatherMap at 3-hour intervals.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            state: State name
            district: District name
            
        Returns:
            Raw API response or None if error
        """
        try:
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric'
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Validate response structure - handle KeyError: 'list' bug
            if not self._validate_weather_response(data):
                logger.error(f"Invalid weather response structure for {state}, {district}")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather for {state}, {district}: {str(e)}")
            return None
    
    def _validate_weather_response(self, response: Dict) -> bool:
        """
        Validate OpenWeatherMap API response structure.
        Prevents KeyError: 'list' bug encountered during early testing.
        
        Args:
            response: Raw API response
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check for required keys
            if 'list' not in response:
                logger.warning("Missing 'list' key in weather API response")
                return False
            
            if 'city' not in response:
                logger.warning("Missing 'city' key in weather API response")
                return False
            
            # Validate list structure
            if not isinstance(response['list'], list) or len(response['list']) == 0:
                logger.warning("Weather 'list' is empty or invalid")
                return False
            
            # Sample first record to validate structure
            first_record = response['list'][0]
            required_keys = ['dt', 'main', 'weather', 'wind']
            
            for key in required_keys:
                if key not in first_record:
                    logger.warning(f"Missing '{key}' in weather forecast record")
                    return False
            
            # Validate nested 'main' structure
            if not all(k in first_record['main'] for k in ['temp', 'humidity', 'pressure']):
                logger.warning("Invalid 'main' structure in forecast record")
                return False
            
            return True
            
        except (KeyError, TypeError) as e:
            logger.error(f"Response validation error: {str(e)}")
            return False
    
    def parse_and_store_weather(self, response: Dict, state: str, district: str) -> int:
        """
        Parse weather response and store in database.
        
        Args:
            response: Raw API response
            state: State name
            district: District name
            
        Returns:
            Number of records inserted
        """
        if not response or 'list' not in response:
            return 0
        
        session = self.db.get_session()
        records_added = 0
        
        try:
            for forecast in response['list']:
                try:
                    # Extract main fields
                    temp_max = forecast['main'].get('temp_max', forecast['main']['temp'])
                    temp_min = forecast['main'].get('temp_min', forecast['main']['temp'])
                    temp_avg = forecast['main']['temp']
                    
                    observation = WeatherObservation(
                        state=state,
                        district=district,
                        observation_date=datetime.fromtimestamp(forecast['dt']),
                        temperature_max=temp_max,
                        temperature_min=temp_min,
                        temperature_avg=temp_avg,
                        humidity=forecast['main'].get('humidity'),
                        rainfall=forecast.get('rain', {}).get('3h', 0),
                        wind_speed=forecast.get('wind', {}).get('speed'),
                        pressure=forecast['main'].get('pressure'),
                        cloud_cover=forecast.get('clouds', {}).get('all'),
                        api_response=json.dumps(forecast)
                    )
                    session.add(observation)
                    records_added += 1
                    
                except (KeyError, ValueError) as e:
                    logger.warning(f"Error parsing weather record: {str(e)}")
                    continue
            
            session.commit()
            logger.info(f"Stored {records_added} weather observations for {state}, {district}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing weather data: {str(e)}")
        finally:
            session.close()
        
        return records_added


class CropYieldIngestion:
    """Ingest historical crop yield data from data.gov.in"""
    
    def __init__(self, db_connector: DatabaseConnector = None):
        """
        Initialize crop yield ingestion.
        
        Args:
            db_connector: Database connector instance.
        """
        self.db = db_connector
        
    def load_from_csv(self, csv_path: str, state: str) -> pd.DataFrame:
        """
        Load crop yield data from CSV file (expected from data.gov.in).
        
        Args:
            csv_path: Path to CSV file
            state: State name
            
        Returns:
            DataFrame with crop yield records
        """
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} records from {csv_path}")
            return df
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_path}")
            return pd.DataFrame()
    
    def parse_and_store_yield(self, df: pd.DataFrame, state: str) -> int:
        """
        Parse yield data and store in PostgreSQL database via SQLAlchemy ORM.
        
        District-level records covering 20 Indian states and 15 major crops (1990-2022).
        
        Args:
            df: DataFrame with columns: district, crop, year, season, area, production, yield
            state: State name
            
        Returns:
            Number of records inserted
        """
        session = self.db.get_session()
        records_added = 0
        
        try:
            for _, row in df.iterrows():
                try:
                    record = CropYieldRecord(
                        state=state,
                        district=row.get('district', ''),
                        crop=row.get('crop', ''),
                        year=int(row.get('year', 0)),
                        season=row.get('season', 'kharif'),
                        area_harvested=float(row.get('area', 0)) if row.get('area') else None,
                        production=float(row.get('production', 0)) if row.get('production') else None,
                        yield_per_hectare=float(row.get('yield', 0))
                    )
                    session.add(record)
                    records_added += 1
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing yield record: {str(e)}")
                    continue
            
            session.commit()
            logger.info(f"Stored {records_added} crop yield records for {state}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing yield data: {str(e)}")
        finally:
            session.close()
        
        return records_added


class SatelliteNDVIIngestion:
    """Ingest satellite NDVI data from Sentinel-2 public archives"""
    
    def __init__(self, db_connector: DatabaseConnector = None):
        """
        Initialize NDVI ingestion.
        
        Args:
            db_connector: Database connector instance.
        """
        self.db = db_connector
        try:
            from sentinelsat import SentinelAPI
            self.SentinelAPI = SentinelAPI
        except ImportError:
            logger.warning("sentinelsat not installed. NDVI ingestion will be limited.")
            self.SentinelAPI = None
    
    def fetch_ndvi_data(self, latitude: float, longitude: float, 
                        start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch Sentinel-2 NDVI data from public archives.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)
            
        Returns:
            List of NDVI data points
        """
        if not self.SentinelAPI:
            logger.warning("Cannot fetch Sentinel-2 data: sentinelsat not available")
            return []
        
        try:
            # This is a stub implementation
            # In production, would use: SentinelAPI(user, password).query()
            logger.info(f"Querying Sentinel-2 for coordinates ({latitude}, {longitude})")
            return []
            
        except Exception as e:
            logger.error(f"Error fetching NDVI data: {str(e)}")
            return []
    
    def store_ndvi_data(self, ndvi_records: List[Dict], state: str, district: str, crop: str) -> int:
        """
        Store NDVI values in database.
        
        Args:
            ndvi_records: List of NDVI data dictionaries
            state: State name
            district: District name
            crop: Crop name
            
        Returns:
            Number of records inserted
        """
        session = self.db.get_session()
        records_added = 0
        
        try:
            for record in ndvi_records:
                try:
                    observation = SatelliteNDVIData(
                        state=state,
                        district=district,
                        crop=crop,
                        observation_date=datetime.fromisoformat(record.get('observation_date')),
                        ndvi_value=float(record.get('ndvi_value', 0)),
                        cloud_coverage=float(record.get('cloud_coverage', 0)),
                        sentinel_tile=record.get('tile'),
                        processing_level=record.get('level', 'L2A'),
                        latitude=float(record.get('latitude', 0)),
                        longitude=float(record.get('longitude', 0)),
                        acquisition_date=datetime.fromisoformat(record.get('acquisition_date'))
                    )
                    session.add(observation)
                    records_added += 1
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing NDVI record: {str(e)}")
                    continue
            
            session.commit()
            logger.info(f"Stored {records_added} NDVI records")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing NDVI data: {str(e)}")
        finally:
            session.close()
        
        return records_added


class SoilFertilityIngestion:
    """Ingest soil fertility measurements"""
    
    def __init__(self, db_connector: DatabaseConnector = None):
        """Initialize soil fertility ingestion."""
        self.db = db_connector
    
    def store_soil_fertility(self, state: str, district: str, 
                            nitrogen: float, phosphorus: float, potassium: float,
                            ph: Optional[float] = None,
                            organic_carbon: Optional[float] = None,
                            electrical_conductivity: Optional[float] = None) -> bool:
        """
        Store soil fertility measurement.
        
        Args:
            state: State name
            district: District name
            nitrogen: N content (kg/hectare)
            phosphorus: P content (kg/hectare)
            potassium: K content (kg/hectare)
            ph: Soil pH
            organic_carbon: Organic carbon percentage
            electrical_conductivity: EC in dS/m
            
        Returns:
            True if successful
        """
        session = self.db.get_session()
        
        try:
            # Calculate Soil Fertility Index (SFI)
            # Normalized composite of N (40%), P (30%), K (30%)
            sfi = self._calculate_sfi(nitrogen, phosphorus, potassium)
            
            record = SoilFertilityRecord(
                state=state,
                district=district,
                measurement_date=datetime.utcnow(),
                nitrogen=nitrogen,
                phosphorus=phosphorus,
                potassium=potassium,
                soil_fertility_index=sfi,
                ph=ph,
                organic_carbon=organic_carbon,
                electrical_conductivity=electrical_conductivity
            )
            session.add(record)
            session.commit()
            logger.info(f"Stored soil fertility record for {state}, {district}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing soil fertility data: {str(e)}")
            return False
        finally:
            session.close()
    
    @staticmethod
    def _calculate_sfi(nitrogen: float, phosphorus: float, potassium: float) -> float:
        """
        Calculate Soil Fertility Index as weighted composite.
        
        Weights: N (40%), P (30%), K (30%)
        Normalized to 0-1 scale based on typical ranges.
        
        Args:
            nitrogen: N content (kg/hectare)
            phosphorus: P content (kg/hectare)
            potassium: K content (kg/hectare)
            
        Returns:
            Normalized SFI (0-1)
        """
        # Normalize each nutrient to 0-1 based on practical ranges
        n_norm = min(nitrogen / 200.0, 1.0)  # Max typical: 200 kg/ha
        p_norm = min(phosphorus / 150.0, 1.0)  # Max typical: 150 kg/ha
        k_norm = min(potassium / 200.0, 1.0)  # Max typical: 200 kg/ha
        
        # Weighted composite
        sfi = (0.4 * n_norm) + (0.3 * p_norm) + (0.3 * k_norm)
        return float(np.clip(sfi, 0.0, 1.0))


class IngestionOrchestrator:
    """Orchestrates data ingestion from all sources"""
    
    def __init__(self, db_connector: DatabaseConnector = None):
        """Initialize ingestion orchestrator."""
        self.db = db_connector or DatabaseConnector()
        self.weather = WeatherIngestion(db_connector=self.db)
        self.yield_data = CropYieldIngestion(db_connector=self.db)
        self.ndvi = SatelliteNDVIIngestion(db_connector=self.db)
        self.soil = SoilFertilityIngestion(db_connector=self.db)
    
    def log_ingestion(self, source_type: str, operation: str, status: str,
                     records_processed: int, records_failed: int = 0,
                     error_message: str = None, start_time: datetime = None):
        """Log ingestion operation to database."""
        session = self.db.get_session()
        
        try:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() if start_time else None
            
            log_entry = IngestionLog(
                source_type=source_type,
                operation=operation,
                status=status,
                records_processed=records_processed,
                records_failed=records_failed,
                error_message=error_message,
                start_time=start_time or end_time,
                end_time=end_time,
                duration_seconds=duration
            )
            session.add(log_entry)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging ingestion: {str(e)}")
        finally:
            session.close()


if __name__ == '__main__':
    # Example usage
    db = DatabaseConnector()
    db.create_tables()
    
    # Initialize orchestrator
    orchestrator = IngestionOrchestrator(db)
    
    logger.info("Ingestion layer initialized successfully")
