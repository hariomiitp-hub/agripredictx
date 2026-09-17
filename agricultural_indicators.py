"""
Agricultural indicator calculators for SFI, GDD, rainfall, and NDVI.
"""

from __future__ import annotations

import logging
import math
import os
from datetime import date, timedelta
from typing import Dict, Optional, Tuple

try:
    import ee  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    ee = None


logger = logging.getLogger(__name__)


class SoilFertilityIndexCalculator:
    """Calculate Soil Fertility Index (SFI) on a 0-1 scale."""

    NITROGEN_OPTIMAL = 200.0
    PHOSPHORUS_OPTIMAL = 100.0
    POTASSIUM_OPTIMAL = 150.0
    PH_OPTIMAL = 6.5
    MOISTURE_OPTIMAL = 60.0
    ORGANIC_CARBON_OPTIMAL = 2.0
    EC_OPTIMAL = 1.0

    ZINC_OPTIMAL = 3.0
    IRON_OPTIMAL = 20.0
    COPPER_OPTIMAL = 1.5
    BORON_OPTIMAL = 1.0
    MANGANESE_OPTIMAL = 10.0

    SOIL_TYPE_SCORES = {
        "loamy": 1.0,
        "clay": 0.85,
        "silt": 0.82,
        "peat": 0.78,
        "sandy": 0.62,
    }

    @staticmethod
    def calculate_parameter_score(value: float, optimal: float, tolerance: float = 0.3) -> float:
        """Return a normalized score where values near the optimum score highest."""
        if value == 0:
            return 0.0

        deviation_ratio = abs(value - optimal) / optimal
        if deviation_ratio <= tolerance:
            return 1.0
        if deviation_ratio <= tolerance * 2:
            return 0.7
        if deviation_ratio <= tolerance * 3:
            return 0.4
        return max(0.0, 1.0 - deviation_ratio)

    @staticmethod
    def calculate_macronutrient_score(nitrogen: float, phosphorus: float, potassium: float) -> float:
        """Calculate the NPK fertility score."""
        n_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            nitrogen, SoilFertilityIndexCalculator.NITROGEN_OPTIMAL
        )
        p_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            phosphorus, SoilFertilityIndexCalculator.PHOSPHORUS_OPTIMAL
        )
        k_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            potassium, SoilFertilityIndexCalculator.POTASSIUM_OPTIMAL
        )
        return (n_score + p_score + k_score) / 3.0

    @staticmethod
    def calculate_micronutrient_score(
        zinc: float,
        iron: float,
        copper: float,
        boron: float,
        manganese: float,
    ) -> float:
        """Calculate the micronutrient fertility score."""
        zinc_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            zinc, SoilFertilityIndexCalculator.ZINC_OPTIMAL, tolerance=0.2
        )
        iron_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            iron, SoilFertilityIndexCalculator.IRON_OPTIMAL, tolerance=0.2
        )
        copper_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            copper, SoilFertilityIndexCalculator.COPPER_OPTIMAL, tolerance=0.2
        )
        boron_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            boron, SoilFertilityIndexCalculator.BORON_OPTIMAL, tolerance=0.2
        )
        manganese_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            manganese, SoilFertilityIndexCalculator.MANGANESE_OPTIMAL, tolerance=0.2
        )
        return (zinc_score + iron_score + copper_score + boron_score + manganese_score) / 5.0

    @staticmethod
    def calculate_soil_health_score(
        ph: float,
        moisture: float,
        organic_carbon: float,
        electrical_conductivity: float,
    ) -> float:
        """Calculate the soil chemistry and moisture health score."""
        ph_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            ph, SoilFertilityIndexCalculator.PH_OPTIMAL, tolerance=0.1
        )
        moisture_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            moisture, SoilFertilityIndexCalculator.MOISTURE_OPTIMAL, tolerance=0.2
        )
        oc_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            organic_carbon, SoilFertilityIndexCalculator.ORGANIC_CARBON_OPTIMAL, tolerance=0.3
        )
        ec_score = SoilFertilityIndexCalculator.calculate_parameter_score(
            electrical_conductivity, SoilFertilityIndexCalculator.EC_OPTIMAL, tolerance=0.3
        )
        return (ph_score + moisture_score + oc_score + ec_score) / 4.0

    @staticmethod
    def calculate_fertilizer_balance_score(dap: float, urea: float, ssp: float, mop: float) -> float:
        """Score how balanced the fertilizer application mix is."""
        total_fert = dap + urea + ssp + mop
        if total_fert == 0:
            return 0.5

        avg_fert = total_fert / 4.0
        variance = sum((value - avg_fert) ** 2 for value in (dap, urea, ssp, mop)) / 4.0
        std_dev = math.sqrt(variance)

        if std_dev < avg_fert * 0.2:
            return 1.0
        if std_dev < avg_fert * 0.5:
            return 0.8
        if std_dev < avg_fert:
            return 0.6
        return 0.4

    @staticmethod
    def calculate_soil_type_score(soil_type: Optional[str]) -> float:
        """Return a normalized score for the reported soil type."""
        normalized = (soil_type or "").strip().lower()
        return SoilFertilityIndexCalculator.SOIL_TYPE_SCORES.get(normalized, 0.7)

    @staticmethod
    def calculate(soil_data: Dict) -> float:
        """Calculate the overall Soil Fertility Index."""
        macronutrient_score = SoilFertilityIndexCalculator.calculate_macronutrient_score(
            soil_data.get("nitrogen", 150.0),
            soil_data.get("phosphorus", 70.0),
            soil_data.get("potassium", 80.0),
        )
        soil_health_score = SoilFertilityIndexCalculator.calculate_soil_health_score(
            soil_data.get("ph", 6.5),
            soil_data.get("moisture", 35.0),
            soil_data.get("organic_carbon", 1.0),
            soil_data.get("electrical_conductivity", 0.5),
        )
        micronutrient_score = SoilFertilityIndexCalculator.calculate_micronutrient_score(
            soil_data.get("zinc", 2.0),
            soil_data.get("iron", 15.0),
            soil_data.get("copper", 0.8),
            soil_data.get("boron", 0.5),
            soil_data.get("manganese", 6.0),
        )
        fertilizer_score = SoilFertilityIndexCalculator.calculate_fertilizer_balance_score(
            soil_data.get("dap", 40.0),
            soil_data.get("urea", 80.0),
            soil_data.get("ssp", 25.0),
            soil_data.get("mop", 25.0),
        )
        soil_type_score = SoilFertilityIndexCalculator.calculate_soil_type_score(
            soil_data.get("soil_type")
        )

        sfi = (
            macronutrient_score * 0.35
            + soil_health_score * 0.30
            + micronutrient_score * 0.15
            + fertilizer_score * 0.10
            + soil_type_score * 0.10
        )
        return round(min(1.0, max(0.0, sfi)), 3)


