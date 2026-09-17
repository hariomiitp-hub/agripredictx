"""Flask REST API for AgriPredictX"""
from datetime import date, timedelta
import json
import os
import traceback
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from data_models import SoilParameters, WeatherData, WeatherForecast, FarmInput
from data_preparation import get_feature_columns
from model import CropPredictionModel, train_model_from_scratch
from openweather_client import OpenWeatherError, OpenWeatherForecastClient
from recommender_engine import CropRecommendationEngine
from agricultural_indicators import (
    SoilFertilityIndexCalculator,
    GrowingDegreeDaysCalculator,
    CumulativeRainfallCalculator,
    NDVICalculator
)

load_dotenv()

app = Flask(__name__)
app.config.update(
    TEMPLATES_AUTO_RELOAD=True,
    SEND_FILE_MAX_AGE_DEFAULT=0,
)
app.jinja_env.auto_reload = True
CORS_HEADERS = {'Access-Control-Allow-Origin': '*'}

# Initialize model and engine
model = None
engine = None
forecast_client = OpenWeatherForecastClient()
model_path = os.getenv("MODEL_PATH", "crop_model.pkl")

DEFAULT_SOIL_FIELDS = {
    "organic_carbon": 1.0,
    "electrical_conductivity": 0.5,
    "dap": 40.0,
    "urea": 80.0,
    "ssp": 25.0,
    "mop": 25.0,
    "zinc": 2.0,
    "iron": 15.0,
    "copper": 0.8,
    "boron": 0.5,
    "manganese": 6.0,
}


def build_soil_parameters(soil_data):
    """Create soil parameters while backfilling legacy payloads."""
    normalized = DEFAULT_SOIL_FIELDS.copy()
    normalized.update(soil_data or {})
    return SoilParameters(**normalized)


def build_manual_location_context(payload):
    """Use request-provided location fields when OpenWeather geocoding is unavailable."""
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    return {
        "location_name": (payload.get("location_name") or payload.get("district") or payload.get("state") or "").strip(),
        "district": (payload.get("district") or payload.get("location_name") or "").strip(),
        "state": (payload.get("state") or "").strip(),
        "country_code": ((payload.get("country_code") or "IN").strip().upper()),
        "latitude": round(float(latitude), 6) if latitude is not None else None,
        "longitude": round(float(longitude), 6) if longitude is not None else None,
        "resolution_method": "manual_input",
    }


def build_local_forecast(payload, location_context, reason):
    """Create a 3-month outlook from the submitted current weather for localhost use."""
    weather = WeatherData(**payload["weather"])
    start_date = date.today()
    monthly_profiles = (
        weather,
        WeatherData(
            temperature=round(weather.temperature + 1.0, 1),
            humidity=round(min(weather.humidity + 3.0, 100.0), 1),
            rainfall=round(max(weather.rainfall * 1.05, 0.0), 1),
        ),
        WeatherData(
            temperature=round(weather.temperature + 0.5, 1),
            humidity=round(max(weather.humidity - 2.0, 0.0), 1),
            rainfall=round(max(weather.rainfall * 0.95, 0.0), 1),
        ),
    )

    forecast = WeatherForecast(*monthly_profiles)
    metadata = {
        "source": "Local weather fallback",
        "analysis_date": start_date.isoformat(),
        "latitude": location_context.get("latitude"),
        "longitude": location_context.get("longitude"),
        "resolved_location": location_context,
        "fallback_reason": reason,
        "windows": [
            {
                "start_date": (start_date + timedelta(days=30 * index)).isoformat(),
                "end_date": (start_date + timedelta(days=(30 * (index + 1)) - 1)).isoformat(),
                "temperature": month.temperature,
                "humidity": month.humidity,
                "rainfall": month.rainfall,
            }
            for index, month in enumerate(monthly_profiles)
        ],
    }
    return forecast, metadata


def fetch_openweather_forecast(payload, location_context=None):
    """Fetch the next 3 forecast windows from OpenWeather using coordinates or a named location."""
    location_context = location_context or resolve_location_context(payload)

    latitude = location_context.get("latitude")
    longitude = location_context.get("longitude")
    if latitude is None or longitude is None:
        return build_local_forecast(
            payload,
            location_context,
            "Coordinates unavailable, so the submitted weather values were reused for the 3-month outlook.",
        )

    try:
        forecast, metadata = forecast_client.build_three_month_forecast(
            latitude=float(latitude),
            longitude=float(longitude),
        )
        metadata["resolved_location"] = location_context
        return forecast, metadata
    except OpenWeatherError as exc:
        return build_local_forecast(payload, location_context, str(exc))


