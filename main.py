"""Main application module - CLI interface for AgriPredictX"""
import json
import os
from dotenv import load_dotenv
from data_models import SoilParameters, WeatherData, FarmInput, RecommendationResult
from data_preparation import get_feature_columns
from model import train_model_from_scratch, CropPredictionModel
from openweather_client import OpenWeatherError, OpenWeatherForecastClient
from recommender_engine import CropRecommendationEngine

load_dotenv()


class CropPredictionApp:
    """Main application class for crop predictions."""

    def __init__(self):
        self.model = None
        self.engine = None
        self.model_path = "crop_model.pkl"
        self.weather_client = OpenWeatherForecastClient()

    def initialize_model(self, force_retrain: bool = False):
        """Initialize or load the ML model."""
        if force_retrain or not os.path.exists(self.model_path):
            print("Training new model...")
            self.model = train_model_from_scratch()
            self.model.save_model(self.model_path)
        else:
            print("Loading existing model...")
            self.model = CropPredictionModel.load_model(self.model_path)
            if not self.model.has_expected_feature_schema():
                print("Existing model is missing the latest OpenWeather and agricultural indicator features. Retraining...")
                self.model = train_model_from_scratch()
                self.model.save_model(self.model_path)

        self.engine = CropRecommendationEngine(self.model)
        print(f"Using {len(get_feature_columns())} input features including OpenWeather outlook, SFI, GDD, cumulative rainfall, and NDVI.")
        print("Model loaded successfully!\n")

    def predict_interactive(self):
        """Interactive mode for making predictions."""
        print("=" * 60)
        print("AGRIPREDICTX - Interactive Mode")
        print("=" * 60)
        print("\nEnter soil parameters:")

        try:
            soil = SoilParameters(
                nitrogen=float(input("Nitrogen (0-200 kg/ha): ")),
                phosphorus=float(input("Phosphorus (0-150 kg/ha): ")),
                potassium=float(input("Potassium (0-200 kg/ha): ")),
                ph=float(input("pH Level (3.5-9.0): ")),
                moisture=float(input("Soil Moisture (0-50%): ")),
                soil_type=input("Soil Type (sandy/clay/loamy/silt/peat): ").lower(),
                
                # Enhanced soil parameters
                organic_carbon=float(input("Organic Carbon (0-5%): ")),
                electrical_conductivity=float(input("Electrical Conductivity (0-10 dS/m): ")),
                
                # Fertilizer components
                dap=float(input("DAP applied (0-100 kg/ha): ")),
                urea=float(input("Urea applied (0-200 kg/ha): ")),
                ssp=float(input("SSP applied (0-100 kg/ha): ")),
                mop=float(input("MOP applied (0-100 kg/ha): ")),
                
                # Micronutrients
                zinc=float(input("Zinc (0-10 ppm): ")),
                iron=float(input("Iron (0-50 ppm): ")),
                copper=float(input("Copper (0-5 ppm): ")),
                boron=float(input("Boron (0-2 ppm): ")),
                manganese=float(input("Manganese (0-20 ppm): ")),
            )

            print("\nEnter weather parameters:")
            weather = WeatherData(
                temperature=float(input("Temperature (-10 to 50 C): ")),
                humidity=float(input("Humidity (0-100%): ")),
                rainfall=float(input("Rainfall (0-500 mm/month): ")),
            )

            print("\nEnter location for OpenWeather 3-month forecast lookup:")
            location_name = input("Village / Town (optional): ").strip() or None
            district = input("District: ").strip() or None
            state_name = input("State: ").strip() or None
            country_code = input("Country code (default IN): ").strip().upper() or "IN"
            resolved_location = self.weather_client.resolve_location(
                location_name=location_name,
                district=district,
                state=state_name,
                country_code=country_code,
            )
            weather_forecast, weather_context = self.weather_client.build_three_month_forecast(
                resolved_location.latitude,
                resolved_location.longitude
            )
            print(
                f"Fetched OpenWeather outlook from {weather_context['analysis_date']} "
                f"for {resolved_location.location_name}, {resolved_location.state} "
                f"({weather_context['latitude']}, {weather_context['longitude']})."
            )

            region = input("\nRegion (optional, press Enter to skip): ").strip() or None
            farm_size = input("Farm size in hectares (optional, press Enter to skip): ").strip()
            farm_size = float(farm_size) if farm_size else None
            irrigation = input("Irrigation available? (y/n, optional): ").strip().lower() == 'y'
            
            farm_input = FarmInput(
                soil=soil, 
                weather=weather, 
                weather_forecast=weather_forecast,
                region=region,
                farm_size=farm_size,
                irrigation_available=irrigation,
                location_name=resolved_location.location_name,
                district=resolved_location.district,
                state=resolved_location.state,
                country_code=resolved_location.country_code,
                latitude=resolved_location.latitude,
                longitude=resolved_location.longitude,
            )

            print("\nGenerating enhanced recommendations...\n")
            result = self.engine.get_recommendations(farm_input, top_n=3)
            self._print_enhanced_recommendations(result)
        except ValueError as e:
            print(f"Error: Invalid input - {e}")
        except OpenWeatherError as e:
            print(f"Error fetching OpenWeather forecast: {e}")
        except Exception as e:
            print(f"Error: {e}")

    def predict_batch(self, input_file: str):
        """Make predictions from a JSON input file."""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            results = []
            for idx, farm_data in enumerate(data, 1):
                soil = SoilParameters(**farm_data["soil"])
                weather = WeatherData(**farm_data["weather"])
                weather_forecast = self._resolve_weather_forecast(farm_data)
                region = farm_data.get("region")
                location = self._resolve_location_context(farm_data)
                farm_input = FarmInput(
                    soil=soil,
                    weather=weather,
                    weather_forecast=weather_forecast,
                    region=region,
                    farm_size=farm_data.get("farm_size", farm_data.get("land_area")),
                    location_name=location.get("location_name"),
                    district=location.get("district"),
                    state=location.get("state"),
                    country_code=location.get("country_code"),
                    latitude=location.get("latitude"),
                    longitude=location.get("longitude"),
                    land_area_unit=farm_data.get("land_area_unit", "hectares"),
                )
                result = self.engine.get_recommendations(farm_input, top_n=3)
                results.append({"farm_id": idx, "recommendations": result.to_dict()})

            output_file = input_file.replace(".json", "_results.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

            print(f"Predictions saved to {output_file}")
        except Exception as e:
            print(f"Error processing batch: {e}")

    def predict_from_dict(self, farm_data: dict) -> dict:
        """Make a prediction from a dictionary."""
        soil = SoilParameters(**farm_data["soil"])
        weather = WeatherData(**farm_data["weather"])
        weather_forecast = self._resolve_weather_forecast(farm_data)
        region = farm_data.get("region")
        location = self._resolve_location_context(farm_data)
        farm_input = FarmInput(
            soil=soil,
            weather=weather,
            weather_forecast=weather_forecast,
            region=region,
            farm_size=farm_data.get("farm_size", farm_data.get("land_area")),
            location_name=location.get("location_name"),
            district=location.get("district"),
            state=location.get("state"),
            country_code=location.get("country_code"),
            latitude=location.get("latitude"),
            longitude=location.get("longitude"),
            land_area_unit=farm_data.get("land_area_unit", "hectares"),
        )
        result = self.engine.get_recommendations(farm_input, top_n=3)
        return result.to_dict()

    def _resolve_weather_forecast(self, farm_data: dict):
        """Fetch the three-month outlook from OpenWeather using coordinates or named location."""
        location = self._resolve_location_context(farm_data)
        weather_forecast, _ = self.weather_client.build_three_month_forecast(
            float(location["latitude"]),
            float(location["longitude"]),
        )
        return weather_forecast

    def _resolve_location_context(self, farm_data: dict) -> dict:
        """Resolve farm location details for forecast lookup."""
        if "latitude" in farm_data and "longitude" in farm_data:
            return {
                "location_name": farm_data.get("location_name") or farm_data.get("district"),
                "district": farm_data.get("district"),
                "state": farm_data.get("state"),
                "country_code": farm_data.get("country_code", "IN"),
                "latitude": float(farm_data["latitude"]),
                "longitude": float(farm_data["longitude"]),
            }

        resolved = self.weather_client.resolve_location(
            location_name=farm_data.get("location_name"),
            district=farm_data.get("district"),
            state=farm_data.get("state"),
            country_code=farm_data.get("country_code", "IN"),
        )
        return resolved.to_dict()

    def _print_enhanced_recommendations(self, result: RecommendationResult):
        """Print enhanced recommendations with yield prediction and fertilizer advice."""
        print("=" * 80)
        print("ENHANCED CROP RECOMMENDATIONS")
        print("=" * 80)

        primary = result.primary_recommendation
        print(f"\n🏆 PRIMARY RECOMMENDATION: {primary.crop_name.upper()}")
        print(f"   Suitability Score: {primary.suitability_score:.1f}/100")
        print(f"   Risk Level: {primary.risk_level.upper()}")
        print(f"   Reason: {primary.recommendation_reason}")

        print("\n✅ Matching Factors:")
        for factor in primary.matching_factors:
            print(f"   - {factor}")

        if primary.mismatched_factors:
            print("\n⚠️  Factors to Consider:")
            for factor in primary.mismatched_factors:
                print(f"   - {factor}")

        # Yield Prediction
        if result.yield_prediction:
            yp = result.yield_prediction
            print(f"\n🌾 YIELD PREDICTION:")
            print(f"   Predicted Yield: {yp.predicted_yield:.1f} tons/hectare")
            print(f"   Yield Range: {yp.yield_range[0]:.1f} - {yp.yield_range[1]:.1f} tons/hectare")
            print(f"   Category: {yp.yield_category.title()}")
            print(f"   Confidence: {yp.confidence_level:.1%}")
            if yp.factors_affecting_yield:
                print(f"   Factors: {', '.join(yp.factors_affecting_yield)}")

        # Fertilizer Recommendations
        if result.fertilizer_recommendation:
            fr = result.fertilizer_recommendation
            print(f"\n🌱 FERTILIZER RECOMMENDATIONS:")
            print(f"   Nitrogen: {fr.nitrogen_recommendation:.1f} kg/ha")
            print(f"   Phosphorus: {fr.phosphorus_recommendation:.1f} kg/ha")
            print(f"   Potassium: {fr.potassium_recommendation:.1f} kg/ha")
            if fr.micronutrient_recommendations:
                print(f"   Micronutrients:")
                for nutrient, amount in fr.micronutrient_recommendations.items():
                    print(f"     - {nutrient.title()}: {amount:.1f} ppm")
            if fr.total_cost_estimate:
                print(f"   Estimated Cost: ₹{fr.total_cost_estimate:.0f}")
            if fr.soil_deficiencies:
                print(f"   Soil Deficiencies: {', '.join(fr.soil_deficiencies)}")

        # Weather Risk Assessment
        if result.weather_risk_assessment:
            print(f"\n🌤️  WEATHER RISK ASSESSMENT:")
            for risk_type, risk_desc in result.weather_risk_assessment.items():
                print(f"   {risk_type.title()}: {risk_desc}")

        # Seasonal Suitability
        if result.seasonal_suitability:
            print(f"\n📅 SEASONAL SUITABILITY:")
            for season, score in result.seasonal_suitability.items():
                print(f"   {season.title()}: {score:.1f}/100")

        if result.alternatives:
            print("\n🔄 ALTERNATIVE RECOMMENDATIONS:")
            for alt in result.alternatives:
                print(f"\n   {alt.rank}. {alt.crop_name.title()}")
                print(f"      Suitability: {alt.suitability_score:.1f}/100")
                print(f"      Risk: {alt.risk_level}")

        print(f"\n📊 Model Confidence: {result.confidence:.1%}")
        print("=" * 80)

    def get_feature_importance(self):
        """Display feature importance from the model."""
        if self.model is None:
            print("Model not initialized. Call initialize_model() first.")
            return

        importance = self.model.get_feature_importance()
        print("\nFeature Importance:")
        print("-" * 40)
        for feature, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
            print(f"{feature:15} : {score:.4f}")


def main():
    """Main entry point."""
    app = CropPredictionApp()
    app.initialize_model(force_retrain=False)

    while True:
        print("\n" + "=" * 60)
        print("AGRIPREDICTX Menu")
        print("=" * 60)
        print("1. Interactive Prediction")
        print("2. Batch Prediction (from JSON file)")
        print("3. View Feature Importance")
        print("4. Retrain Model")
        print("5. Exit")
        print("-" * 60)

        choice = input("Select option (1-5): ").strip()

        if choice == "1":
            app.predict_interactive()
        elif choice == "2":
            input_file = input("Enter path to JSON input file: ").strip()
            if os.path.exists(input_file):
                app.predict_batch(input_file)
            else:
                print(f"File not found: {input_file}")
        elif choice == "3":
            app.get_feature_importance()
        elif choice == "4":
            app.initialize_model(force_retrain=True)
        elif choice == "5":
            print("Exiting...")
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
