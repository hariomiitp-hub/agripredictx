"""Background jobs for Insurance Assurance; scheduling is supplied by deployment."""
import logging
from datetime import datetime

from database_models import FarmRecord
from insurance_assurance import detect_loss_events

logger = logging.getLogger(__name__)


def scan_registered_farms(db_connector, ndvi_drop_pct=20, window_days=14, cooldown_days=14):
    """Scan every registered farm once and return newly detected or cooldown-held events."""
    session = db_connector.get_session()
    events = []
    try:
        farms = session.query(FarmRecord).all()
        for farm in farms:
            event = detect_loss_events(
                session, farm,
                ndvi_drop_pct=ndvi_drop_pct,
                window_days=window_days,
                cooldown_days=cooldown_days,
            )
            if event is not None:
                events.append({
                    "farm_id": farm.farm_id,
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "detected_at": event.detected_at.isoformat(),
                    "severity": event.severity,
                })
        return {"scanned_at": datetime.utcnow().isoformat(), "farms_scanned": len(farms), "events": events}
    finally:
        session.close()