class GrowingDegreeDaysCalculator:
    """Calculate Growing Degree Days (GDD) from weather data."""

    BASE_TEMPERATURE = 10.0

    @staticmethod
    def calculate_daily_gdd(max_temp: float, min_temp: float, base: float = 10.0) -> float:
        """Calculate GDD for a single day."""
        avg_temp = (max_temp + min_temp) / 2.0
        return max(0.0, avg_temp - base)

    @staticmethod
    def _environment_modifier(humidity: float, rainfall: float) -> float:
        """Apply a mild stress adjustment so humidity and rainfall influence seasonal GDD."""
        modifier = 1.0

        if humidity < 35 or humidity > 90:
            modifier -= 0.05
        elif 50 <= humidity <= 80:
            modifier += 0.02

        if rainfall < 25:
            modifier -= 0.06
        elif rainfall > 300:
            modifier -= 0.03
        elif 75 <= rainfall <= 200:
            modifier += 0.02

        return max(0.85, min(1.08, modifier))

    @staticmethod
    def calculate_seasonal_gdd(
        current_temperature: float,
        humidity: float,
        rainfall: float = 100.0,
        forecast_windows: Optional[list] = None,
        season_length_days: int = 120,
    ) -> float:
        """Calculate cumulative GDD using current weather and forecast windows."""
        modifier = GrowingDegreeDaysCalculator._environment_modifier(humidity, rainfall)

        daily_gdd = GrowingDegreeDaysCalculator.calculate_daily_gdd(
            current_temperature + 2.0,
            current_temperature - 2.0,
        )

        if forecast_windows:
            total_gdd = 0.0
            days_counted = 0

            for window in forecast_windows:
                if "temperature" not in window:
                    continue

                window_temp = float(window["temperature"])
                window_humidity = float(window.get("humidity", humidity))
                window_rainfall = float(window.get("rainfall", rainfall))
                window_modifier = GrowingDegreeDaysCalculator._environment_modifier(
                    window_humidity, window_rainfall
                )
                window_gdd = GrowingDegreeDaysCalculator.calculate_daily_gdd(
                    window_temp + 2.0,
                    window_temp - 2.0,
                )
                total_gdd += window_gdd * 30.0 * window_modifier
                days_counted += 30

            if days_counted > 0:
                return round(total_gdd, 1)

        return round(daily_gdd * season_length_days * modifier, 1)


