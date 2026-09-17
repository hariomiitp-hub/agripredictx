"""Data preparation and preprocessing for AgriPredictX."""
import numpy as np
import pandas as pd
from typing import Tuple
from agricultural_indicators import (
    CumulativeRainfallCalculator,
    GrowingDegreeDaysCalculator,
    NDVICalculator,
    SoilFertilityIndexCalculator,
)
from config import CROP_REQUIREMENTS, SOIL_TYPES, MODEL_CONFIG


FORECAST_MONTHS = ("month_1", "month_2", "month_3")


def get_feature_columns() -> list[str]:
    """Return the canonical feature order used for training and inference."""
    feature_cols = [
        "N", "P", "K", "pH", "moisture", "organic_carbon", "electrical_conductivity",
        "dap", "urea", "ssp", "mop", "zinc", "iron", "copper", "boron", "manganese",
        "temperature", "humidity", "rainfall",
    ]

    for month in FORECAST_MONTHS:
        feature_cols.extend([
            f"{month}_temperature",
            f"{month}_humidity",
            f"{month}_rainfall",
        ])

    feature_cols.extend([
        "gdd",
        "cumulative_rainfall",
        "soil_fertility_index",
        "ndvi",
    ])
    feature_cols.append("soil_type")
    return feature_cols


def _get_expected_humidity(requirements: dict) -> float:
    """Estimate a realistic humidity center from rainfall and moisture needs."""
    rainfall_mid = np.mean(requirements["rainfall"])
    moisture_mid = np.mean(requirements["moisture"])
    humidity = 45 + (rainfall_mid / 500) * 30 + (moisture_mid / 50) * 15
    return float(np.clip(humidity, 40, 90))


def _generate_forecast_window(requirements: dict) -> list[tuple[float, float, float]]:
    """Generate a 3-month forecast window around crop requirements."""
    base_temp = np.mean(requirements["temp"])
    base_rainfall = np.mean(requirements["rainfall"])
    base_humidity = _get_expected_humidity(requirements)
    monthly_rainfall_factors = (0.95, 1.0, 1.05)

    forecast_window = []
    for month_index, rainfall_factor in enumerate(monthly_rainfall_factors):
        temp = np.random.normal(base_temp + (month_index - 1) * 0.6, 2.8)
        humidity = np.random.normal(base_humidity + (month_index - 1) * 2.0, 7.0)
        rainfall = np.random.normal(base_rainfall * rainfall_factor, 18)

        forecast_window.append((
            float(np.clip(temp, -10, 50)),
            float(np.clip(humidity, 0, 100)),
            float(np.clip(rainfall, 0, 500)),
        ))

    return forecast_window


