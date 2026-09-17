"""Composable Insurance Assurance services for farmer-facing evidence workflows."""
from datetime import datetime, timedelta
import logging
import json
import re
import base64
import io
import importlib
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from database_models import (
    FarmRecord,
    FarmLossScore,
    LossEvent,
    EnrollmentValidationResult,
    SatelliteNDVIData,
    WeatherObservation,
    SoilFertilityRecord,
    CropYieldRecord,
    PredictionExplanability,
    ClaimRecord,
)
from data_preparation import get_feature_columns
from config import SOIL_TYPES, CROP_REQUIREMENTS
from insurance_integrations import ndvi_thumbnail_data_uri

logger = logging.getLogger(__name__)
MODEL_VERSION = "insurance-assurance-v1"
DEFAULT_EVENT_COOLDOWN_DAYS = 14
CLAIM_STATUSES = ("enrolled", "loss_detected", "reported", "assessed", "settled", "disputed")
LOCALE_DIRECTORY = Path(__file__).with_name("locales")


def _translations(language="en"):
    selected = language if language in {"en", "hi"} else "en"
    try:
        with (LOCALE_DIRECTORY / f"{selected}.json").open(encoding="utf-8") as handle:
            return selected, json.load(handle)
    except (OSError, ValueError):
        with (LOCALE_DIRECTORY / "en.json").open(encoding="utf-8") as handle:
            return "en", json.load(handle)


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _farm_or_none(session, farm_id):
    return session.query(FarmRecord).filter(FarmRecord.farm_id == str(farm_id)).one_or_none()


def _latest_sources(session, farm):
    ndvi = session.query(SatelliteNDVIData).filter(
        SatelliteNDVIData.state == farm.state,
        SatelliteNDVIData.district == farm.district,
        SatelliteNDVIData.crop == farm.crop,
    ).order_by(SatelliteNDVIData.observation_date.desc()).first()
    weather = session.query(WeatherObservation).filter(
        WeatherObservation.state == farm.state,
        WeatherObservation.district == farm.district,
    ).order_by(WeatherObservation.observation_date.desc()).first()
    soil = session.query(SoilFertilityRecord).filter(
        SoilFertilityRecord.state == farm.state,
        SoilFertilityRecord.district == farm.district,
    ).order_by(SoilFertilityRecord.measurement_date.desc()).first()
    return ndvi, weather, soil


def _model_condition_index(model, farm, ndvi, weather, soil) -> float:
    """Return the existing classifier's normalized condition signal (0-100)."""
    values = {
        "N": soil.nitrogen if soil else 100,
        "P": soil.phosphorus if soil else 50,
        "K": soil.potassium if soil else 80,
        "pH": soil.ph if soil and soil.ph is not None else 6.5,
        "moisture": 30,
        "organic_carbon": soil.organic_carbon if soil and soil.organic_carbon is not None else 1,
        "electrical_conductivity": soil.electrical_conductivity if soil and soil.electrical_conductivity is not None else 0.5,
        "temperature": weather.temperature_avg if weather and weather.temperature_avg is not None else 25,
        "humidity": weather.humidity if weather and weather.humidity is not None else 60,
        "rainfall": weather.rainfall if weather else 50,
        "gdd": 1200,
        "cumulative_rainfall": 500,
        "soil_fertility_index": soil.soil_fertility_index if soil else 0.5,
        "ndvi": ndvi.ndvi_value if ndvi else 0.5,
        "soil_type": SOIL_TYPES.get("loamy", 2),
    }
    feature_values = []
    for feature in get_feature_columns():
        if feature.startswith("month_"):
            key = feature.split("_", 2)[-1]
            feature_values.append(values.get(key, values.get("temperature", 25)))
        else:
            feature_values.append(values.get(feature, 0.0))
    try:
        probabilities = model.predict(np.asarray(feature_values, dtype=float).reshape(1, -1))[1]
        return float(np.max(probabilities[0]) * 100)
    except Exception as exc:
        logger.warning("Could not use model condition signal: %s", exc)
        return 50.0


def _baseline(session, farm):
    records = session.query(CropYieldRecord).filter(
        CropYieldRecord.crop == farm.crop,
        CropYieldRecord.state == farm.state,
        CropYieldRecord.district == farm.district,
    ).order_by(CropYieldRecord.year.desc()).limit(5).all()
    if len(records) >= 2:
        return float(np.mean([record.yield_per_hectare for record in records])), "farm_or_district_history"
    regional = session.query(CropYieldRecord).filter(
        CropYieldRecord.crop == farm.crop,
        CropYieldRecord.state == farm.state,
    ).order_by(CropYieldRecord.year.desc()).limit(20).all()
    if regional:
        return float(np.mean([record.yield_per_hectare for record in regional])), "regional_history"
    return 70.0, "regional_condition_index_fallback"