def build_agricultural_indicator_bundle(soil_data, weather_data, weather_context, location_context):
    """Calculate agricultural indicators and attach source metadata."""
    forecast_windows = (weather_context or {}).get("windows", [])
    coordinates = None
    if location_context.get("latitude") is not None and location_context.get("longitude") is not None:
        coordinates = (float(location_context["latitude"]), float(location_context["longitude"]))

    sfi = SoilFertilityIndexCalculator.calculate(soil_data)
    gdd = GrowingDegreeDaysCalculator.calculate_seasonal_gdd(
        current_temperature=weather_data.get("temperature", 25),
        humidity=weather_data.get("humidity", 70),
        rainfall=weather_data.get("rainfall", 100),
        forecast_windows=forecast_windows,
        season_length_days=120,
    )
    cumulative_rainfall = CumulativeRainfallCalculator.calculate_seasonal_rainfall(
        current_rainfall=weather_data.get("rainfall", 100),
        forecast_windows=forecast_windows,
        months_ahead=3,
    )
    ndvi, ndvi_metadata = NDVICalculator.calculate_with_metadata(
        soil_fertility_index=sfi,
        rainfall=cumulative_rainfall,
        current_temperature=weather_data.get("temperature", 25),
        soil_moisture=soil_data.get("moisture", 35),
        coordinates=coordinates,
    )

    return {
        "gdd": gdd,
        "cumulative_rainfall": cumulative_rainfall,
        "soil_fertility_index": sfi,
        "ndvi": ndvi,
        "auto_filled": True,
        "calculation_method": "automatic_from_soil_inputs_openweather_and_google_earth_engine",
        "indicator_descriptions": {
            "gdd": "Growing Degree Days derived from temperature with humidity and rainfall stress adjustment across the OpenWeather outlook.",
            "cumulative_rainfall": "Current rainfall plus the next 3 OpenWeather forecast windows for seasonal water availability.",
            "soil_fertility_index": "Composite soil health score derived from N, P, K, pH, moisture, soil type, organic carbon, EC, fertilizers, and micronutrients.",
            "ndvi": "Vegetation health from Google Earth Engine Sentinel-2 imagery when configured, otherwise estimated from soil and weather conditions.",
        },
        "input_factors": {
            "soil_fertility_index": [
                "nitrogen",
                "phosphorus",
                "potassium",
                "soil_pH",
                "moisture",
                "soil_type",
                "organic_carbon",
                "electrical_conductivity",
                "dap",
                "urea",
                "ssp",
                "mop",
                "zinc",
                "iron",
                "copper",
                "boron",
                "manganese",
            ],
            "gdd": ["temperature", "humidity", "rainfall", "openweather_forecast"],
            "cumulative_rainfall": ["rainfall", "openweather_forecast"],
            "ndvi": [
                "openweather_resolved_coordinates",
                "google_earth_engine",
                "soil_fertility_index",
                "cumulative_rainfall",
                "temperature",
                "moisture",
            ],
        },
        "data_sources": {
            "weather_forecast": weather_context.get("source"),
            "location_resolution": location_context.get("resolution_method"),
            "ndvi": ndvi_metadata.get("source"),
        },
        "ndvi_metadata": ndvi_metadata,
    }


def resolve_location_context(payload):
    """Resolve request location details into a normalized location context."""
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    if latitude is not None or longitude is not None:
        if latitude is None or longitude is None:
            raise ValueError("Both latitude and longitude are required when using coordinates.")

        resolved_location = {
            "location_name": (payload.get("location_name") or payload.get("district") or "").strip(),
            "district": (payload.get("district") or "").strip(),
            "state": (payload.get("state") or "").strip(),
            "country_code": ((payload.get("country_code") or "IN").strip().upper()),
            "latitude": round(float(latitude), 6),
            "longitude": round(float(longitude), 6),
            "resolution_method": "coordinates",
        }
        try:
            reverse_location = forecast_client.reverse_geocode(
                latitude=float(latitude),
                longitude=float(longitude),
            ).to_dict()
            for key, value in reverse_location.items():
                if key not in resolved_location or not resolved_location[key]:
                    resolved_location[key] = value
        except OpenWeatherError:
            pass
        return resolved_location

    location_name = (payload.get("location_name") or "").strip() or None
    district = (payload.get("district") or "").strip() or None
    state_name = (payload.get("state") or "").strip() or None
    country_code = (payload.get("country_code") or "IN").strip().upper()

    if not any([location_name, district, state_name]):
        raise ValueError(
            "Please provide a location name, district, or state so AgriPredictX can fetch the OpenWeather forecast."
        )

    if not forecast_client.api_key:
        return build_manual_location_context(payload)

    return forecast_client.resolve_location(
        location_name=location_name,
        district=district,
        state=state_name,
        country_code=country_code,
    ).to_dict()


