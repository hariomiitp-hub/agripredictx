"""Advanced feature engineering for yield prediction"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Compute agronomically significant engineered features"""
    
    # Base temperatures for different crops (Celsius)
    BASE_TEMPERATURES = {
        'wheat': 10,
        'rice': 10,
        'maize': 10,
        'cotton': 15.6,
        'sugarcane': 15,
        'potato': 7,
        'tomato': 10,
        'chilli': 15,
        'soybean': 10,
        'groundnut': 15,
        'sorghum': 12,
        'pearl_millet': 13,
        'chickpea': 8,
        'lentil': 8,
        'mustard': 5,
    }
    
    @staticmethod
    def calculate_growing_degree_days(daily_temps: pd.Series, crop: str) -> float:
        """
        Calculate Cumulative Growing Degree Days (GDD).
        
        GDD = sum of [max((T_max + T_min)/2 - base_temp, 0)]
        
        Where:
        - T_max, T_min are daily max/min temperatures
        - base_temp is crop-specific (e.g., 10°C for wheat/rice)
        - Only positive contributions accumulate
        
        Args:
            daily_temps: Series with columns 'temp_max', 'temp_min'
            crop: Crop name
            
        Returns:
            Cumulative GDD value
        """
        base_temp = FeatureEngineer.BASE_TEMPERATURES.get(crop.lower(), 10)
        
        # Calculate mean daily temperature
        mean_temps = (daily_temps['temp_max'] + daily_temps['temp_min']) / 2.0
        
        # Calculate GDD: max((mean_temp - base), 0) for each day, then sum
        gdd_daily = np.maximum(mean_temps - base_temp, 0)
        cumulative_gdd = gdd_daily.sum()
        
        return float(cumulative_gdd)
    
    @staticmethod
    def calculate_rolling_rainfall(rainfall_series: pd.Series, window_days: int = 7) -> Tuple[float, float]:
        """
        Calculate rolling rainfall totals capturing moisture availability during critical growth stages.
        
        Args:
            rainfall_series: Series of daily rainfall (mm)
            window_days: Window size (7 or 14 days)
            
        Returns:
            Tuple of (mean_rolling_total, peak_rolling_total)
        """
        rolling_sum = rainfall_series.rolling(window=window_days, min_periods=1).sum()
        
        mean_rolling = float(rolling_sum.mean())
        peak_rolling = float(rolling_sum.max())
        
        return mean_rolling, peak_rolling
    
    @staticmethod
    def calculate_rainfall_statistics(rainfall_series: pd.Series) -> Dict[str, float]:
        """
        Calculate comprehensive rainfall statistics.
        
        Args:
            rainfall_series: Series of daily rainfall (mm)
            
        Returns:
            Dictionary with rainfall metrics
        """
        return {
            'total_rainfall': float(rainfall_series.sum()),
            'mean_daily_rainfall': float(rainfall_series.mean()),
            'max_daily_rainfall': float(rainfall_series.max()),
            'rainfall_7day_mean': float(rainfall_series.rolling(7, min_periods=1).sum().mean()),
            'rainfall_14day_mean': float(rainfall_series.rolling(14, min_periods=1).sum().mean()),
            'rainy_days_count': int((rainfall_series > 2.5).sum()),  # Days with >2.5mm
        }
    
    @staticmethod
    def calculate_soil_fertility_index(nitrogen: float, phosphorus: float, 
                                       potassium: float, 
                                       max_n: float = 200.0,
                                       max_p: float = 150.0,
                                       max_k: float = 200.0) -> float:
        """
        Calculate Soil Fertility Index (SFI) as weighted composite.
        
        SFI = (N_norm * 0.40) + (P_norm * 0.30) + (K_norm * 0.30)
        
        Where each nutrient is normalized to 0-1 scale:
        - N: Nitrogen (40% weight) - typical range 0-200 kg/ha
        - P: Phosphorus (30% weight) - typical range 0-150 kg/ha
        - K: Potassium (30% weight) - typical range 0-200 kg/ha
        
        Args:
            nitrogen: N concentration (kg/hectare)
            phosphorus: P concentration (kg/hectare)
            potassium: K concentration (kg/hectare)
            max_n: Maximum N for normalization
            max_p: Maximum P for normalization
            max_k: Maximum K for normalization
            
        Returns:
            Normalized SFI (0-1 scale)
        """
        # Normalize each nutrient to 0-1
        n_norm = min(nitrogen / max_n, 1.0)
        p_norm = min(phosphorus / max_p, 1.0)
        k_norm = min(potassium / max_k, 1.0)
        
        # Weighted composite
        sfi = (n_norm * 0.40) + (p_norm * 0.30) + (k_norm * 0.30)
        
        return float(np.clip(sfi, 0.0, 1.0))
    
    @staticmethod
    def calculate_ndvi_features(ndvi_series: pd.Series, days_after_sowing: int = 60) -> Dict[str, float]:
        """
        Extract NDVI features as proxy indicators of canopy health.
        
        Args:
            ndvi_series: Series of NDVI values over time
            days_after_sowing: Days to look for NDVI at specific growth stage
            
        Returns:
            Dictionary with NDVI features
        """
        # Handle empty series
        if ndvi_series.empty or ndvi_series.isna().all():
            return {
                'ndvi_peak': 0.0,
                'ndvi_mean': 0.0,
                'ndvi_at_60das': 0.0,
                'ndvi_gain': 0.0,
            }
        
        # Remove NaN values
        ndvi_clean = ndvi_series.dropna()
        
        features = {
            'ndvi_peak': float(ndvi_clean.max()),  # Peak canopy health
            'ndvi_mean': float(ndvi_clean.mean()),  # Average health
            'ndvi_std': float(ndvi_clean.std()),   # Variability
        }
        
        # NDVI at specific growth stage (60 days after sowing, if available)
        if len(ndvi_clean) >= days_after_sowing:
            features['ndvi_at_60das'] = float(ndvi_clean.iloc[days_after_sowing])
        else:
            features['ndvi_at_60das'] = float(ndvi_clean.iloc[-1]) if not ndvi_clean.empty else 0.0
        
        # NDVI gain (improvement over growing season)
        if len(ndvi_clean) > 1:
            features['ndvi_gain'] = float(ndvi_clean.iloc[-1] - ndvi_clean.iloc[0])
        else:
            features['ndvi_gain'] = 0.0
        
        return features
    
    @staticmethod
    def encode_categorical_features(crop: str, state: str, district: str,
                                    crop_mapping: Dict = None,
                                    state_mapping: Dict = None,
                                    district_mapping: Dict = None) -> Dict[str, int]:
        """
        Encode categorical representations of crop variety, state, and district.
        
        Args:
            crop: Crop name
            state: State name
            district: District name
            crop_mapping: Pre-built mapping dictionary for crops
            state_mapping: Pre-built mapping dictionary for states
            district_mapping: Pre-built mapping dictionary for districts
            
        Returns:
            Dictionary with encoded values
        """
        # Default mappings if not provided (would typically be loaded from training data)
        if crop_mapping is None:
            crop_mapping = {}
        if state_mapping is None:
            state_mapping = {}
        if district_mapping is None:
            district_mapping = {}
        
        return {
            'crop_encoded': crop_mapping.get(crop.lower(), 0),
            'state_encoded': state_mapping.get(state.upper(), 0),
            'district_encoded': district_mapping.get(district.upper(), 0),
        }
    
    @staticmethod
    def create_comprehensive_features(weather_data: pd.DataFrame,
                                     soil_data: Dict,
                                     ndvi_data: pd.Series,
                                     crop: str,
                                     state: str,
                                     district: str,
                                     crop_mapping: Dict = None,
                                     state_mapping: Dict = None,
                                     district_mapping: Dict = None) -> Dict:
        """
        Create comprehensive feature set for yield prediction.
        
        Combines all engineered features:
        - Cumulative Growing Degree Days (GDD)
        - 7-day and 14-day rolling rainfall totals
        - Soil Fertility Index (SFI)
        - NDVI peak and NDVI at 60 DAS
        - Encoded categorical features
        
        Args:
            weather_data: DataFrame with columns 'temp_max', 'temp_min', 'rainfall'
            soil_data: Dictionary with 'nitrogen', 'phosphorus', 'potassium'
            ndvi_data: Series of NDVI values
            crop: Crop name
            state: State name
            district: District name
            crop_mapping: Crop encoding mapping
            state_mapping: State encoding mapping
            district_mapping: District encoding mapping
            
        Returns:
            Comprehensive feature dictionary
        """
        features = {}
        
        # Growing Degree Days
        if 'temp_max' in weather_data.columns and 'temp_min' in weather_data.columns:
            features['gdd_cumulative'] = FeatureEngineer.calculate_growing_degree_days(
                weather_data[['temp_max', 'temp_min']], crop
            )
        else:
            features['gdd_cumulative'] = 0.0
        
        # Rolling rainfall totals
        if 'rainfall' in weather_data.columns:
            rainfall_7day, rainfall_7day_peak = FeatureEngineer.calculate_rolling_rainfall(
                weather_data['rainfall'], window_days=7
            )
            rainfall_14day, rainfall_14day_peak = FeatureEngineer.calculate_rolling_rainfall(
                weather_data['rainfall'], window_days=14
            )
            
            features['rainfall_7day_mean'] = rainfall_7day
            features['rainfall_7day_peak'] = rainfall_7day_peak
            features['rainfall_14day_mean'] = rainfall_14day
            features['rainfall_14day_peak'] = rainfall_14day_peak
        else:
            features['rainfall_7day_mean'] = 0.0
            features['rainfall_7day_peak'] = 0.0
            features['rainfall_14day_mean'] = 0.0
            features['rainfall_14day_peak'] = 0.0
        
        # Soil Fertility Index
        sfi = FeatureEngineer.calculate_soil_fertility_index(
            soil_data.get('nitrogen', 0),
            soil_data.get('phosphorus', 0),
            soil_data.get('potassium', 0)
        )
        features['soil_fertility_index'] = sfi
        
        # NDVI features
        ndvi_features = FeatureEngineer.calculate_ndvi_features(ndvi_data)
        features.update(ndvi_features)
        
        # Categorical encodings
        categorical = FeatureEngineer.encode_categorical_features(
            crop, state, district,
            crop_mapping, state_mapping, district_mapping
        )
        features.update(categorical)
        
        return features