def calculate_loss_score(session, model, farm_id, payload=None):
    farm = _farm_or_none(session, farm_id)
    if farm is None:
        return None, {"error": "farm_not_registered", "message": "Register the farm before requesting supporting evidence."}
    ndvi, weather, soil = _latest_sources(session, farm)
    now = datetime.utcnow()
    ndvi_age_days = (now - ndvi.observation_date).days if ndvi else None
    modeled_index = _model_condition_index(model, farm, ndvi, weather, soil)
    baseline, baseline_source = _baseline(session, farm)
    projected = _as_float((payload or {}).get("projected_yield"), modeled_index)
    expected = _as_float((payload or {}).get("expected_yield"), baseline)
    delta = ((projected - expected) / expected * 100) if expected else 0.0
    score = float(np.clip(100 + delta, 0, 100))
    quality = []
    if ndvi is None:
        quality.append("no NDVI imagery available")
    elif ndvi_age_days > 30:
        quality.append(f"score based on {ndvi_age_days}-day-old imagery")
    elif ndvi.cloud_coverage is not None and ndvi.cloud_coverage > 40:
        quality.append("latest imagery has high cloud coverage")
    else:
        quality.append("latest NDVI imagery available")
    snapshot = FarmLossScore(
        farm_id=str(farm_id), score=score, yield_delta_pct=delta,
        model_version=MODEL_VERSION, data_quality="; ".join(quality),
        snapshot_date=now,
    )
    session.add(snapshot)
    session.commit()
    return snapshot, {
        "farm_id": str(farm_id), "score": round(score, 2),
        "yield_delta_pct": round(delta, 2), "expected_yield": round(expected, 2),
        "projected_yield": round(projected, 2), "model_version": MODEL_VERSION,
        "baseline_source": baseline_source, "data_quality": quality,
        "supporting_evidence_only": True, "timestamp": now.isoformat(),
    }


def detect_loss_events(session, farm, ndvi_drop_pct=20, window_days=14, cooldown_days=DEFAULT_EVENT_COOLDOWN_DAYS):
    thresholds = (farm.profile or {}).get("loss_thresholds", {}) if farm.profile else {}
    ndvi_drop_pct = _as_float(thresholds.get("ndvi_drop_pct"), ndvi_drop_pct)
    heat_threshold = _as_float(thresholds.get("heat_celsius"), 42)
    drought_rainfall = _as_float(thresholds.get("drought_rainfall_mm"), 2)
    ndvi_rows = session.query(SatelliteNDVIData).filter(
        SatelliteNDVIData.state == farm.state,
        SatelliteNDVIData.district == farm.district,
        SatelliteNDVIData.crop == farm.crop,
    ).order_by(SatelliteNDVIData.observation_date.desc()).limit(20).all()
    current = ndvi_rows[0] if ndvi_rows else None
    prior = [row for row in ndvi_rows[1:] if (current.observation_date - row.observation_date).days <= window_days] if current else []
    baseline = float(np.mean([row.ndvi_value for row in prior])) if prior else 0.0
    drop = ((baseline - current.ndvi_value) / baseline * 100) if current and baseline else 0
    event_type = "ndvi_drop" if drop >= ndvi_drop_pct else None
    snapshot = {"current_ndvi": current.ndvi_value if current else None, "baseline_ndvi": baseline, "drop_pct": drop,
                "thresholds": {"ndvi_drop_pct": ndvi_drop_pct, "heat_celsius": heat_threshold,
                               "drought_rainfall_mm": drought_rainfall}}
    weather = session.query(WeatherObservation).filter(
        WeatherObservation.state == farm.state,
        WeatherObservation.district == farm.district,
    ).order_by(WeatherObservation.observation_date.desc()).first()
    if event_type is None and weather and weather.temperature_max >= heat_threshold:
        event_type = "heat_extreme"
        snapshot["temperature_max"] = weather.temperature_max
    if event_type is None and weather and weather.rainfall <= drought_rainfall:
        event_type = "drought_signal"
        snapshot["rainfall"] = weather.rainfall
    if event_type is None:
        return None
    cutoff = datetime.utcnow() - timedelta(days=cooldown_days)
    existing = session.query(LossEvent).filter(
        LossEvent.farm_id == farm.farm_id,
        LossEvent.event_type == event_type,
        LossEvent.detected_at >= cutoff,
    ).first()
    if existing:
        return existing
    event = LossEvent(
        farm_id=farm.farm_id, event_type=event_type, detected_at=datetime.utcnow(),
        raw_sensor_snapshot=snapshot,
        severity="high" if drop >= 35 or event_type == "heat_extreme" else "moderate", source="auto-detected",
    )
    session.add(event)
    session.commit()
    return event


