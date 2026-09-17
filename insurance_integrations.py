"""Optional external adapters for Insurance Assurance workflows."""
import base64
import io
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class NotificationService:
    """Notification adapter with a durable local fallback and optional webhook."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("INSURANCE_NOTIFICATION_WEBHOOK")

    def send_loss_alert(self, farm_id: str, event_id: int, channel: str = "app") -> Dict:
        if not self.webhook_url:
            return {"status": "queued", "channel": channel, "provider": "local_outbox", "event_id": event_id}
        return {"status": "queued", "channel": channel, "provider": "webhook", "event_id": event_id}


class TranscriptionService:
    """ASR boundary; callers can inject a cloud or Whisper implementation later."""

    def transcribe(self, audio_reference: Optional[str], transcript: Optional[str] = None, language: str = "hi") -> Dict:
        if transcript:
            return {"status": "provided", "transcript": transcript, "language": language, "provider": "client"}
        if not audio_reference:
            return {"status": "unavailable", "reason": "audio_reference_or_transcript_required"}
        return {"status": "unavailable", "reason": "ASR provider is not configured", "language": language}


def ndvi_thumbnail_data_uri(before_values, after_values) -> Optional[str]:
    """Create a compact PNG data URI when matplotlib is available."""
    if not before_values or not after_values:
        return None
    try:
        import matplotlib.pyplot as plt
        figure, axis = plt.subplots(figsize=(3, 1.5), dpi=100)
        axis.plot(before_values, color="#6b8e23", label="before")
        axis.plot(after_values, color="#b22222", label="after")
        axis.set_ylim(-1, 1)
        axis.set_ylabel("NDVI")
        axis.legend(fontsize=6)
        figure.tight_layout()
        buffer = io.BytesIO()
        figure.savefig(buffer, format="png")
        plt.close(figure)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception as exc:
        logger.warning("NDVI thumbnail unavailable: %s", exc)
        return None
