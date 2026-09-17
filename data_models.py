"""Data models for soil and weather parameters"""
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple, Dict
from enum import Enum


class SoilType(Enum):
    """Soil type enumeration"""
    SANDY = "sandy"
    CLAY = "clay"
    LOAMY = "loamy"


@dataclass
class SoilParameters:
    """Represents comprehensive soil composition and health parameters"""
    nitrogen: float  # kg/hectare
    phosphorus: float  # kg/hectare
    potassium: float  # kg/hectare
    ph: float  # pH level (0-14)
    moisture: float  # percentage (0-100)
    soil_type: str  # 'sandy', 'clay', 'loamy', 'silt', 'peat'
    
    # Enhanced soil parameters
    organic_carbon: float  # percentage (0-5%)
    electrical_conductivity: float  # dS/m (0-10)
    
    # Fertilizer components
    dap: float  # kg/hectare (0-100)
    urea: float  # kg/hectare (0-200)
    ssp: float  # kg/hectare (0-100)
    mop: float  # kg/hectare (0-100)
    
    # Micronutrients
    zinc: float  # ppm (0-10)
    iron: float  # ppm (0-50)
    copper: float  # ppm (0-5)
    boron: float  # ppm (0-2)
    manganese: float  # ppm (0-20)
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)
    
    def validate(self) -> bool:
        """Validate soil parameters are within reasonable ranges"""
        from config import SOIL_CONFIG
        
        checks = [
            0 <= self.nitrogen <= 200,
            0 <= self.phosphorus <= 150,
            0 <= self.potassium <= 200,
            3.5 <= self.ph <= 9.0,
            0 <= self.moisture <= 50,
            self.soil_type in ['sandy', 'clay', 'loamy', 'silt', 'peat'],
            0 <= self.organic_carbon <= 5.0,
            0 <= self.electrical_conductivity <= 10.0,
            0 <= self.dap <= 100,
            0 <= self.urea <= 200,
            0 <= self.ssp <= 100,
            0 <= self.mop <= 100,
            0 <= self.zinc <= 10,
            0 <= self.iron <= 50,
            0 <= self.copper <= 5,
            0 <= self.boron <= 2,
            0 <= self.manganese <= 20,
        ]
        return all(checks)