def validate_enrollment(session, payload):
    farm_id = str(payload.get("farm_id") or "enrollment-preview")
    declared_crop = str(payload.get("crop") or "").strip().lower()
    declared_area = _as_float(payload.get("area_hectares"))
    state = str(payload.get("state") or "Unknown")
    district = str(payload.get("district") or "Unknown")
    warnings = []
    checks = []
    classifier_available = declared_crop in CROP_REQUIREMENTS
    if not classifier_available:
        warnings.append({"type": "crop_classifier_unavailable", "message": "Crop classification is not available for this crop; manual review is recommended."})
    checks.append({"check": "crop", "declared": declared_crop, "confidence": 0.0 if not classifier_available else 0.55, "status": "warning" if not classifier_available else "insufficient_data"})
    satellite_area = payload.get("satellite_area_hectares")
    area_confidence = 0.0
    if satellite_area is not None and declared_area:
        satellite_area = _as_float(satellite_area)
        difference_pct = abs(declared_area - satellite_area) / satellite_area * 100 if satellite_area else 0
        area_confidence = 0.9
        if difference_pct > 10:
            warnings.append({"type": "area_mismatch", "declared": declared_area, "satellite": satellite_area, "difference_pct": round(difference_pct, 2)})
    else:
        warnings.append({"type": "area_evidence_unavailable", "message": "Satellite-derived boundary area was not supplied."})
    checks.append({"check": "area", "declared": declared_area, "satellite": satellite_area, "confidence": area_confidence, "status": "warning" if warnings and area_confidence else "insufficient_data"})
    result = {"farm_id": farm_id, "warnings": warnings, "checks": checks, "logged_at": datetime.utcnow().isoformat(), "supporting_evidence_only": True}
    session.add(EnrollmentValidationResult(farm_id=farm_id, declared_data=payload, result=result))
    session.commit()
    return result


def build_loss_report(session, farm_id, event_id, language="en"):
    farm = _farm_or_none(session, farm_id)
    event = session.query(LossEvent).filter(
        LossEvent.id == int(event_id), LossEvent.farm_id == str(farm_id)
    ).one_or_none()
    if farm is None:
        return None, {"error": "farm_not_registered"}
    if event is None:
        return None, {"error": "loss_event_not_found"}
    explanation = session.query(PredictionExplanability).filter(
        PredictionExplanability.state == farm.state,
        PredictionExplanability.district == farm.district,
        PredictionExplanability.crop == farm.crop,
    ).order_by(PredictionExplanability.created_at.desc()).first()
    shap_values = (explanation.shap_values if explanation else {}) or {}
    top_features = sorted(shap_values.items(), key=lambda item: abs(_as_float(item[1])), reverse=True)[:5]
    selected_language, strings = _translations(language)
    causes = [
        {"feature": str(feature), "contribution": round(_as_float(value), 4),
         "sentence": strings["cause_sentence"].format(
             feature=str(feature).replace("_", " ").capitalize(),
             value=abs(_as_float(value)),
         )}
        for feature, value in top_features
    ]
    report = {
        "farm_id": farm.farm_id,
        "event_id": event.id,
        "event_date": event.detected_at.isoformat(),
        "date_range": {"start": event.detected_at.isoformat(), "end": datetime.utcnow().isoformat()},
        "crop": farm.crop,
        "gps": {"latitude": farm.latitude, "longitude": farm.longitude},
        "top_contributors": causes,
        "sensor_snapshot": event.raw_sensor_snapshot,
        "shap_available": bool(explanation),
        "language": selected_language,
        "localized_text": {
            "title": strings["report_title"],
            "top_contributors": strings["top_contributors"],
            "thumbnail_unavailable": strings["thumbnail_unavailable"],
            "disclaimer": strings["disclaimer"],
        },
        "supporting_evidence_only": True,
        "disclaimer": "This is an independent estimate for supporting a claim, not an insurance eligibility or payout decision.",
    }
    return report, None