def generate_synthetic_training_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    Generate synthetic training data based on crop requirements.
    This simulates historical agricultural data.
    """
    np.random.seed(42)
    
    data = []
    crops = list(CROP_REQUIREMENTS.keys())
    
    for _ in range(n_samples):
        crop = np.random.choice(crops)
        requirements = CROP_REQUIREMENTS[crop]
        
        # Generate variations around optimal ranges
        nitrogen = np.random.normal(np.mean(requirements['N']), 20)
        phosphorus = np.random.normal(np.mean(requirements['P']), 15)
        potassium = np.random.normal(np.mean(requirements['K']), 20)
        ph = np.random.normal(np.mean(requirements['pH']), 0.3)
        moisture = np.random.normal(np.mean(requirements['moisture']), 5)
        temperature = np.random.normal(np.mean(requirements['temp']), 3)
        humidity = np.random.normal(_get_expected_humidity(requirements), 8)
        rainfall = np.random.normal(np.mean(requirements['rainfall']), 20)
        soil_type = np.random.choice(requirements['soil_type'])
        forecast_window = _generate_forecast_window(requirements)
        
        # New enhanced soil parameters
        organic_carbon = np.random.normal(1.5, 0.5)  # percentage
        electrical_conductivity = np.random.normal(1.0, 0.5)  # dS/m
        
        # Fertilizer components
        dap = np.random.normal(30, 10)  # kg/ha
        urea = np.random.normal(80, 20)  # kg/ha
        ssp = np.random.normal(20, 8)  # kg/ha
        mop = np.random.normal(25, 10)  # kg/ha
        
        # Micronutrients
        zinc = np.random.normal(2.0, 1.0)  # ppm
        iron = np.random.normal(15.0, 5.0)  # ppm
        copper = np.random.normal(1.0, 0.5)  # ppm
        boron = np.random.normal(0.8, 0.3)  # ppm
        manganese = np.random.normal(8.0, 3.0)  # ppm
        
        # Clamp values to valid ranges
        nitrogen = np.clip(nitrogen, 0, 200)
        phosphorus = np.clip(phosphorus, 0, 150)
        potassium = np.clip(potassium, 0, 200)
        ph = np.clip(ph, 3.5, 9.0)
        moisture = np.clip(moisture, 0, 50)
        temperature = np.clip(temperature, -10, 50)
        humidity = np.clip(humidity, 0, 100)
        rainfall = np.clip(rainfall, 0, 500)
        organic_carbon = np.clip(organic_carbon, 0, 5)
        electrical_conductivity = np.clip(electrical_conductivity, 0, 10)
        dap = np.clip(dap, 0, 100)
        urea = np.clip(urea, 0, 200)
        ssp = np.clip(ssp, 0, 100)
        mop = np.clip(mop, 0, 100)
        zinc = np.clip(zinc, 0, 10)
        iron = np.clip(iron, 0, 50)
        copper = np.clip(copper, 0, 5)
        boron = np.clip(boron, 0, 2)
        manganese = np.clip(manganese, 0, 20)
        
        # Simulate yield based on how well conditions match requirements
        yield_score = calculate_yield_score(
            nitrogen, phosphorus, potassium, ph, moisture,
            temperature, humidity, rainfall, crop
        )

        forecast_payload = {}
        forecast_windows = []
        for index, (month_temp, month_humidity, month_rainfall) in enumerate(
            forecast_window, 1
        ):
            forecast_payload[f"month_{index}_temperature"] = month_temp
            forecast_payload[f"month_{index}_humidity"] = month_humidity
            forecast_payload[f"month_{index}_rainfall"] = month_rainfall
            forecast_windows.append({
                "temperature": month_temp,
                "humidity": month_humidity,
                "rainfall": month_rainfall,
            })

        soil_payload = {
            "nitrogen": nitrogen,
            "phosphorus": phosphorus,
            "potassium": potassium,
            "ph": ph,
            "moisture": moisture,
            "soil_type": soil_type,
            "organic_carbon": organic_carbon,
            "electrical_conductivity": electrical_conductivity,
            "dap": dap,
            "urea": urea,
            "ssp": ssp,
            "mop": mop,
            "zinc": zinc,
            "iron": iron,
            "copper": copper,
            "boron": boron,
            "manganese": manganese,
        }
        soil_fertility_index = SoilFertilityIndexCalculator.calculate(soil_payload)
        gdd = GrowingDegreeDaysCalculator.calculate_seasonal_gdd(
            current_temperature=temperature,
            humidity=humidity,
            rainfall=rainfall,
            forecast_windows=forecast_windows,
            season_length_days=requirements.get("duration", 120),
        )
        cumulative_rainfall = CumulativeRainfallCalculator.calculate_seasonal_rainfall(
            current_rainfall=rainfall,
            forecast_windows=forecast_windows,
            months_ahead=3,
        )
        ndvi = NDVICalculator.calculate(
            soil_fertility_index=soil_fertility_index,
            rainfall=cumulative_rainfall,
            current_temperature=temperature,
            soil_moisture=moisture,
        )
        
        data.append({
            'N': nitrogen,
            'P': phosphorus,
            'K': potassium,
            'pH': ph,
            'moisture': moisture,
            'organic_carbon': organic_carbon,
            'electrical_conductivity': electrical_conductivity,
            'dap': dap,
            'urea': urea,
            'ssp': ssp,
            'mop': mop,
            'zinc': zinc,
            'iron': iron,
            'copper': copper,
            'boron': boron,
            'manganese': manganese,
            'temperature': temperature,
            'humidity': humidity,
            'rainfall': rainfall,
            **forecast_payload,
            'gdd': gdd,
            'cumulative_rainfall': cumulative_rainfall,
            'soil_fertility_index': soil_fertility_index,
            'ndvi': ndvi,
            'soil_type': SOIL_TYPES[soil_type],
            'crop': crop,
            'yield': yield_score,
        })
    
    return pd.DataFrame(data)


def calculate_yield_score(n, p, k, ph, moisture, temp, humidity, rainfall, crop):
    """
    Calculate yield score based on how well parameters match crop requirements.
    Score ranges from 0 to 100.
    """
    requirements = CROP_REQUIREMENTS[crop]
    
    # Calculate deviations from optimal ranges
    scores = []
    
    # Nitrogen score
    n_score = calculate_parameter_score(n, requirements['N'])
    scores.append(n_score * 0.25)
    
    # Phosphorus score
    p_score = calculate_parameter_score(p, requirements['P'])
    scores.append(p_score * 0.15)
    
    # Potassium score
    k_score = calculate_parameter_score(k, requirements['K'])
    scores.append(k_score * 0.20)
    
    # pH score
    ph_score = calculate_parameter_score(ph, requirements['pH'])
    scores.append(ph_score * 0.10)
    
    # Moisture score
    moisture_score = calculate_parameter_score(moisture, requirements['moisture'])
    scores.append(moisture_score * 0.15)
    
    # Temperature score
    temp_score = calculate_parameter_score(temp, requirements['temp'])
    scores.append(temp_score * 0.10)
    
    # Rainfall score
    rainfall_score = calculate_parameter_score(rainfall, requirements['rainfall'])
    scores.append(rainfall_score * 0.05)
    
    # Add some noise to make it more realistic
    yield_score = sum(scores) * 100 + np.random.normal(0, 5)
    
    return np.clip(yield_score, 0, 100)


def calculate_parameter_score(value, optimal_range: Tuple[float, float]) -> float:
    """
    Calculate how well a value matches an optimal range.
    Returns score between 0 and 1.
    """
    min_val, max_val = optimal_range
    mid_val = (min_val + max_val) / 2
    range_width = max_val - min_val
    
    if value < min_val:
        # Below range
        deviation = min_val - value
        return max(0, 1 - (deviation / range_width) * 0.5)
    elif value > max_val:
        # Above range
        deviation = value - max_val
        return max(0, 1 - (deviation / range_width) * 0.5)
    else:
        # Within range - closer to middle is better
        distance_from_mid = abs(value - mid_val)
        return 1 - (distance_from_mid / (range_width / 2)) * 0.3


def prepare_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, list]:
    """
    Prepare features and target for model training.
    Returns X, y, and feature names.
    """
    # Create a mapping for crop labels
    crops = df['crop'].unique()
    crop_mapping = {crop: idx for idx, crop in enumerate(crops)}
    
    feature_cols = get_feature_columns()
    
    X = df[feature_cols].values
    y = df['crop'].map(crop_mapping).values
    
    return X, y, feature_cols, crop_mapping, crops


def normalize_features(X_train: np.ndarray, X_test: np.ndarray = None) -> Tuple:
    """
    Normalize features using z-score normalization.
    """
    from sklearn.preprocessing import StandardScaler
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    if X_test is not None:
        X_test_scaled = scaler.transform(X_test)
        return X_train_scaled, X_test_scaled, scaler
    
    return X_train_scaled, scaler


def split_data(X: np.ndarray, y: np.ndarray) -> Tuple:
    """
    Split data into training and testing sets.
    """
    from sklearn.model_selection import train_test_split
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=MODEL_CONFIG['test_size'],
        random_state=MODEL_CONFIG['random_state'],
        stratify=y
    )
    
    return X_train, X_test, y_train, y_test


def create_sample_dataset() -> pd.DataFrame:
    """
    Create and return a sample dataset for training.
    """
    return generate_synthetic_training_data(n_samples=1000)