@dataclass
class WeatherData:
    """Represents weather conditions"""
    temperature: float  # Celsius
    humidity: float  # percentage (0-100)
    rainfall: float  # mm/month
    wind_speed: Optional[float] = None  # km/h
    sunshine_hours: Optional[float] = None  # hours/day
    
    def to_dict(self):
        """Convert to dictionary"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}
    
    def validate(self) -> bool:
        """Validate weather parameters are within reasonable ranges"""
        checks = [
            -10 <= self.temperature <= 50,
            0 <= self.humidity <= 100,
            0 <= self.rainfall <= 500,
        ]
        if self.wind_speed is not None:
            checks.append(0 <= self.wind_speed <= 100)
        if self.sunshine_hours is not None:
            checks.append(0 <= self.sunshine_hours <= 24)
        return all(checks)


@dataclass
class WeatherForecast:
    """Represents the automated 3-month OpenWeather outlook."""
    month_1: WeatherData
    month_2: WeatherData
    month_3: WeatherData
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'month_1': self.month_1.to_dict(),
            'month_2': self.month_2.to_dict(),
            'month_3': self.month_3.to_dict(),
        }
    
    def validate(self) -> bool:
        """Validate all forecast months"""
        return all([
            self.month_1.validate(),
            self.month_2.validate(),
            self.month_3.validate()
        ])

    def get_months(self) -> List[WeatherData]:
        """Return forecast months in chronological order."""
        return [self.month_1, self.month_2, self.month_3]

    def get_total_rainfall(self) -> float:
        """Get total forecast rainfall across all months."""
        return sum(month.rainfall for month in self.get_months())
    
    def get_average_conditions(self) -> WeatherData:
        """Get average weather conditions across the 3-month outlook."""
        months = self.get_months()
        avg_temp = sum(month.temperature for month in months) / len(months)
        avg_humidity = sum(month.humidity for month in months) / len(months)
        avg_rainfall = sum(month.rainfall for month in months) / len(months)

        # Use month 2 as representative for optional fields.
        representative_month = self.month_2
        wind_speed = representative_month.wind_speed
        sunshine_hours = representative_month.sunshine_hours

        return WeatherData(
            temperature=avg_temp,
            humidity=avg_humidity,
            rainfall=avg_rainfall,
            wind_speed=wind_speed,
            sunshine_hours=sunshine_hours
        )


@dataclass
class YieldPrediction:
    """Represents yield prediction for a crop"""
    crop_name: str
    predicted_yield: float  # tons per hectare
    yield_range: Tuple[float, float]  # (min, max) tons per hectare
    confidence_level: float  # 0-1
    factors_affecting_yield: List[str]
    yield_category: str  # 'low', 'medium', 'high', 'very_high'
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class FertilizerRecommendation:
    """Represents fertilizer recommendations"""
    crop_name: str
    nitrogen_recommendation: float  # kg/ha
    phosphorus_recommendation: float  # kg/ha
    potassium_recommendation: float  # kg/ha
    micronutrient_recommendations: Dict[str, float]  # nutrient -> amount
    application_schedule: Dict[str, str]  # timing -> fertilizer_type
    total_cost_estimate: Optional[float] = None  # estimated cost
    soil_deficiencies: List[str] = None  # list of deficiencies found
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class FarmInput:
    """Complete input for enhanced crop prediction"""
    soil: SoilParameters
    weather: WeatherData
    weather_forecast: Optional[WeatherForecast] = None
    agricultural_indicators: Optional[Dict[str, float]] = None
    region: Optional[str] = None
    farm_size: Optional[float] = None  # hectares
    irrigation_available: Optional[bool] = None
    historical_yield: Optional[List[float]] = None
    location_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country_code: Optional[str] = "IN"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    land_area_unit: Optional[str] = "hectares"
    
    def validate(self) -> tuple[bool, List[str]]:
        """Validate all inputs"""
        errors = []
        
        if not self.soil.validate():
            errors.append("Invalid soil parameters")
        if not self.weather.validate():
            errors.append("Invalid weather parameters")
        if self.weather_forecast and not self.weather_forecast.validate():
            errors.append("Invalid weather forecast")
        
        return len(errors) == 0, errors


@dataclass
class CropRecommendation:
    """Recommendation for a single crop"""
    crop_name: str
    suitability_score: float  # 0-100
    rank: int
    matching_factors: List[str]
    mismatched_factors: List[str]
    recommendation_reason: str
    estimated_yield: Optional[float] = None
    risk_level: str = "medium"  # low, medium, high
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class RecommendationResult:
    """Complete recommendation result with enhanced features"""
    primary_recommendation: CropRecommendation
    alternatives: List[CropRecommendation]
    farm_input: FarmInput
    confidence: float  # 0-1
    model_version: str = "2.0"
    
    # Enhanced features
    yield_prediction: Optional[YieldPrediction] = None
    fertilizer_recommendation: Optional[FertilizerRecommendation] = None
    weather_risk_assessment: Optional[Dict[str, str]] = None  # risk factors for 3 months
    seasonal_suitability: Optional[Dict[str, float]] = None  # season -> suitability score
    
    def to_dict(self):
        """Convert to dictionary"""
        result = {
            'primary_recommendation': self.primary_recommendation.to_dict(),
            'alternatives': [alt.to_dict() for alt in self.alternatives],
            'confidence': self.confidence,
            'model_version': self.model_version,
        }

        farm_context = {
            'location_name': self.farm_input.location_name,
            'district': self.farm_input.district,
            'state': self.farm_input.state,
            'country_code': self.farm_input.country_code,
            'latitude': self.farm_input.latitude,
            'longitude': self.farm_input.longitude,
            'farm_size': self.farm_input.farm_size,
            'land_area_unit': self.farm_input.land_area_unit,
            'region': self.farm_input.region,
        }
        result['farm_context'] = {
            key: value for key, value in farm_context.items()
            if value is not None and value != ""
        }
        
        if self.yield_prediction:
            result['yield_prediction'] = self.yield_prediction.to_dict()
        if self.fertilizer_recommendation:
            result['fertilizer_recommendation'] = self.fertilizer_recommendation.to_dict()
        if self.weather_risk_assessment:
            result['weather_risk_assessment'] = self.weather_risk_assessment
        if self.seasonal_suitability:
            result['seasonal_suitability'] = self.seasonal_suitability
            
        return result