class CumulativeRainfallCalculator:
    """Calculate cumulative rainfall from current and forecast data."""

    @staticmethod
    def calculate_seasonal_rainfall(
        current_rainfall: float,
        forecast_windows: Optional[list] = None,
        months_ahead: int = 3,
    ) -> float:
        """Calculate cumulative rainfall over the growing season."""
        total_rainfall = float(current_rainfall)

        if forecast_windows:
            for window in forecast_windows:
                if "rainfall" in window:
                    total_rainfall += float(window["rainfall"])
        else:
            total_rainfall += float(current_rainfall) * max(0, months_ahead - 1)

        return round(total_rainfall, 1)


class EarthEngineNDVIProvider:
    """Fetch NDVI from Google Earth Engine when credentials are available."""

    COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"
    BUFFER_METERS = 250
    LOOKBACK_DAYS = 30
    CLOUD_COVER_THRESHOLD = 20
    _initialized = False
    _available = False

    @classmethod
    def _initialize(cls) -> bool:
        if cls._initialized:
            return cls._available

        cls._initialized = True
        if ee is None:
            logger.info("earthengine-api is not installed; NDVI will use the fallback estimator.")
            return False

        project = os.getenv("EARTH_ENGINE_PROJECT") or os.getenv("GEE_PROJECT")
        service_account = os.getenv("GEE_SERVICE_ACCOUNT")
        credentials_file = os.getenv("GEE_CREDENTIALS_FILE") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        try:
            if service_account and credentials_file:
                credentials = ee.ServiceAccountCredentials(service_account, credentials_file)
                ee.Initialize(credentials=credentials, project=project)
            elif project:
                ee.Initialize(project=project)
            else:
                ee.Initialize()
            cls._available = True
        except Exception as exc:  # pragma: no cover - depends on external auth
            logger.warning("Google Earth Engine initialization failed: %s", exc)
            cls._available = False

        return cls._available

    @classmethod
    def fetch_ndvi(
        cls,
        latitude: float,
        longitude: float,
        reference_date: Optional[date] = None,
    ) -> Tuple[Optional[float], Dict[str, object]]:
        """Fetch recent NDVI around a farm coordinate from Earth Engine."""
        metadata: Dict[str, object] = {
            "source": "fallback_estimate",
            "provider": "Google Earth Engine",
            "collection": cls.COLLECTION_ID,
            "latitude": round(float(latitude), 6),
            "longitude": round(float(longitude), 6),
            "buffer_meters": cls.BUFFER_METERS,
        }

        if not cls._initialize():
            metadata["reason"] = "Earth Engine is not configured."
            return None, metadata

        end_date = reference_date or date.today()
        start_date = end_date - timedelta(days=cls.LOOKBACK_DAYS)
        metadata["start_date"] = start_date.isoformat()
        metadata["end_date"] = end_date.isoformat()

        try:
            point = ee.Geometry.Point([float(longitude), float(latitude)])
            area = point.buffer(cls.BUFFER_METERS)

            collection = (
                ee.ImageCollection(cls.COLLECTION_ID)
                .filterBounds(area)
                .filterDate(start_date.isoformat(), end_date.isoformat())
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cls.CLOUD_COVER_THRESHOLD))
            )

            image_count = int(collection.size().getInfo())
            metadata["image_count"] = image_count
            if image_count == 0:
                metadata["reason"] = "No Sentinel-2 scenes matched the NDVI lookup window."
                return None, metadata

            ndvi_image = collection.map(
                lambda image: image.normalizedDifference(["B8", "B4"]).rename("NDVI")
            ).mean()
            stats = ndvi_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=area,
                scale=10,
                bestEffort=True,
                maxPixels=1_000_000,
            ).getInfo()

            ndvi_value = stats.get("NDVI") if stats else None
            if ndvi_value is None:
                metadata["reason"] = "Earth Engine returned an empty NDVI statistic."
                return None, metadata

            metadata["source"] = "google_earth_engine"
            return round(float(ndvi_value), 3), metadata
        except Exception as exc:  # pragma: no cover - depends on remote API
            logger.warning("Google Earth Engine NDVI lookup failed: %s", exc)
            metadata["reason"] = str(exc)
            return None, metadata


