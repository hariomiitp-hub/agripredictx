"""
Enhanced Flask API Server for AgriPredictX with SHAP Explainability
Local deployment with integrated ingestion, feature engineering, and explanations
"""
import os
import json
import logging
import time
import traceback
from datetime import datetime
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import uuid

# Import system components
from system_integration import initialize_system, PredictionPipeline
from model import CropPredictionModel, train_model_from_scratch
from recommender_engine import CropRecommendationEngine
from data_preparation import get_feature_columns
from data_models import FarmInput, SoilParameters, WeatherData, WeatherForecast
from agricultural_indicators import (
    SoilFertilityIndexCalculator,
    GrowingDegreeDaysCalculator,
    CumulativeRainfallCalculator,
    NDVICalculator,
)
from ingestion_layer import DatabaseConnector, IngestionOrchestrator
from database_models import ClaimRecord, FarmLossScore, FarmRecord, LossEvent
from insurance_assurance import (
    build_loss_report,
    build_evidence_packet,
    calculate_loss_score,
    claim_to_dict,
    claim_outcome_analytics,
    counterfactual_loss,
    detect_loss_events,
    report_pdf_bytes,
    save_claim,
    save_voice_loss_report,
    validate_enrollment,
)
from insurance_integrations import NotificationService, TranscriptionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.update(
    TEMPLATES_AUTO_RELOAD=True,
    SEND_FILE_MAX_AGE_DEFAULT=0,
)
app.jinja_env.auto_reload = True
CORS(app)

# Global state
system = None
model = None
pipeline = None
engine = None
db_connector = None
orchestrator = None
notification_service = NotificationService()
transcription_service = TranscriptionService()

# Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "crop_model.pkl")
DATABASE_URL = os.getenv("DATABASE_URL", 
                         "postgresql://agripredictx:agripredict123@localhost:5432/agripredictx")
B2B_API_KEY = os.getenv("AGRIPREDICTX_B2B_API_KEY", "")
B2B_RATE_LIMIT = int(os.getenv("B2B_RATE_LIMIT_PER_MINUTE", "60"))
B2B_REQUESTS = {}


def require_b2b_access():
    """Apply a minimal API-key/role boundary until production auth is integrated."""
    supplied_key = request.headers.get("X-API-Key", "")
    role = request.headers.get("X-Role", "")
    if not B2B_API_KEY or supplied_key != B2B_API_KEY:
        return jsonify({'error': 'b2b_authentication_required'}), 401
    if role not in {'insurer', 'state_department', 'fpo_admin'}:
        return jsonify({'error': 'b2b_role_required'}), 403
    identity = f'{supplied_key}:{role}'
    now = time.time()
    recent = [stamp for stamp in B2B_REQUESTS.get(identity, []) if now - stamp < 60]
    if len(recent) >= B2B_RATE_LIMIT:
        return jsonify({'error': 'b2b_rate_limit_exceeded'}), 429
    recent.append(now)
    B2B_REQUESTS[identity] = recent
    return None