def initialize_app():
    """Initialize the Flask app with model"""
    global model, engine

    if model is not None and engine is not None:
        return True

    if os.path.exists(model_path):
        print("Loading model...")
        print(f"DEBUG: Model path: {os.path.abspath(model_path)}")
        print(f"DEBUG: Model file exists: {os.path.exists(model_path)}")
        model = CropPredictionModel.load_model(model_path)
        if not model.has_expected_feature_schema():
            print("Existing model schema is outdated. Retraining for OpenWeather, SFI, GDD, rainfall, and NDVI support...")
            model = train_model_from_scratch()
            model.save_model(model_path)
        print(f"DEBUG: Model loaded with {len(model.feature_cols)} features")
        print(f"DEBUG: Expected feature count: {len(get_feature_columns())}")
        print(f"DEBUG: Scaler expects {model.scaler.n_features_in_} features")
    else:
        print("Model not found. Training a new model...")
        model = train_model_from_scratch()
        model.save_model(model_path)

    engine = CropRecommendationEngine(model)
    print(f"DEBUG: Created engine with model id: {id(model)}", flush=True)
    return True


def ensure_initialized():
    """Ensure the application model is ready before serving a request."""
    return initialize_app()


@app.route("/", methods=["GET"])
def dashboard():
    """Serve the dashboard website."""
    ensure_initialized()
    return render_template("index.html", product_name="AgriPredictX")