class NDVICalculator:
    """Calculate NDVI using Earth Engine when available, otherwise estimate locally."""

    @staticmethod
    def estimate_ndvi_from_conditions(
        soil_fertility_index: float,
        rainfall: float,
        current_temperature: float,
        soil_moisture: float,
    ) -> float:
        """Estimate NDVI from soil and weather conditions."""
        fertility_ndvi = soil_fertility_index * 0.3

        optimal_rainfall = 250.0
        rainfall_ratio = min(rainfall / optimal_rainfall, 1.0)
        rainfall_ndvi = rainfall_ratio * 0.25

        temp_optimal = 25.0
        temp_deviation = abs(current_temperature - temp_optimal)
        temp_score = max(0.0, 1.0 - (temp_deviation / 20.0))
        temperature_ndvi = temp_score * 0.25

        if 40 <= soil_moisture <= 60:
            moisture_ndvi = 0.2
        elif 30 <= soil_moisture <= 70:
            moisture_ndvi = 0.15
        elif 20 <= soil_moisture <= 80:
            moisture_ndvi = 0.1
        else:
            moisture_ndvi = 0.05

        total_ndvi = 0.2 + fertility_ndvi + rainfall_ndvi + temperature_ndvi + moisture_ndvi
        return round(min(0.95, max(0.2, total_ndvi)), 3)

    @staticmethod
    def calculate_with_metadata(
        soil_fertility_index: float,
        rainfall: float,
        current_temperature: float,
        soil_moisture: float,
        coordinates: Optional[Tuple[float, float]] = None,
    ) -> Tuple[float, Dict[str, object]]:
        """Calculate NDVI and describe whether the value came from Earth Engine or fallback logic."""
        fallback_ndvi = NDVICalculator.estimate_ndvi_from_conditions(
            soil_fertility_index,
            rainfall,
            current_temperature,
            soil_moisture,
        )

        metadata: Dict[str, object] = {
            "source": "fallback_estimate",
            "fallback_value": fallback_ndvi,
        }

        if coordinates:
            latitude, longitude = coordinates
            gee_ndvi, gee_metadata = EarthEngineNDVIProvider.fetch_ndvi(latitude, longitude)
            metadata.update(gee_metadata)
            if gee_ndvi is not None:
                metadata["fallback_value"] = fallback_ndvi
                return gee_ndvi, metadata

        return fallback_ndvi, metadata

    @staticmethod
    def calculate(
        soil_fertility_index: float,
        rainfall: float,
        current_temperature: float,
        soil_moisture: float,
        coordinates: Optional[Tuple[float, float]] = None,
    ) -> float:
        """Calculate NDVI as a scalar value."""
        ndvi, _ = NDVICalculator.calculate_with_metadata(
            soil_fertility_index,
            rainfall,
            current_temperature,
            soil_moisture,
            coordinates,
        )
        return ndvi