def initialize_system_components():
    """Initialize all system components on startup"""
    global system, model, pipeline, engine, db_connector, orchestrator
    
    if system is not None:
        return True
    
    try:
        logger.info("Initializing AgriPredictX system components...")
        
        # Initialize database
        db_connector = DatabaseConnector(DATABASE_URL)
        logger.info("✓ Database connector initialized")
        
        # Initialize system
        system = initialize_system(DATABASE_URL)
        logger.info("✓ System initialized")
        
        # Load or train model
        if os.path.exists(MODEL_PATH):
            logger.info(f"Loading model from {MODEL_PATH}")
            model = CropPredictionModel.load_model(MODEL_PATH)
        else:
            logger.info("Training new model...")
            model = train_model_from_scratch()
            model.save_model(MODEL_PATH)
        
        logger.info("✓ Model loaded/trained")
        engine = CropRecommendationEngine(model)
        logger.info("✓ Recommendation engine ready")
        
        # Setup explainability
        X_train = np.random.randn(100, len(get_feature_columns()))
        system.setup_explainability(
            model=model,
            X_train=X_train,
            feature_names=get_feature_columns(),
            model_type='tree'
        )
        logger.info("✓ SHAP explainability configured")
        
        # Create prediction pipeline
        pipeline = PredictionPipeline(system, model)
        logger.info("✓ Prediction pipeline ready")
        
        # Initialize ingestion orchestrator
        orchestrator = IngestionOrchestrator(db_connector)
        logger.info("✓ Ingestion orchestrator ready")
        
        logger.info("✓ All system components initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"System initialization failed: {str(e)}")
        return False


def ensure_initialized():
    """Middleware to ensure system is initialized"""
    if system is None:
        initialize_system_components()


@app.after_request
def after_request(response):
    """Prevent stale dashboard assets during local hosting."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    ensure_initialized()
    return jsonify({
        'status': 'healthy',
        'service': 'AgriPredictX API',
        'version': '2.0',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'model': model is not None,
            'database': db_connector is not None,
            'explainability': system.explainer is not None if system else False,
        }
    }), 200


@app.route('/', methods=['GET'])
def dashboard():
    """Serve the dashboard website"""
    ensure_initialized()
    return render_template("index.html", product_name="AgriPredictX")


@app.route('/sample-farms', methods=['GET'])
def sample_farms():
    """Return bundled sample farms for demo"""
    try:
        with open("sample_farms.json", "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return jsonify(data), 200
    except FileNotFoundError:
        return jsonify({'error': 'Sample farms file not found'}), 404


@app.route('/api/farm/register', methods=['POST', 'OPTIONS'])
def register_farm():
    """Register the minimum farm context required for assurance evidence."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    payload = request.get_json() or {}
    required = ('farm_id', 'state', 'district', 'crop')
    if any(not str(payload.get(field, '')).strip() for field in required):
        return jsonify({'error': 'farm_id, state, district, and crop are required'}), 400
    session = db_connector.get_session()
    try:
        farm = session.query(FarmRecord).filter(FarmRecord.farm_id == str(payload['farm_id'])).one_or_none()
        if farm is None:
            farm = FarmRecord(farm_id=str(payload['farm_id']))
            session.add(farm)
        for field in ('state', 'district', 'crop', 'season'):
            if payload.get(field) is not None:
                setattr(farm, field, str(payload[field]))
        for field in ('area_hectares', 'latitude', 'longitude'):
            if payload.get(field) is not None:
                setattr(farm, field, float(payload[field]))
        farm.profile = payload
        session.commit()
        return jsonify({'status': 'registered', 'farm_id': farm.farm_id}), 201
    except (TypeError, ValueError) as exc:
        session.rollback()
        return jsonify({'error': 'invalid farm data', 'details': str(exc)}), 400
    finally:
        session.close()


@app.route('/api/farm/<farm_id>/loss-score', methods=['GET', 'POST', 'OPTIONS'])
def farm_loss_score(farm_id):
    """Create a timestamped loss verification snapshot for a registered farm."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    session = db_connector.get_session()
    try:
        snapshot, response = calculate_loss_score(session, model, farm_id, request.get_json(silent=True) or {})
        if snapshot is None:
            return jsonify(response), 404
        return jsonify(response), 200
    except Exception as exc:
        session.rollback()
        logger.exception('Loss score calculation failed')
        return jsonify({'error': 'loss_score_unavailable', 'details': str(exc)}), 503
    finally:
        session.close()


@app.route('/api/loss-events/detect', methods=['POST', 'OPTIONS'])
def detect_farm_loss_event():
    """Run the idempotent NDVI loss detector for one registered farm."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    payload = request.get_json() or {}
    farm_id = payload.get('farm_id')
    if not farm_id:
        return jsonify({'error': 'farm_id is required'}), 400
    session = db_connector.get_session()
    try:
        farm = session.query(FarmRecord).filter(FarmRecord.farm_id == str(farm_id)).one_or_none()
        if farm is None:
            return jsonify({'error': 'farm_not_registered'}), 404
        event = detect_loss_events(
            session, farm,
            ndvi_drop_pct=float(payload.get('ndvi_drop_pct', 20)),
            window_days=int(payload.get('window_days', 14)),
            cooldown_days=int(payload.get('cooldown_days', 14)),
        )
        if event is None:
            return jsonify({'detected': False, 'message': 'No configured loss threshold crossed.'}), 200
        if not event.claim_draft:
            event.claim_draft = {
                'farm_id': farm.farm_id,
                'status': 'loss_detected',
                'event_id': event.id,
                'requires_farmer_confirmation': True,
            }
            session.commit()
        notification = notification_service.send_loss_alert(farm.farm_id, event.id, payload.get('channel', 'app'))
        return jsonify({'detected': True, 'event_id': event.id, 'event_type': event.event_type,
                        'detected_at': event.detected_at.isoformat(), 'severity': event.severity,
                'claim_draft': event.claim_draft, 'notification': notification}), 201
    except (TypeError, ValueError) as exc:
        session.rollback()
        return jsonify({'error': 'invalid_detection_configuration', 'details': str(exc)}), 400
    finally:
        session.close()


@app.route('/api/farm/enroll/validate', methods=['POST', 'OPTIONS'])
def validate_farm_enrollment():
    """Run non-blocking crop and area sanity checks and persist the audit result."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    payload = request.get_json() or {}
    if not payload.get('farm_id') and not payload.get('crop'):
        return jsonify({'error': 'farm_id or crop is required'}), 400
    session = db_connector.get_session()
    try:
        return jsonify(validate_enrollment(session, payload)), 200
    except Exception as exc:
        session.rollback()
        return jsonify({'error': 'enrollment_validation_unavailable', 'details': str(exc)}), 503
    finally:
        session.close()


@app.route('/api/farm/<farm_id>/loss-report', methods=['GET', 'OPTIONS'])
def farm_loss_report(farm_id):
    """Return a plain-language loss report or its standalone PDF artifact."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    event_id = request.args.get('event_id')
    if not event_id:
        return jsonify({'error': 'event_id is required'}), 400
    session = db_connector.get_session()
    try:
        report, error = build_loss_report(session, farm_id, event_id, request.args.get('language', 'en'))
        if report is None:
            return jsonify(error), 404
        if request.args.get('format') == 'pdf' or 'application/pdf' in request.headers.get('Accept', ''):
            response = app.response_class(report_pdf_bytes(report), mimetype='application/pdf')
            response.headers['Content-Disposition'] = f'attachment; filename="loss-report-{farm_id}-{event_id}.pdf"'
            return response
        return jsonify(report), 200
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid_event_id'}), 400
    finally:
        session.close()


@app.route('/api/farm/<farm_id>/counterfactual-loss', methods=['GET', 'OPTIONS'])
def farm_counterfactual_loss(farm_id):
    """Compare the normal bounded trajectory with recorded loss-score trajectory."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    session = db_connector.get_session()
    try:
        result, error = counterfactual_loss(session, farm_id, request.args.get('start_date'), request.args.get('end_date'))
        return (jsonify(error), 404) if result is None else (jsonify(result), 200)
    finally:
        session.close()


@app.route('/api/claims', methods=['GET', 'POST', 'OPTIONS'])
def claims_collection():
    """Create a claim timeline entry or list claims for a farm."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    session = db_connector.get_session()
    try:
        if request.method == 'POST':
            return jsonify(save_claim(session, request.get_json() or {})), 201
        farm_id = request.args.get('farm_id')
        query = session.query(ClaimRecord)
        if farm_id:
            query = query.filter(ClaimRecord.farm_id == farm_id)
        return jsonify({'claims': [claim_to_dict(claim) for claim in query.order_by(ClaimRecord.status_updated_at.desc()).all()]}), 200
    except ValueError as exc:
        session.rollback()
        return jsonify({'error': 'invalid_claim', 'details': str(exc)}), 400
    finally:
        session.close()


@app.route('/api/claims/<int:claim_id>', methods=['GET', 'PATCH', 'OPTIONS'])
def claim_item(claim_id):
    """Read or update a claim timeline entry."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    session = db_connector.get_session()
    try:
        claim = session.query(ClaimRecord).filter(ClaimRecord.id == claim_id).one_or_none()
        if claim is None:
            return jsonify({'error': 'claim_not_found'}), 404
        if request.method == 'PATCH':
            payload = request.get_json() or {}
            payload['farm_id'] = claim.farm_id
            return jsonify(save_claim(session, payload, claim_id)), 200
        return jsonify(claim_to_dict(claim)), 200
    except ValueError as exc:
        session.rollback()
        return jsonify({'error': 'invalid_claim', 'details': str(exc)}), 400
    finally:
        session.close()


@app.route('/api/b2b/loss-summary', methods=['GET', 'OPTIONS'])
def b2b_loss_summary():
    """Aggregate supporting loss scores for authorized insurer/state consumers."""
    if request.method == 'OPTIONS':
        return '', 200
    denied = require_b2b_access()
    if denied:
        return denied
    ensure_initialized()
    session = db_connector.get_session()
    try:
        farms = session.query(FarmRecord).all()
        state = request.args.get('state')
        district = request.args.get('district')
        rows = []
        for farm in farms:
            if state and farm.state != state or district and farm.district != district:
                continue
            score = session.query(FarmLossScore).filter(FarmLossScore.farm_id == farm.farm_id).order_by(FarmLossScore.snapshot_date.desc()).first()
            if score:
                rows.append({'farm_id': farm.farm_id, 'state': farm.state, 'district': farm.district,
                             'crop': farm.crop, 'score': score.score, 'yield_delta_pct': score.yield_delta_pct,
                             'snapshot_date': score.snapshot_date.isoformat()})
        return jsonify({'scope': {'state': state, 'district': district}, 'farms': rows,
                        'supporting_evidence_only': True}), 200
    finally:
        session.close()


@app.route('/api/b2b/anomalies', methods=['GET', 'OPTIONS'])
def b2b_anomalies():
    """Surface review candidates, never fraud determinations."""
    if request.method == 'OPTIONS':
        return '', 200
    denied = require_b2b_access()
    if denied:
        return denied
    ensure_initialized()
    session = db_connector.get_session()
    try:
        candidates = []
        for farm in session.query(FarmRecord).all():
            score = session.query(FarmLossScore).filter(FarmLossScore.farm_id == farm.farm_id).order_by(FarmLossScore.snapshot_date.desc()).first()
            if score and score.score < 20:
                candidates.append({'farm_id': farm.farm_id, 'score': score.score,
                                   'review_reason': 'severe modeled loss signal; verify independently',
                                   'fraud_determination': False})
        return jsonify({'candidates': candidates, 'sensitive_use_notice': 'These are review candidates, not fraud findings.'}), 200
    finally:
        session.close()


@app.route('/fpo/dashboard', methods=['GET', 'OPTIONS'])
def fpo_dashboard():
    """Return an aggregate member view for an authorized FPO administrator."""
    if request.method == 'OPTIONS':
        return '', 200
    denied = require_b2b_access()
    if denied:
        return denied
    ensure_initialized()
    session = db_connector.get_session()
    try:
        crop = request.args.get('crop')
        village = request.args.get('village')
        members = []
        for farm in session.query(FarmRecord).all():
            profile = farm.profile or {}
            if crop and farm.crop != crop or village and profile.get('village') != village:
                continue
            score = session.query(FarmLossScore).filter(FarmLossScore.farm_id == farm.farm_id).order_by(FarmLossScore.snapshot_date.desc()).first()
            claims = session.query(ClaimRecord).filter(ClaimRecord.farm_id == farm.farm_id).all()
            members.append({'farm_id': farm.farm_id, 'crop': farm.crop,
                            'loss_score': score.score if score else None,
                            'claims': [claim_to_dict(claim) for claim in claims]})
        return jsonify({'filters': {'crop': crop, 'village': village}, 'members': members}), 200
    finally:
        session.close()


@app.route('/fpo/evidence-packets', methods=['POST', 'OPTIONS'])
def fpo_evidence_packets():
    """Prepare evidence packet payloads for multiple authorized FPO members."""
    if request.method == 'OPTIONS':
        return '', 200
    denied = require_b2b_access()
    if denied:
        return denied
    ensure_initialized()
    payload = request.get_json() or {}
    requests = payload.get('farms') or []
    if not isinstance(requests, list) or len(requests) > 100:
        return jsonify({'error': 'farms must be a list with at most 100 entries'}), 400
    session = db_connector.get_session()
    try:
        packets = []
        for item in requests:
            farm_id = item.get('farm_id')
            event_id = item.get('event_id')
            if not farm_id or not event_id:
                packets.append({'farm_id': farm_id, 'status': 'error', 'error': 'event_id_required'})
                continue
            packet, error = build_evidence_packet(session, farm_id, event_id, payload.get('language', 'en'))
            packets.append({'farm_id': farm_id, 'status': 'success', 'packet': packet} if packet else {
                'farm_id': farm_id, 'status': 'error', 'error': error,
            })
        return jsonify({'packets': packets, 'supporting_evidence_only': True}), 200
    finally:
        session.close()


@app.route('/api/farm/<farm_id>/voice-report', methods=['POST', 'OPTIONS'])
def farm_voice_report(farm_id):
    """Persist a Hindi-first voice transcript fallback as a farmer-reported event."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    session = db_connector.get_session()
    try:
        payload = request.get_json() or {}
        transcription = transcription_service.transcribe(
            payload.get('audio_reference'), payload.get('transcript'), payload.get('language', 'hi')
        )
        if transcription.get('transcript'):
            payload['transcript'] = transcription['transcript']
        result, error = save_voice_loss_report(session, farm_id, payload)
        if result is not None:
            result['transcription'] = transcription
        return (jsonify(error), 404 if error and error.get('error') == 'farm_not_registered' else 400) if result is None else (jsonify(result), 201)
    finally:
        session.close()


@app.route('/api/farm/<farm_id>/evidence-packet', methods=['GET', 'OPTIONS'])
def farm_evidence_packet(farm_id):
    """Bundle score history, events, SHAP report, weather, and counterfactual evidence."""
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200
    event_id = request.args.get('event_id')
    if not event_id:
        return jsonify({'error': 'event_id is required'}), 400
    session = db_connector.get_session()
    try:
        packet, error = build_evidence_packet(session, farm_id, event_id, request.args.get('language', 'en'))
        if packet is None:
            return jsonify(error), 404
        report = packet['cover']
        if request.args.get('format') == 'pdf' or 'application/pdf' in request.headers.get('Accept', ''):
            response = app.response_class(report_pdf_bytes({
                **report,
                'localized_text': {**report.get('localized_text', {}),
                                   'title': f"Evidence Packet - {report['farm_id']}"},
                'top_contributors': report.get('top_contributors', []) + [
                    {'sentence': f"Included {len(packet['loss_score_history'])} loss-score snapshots and {len(packet['weather_evidence'])} weather observations."}
                ],
            }, packet.get('imagery', {}).get('thumbnail_data_uri')), mimetype='application/pdf')
            response.headers['Content-Disposition'] = f'attachment; filename="evidence-packet-{farm_id}-{event_id}.pdf"'
            return response
        return jsonify(packet), 200
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid_event_id'}), 400
    finally:
        session.close()


@app.route('/api/b2b/claim-analytics', methods=['GET', 'OPTIONS'])
def b2b_claim_analytics():
    """Return descriptive claim outcome metrics once enough history exists."""
    if request.method == 'OPTIONS':
        return '', 200
    denied = require_b2b_access()
    if denied:
        return denied
    ensure_initialized()
    session = db_connector.get_session()
    try:
        return jsonify(claim_outcome_analytics(session)), 200
    finally:
        session.close()


def build_location_context(payload):
    latitude = payload.get('latitude')
    longitude = payload.get('longitude')

    if latitude is not None or longitude is not None:
        if latitude is None or longitude is None:
            raise ValueError('Both latitude and longitude are required when using coordinates.')

        return {
            'location_name': payload.get('location_name') or f"Current location ({float(latitude):.6f}, {float(longitude):.6f})",
            'district': payload.get('district') or '',
            'state': payload.get('state') or '',
            'country_code': (payload.get('country_code') or 'IN').strip().upper(),
            'latitude': round(float(latitude), 6),
            'longitude': round(float(longitude), 6),
            'resolution_method': 'coordinates',
        }

    return {
        'location_name': payload.get('location_name') or payload.get('district') or payload.get('state') or '',
        'district': payload.get('district') or '',
        'state': payload.get('state') or '',
        'country_code': (payload.get('country_code') or 'IN').strip().upper(),
        'latitude': None,
        'longitude': None,
        'resolution_method': 'manual_input',
    }


def build_agricultural_indicator_bundle(soil_data, weather_data, location_context):
    sfi = SoilFertilityIndexCalculator.calculate(soil_data)
    gdd = GrowingDegreeDaysCalculator.calculate_seasonal_gdd(
        current_temperature=weather_data.get('temperature', 25),
        humidity=weather_data.get('humidity', 70),
        rainfall=weather_data.get('rainfall', 100),
        forecast_windows=[],
        season_length_days=120,
    )
    cumulative_rainfall = CumulativeRainfallCalculator.calculate_seasonal_rainfall(
        current_rainfall=weather_data.get('rainfall', 100),
        forecast_windows=[],
        months_ahead=3,
    )
    ndvi, ndvi_metadata = NDVICalculator.calculate_with_metadata(
        soil_fertility_index=sfi,
        rainfall=cumulative_rainfall,
        current_temperature=weather_data.get('temperature', 25),
        soil_moisture=soil_data.get('moisture', 35),
        coordinates=(
            (location_context['latitude'], location_context['longitude'])
            if location_context['latitude'] is not None else None
        ),
    )

    return {
        'gdd': gdd,
        'cumulative_rainfall': cumulative_rainfall,
        'soil_fertility_index': sfi,
        'ndvi': ndvi,
        'auto_filled': True,
        'data_sources': {
            'weather_forecast': 'fallback_estimate',
            'ndvi': ndvi_metadata.get('source', 'fallback_estimate'),
            'location_resolution': location_context.get('resolution_method'),
        },
        'indicator_descriptions': {
            'gdd': 'Estimated Growing Degree Days using submitted weather and fallback outlook.',
            'cumulative_rainfall': 'Seasonal rainfall estimated from current rainfall plus simple local forecast.',
            'soil_fertility_index': 'Soil Fertility Index calculated from soil nutrient, moisture, and fertilizer inputs.',
            'ndvi': 'Estimated NDVI via soil, weather, and fallback Earth Engine metadata.',
        },
        'ndvi_metadata': ndvi_metadata,
    }


@app.route('/calculate-indicators', methods=['POST', 'OPTIONS'])
def calculate_indicators():
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200

    try:
        payload = request.get_json()
        if not payload or 'soil' not in payload or 'weather' not in payload:
            return jsonify({'error': 'Invalid input. Must include soil and weather data'}), 400

        location_context = build_location_context(payload)
        indicators = build_agricultural_indicator_bundle(payload['soil'], payload['weather'], location_context)
        return jsonify({
            'agricultural_indicators': indicators,
            'location_context': location_context,
        }), 200
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        logger.error(f'Indicator calculation error: {exc}')
        return jsonify({'error': str(exc)}), 500


@app.route('/resolve-location', methods=['POST', 'OPTIONS'])
def resolve_location():
    ensure_initialized()
    if request.method == 'OPTIONS':
        return '', 200

    payload = request.get_json() or {}
    try:
        location_context = build_location_context(payload)
        return jsonify(location_context), 200
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400


@app.route('/model-info', methods=['GET', 'OPTIONS'])
def model_info():
    ensure_initialized()
    try:
        importance = model.get_feature_importance() if model else {}
    except Exception:
        importance = {}

    return jsonify({
        'model_type': type(model).__name__ if model is not None else 'UnknownModel',
        'n_crops': len(get_feature_columns()),
        'n_features': len(get_feature_columns()),
        'feature_importance': {str(name): float(score) for name, score in importance.items()},
        'features': [str(feature) for feature in get_feature_columns()],
    }), 200


@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    """
    Predict crop yield with SHAP explanation.
    
    Expected JSON:
    {
        "soil": {
            "nitrogen": 150,
            "phosphorus": 80,
            "potassium": 120,
            "ph": 7.0,
            "moisture": 25,
            "soil_type": "loamy",
            "organic_carbon": 1.5,
            "electrical_conductivity": 0.8,
            ...
        },
        "weather": {
            "temperature": 28.5,
            "humidity": 65,
            "rainfall": 50
        },
        "state": "Punjab",
        "district": "Ludhiana",
        "crop": "wheat"
    }
    """
    ensure_initialized()
    
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        # Extract parameters
        soil_data = data.get('soil', {})
        weather_data = data.get('weather', {})
        state = data.get('state', 'Unknown')
        district = data.get('district', 'Unknown')
        crop = data.get('crop', 'wheat')
        baseline_yield = data.get('baseline_yield', 3.0)

        soil_values = {
            'nitrogen': 150, 'phosphorus': 80, 'potassium': 120, 'ph': 7.0,
            'moisture': 25, 'soil_type': 'loamy', 'organic_carbon': 1.5,
            'electrical_conductivity': 0.8, 'dap': 40, 'urea': 80, 'ssp': 25,
            'mop': 25, 'zinc': 2.0, 'iron': 15.0, 'copper': 1.0,
            'boron': 0.8, 'manganese': 6.0,
        }
        soil_values.update(soil_data)
        soil = SoilParameters(**soil_values)
        weather = WeatherData(
            temperature=weather_data.get('temperature', 25),
            humidity=weather_data.get('humidity', 60),
            rainfall=weather_data.get('rainfall', 50),
        )
        forecast = WeatherForecast(
            WeatherData(weather.temperature, weather.humidity, weather.rainfall),
            WeatherData(weather.temperature + 1, min(weather.humidity + 3, 100), weather.rainfall * 1.05),
            WeatherData(weather.temperature + 0.5, max(weather.humidity - 2, 0), weather.rainfall * 0.95),
        )
        location_context = build_location_context(data)
        indicators = build_agricultural_indicator_bundle(soil_values, weather_data, location_context)
        farm_input = FarmInput(
            soil=soil,
            weather=weather,
            weather_forecast=forecast,
            agricultural_indicators={key: indicators[key] for key in ('gdd', 'cumulative_rainfall', 'soil_fertility_index', 'ndvi')},
            region=data.get('region'),
            farm_size=data.get('farm_size', data.get('land_area')),
            irrigation_available=data.get('irrigation_available'),
            historical_yield=data.get('historical_yield'),
            location_name=location_context.get('location_name'),
            district=location_context.get('district'),
            state=location_context.get('state'),
            country_code=location_context.get('country_code', 'IN'),
            latitude=location_context.get('latitude'),
            longitude=location_context.get('longitude'),
            land_area_unit=data.get('land_area_unit', 'hectares'),
        )
        
        # Prepare weather DataFrame
        weather_df = pd.DataFrame({
            'temp_max': [weather_data.get('temperature', 30)] * 100,
            'temp_min': [weather_data.get('temperature', 20) - 10] * 100,
            'rainfall': [weather_data.get('rainfall', 10)] * 100
        })
        
        # Prepare soil parameters
        soil_params = {
            'nitrogen': soil_data.get('nitrogen', 150),
            'phosphorus': soil_data.get('phosphorus', 80),
            'potassium': soil_data.get('potassium', 120)
        }
        
        # Generate prediction
        prediction_id = str(uuid.uuid4())
        result = pipeline.predict_from_raw_data(
            state=state,
            district=district,
            crop=crop,
            weather_df=weather_df,
            soil_params=soil_params,
            ndvi_series=pd.Series(np.linspace(0.3, 0.8, 100)),
            feature_names=get_feature_columns(),
            baseline_yield=baseline_yield
        )
        recommendations = engine.get_recommendations(farm_input, top_n=3).to_dict()
        
        logger.info(f"Prediction {prediction_id}: {result['predicted_yield']:.2f} t/ha")
        
        return jsonify({
            'success': True,
            'prediction_id': result['prediction_id'],
            'location': f"{state}, {district}",
            'crop': crop,
            'predicted_yield': f"{result['predicted_yield']:.2f} t/ha",
            'baseline_yield': f"{baseline_yield:.2f} t/ha",
            'difference': f"{result['predicted_yield'] - baseline_yield:+.2f} t/ha",
            'top_positive_factors': result.get('top_positive_features', [])[:3],
            'top_negative_factors': result.get('top_negative_features', [])[:3],
            'shap_values': result.get('shap_values', {}),
            'explanation': result.get('explanation', {}),
            'timestamp': datetime.utcnow().isoformat()
            , **recommendations
        }), 200
        
    except Exception as e:
        logger.error("Prediction error: %s\n%s", str(e), traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/ingestion/weather', methods=['POST'])
def ingest_weather():
    """Ingest weather data from OpenWeatherMap"""
    ensure_initialized()
    
    try:
        data = request.get_json()
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        state = data.get('state', 'Unknown')
        district = data.get('district', 'Unknown')
        
        if not all([latitude, longitude]):
            return jsonify({'error': 'Missing latitude/longitude'}), 400
        
        # Fetch and store weather
        records = orchestrator.weather.fetch_weather(
            latitude, longitude, state, district
        )
        
        if records:
            orchestrator.weather.parse_and_store_weather(records, state, district)
            orchestrator.log_ingestion(
                source_type='weather',
                operation='api_fetch',
                status='success',
                records_processed=len(records.get('list', [])) if isinstance(records, dict) else 0,
                start_time=datetime.utcnow()
            )
            logger.info(f"Ingested weather for {state}, {district}")
            
            return jsonify({
                'success': True,
                'message': f'Ingested weather data for {state}, {district}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch weather data'
            }), 400
        
    except Exception as e:
        logger.error(f"Weather ingestion error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/ingestion/soil', methods=['POST'])
def ingest_soil():
    """Ingest soil fertility data"""
    ensure_initialized()
    
    try:
        data = request.get_json()
        
        state = data.get('state', 'Unknown')
        district = data.get('district', 'Unknown')
        nitrogen = data.get('nitrogen', 150)
        phosphorus = data.get('phosphorus', 80)
        potassium = data.get('potassium', 120)
        
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
            sfi = orchestrator.soil._calculate_sfi(nitrogen, phosphorus, potassium)
            logger.info(f"Ingested soil data for {state}, {district} (SFI: {sfi:.3f})")
            
            return jsonify({
                'success': True,
                'message': f'Soil fertility data stored for {state}, {district}',
                'soil_fertility_index': sfi
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to store soil data'
            }), 400
        
    except Exception as e:
        logger.error(f"Soil ingestion error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/prediction-history', methods=['GET'])
def prediction_history():
    """Get recent prediction history"""
    ensure_initialized()
    
    try:
        from database_models import PredictionExplanability
        
        session = db_connector.get_session()
        predictions = session.query(PredictionExplanability).order_by(
            PredictionExplanability.created_at.desc()
        ).limit(10).all()
        
        history = []
        for pred in predictions:
            history.append({
                'prediction_id': pred.prediction_id,
                'state': pred.state,
                'district': pred.district,
                'crop': pred.crop,
                'predicted_yield': pred.predicted_yield,
                'baseline_yield': pred.baseline_yield,
                'created_at': pred.created_at.isoformat() if pred.created_at else None,
                'top_positive': json.loads(pred.top_positive_features) if pred.top_positive_features else [],
                'top_negative': json.loads(pred.top_negative_features) if pred.top_negative_features else []
            })
        
        session.close()
        
        return jsonify({
            'success': True,
            'predictions': history
        }), 200
        
    except Exception as e:
        logger.error(f"History retrieval error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/ingestion-logs', methods=['GET'])
def ingestion_logs():
    """Get recent ingestion operation logs"""
    ensure_initialized()
    
    try:
        from database_models import IngestionLog
        
        session = db_connector.get_session()
        logs = session.query(IngestionLog).order_by(
            IngestionLog.created_at.desc()
        ).limit(20).all()
        
        log_data = []
        for log in logs:
            log_data.append({
                'source_type': log.source_type,
                'operation': log.operation,
                'status': log.status,
                'records_processed': log.records_processed,
                'records_failed': log.records_failed,
                'duration_seconds': log.duration_seconds,
                'error_message': log.error_message,
                'created_at': log.created_at.isoformat() if log.created_at else None
            })
        
        session.close()
        
        return jsonify({
            'success': True,
            'logs': log_data
        }), 200
        
    except Exception as e:
        logger.error(f"Log retrieval error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api-docs', methods=['GET'])
def api_docs():
    """API documentation"""
    return jsonify({
        'service': 'AgriPredictX API v2.0',
        'endpoints': {
            'GET /health': 'Health check',
            'GET /': 'Dashboard UI',
            'POST /predict': 'Predict yield with SHAP explanation',
            'POST /ingestion/weather': 'Ingest weather data',
            'POST /ingestion/soil': 'Ingest soil fertility data',
            'GET /prediction-history': 'Recent predictions',
            'GET /ingestion-logs': 'Ingestion operation logs',
            'POST /api/farm/register': 'Register farm context for supporting evidence',
            'GET|POST /api/farm/{farm_id}/loss-score': 'Timestamped loss verification score',
            'POST /api/loss-events/detect': 'Run cooldown-protected loss-event detection',
            'GET /api/farm/{farm_id}/loss-report': 'Plain-language loss report or PDF artifact',
            'POST /api/farm/enroll/validate': 'Non-blocking enrollment sanity checks',
            'GET /api/farm/{farm_id}/counterfactual-loss': 'Bounded normal-vs-loss trajectory comparison',
            'GET|POST /api/claims': 'Claim timeline collection',
            'GET|PATCH /api/claims/{claim_id}': 'Claim timeline item',
            'GET /api/b2b/loss-summary': 'Authenticated regional loss-score aggregation',
            'GET /api/b2b/anomalies': 'Authenticated review candidates, not fraud findings',
            'GET /fpo/dashboard': 'Authenticated FPO member and claim view',
            'POST /api/farm/{farm_id}/voice-report': 'Hindi-first transcript fallback for farmer reports',
            'GET /api/farm/{farm_id}/evidence-packet': 'Combined grievance evidence packet or PDF',
            'POST /fpo/evidence-packets': 'Bulk evidence packet preparation for FPO members',
            'GET /api/b2b/claim-analytics': 'Descriptive historical claim outcome analytics',
            'GET /api-docs': 'This documentation'
        },
        'features': [
            'Crop yield prediction',
            'SHAP explainability',
            'Multi-source data ingestion',
            'Soil Fertility Index calculation',
            'Growing Degree Days computation',
            'Complete audit logging',
            'Insurance Assurance supporting evidence workflows'
        ]
    }), 200


@app.before_request
def before_request():
    """Handle CORS preflight requests"""
    if request.method == 'OPTIONS':
        return '', 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found', 'available': '/api-docs'}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info("Starting AgriPredictX API Server...")
    logger.info(f"Database URL: {DATABASE_URL}")
    
    # Initialize on startup
    if initialize_system_components():
        logger.info("\n" + "="*60)
        logger.info("✓ AgriPredictX API Ready!")
        logger.info("="*60)
        logger.info("Local API running on: http://localhost:5000")
        logger.info("Dashboard: http://localhost:5000/")
        logger.info("API Docs: http://localhost:5000/api-docs")
        logger.info("Health Check: http://localhost:5000/health")
        logger.info("="*60 + "\n")
        
        # Start Flask server
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
            use_reloader=False
        )
    else:
        logger.error("Failed to initialize system components!")
        exit(1)
