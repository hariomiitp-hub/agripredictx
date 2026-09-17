"""Crop recommendation engine with explainability."""
import numpy as np
from typing import Dict, List, Optional, Tuple

from agricultural_indicators import (
    CumulativeRainfallCalculator,
    GrowingDegreeDaysCalculator,
    NDVICalculator,
    SoilFertilityIndexCalculator,
)
from config import CROP_REQUIREMENTS
from data_models import (
    CropRecommendation,
    FarmInput,
    FertilizerRecommendation,
    RecommendationResult,
    YieldPrediction,
)
from data_preparation import calculate_parameter_score
from model import CropPredictionModel


class CropRecommendationEngine:
    """
    Enhanced crop recommendation engine with yield prediction, fertilizer advice,
    and 3-month weather integration.
    """

    def __init__(self, ml_model: CropPredictionModel):
        """Initialize the recommendation engine."""
        self.model = ml_model

    def get_recommendations(
        self, farm_input: FarmInput, top_n: int = 3
    ) -> RecommendationResult:
        """Generate comprehensive crop recommendations."""
        is_valid, errors = farm_input.validate()
        if not is_valid:
            raise ValueError(f"Invalid input: {errors}")

        X = self._prepare_input_features(farm_input)
        candidate_count = min(len(self.model.crops), max(top_n * 3, top_n))
        crop_probs = self.model.get_top_crops(X, top_n=candidate_count)

        recommendations = []
        for crop_name, ml_probability in crop_probs:
            suitability_score = self._calculate_suitability_score(
                farm_input, crop_name, ml_probability
            )
            matching_factors, mismatched_factors = self._analyze_factors(
                farm_input, crop_name
            )
            reason = self._generate_recommendation_reason(
                crop_name, matching_factors, mismatched_factors
            )
            risk_level = self._assess_risk_level(
                farm_input, crop_name, suitability_score
            )

            recommendations.append(
                CropRecommendation(
                    crop_name=crop_name,
                    suitability_score=suitability_score,
                    rank=0,
                    matching_factors=matching_factors,
                    mismatched_factors=mismatched_factors,
                    recommendation_reason=reason,
                    risk_level=risk_level,
                )
            )

        recommendations.sort(key=lambda item: item.suitability_score, reverse=True)
        recommendations = recommendations[:top_n]
        for rank, recommendation in enumerate(recommendations, 1):
            recommendation.rank = rank

        confidence = float(np.mean([prob for _, prob in crop_probs[:top_n]]))
        primary = recommendations[0]
        alternatives = recommendations[1:] if len(recommendations) > 1 else []

        return RecommendationResult(
            primary_recommendation=primary,
            alternatives=alternatives,
            farm_input=farm_input,
            confidence=confidence,
            yield_prediction=self._predict_yield(farm_input, primary.crop_name),
            fertilizer_recommendation=self._generate_fertilizer_recommendation(
                farm_input, primary.crop_name
            ),
            weather_risk_assessment=self._assess_weather_risks(farm_input),
            seasonal_suitability=self._calculate_seasonal_suitability(farm_input),
        )

    def _prepare_input_features(self, farm_input: FarmInput) -> np.ndarray:
        """Convert FarmInput to feature array for the ML model."""
        from config import SOIL_TYPES

        soil = farm_input.soil
        weather = farm_input.weather
        forecast_months = self._get_forecast_months(farm_input)
        indicators = self._get_agricultural_indicators(farm_input)

        features = [
            soil.nitrogen,
            soil.phosphorus,
            soil.potassium,
            soil.ph,
            soil.moisture,
            soil.organic_carbon,
            soil.electrical_conductivity,
            soil.dap,
            soil.urea,
            soil.ssp,
            soil.mop,
            soil.zinc,
            soil.iron,
            soil.copper,
            soil.boron,
            soil.manganese,
            weather.temperature,
            weather.humidity,
            weather.rainfall,
        ]

        for month_weather in forecast_months:
            features.extend([
                month_weather.temperature,
                month_weather.humidity,
                month_weather.rainfall,
            ])

        features.extend([
            indicators["gdd"],
            indicators["cumulative_rainfall"],
            indicators["soil_fertility_index"],
            indicators["ndvi"],
        ])
        features.append(SOIL_TYPES[soil.soil_type])
        return np.array(features).reshape(1, -1)

    def _calculate_suitability_score(
        self, farm_input: FarmInput, crop_name: str, ml_probability: float
    ) -> float:
        """Calculate overall suitability score combining rule-based and ML scores."""
        rule_score = self._calculate_rule_based_score(farm_input, crop_name)
        combined_score = (rule_score * 0.65) + (ml_probability * 100 * 0.35)
        return min(100, max(0, combined_score))

    def _calculate_rule_based_score(self, farm_input: FarmInput, crop_name: str) -> float:
        """Calculate score using all soil parameters and 3-month forecast weather."""
        if crop_name not in CROP_REQUIREMENTS:
            return 0.0

        components = self._build_scored_components(farm_input, crop_name)
        total_weight = sum(component["weight"] for component in components)
        if total_weight == 0:
            return 0.0

        weighted_score = sum(
            component["score"] * component["weight"] for component in components
        )
        return (weighted_score / total_weight) * 100

    def _analyze_factors(
        self, farm_input: FarmInput, crop_name: str
    ) -> Tuple[List[str], List[str]]:
        """Analyze which factors match and which do not for a crop."""
        if crop_name not in CROP_REQUIREMENTS:
            return [], []

        components = self._build_scored_components(farm_input, crop_name)
        matching_components = sorted(
            [component for component in components if component["matched"]],
            key=lambda component: component["score"] * component["weight"],
            reverse=True,
        )
        mismatched_components = sorted(
            [component for component in components if not component["matched"]],
            key=lambda component: (1 - component["score"]) * component["weight"],
            reverse=True,
        )

        matching = [component["detail"] for component in matching_components[:6]]
        mismatched = [component["detail"] for component in mismatched_components[:6]]
        return matching, mismatched

    def _generate_recommendation_reason(
        self,
        crop_name: str,
        matching_factors: List[str],
        mismatched_factors: List[str],
    ) -> str:
        """Generate a human-readable explanation for the recommendation."""
        if crop_name not in CROP_REQUIREMENTS:
            return "Insufficient data for recommendation"

        reason = CROP_REQUIREMENTS[crop_name]["description"]

        if matching_factors:
            reason += " Your farm has "
            reason += ", ".join([f.split(":")[0].lower() for f in matching_factors[:2]])
            reason += " at suitable levels."

        if mismatched_factors:
            reason += " Note: "
            reason += ", and ".join([f.lower() for f in mismatched_factors[:2]])
            reason += "."

        forecast_match = any("Forecast Month" in factor for factor in matching_factors)
        forecast_mismatch = any("Forecast Month" in factor for factor in mismatched_factors)
        if forecast_match and not forecast_mismatch:
            reason += " The 3-month forecast is also supportive for this crop."
        elif forecast_mismatch:
            reason += " The upcoming 3-month weather window needs close monitoring."

        return reason

    def _assess_risk_level(
        self, farm_input: FarmInput, crop_name: str, suitability_score: float
    ) -> str:
        """Assess the risk level for growing a particular crop."""
        components = self._build_scored_components(farm_input, crop_name)
        forecast_components = [
            component for component in components
            if component["name"].startswith("Forecast Month")
        ]
        forecast_score = (
            sum(component["score"] * component["weight"] for component in forecast_components)
            / sum(component["weight"] for component in forecast_components)
            if forecast_components
            else 1.0
        )
        _, mismatched = self._analyze_factors(farm_input, crop_name)

        if suitability_score >= 75 and forecast_score >= 0.75 and len(mismatched) <= 2:
            return "low"
        if suitability_score >= 55 and forecast_score >= 0.6 and len(mismatched) <= 4:
            return "medium"
        return "high"

    def get_regional_insights(self, region: str) -> dict:
        """Get insights specific to a region."""
        from config import REGIONS

        if region not in REGIONS:
            return {}

        region_profile = REGIONS[region]
        return {
            "region": region,
            "average_temperature": region_profile["avg_temp"],
            "average_rainfall": region_profile["avg_rainfall"],
            "typical_soil_type": region_profile["soil_type"],
        }

    def _predict_yield(
        self, farm_input: FarmInput, crop_name: str
    ) -> Optional[YieldPrediction]:
        """Predict yield using soil health and current plus forecast weather."""
        if crop_name not in CROP_REQUIREMENTS:
            return None

        requirements = CROP_REQUIREMENTS[crop_name]
        soil = farm_input.soil

        base_yield_min, base_yield_max = requirements.get("yield_range", (1.0, 3.0))
        base_yield = (base_yield_min + base_yield_max) / 2

        soil_modifier = self._calculate_soil_yield_modifier(soil, requirements)
        weather_modifier = self._calculate_multi_period_weather_modifier(
            farm_input, requirements
        )
        irrigation_modifier = 1.2 if farm_input.irrigation_available else 1.0
        historical_modifier = self._calculate_historical_yield_modifier(
            farm_input.historical_yield
        )

        predicted_yield = (
            base_yield
            * soil_modifier
            * weather_modifier
            * irrigation_modifier
            * historical_modifier
        )

        yield_categories = {
            "low": (0, predicted_yield * 0.7),
            "medium": (predicted_yield * 0.7, predicted_yield * 1.3),
            "high": (predicted_yield * 1.3, predicted_yield * 1.7),
            "very_high": (predicted_yield * 1.7, float("inf")),
        }

        yield_category = "medium"
        for category, (min_val, max_val) in yield_categories.items():
            if min_val <= predicted_yield < max_val:
                yield_category = category
                break

        factors = []
        if soil_modifier < 0.9:
            factors.append("Soil nutrient deficiencies")
        if weather_modifier < 0.9:
            factors.append("Suboptimal current or forecast weather")
        if not farm_input.irrigation_available:
            factors.append("Rain-fed farming")
        if historical_modifier < 1.0:
            factors.append("Historical yield trends")

        confidence = min(0.95, 0.7 + (soil_modifier + weather_modifier) / 4)

        return YieldPrediction(
            crop_name=crop_name,
            predicted_yield=round(predicted_yield, 2),
            yield_range=(
                round(base_yield_min * soil_modifier * weather_modifier, 2),
                round(base_yield_max * soil_modifier * weather_modifier, 2),
            ),
            confidence_level=confidence,
            factors_affecting_yield=factors,
            yield_category=yield_category,
        )

    def _calculate_soil_yield_modifier(self, soil, requirements) -> float:
        """Calculate yield modifier based on soil conditions."""
        modifier = 1.0

        n_score = calculate_parameter_score(soil.nitrogen, requirements["N"])
        p_score = calculate_parameter_score(soil.phosphorus, requirements["P"])
        k_score = calculate_parameter_score(soil.potassium, requirements["K"])
        nutrient_avg = (n_score + p_score + k_score) / 3
        modifier *= (0.7 + 0.3 * nutrient_avg)

        ph_score = calculate_parameter_score(soil.ph, requirements["pH"])
        modifier *= (0.8 + 0.2 * ph_score)

        if soil.organic_carbon > 1.0:
            modifier *= 1.1

        deficiencies = []
        if soil.zinc < 1.0:
            deficiencies.append("zinc")
        if soil.iron < 10.0:
            deficiencies.append("iron")
        if soil.copper < 0.5:
            deficiencies.append("copper")
        if soil.boron < 0.5:
            deficiencies.append("boron")

        modifier *= max(0.8, 1.0 - len(deficiencies) * 0.05)
        return modifier

    def _calculate_weather_yield_modifier(self, weather, requirements) -> float:
        """Calculate yield modifier based on one period of weather conditions."""
        modifier = 1.0
        temp_score = calculate_parameter_score(weather.temperature, requirements["temp"])
        rainfall_score = calculate_parameter_score(
            weather.rainfall, requirements["rainfall"]
        )
        humidity_score = calculate_parameter_score(
            weather.humidity, self._get_humidity_range(requirements)
        )

        modifier *= (0.7 + 0.3 * temp_score)
        modifier *= (0.8 + 0.2 * rainfall_score)
        modifier *= (0.85 + 0.15 * humidity_score)
        return modifier

    def _calculate_multi_period_weather_modifier(
        self, farm_input: FarmInput, requirements
    ) -> float:
        """Blend current weather with the next 3 forecast months."""
        if not farm_input.weather_forecast:
            return self._calculate_weather_yield_modifier(
                farm_input.weather, requirements
            )

        periods = [farm_input.weather, *self._get_forecast_months(farm_input)]
        period_weights = [0.2, 0.4, 0.25, 0.15]
        modifiers = [
            self._calculate_weather_yield_modifier(period, requirements)
            for period in periods
        ]
        return float(np.average(modifiers, weights=period_weights))

    def _calculate_historical_yield_modifier(
        self, historical_yield: Optional[List[float]]
    ) -> float:
        """Calculate yield modifier based on historical data."""
        if not historical_yield or len(historical_yield) < 2:
            return 1.0

        recent_avg = (
            np.mean(historical_yield[-3:])
            if len(historical_yield) >= 3
            else np.mean(historical_yield)
        )
        overall_avg = np.mean(historical_yield)
        trend_modifier = recent_avg / overall_avg if overall_avg > 0 else 1.0
        return max(0.8, min(1.2, trend_modifier))

    def _generate_fertilizer_recommendation(
        self, farm_input: FarmInput, crop_name: str
    ) -> Optional[FertilizerRecommendation]:
        """Generate fertilizer recommendations based on soil deficiencies."""
        if crop_name not in CROP_REQUIREMENTS:
            return None

        requirements = CROP_REQUIREMENTS[crop_name]
        soil = farm_input.soil

        n_required = (requirements["N"][0] + requirements["N"][1]) / 2
        p_required = (requirements["P"][0] + requirements["P"][1]) / 2
        k_required = (requirements["K"][0] + requirements["K"][1]) / 2

        n_recommendation = max(0, n_required - soil.nitrogen)
        p_recommendation = max(0, p_required - soil.phosphorus)
        k_recommendation = max(0, k_required - soil.potassium)

        micronutrients = {}
        deficiencies = []

        if soil.zinc < 2.0:
            micronutrients["zinc"] = max(0, 5.0 - soil.zinc)
            deficiencies.append("zinc")
        if soil.iron < 15.0:
            micronutrients["iron"] = max(0, 20.0 - soil.iron)
            deficiencies.append("iron")
        if soil.copper < 1.0:
            micronutrients["copper"] = max(0, 2.0 - soil.copper)
            deficiencies.append("copper")
        if soil.boron < 0.8:
            micronutrients["boron"] = max(0, 1.5 - soil.boron)
            deficiencies.append("boron")
        if soil.manganese < 5.0:
            micronutrients["manganese"] = max(0, 10.0 - soil.manganese)
            deficiencies.append("manganese")

        application_schedule = {
            "basal": "urea, ssp, mop",
            "30_days": "urea, dap",
            "60_days": "urea, mop",
            "micronutrients": "foliar application as needed",
        }

        cost_estimate = (
            n_recommendation * 0.3
            + p_recommendation * 0.5
            + k_recommendation * 0.4
            + sum(micronutrients.values()) * 2.0
        )

        return FertilizerRecommendation(
            crop_name=crop_name,
            nitrogen_recommendation=round(n_recommendation, 1),
            phosphorus_recommendation=round(p_recommendation, 1),
            potassium_recommendation=round(k_recommendation, 1),
            micronutrient_recommendations={
                key: round(value, 1) for key, value in micronutrients.items()
            },
            application_schedule=application_schedule,
            total_cost_estimate=round(cost_estimate, 2),
            soil_deficiencies=deficiencies,
        )

    def _assess_weather_risks(self, farm_input: FarmInput) -> Optional[Dict[str, str]]:
        """Assess weather-related risks for the next 3 months."""
        if not farm_input.weather_forecast:
            return None

        risks = {}
        for month_index, month_weather in enumerate(self._get_forecast_months(farm_input), 1):
            month_alerts = []
            if month_weather.temperature < 15:
                month_alerts.append("cool stress risk")
            elif month_weather.temperature > 35:
                month_alerts.append("heat stress risk")

            if month_weather.rainfall < 40:
                month_alerts.append("dry spell risk")
            elif month_weather.rainfall > 180:
                month_alerts.append("waterlogging risk")

            if month_weather.humidity < 35:
                month_alerts.append("high evaporation risk")
            elif month_weather.humidity > 85:
                month_alerts.append("fungal disease risk")

            if month_alerts:
                risks[f"month_{month_index}"] = ", ".join(month_alerts)

        return risks if risks else {
            "overall": "Weather conditions appear favorable across the next 3 months"
        }

    def _calculate_seasonal_suitability(
        self, farm_input: FarmInput
    ) -> Optional[Dict[str, float]]:
        """Calculate season-level suitability using the forecast window."""
        forecast_months = self._get_forecast_months(farm_input)
        avg_temperature = np.mean([month.temperature for month in forecast_months])
        avg_humidity = np.mean([month.humidity for month in forecast_months])
        avg_rainfall = np.mean([month.rainfall for month in forecast_months])

        seasonal_scores = {}
        for crop_name, requirements in CROP_REQUIREMENTS.items():
            season = requirements.get("season", "unknown")
            seasonal_scores.setdefault(season, [])

            temp_score = calculate_parameter_score(avg_temperature, requirements["temp"])
            rainfall_score = calculate_parameter_score(
                avg_rainfall, requirements["rainfall"]
            )
            humidity_score = calculate_parameter_score(
                avg_humidity, self._get_humidity_range(requirements)
            )

            suitability = (
                (temp_score * 0.45)
                + (rainfall_score * 0.35)
                + (humidity_score * 0.20)
            )
            seasonal_scores[season].append(suitability)

        return {
            season: round(np.mean(scores) * 100, 1)
            for season, scores in seasonal_scores.items()
            if scores
        }

    def _get_forecast_months(self, farm_input: FarmInput) -> List:
        """Return forecast months or repeat current weather when absent."""
        if farm_input.weather_forecast:
            return [
                farm_input.weather_forecast.month_1,
                farm_input.weather_forecast.month_2,
                farm_input.weather_forecast.month_3,
            ]
        return [farm_input.weather, farm_input.weather, farm_input.weather]

    def _get_agricultural_indicators(self, farm_input: FarmInput) -> Dict[str, float]:
        """Return precomputed agricultural indicators or derive them from the farm input."""
        if farm_input.agricultural_indicators:
            return {
                "gdd": float(farm_input.agricultural_indicators["gdd"]),
                "cumulative_rainfall": float(farm_input.agricultural_indicators["cumulative_rainfall"]),
                "soil_fertility_index": float(farm_input.agricultural_indicators["soil_fertility_index"]),
                "ndvi": float(farm_input.agricultural_indicators["ndvi"]),
            }

        soil = farm_input.soil
        weather = farm_input.weather
        forecast_windows = [
            {
                "temperature": month.temperature,
                "humidity": month.humidity,
                "rainfall": month.rainfall,
            }
            for month in self._get_forecast_months(farm_input)
        ]
        soil_payload = {
            "nitrogen": soil.nitrogen,
            "phosphorus": soil.phosphorus,
            "potassium": soil.potassium,
            "ph": soil.ph,
            "moisture": soil.moisture,
            "soil_type": soil.soil_type,
            "organic_carbon": soil.organic_carbon,
            "electrical_conductivity": soil.electrical_conductivity,
            "dap": soil.dap,
            "urea": soil.urea,
            "ssp": soil.ssp,
            "mop": soil.mop,
            "zinc": soil.zinc,
            "iron": soil.iron,
            "copper": soil.copper,
            "boron": soil.boron,
            "manganese": soil.manganese,
        }
        coordinates = None
        if farm_input.latitude is not None and farm_input.longitude is not None:
            coordinates = (float(farm_input.latitude), float(farm_input.longitude))

        sfi = SoilFertilityIndexCalculator.calculate(soil_payload)
        gdd = GrowingDegreeDaysCalculator.calculate_seasonal_gdd(
            current_temperature=weather.temperature,
            humidity=weather.humidity,
            rainfall=weather.rainfall,
            forecast_windows=forecast_windows,
            season_length_days=120,
        )
        cumulative_rainfall = CumulativeRainfallCalculator.calculate_seasonal_rainfall(
            current_rainfall=weather.rainfall,
            forecast_windows=forecast_windows,
            months_ahead=3,
        )
        ndvi = NDVICalculator.calculate(
            soil_fertility_index=sfi,
            rainfall=cumulative_rainfall,
            current_temperature=weather.temperature,
            soil_moisture=soil.moisture,
            coordinates=coordinates,
        )
        return {
            "gdd": gdd,
            "cumulative_rainfall": cumulative_rainfall,
            "soil_fertility_index": sfi,
            "ndvi": ndvi,
        }

    def _get_humidity_range(self, requirements: dict) -> Tuple[float, float]:
        """Estimate crop-friendly humidity from rainfall and moisture needs."""
        rainfall_mid = np.mean(requirements["rainfall"])
        moisture_mid = np.mean(requirements["moisture"])
        low = 40 + min(20, rainfall_mid / 25)
        high = 70 + min(20, moisture_mid / 2.5)
        return float(min(low, 85)), float(min(max(low + 10, high), 95))

    def _get_fertilizer_range(
        self, crop_name: str, key: str, fallback: Tuple[float, float]
    ) -> Tuple[float, float]:
        """Build a reasonable application range from crop fertilizer advice."""
        advice = CROP_REQUIREMENTS[crop_name].get("fertilizer_advice", {})
        recommended = advice.get(key)
        if recommended is None:
            return fallback
        lower = max(0.0, recommended * 0.4)
        upper = max(lower + 5.0, recommended * 1.2)
        return lower, upper

    def _build_numeric_component(
        self,
        name: str,
        value: float,
        optimal_range: Tuple[float, float],
        weight: float,
        unit: str = "",
        precision: int = 1,
    ) -> Dict[str, object]:
        """Create a weighted factor descriptor for explanation and scoring."""
        score = float(calculate_parameter_score(value, optimal_range))
        min_val, max_val = optimal_range
        description = f"{value:.{precision}f}{unit}"
        matched = min_val <= value <= max_val

        if matched:
            detail = f"{name}: {description} [ok]"
        else:
            direction = "too low" if value < min_val else "too high"
            detail = f"{name}: {direction} ({description})"

        return {
            "name": name,
            "score": score,
            "weight": weight,
            "matched": matched,
            "detail": detail,
        }

    def _build_scored_components(
        self, farm_input: FarmInput, crop_name: str
    ) -> List[Dict[str, object]]:
        """Build weighted crop-fit components using full soil and forecast data."""
        requirements = CROP_REQUIREMENTS[crop_name]
        soil = farm_input.soil
        weather = farm_input.weather
        forecast_months = self._get_forecast_months(farm_input)
        humidity_range = self._get_humidity_range(requirements)

        components = [
            self._build_numeric_component("Nitrogen", soil.nitrogen, requirements["N"], 14, " kg/ha", 0),
            self._build_numeric_component("Phosphorus", soil.phosphorus, requirements["P"], 10, " kg/ha", 0),
            self._build_numeric_component("Potassium", soil.potassium, requirements["K"], 10, " kg/ha", 0),
            self._build_numeric_component("pH Level", soil.ph, requirements["pH"], 8),
            self._build_numeric_component("Soil Moisture", soil.moisture, requirements["moisture"], 8, "%"),
            self._build_numeric_component("Organic Carbon", soil.organic_carbon, (0.8, 2.5), 5, "%"),
            self._build_numeric_component("Electrical Conductivity", soil.electrical_conductivity, (0.2, 1.5), 4, " dS/m"),
            self._build_numeric_component("DAP", soil.dap, self._get_fertilizer_range(crop_name, "dap", (20, 60)), 3, " kg/ha", 0),
            self._build_numeric_component("Urea", soil.urea, self._get_fertilizer_range(crop_name, "urea", (40, 120)), 3, " kg/ha", 0),
            self._build_numeric_component("SSP", soil.ssp, self._get_fertilizer_range(crop_name, "ssp", (10, 40)), 2, " kg/ha", 0),
            self._build_numeric_component("MOP", soil.mop, self._get_fertilizer_range(crop_name, "mop", (15, 50)), 2, " kg/ha", 0),
            self._build_numeric_component("Zinc", soil.zinc, (1.5, 5.0), 3, " ppm"),
            self._build_numeric_component("Iron", soil.iron, (10.0, 30.0), 3, " ppm"),
            self._build_numeric_component("Copper", soil.copper, (0.5, 2.0), 2, " ppm"),
            self._build_numeric_component("Boron", soil.boron, (0.5, 1.5), 2, " ppm"),
            self._build_numeric_component("Manganese", soil.manganese, (4.0, 12.0), 2, " ppm"),
            self._build_numeric_component("Current Temperature", weather.temperature, requirements["temp"], 6, " C"),
            self._build_numeric_component("Current Humidity", weather.humidity, humidity_range, 3, "%"),
            self._build_numeric_component("Current Rainfall", weather.rainfall, requirements["rainfall"], 4, " mm/month", 0),
        ]

        forecast_weight_factors = [1.0, 0.85, 0.7]
        for month_index, (month_weather, weight_factor) in enumerate(
            zip(forecast_months, forecast_weight_factors), 1
        ):
            components.extend([
                self._build_numeric_component(
                    f"Forecast Month {month_index} Temperature",
                    month_weather.temperature,
                    requirements["temp"],
                    6 * weight_factor,
                    " C",
                ),
                self._build_numeric_component(
                    f"Forecast Month {month_index} Humidity",
                    month_weather.humidity,
                    humidity_range,
                    3 * weight_factor,
                    "%",
                ),
                self._build_numeric_component(
                    f"Forecast Month {month_index} Rainfall",
                    month_weather.rainfall,
                    requirements["rainfall"],
                    4 * weight_factor,
                    " mm/month",
                    0,
                ),
            ])

        soil_type_match = soil.soil_type in requirements["soil_type"]
        preferred = ", ".join(requirements["soil_type"])
        components.append({
            "name": "Soil Type",
            "score": 1.0 if soil_type_match else 0.25,
            "weight": 8,
            "matched": soil_type_match,
            "detail": (
                f"Soil Type: {soil.soil_type} [ok]"
                if soil_type_match
                else f"Soil Type: {soil.soil_type} (prefers {preferred})"
            ),
        })

        return components