@app.route("/sample-farms", methods=["GET"])
def sample_farms():
    """Return bundled sample farms for the dashboard demo."""
    with open("sample_farms.json", "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return jsonify(data), 200


@app.before_request
def before_request():
    """Handle CORS preflight"""
    if request.method == 'OPTIONS':
        return '', 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    ensure_initialized()
    return jsonify({
        'product': 'AgriPredictX',
        'status': 'healthy',
        'model_loaded': model is not None,
        'version': '2.0',
        'features': [
            'yield_prediction',
            'fertilizer_advice',
            'weather_integration',
            'micronutrient_analysis',
            'automatic_agricultural_indicators',
            'earth_engine_ndvi_support',
        ]
    }), 200


@app.route('/calculate-indicators', methods=['POST', 'OPTIONS'])
def calculate_indicators():
    """
    Calculate agricultural indicators automatically from soil/weather data.
    
    Expected JSON:
    {
        "soil": {soil parameters dict},
        "weather": {weather parameters dict},
        "district": str,
        "state": str,
        "latitude": optional float,
        "longitude": optional float
    }
    """
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.update(CORS_HEADERS)
        return response, 200
    
    try:
        data = request.get_json()
        
        if not data or 'soil' not in data or 'weather' not in data:
            return jsonify({
                'error': 'Invalid input. Must include soil and weather data'
            }), 400

        location_context = resolve_location_context(data)
        weather_forecast, weather_context = fetch_openweather_forecast(data, location_context)
        response_payload = {
            'agricultural_indicators': build_agricultural_indicator_bundle(
                data['soil'],
                data['weather'],
                weather_context,
                location_context,
            ),
            'weather_context': weather_context,
            'location_context': location_context,
            'forecast': weather_forecast.to_dict(),
        }
        
        response = jsonify(response_payload)
        response.headers.update(CORS_HEADERS)
        return response, 200
        
    except ValueError as e:
        response = jsonify({'error': f'Invalid input: {str(e)}'})
        response.headers.update(CORS_HEADERS)
        return response, 400
    except OpenWeatherError as e:
        response = jsonify({'error': str(e)})
        response.headers.update(CORS_HEADERS)
        return response, 502
    except Exception as e:
        response = jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        response.headers.update(CORS_HEADERS)
        return response, 500


@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    """
    Enhanced prediction endpoint with yield prediction and fertilizer advice.
    
    Expected JSON:
    {
        "soil": {
            "nitrogen": float,
            "phosphorus": float,
            "potassium": float,
            "ph": float,
            "moisture": float,
            "soil_type": str,
            "organic_carbon": float,
            "electrical_conductivity": float,
            "dap": float,
            "urea": float,
            "ssp": float,
            "mop": float,
            "zinc": float,
            "iron": float,
            "copper": float,
            "boron": float,
            "manganese": float
        },
        "weather": {
            "temperature": float,
            "humidity": float,
            "rainfall": float
        },
        "location_name": str,  // optional
        "district": str,  // recommended
        "state": str,  // recommended
        "country_code": str,  // optional, defaults to IN
        "latitude": float,  // optional coordinate override
        "longitude": float,  // optional coordinate override
        "region": str,  // optional
        "farm_size": float,  // optional
        "land_area": float,  // optional alias for farm_size
        "irrigation_available": bool,  // optional
        "historical_yield": [float]  // optional
    }
    """
    print("DEBUG: Predict endpoint called", flush=True)
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.update(CORS_HEADERS)
        return response, 200
    
    try:
        print("DEBUG: About to ensure_initialized", flush=True)
        if not ensure_initialized():
            print("DEBUG: ensure_initialized failed", flush=True)
            return jsonify({'error': 'Model not initialized'}), 500
        
        print("DEBUG: ensure_initialized passed", flush=True)
        print(f"DEBUG: Using model id: {id(model)}, scaler expects: {model.scaler.n_features_in_}", flush=True)
        data = request.get_json()
        print(f"DEBUG: Received data: {data}", flush=True)
        
        # Validate input
        if not data or 'soil' not in data or 'weather' not in data:
            return jsonify({
                'error': 'Invalid input. Must include soil and weather data'
            }), 400
        
        # Create farm input with enhanced parameters
        soil = build_soil_parameters(data['soil'])
        weather = WeatherData(**data['weather'])
        location_context = resolve_location_context(data)
        weather_forecast, weather_context = fetch_openweather_forecast(data, location_context)
        agricultural_indicators = build_agricultural_indicator_bundle(
            data['soil'],
            data['weather'],
            weather_context,
            location_context,
        )
        farm_size = data.get('farm_size', data.get('land_area'))
        
        farm_input = FarmInput(
            soil=soil, 
            weather=weather, 
            weather_forecast=weather_forecast,
            agricultural_indicators={
                'gdd': agricultural_indicators['gdd'],
                'cumulative_rainfall': agricultural_indicators['cumulative_rainfall'],
                'soil_fertility_index': agricultural_indicators['soil_fertility_index'],
                'ndvi': agricultural_indicators['ndvi'],
            },
            region=data.get('region'),
            farm_size=farm_size,
            irrigation_available=data.get('irrigation_available'),
            historical_yield=data.get('historical_yield'),
            location_name=location_context.get('location_name') or data.get('location_name'),
            district=location_context.get('district') or data.get('district'),
            state=location_context.get('state') or data.get('state'),
            country_code=location_context.get('country_code') or data.get('country_code') or 'IN',
            latitude=location_context.get('latitude'),
            longitude=location_context.get('longitude'),
            land_area_unit=data.get('land_area_unit', 'hectares'),
        )
        
        # Get enhanced recommendations
        result = engine.get_recommendations(farm_input, top_n=3)

        response_payload = result.to_dict()
        response_payload['weather_context'] = weather_context
        response_payload['location_context'] = location_context
        response_payload['agricultural_indicators'] = agricultural_indicators
        
        response = jsonify(response_payload)
        response.headers.update(CORS_HEADERS)
        return response, 200
        
    except ValueError as e:
        response = jsonify({'error': f'Invalid input: {str(e)}'})
        response.headers.update(CORS_HEADERS)
        return response, 400
    except OpenWeatherError as e:
        response = jsonify({'error': str(e)})
        response.headers.update(CORS_HEADERS)
        return response, 502
    except Exception as e:
        response = jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        response.headers.update(CORS_HEADERS)
        return response, 500


@app.route('/predict-batch', methods=['POST', 'OPTIONS'])
def predict_batch():
    """
    Batch prediction endpoint.
    
    Expected JSON: Array of farm data objects
    """
    print("DEBUG: Predict endpoint called")
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.update(CORS_HEADERS)
        return response, 200
    
    try:
        if not ensure_initialized():
            return jsonify({'error': 'Model not initialized'}), 500
        
        data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({'error': 'Expected JSON array'}), 400
        
        results = []
        for idx, farm_data in enumerate(data):
            try:
                soil = build_soil_parameters(farm_data['soil'])
                weather = WeatherData(**farm_data['weather'])
                location_context = resolve_location_context(farm_data)
                weather_forecast, weather_context = fetch_openweather_forecast(farm_data, location_context)
                agricultural_indicators = build_agricultural_indicator_bundle(
                    farm_data['soil'],
                    farm_data['weather'],
                    weather_context,
                    location_context,
                )
                farm_size = farm_data.get('farm_size', farm_data.get('land_area'))
                
                farm_input = FarmInput(
                    soil=soil, 
                    weather=weather, 
                    weather_forecast=weather_forecast,
                    agricultural_indicators={
                        'gdd': agricultural_indicators['gdd'],
                        'cumulative_rainfall': agricultural_indicators['cumulative_rainfall'],
                        'soil_fertility_index': agricultural_indicators['soil_fertility_index'],
                        'ndvi': agricultural_indicators['ndvi'],
                    },
                    region=farm_data.get('region'),
                    farm_size=farm_size,
                    irrigation_available=farm_data.get('irrigation_available'),
                    historical_yield=farm_data.get('historical_yield'),
                    location_name=location_context.get('location_name') or farm_data.get('location_name'),
                    district=location_context.get('district') or farm_data.get('district'),
                    state=location_context.get('state') or farm_data.get('state'),
                    country_code=location_context.get('country_code') or farm_data.get('country_code') or 'IN',
                    latitude=location_context.get('latitude'),
                    longitude=location_context.get('longitude'),
                    land_area_unit=farm_data.get('land_area_unit', 'hectares'),
                )
                result = engine.get_recommendations(farm_input, top_n=3)
                
                results.append({
                    'id': idx,
                    'status': 'success',
                    'recommendations': {
                        **result.to_dict(),
                        'agricultural_indicators': agricultural_indicators,
                        'weather_context': weather_context,
                        'location_context': location_context,
                    }
                })
            except OpenWeatherError as e:
                results.append({
                    'id': idx,
                    'status': 'error',
                    'error': str(e)
                })
            except Exception as e:
                results.append({
                    'id': idx,
                    'status': 'error',
                    'error': str(e)
                })
        
        response = jsonify({'results': results})
        response.headers.update(CORS_HEADERS)
        return response, 200
        
    except Exception as e:
        response = jsonify({'error': str(e)})
        response.headers.update(CORS_HEADERS)
        return response, 500


@app.route('/model-info', methods=['GET', 'OPTIONS'])
def model_info():
    """Get information about the loaded model"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.update(CORS_HEADERS)
        return response, 200
    
    if not ensure_initialized():
        return jsonify({'error': 'Model not loaded'}), 500
    
    feature_importance = model.get_feature_importance()
    
    info = {
        'model_type': str(model.model_type),
        'is_trained': bool(model.is_trained),
        'crops': [str(crop) for crop in model.crops],
        'features': [str(feature) for feature in model.feature_cols],
        'feature_importance': {
            str(name): float(score) for name, score in feature_importance.items()
        },
        'n_features': int(len(model.feature_cols)),
        'n_crops': int(len(model.crops)),
    }
    
    response = jsonify(info)
    response.headers.update(CORS_HEADERS)
    return response, 200


@app.route('/resolve-location', methods=['POST', 'OPTIONS'])
def resolve_location():
    """Resolve a user-entered location or coordinates into a normalized location context."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.update(CORS_HEADERS)
        return response, 200

    try:
        data = request.get_json() or {}
        location_context = resolve_location_context(data)
        response = jsonify(location_context)
        response.headers.update(CORS_HEADERS)
        return response, 200
    except ValueError as e:
        response = jsonify({'error': f'Invalid input: {str(e)}'})
        response.headers.update(CORS_HEADERS)
        return response, 400
    except OpenWeatherError as e:
        response = jsonify({'error': str(e)})
        response.headers.update(CORS_HEADERS)
        return response, 502


@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.update(CORS_HEADERS)
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


if __name__ == '__main__':
    if initialize_app():
        print("\nStarting Flask API server...")
        print("API endpoints:")
        print("  GET  /health          - Health check")
        print("  POST /predict         - Make a single prediction")
        print("  POST /predict-batch   - Make batch predictions")
        print("  GET  /model-info      - Get model information")
        print("\nServer running at http://localhost:5000")
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        print("Failed to initialize app")
