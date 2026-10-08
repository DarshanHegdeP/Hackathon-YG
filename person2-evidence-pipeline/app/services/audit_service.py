from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger("audit")
logger.setLevel(logging.INFO)


class AuditService:
    def __init__(self):
        self.event_bus_name = os.getenv("EVENT_BUS_NAME")
        self.use_eventbridge = bool(self.event_bus_name and os.getenv("AWS_DEFAULT_REGION"))

    def emit_event(self, event_type: str, detail: Dict[str, Any]) -> None:
        """
        Emits an audit event to AWS EventBridge or structured logging.
        """
        payload = {
            "eventType": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        }

        if self.use_eventbridge:
            try:
                import boto3

                client = boto3.client("events")
                client.put_events(
                    Entries=[
                        {
                            "Source": "fintech.evidence.pipeline",
                            "DetailType": event_type,
                            "Detail": json.dumps(payload),
                            "EventBusName": self.event_bus_name,
                        }
                    ]
                )
            except Exception as exc:
                logger.warning(f"Failed to publish EventBridge audit event: {exc}")
        else:
            logger.info(f"[AUDIT EVENT] {event_type}: {json.dumps(payload)}")