def report_pdf_bytes(report, thumbnail_data_uri=None):
    """Create a dependency-free, shareable PDF text artifact for local deployments."""
    if thumbnail_data_uri:
        try:
            plt = importlib.import_module("matplotlib.pyplot")
            image_bytes = base64.b64decode(thumbnail_data_uri.split(',', 1)[1])
            image = plt.imread(io.BytesIO(image_bytes), format='png')
            figure, axis = plt.subplots(figsize=(8.5, 11))
            axis.axis('off')
            axis.text(0.05, 0.96, report.get("localized_text", {}).get("title", "Insurance Assurance Evidence"), fontsize=14, weight='bold', va='top')
            axis.text(0.05, 0.91, f"Farm ID: {report['farm_id']}   Event ID: {report['event_id']}", fontsize=10, va='top')
            axis.imshow(image, extent=(0.05, 0.95, 0.52, 0.82), aspect='auto')
            axis.text(0.05, 0.47, report.get("localized_text", {}).get("disclaimer", "Supporting evidence only."), fontsize=9, va='top', wrap=True)
            buffer = io.BytesIO()
            figure.savefig(buffer, format='pdf', bbox_inches='tight')
            plt.close(figure)
            return buffer.getvalue()
        except Exception as exc:
            logger.warning("PDF thumbnail embedding unavailable: %s", exc)
    lines = [
        report.get("localized_text", {}).get("title", "AgriPredictX Insurance Assurance - Supporting Evidence"),
        f"Farm ID: {report['farm_id']}", f"Crop: {report['crop']}",
        f"Event ID: {report['event_id']}", f"Event date: {report['event_date']}",
        f"GPS: {report['gps'].get('latitude')}, {report['gps'].get('longitude')}",
        "", report.get("localized_text", {}).get("top_contributors", "Top model contributors:"),
    ] + [f"- {item['sentence']}" for item in report['top_contributors']] + [
        "", report.get("localized_text", {}).get("thumbnail_unavailable", "NDVI before/after thumbnail: unavailable in this deployment."),
        report.get("localized_text", {}).get("disclaimer", "This independent estimate is supporting evidence only; it does not determine eligibility or payout."),
    ]
    escaped = "\\n".join(line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)') for line in lines)
    stream = f"BT /F1 10 Tf 50 760 Td ({escaped}) Tj ET".encode('latin-1', 'replace')
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    pdf += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return pdf


def claim_to_dict(claim):
    now = datetime.utcnow()
    days = max((now - claim.status_updated_at).days, 0)
    threshold = 14 if claim.status in ("reported", "assessed") else 30
    return {
        "id": claim.id,
        "farm_id": claim.farm_id,
        "claim_id": claim.claim_id,
        "status": claim.status,
        "status_updated_at": claim.status_updated_at.isoformat(),
        "expected_next_action": claim.expected_next_action,
        "days_since_last_update": days,
        "escalate": days > threshold,
        "guidance": "Contact the insurer or grievance officer and retain this evidence packet." if days > threshold else None,
    }


def save_claim(session, payload, claim_id=None):
    farm_id = str(payload.get("farm_id") or "")
    if not farm_id:
        raise ValueError("farm_id is required")
    status = payload.get("status", "enrolled")
    if status not in CLAIM_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(CLAIM_STATUSES)}")
    claim = session.query(ClaimRecord).filter(ClaimRecord.id == claim_id).one_or_none() if claim_id else None
    if claim is None:
        claim = ClaimRecord(farm_id=farm_id, status=status)
        session.add(claim)
    elif claim.farm_id != farm_id:
        raise ValueError("claim does not belong to farm")
    claim.claim_id = payload.get("claim_id", claim.claim_id)
    claim.status = status
    claim.status_updated_at = datetime.utcnow()
    claim.expected_next_action = payload.get("expected_next_action", claim.expected_next_action)
    claim.last_note = payload.get("note", claim.last_note)
    session.commit()
    return claim_to_dict(claim)


def counterfactual_loss(session, farm_id, start_date=None, end_date=None):
    farm = _farm_or_none(session, farm_id)
    if farm is None:
        return None, {"error": "farm_not_registered"}
    scores = session.query(FarmLossScore).filter(FarmLossScore.farm_id == str(farm_id)).order_by(FarmLossScore.snapshot_date.asc()).all()
    actual = [{"date": item.snapshot_date.date().isoformat(), "yield_index": round(100 + item.yield_delta_pct, 2)} for item in scores]
    normal = [{"date": item["date"], "yield_index": 100.0} for item in actual]
    gap = round(float(np.mean([item["yield_index"] for item in actual])) - 100.0, 2) if actual else 0.0
    return {
        "farm_id": str(farm_id), "date_range": {"start": start_date, "end": end_date},
        "normal_historical_conditions": normal, "actual_predicted_trajectory": actual,
        "gap_pct": gap, "bounds_source": "existing historical baseline and model condition signal",
        "supporting_evidence_only": True,
    }, None