class TimeSeriesFeatureExtractor:
    """Extract features from time series data"""
    
    @staticmethod
    def extract_trend(series: pd.Series) -> float:
        """Extract trend from time series using linear regression"""
        if len(series) < 2:
            return 0.0
        
        x = np.arange(len(series))
        y = series.values
        
        # Skip NaN values
        valid_idx = ~np.isnan(y)
        x_valid = x[valid_idx]
        y_valid = y[valid_idx]
        
        if len(x_valid) < 2:
            return 0.0
        
        coefficients = np.polyfit(x_valid, y_valid, 1)
        return float(coefficients[0])  # Slope
    
    @staticmethod
    def extract_seasonality(series: pd.Series, period: int = 30) -> float:
        """Extract seasonality strength from time series"""
        if len(series) < period * 2:
            return 0.0
        
        # Calculate variance within and between seasons
        seasonal_var = 0.0
        for i in range(period):
            seasonal_values = series.iloc[i::period]
            seasonal_var += seasonal_values.var()
        
        return float(seasonal_var / period)
    
    @staticmethod
    def extract_stationarity(series: pd.Series) -> float:
        """Simple stationarity measure (ratio of variance to mean)"""
        if series.mean() == 0:
            return 0.0
        
        cv = series.std() / abs(series.mean())
        return float(cv)
