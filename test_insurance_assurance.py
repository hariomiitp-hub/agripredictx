from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_models import (
    Base,
    FarmRecord,
    SatelliteNDVIData,
    WeatherObservation,
)
from insurance_assurance import (
    build_evidence_packet,
    calculate_loss_score,
    detect_loss_events,
    save_claim,
    save_voice_loss_report,
    validate_enrollment,
)


class FakeModel:
    def predict(self, values):
        return np.array([0]), np.array([[0.2, 0.8]])


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_farm(session):
    farm = FarmRecord(
        farm_id="F-1", state="Punjab", district="Ludhiana", crop="wheat",
        latitude=30.9, longitude=75.8,
    )
    session.add(farm)
    session.commit()
    return farm


def test_loss_score_persists_with_quality_flag():
    session = make_session()
    make_farm(session)

    snapshot, response = calculate_loss_score(session, FakeModel(), "F-1")

    assert snapshot.id == 1
    assert response["model_version"] == "insurance-assurance-v1"
    assert "no NDVI imagery available" in response["data_quality"]


def test_ndvi_event_is_idempotent_during_cooldown():
    session = make_session()
    farm = make_farm(session)
    now = datetime.utcnow()
    session.add_all([
        SatelliteNDVIData(state="Punjab", district="Ludhiana", crop="wheat", observation_date=now - timedelta(days=10), acquisition_date=now - timedelta(days=10), ndvi_value=0.8),
        SatelliteNDVIData(state="Punjab", district="Ludhiana", crop="wheat", observation_date=now, acquisition_date=now, ndvi_value=0.4),
    ])
    session.commit()

    first = detect_loss_events(session, farm)
    second = detect_loss_events(session, farm)

    assert first.id == second.id
    assert first.event_type == "ndvi_drop"


def test_enrollment_and_claim_audits():
    session = make_session()
    make_farm(session)

    validation = validate_enrollment(session, {
        "farm_id": "F-1", "crop": "wheat", "area_hectares": 2,
        "satellite_area_hectares": 2.5,
    })
    claim = save_claim(session, {"farm_id": "F-1", "status": "reported"})

    assert validation["warnings"]
    assert claim["status"] == "reported"


def test_voice_report_and_evidence_packet():
    session = make_session()
    make_farm(session)
    event, error = save_voice_loss_report(session, "F-1", {
        "transcript": "गेहूं में 40% नुकसान", "language": "hi",
    })
    packet, packet_error = build_evidence_packet(session, "F-1", event["event_id"], "hi")

    assert error is None
    assert event["source"] == "farmer-reported"
    assert packet_error is None
    assert packet["cover"]["language"] == "hi"
    assert packet["supporting_evidence_only"] is True