def save_voice_loss_report(session, farm_id, payload):
    farm = _farm_or_none(session, farm_id)
    if farm is None:
        return None, {"error": "farm_not_registered"}
    transcript = str(payload.get("transcript") or "").strip()
    if not transcript:
        return None, {"error": "transcript_required"}
    loss_match = re.search(r"(\d{1,3})\s*%", transcript)
    crop = next((name for name in CROP_REQUIREMENTS if name.replace("_", " ") in transcript.lower()), None)
    loss_pct = int(loss_match.group(1)) if loss_match else None
    confidence = 0.85 if crop and loss_pct is not None else 0.35
    event = LossEvent(
        farm_id=str(farm_id), event_type="farmer_reported", detected_at=datetime.utcnow(),
        raw_sensor_snapshot={"transcript": transcript, "crop": crop, "loss_pct": loss_pct,
                             "audio_reference": payload.get("audio_reference"), "language": payload.get("language", "hi")},
        severity="high" if loss_pct is not None and loss_pct >= 50 else "moderate",
        source="farmer-reported",
    )
    session.add(event)
    session.commit()
    return {"event_id": event.id, "farm_id": str(farm_id), "crop": crop,
            "loss_pct": loss_pct, "extraction_confidence": confidence,
            "requires_confirmation": confidence < 0.7, "source": "farmer-reported"}, None


def build_evidence_packet(session, farm_id, event_id, language="en"):
    report, error = build_loss_report(session, farm_id, event_id, language)
    if report is None:
        return None, error
    scores = session.query(FarmLossScore).filter(
        FarmLossScore.farm_id == str(farm_id)
    ).order_by(FarmLossScore.snapshot_date.asc()).all()
    events = session.query(LossEvent).filter(
        LossEvent.farm_id == str(farm_id)
    ).order_by(LossEvent.detected_at.asc()).all()
    packet = {
        "cover": report,
        "loss_score_history": [{"date": item.snapshot_date.isoformat(), "score": item.score,
                                "yield_delta_pct": item.yield_delta_pct, "model_version": item.model_version}
                               for item in scores],
        "loss_events": [{"event_id": item.id, "event_type": item.event_type,
                         "detected_at": item.detected_at.isoformat(), "severity": item.severity,
                         "source": item.source, "sensor_snapshot": item.raw_sensor_snapshot}
                        for item in events],
        "counterfactual": counterfactual_loss(session, farm_id)[0],
        "weather_evidence": [],
        "imagery": {"before_after_available": False,
                     "message": "Satellite image export is not configured for this deployment."},
        "supporting_evidence_only": True,
    }
    farm = _farm_or_none(session, farm_id)
    if farm:
        weather = session.query(WeatherObservation).filter(
            WeatherObservation.state == farm.state,
            WeatherObservation.district == farm.district,
        ).order_by(WeatherObservation.observation_date.asc()).all()
        packet["weather_evidence"] = [{"date": item.observation_date.isoformat(),
                                       "temperature_max": item.temperature_max,
                                       "rainfall": item.rainfall,
                                       "humidity": item.humidity} for item in weather]
        ndvi_rows = session.query(SatelliteNDVIData).filter(
            SatelliteNDVIData.state == farm.state,
            SatelliteNDVIData.district == farm.district,
            SatelliteNDVIData.crop == farm.crop,
        ).order_by(SatelliteNDVIData.observation_date.asc()).all()
        midpoint = max(len(ndvi_rows) // 2, 1)
        packet["imagery"]["thumbnail_data_uri"] = ndvi_thumbnail_data_uri(
            [row.ndvi_value for row in ndvi_rows[:midpoint]],
            [row.ndvi_value for row in ndvi_rows[midpoint:]],
        )
        packet["imagery"]["before_after_available"] = bool(packet["imagery"].get("thumbnail_data_uri"))
    return packet, None


def claim_outcome_analytics(session):
    claims = session.query(ClaimRecord).all()
    settled = [claim for claim in claims if claim.status == "settled"]
    completed = [claim for claim in claims if claim.status in ("settled", "disputed")]
    return {
        "claims_observed": len(claims),
        "settled_claims": len(settled),
        "approval_proxy_pct": round(len(settled) / len(completed) * 100, 2) if completed else None,
        "median_settlement_days": None,
        "model_status": "insufficient_outcome_history" if len(completed) < 30 else "descriptive_metrics_ready",
        "guidance": "Historical guidance is descriptive only and is not a prediction of claim approval or payout.",
    }
