"""Usage repository for router request history and cost analytics in MongoDB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from pymongo.database import Database
from app.db.models import UsageEventDocument
from app.db.mongodb import get_db

logger = logging.getLogger(__name__)


class UsageRepository:
    def __init__(self, db: Database | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Database | None:
        return self._db if self._db is not None else get_db()

    def save_usage_event(self, clerk_user_id: str, event_data: dict[str, Any]) -> dict[str, Any] | None:
        """Persist a router or agent execution event into usage_events collection."""
        db = self.db
        if db is None or not clerk_user_id:
            return None

        try:
            event = UsageEventDocument(
                request_id=event_data.get("request_id") or f"req_{int(datetime.now().timestamp() * 1000)}",
                clerk_user_id=clerk_user_id,
                model=event_data.get("model") or event_data.get("final_model"),
                status=event_data.get("status", "success"),
                confidence=float(event_data.get("confidence")) if event_data.get("confidence") is not None else None,
                escalated=bool(event_data.get("escalated", False)),
                escalation_reason=event_data.get("escalation_reason"),
                input_tokens=event_data.get("input_tokens"),
                output_tokens=event_data.get("output_tokens"),
                actual_cost=float(event_data.get("actual_cost") if event_data.get("actual_cost") is not None else event_data.get("cost", 0.0) or 0.0),
                baseline_cost=float(event_data.get("baseline_cost", 0.0) or 0.0),
                savings=float(event_data.get("savings", 0.0) or 0.0),
                savings_percentage=float(event_data.get("savings_percentage", 0.0) or 0.0),
                tools_used=list(event_data.get("tools_used", [])),
                task_type=event_data.get("task_type"),
                complexity=event_data.get("complexity"),
                created_at=event_data.get("created_at") or datetime.now(timezone.utc).isoformat(),
            )
            doc_dict = event.model_dump()
            db["usage_events"].insert_one(doc_dict)
            doc_dict.pop("_id", None)
            return doc_dict
        except Exception as exc:
            logger.warning("MongoDB UsageRepository.save_usage_event failed for user %s: %s", clerk_user_id, exc)
            return None

    def get_user_logs(self, clerk_user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        db = self.db
        if db is None or not clerk_user_id:
            return []
        try:
            cursor = db["usage_events"].find({"clerk_user_id": clerk_user_id}).sort("created_at", -1).limit(limit)
            logs = []
            for doc in cursor:
                doc.pop("_id", None)
                # Ensure backward-compatible keys exist for existing frontend UI
                doc.setdefault("final_model", doc.get("model"))
                doc.setdefault("initial_model", "gemini" if str(doc.get("model", "")).lower() != "mistral" else "mistral")
                doc.setdefault("cost", doc.get("actual_cost", 0.0))
                doc.setdefault("user_id", clerk_user_id)
                logs.append(doc)
            return logs
        except Exception as exc:
            logger.warning("MongoDB UsageRepository.get_user_logs failed for user %s: %s", clerk_user_id, exc)
            return []

    def get_user_dashboard_metrics(self, clerk_user_id: str) -> dict[str, Any] | None:
        """Compute user-scoped aggregated dashboard metrics using MongoDB aggregation pipeline."""
        db = self.db
        if db is None or not clerk_user_id:
            return None

        try:
            pipeline = [
                {"$match": {"clerk_user_id": clerk_user_id}},
                {
                    "$group": {
                        "_id": None,
                        "total_requests": {"$sum": 1},
                        "gemini_requests": {
                            "$sum": {
                                "$cond": [
                                    {"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$model", ""]}}, "regex": "gemini"}},
                                    1,
                                    0,
                                ]
                            }
                        },
                        "mistral_requests": {
                            "$sum": {
                                "$cond": [
                                    {"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$model", ""]}}, "regex": "mistral"}},
                                    1,
                                    0,
                                ]
                            }
                        },
                        "escalations": {"$sum": {"$cond": ["$escalated", 1, 0]}},
                        "total_confidence": {"$sum": {"$ifNull": ["$confidence", 0.0]}},
                        "confidence_count": {"$sum": {"$cond": [{"$ne": ["$confidence", None]}, 1, 0]}},
                        "total_actual_cost": {"$sum": "$actual_cost"},
                        "total_baseline_cost": {"$sum": "$baseline_cost"},
                        "total_savings": {"$sum": "$savings"},
                    }
                },
            ]

            aggregated_results = list(db["usage_events"].aggregate(pipeline))
            events = self.get_user_logs(clerk_user_id, limit=200)

            if not aggregated_results:
                return {
                    "total_requests": 0,
                    "gemini_requests": 0,
                    "mistral_requests": 0,
                    "escalation_rate": 0.0,
                    "average_confidence": 0.0,
                    "average_latency": 0.0,
                    "total_cost": 0.0,
                    "baseline_cost": 0.0,
                    "total_savings": 0.0,
                    "savings_percentage": 0.0,
                    "accuracy": None,
                    "events": [],
                }

            agg = aggregated_results[0]
            total = agg.get("total_requests", 0)
            gemini = agg.get("gemini_requests", 0)
            mistral = agg.get("mistral_requests", 0)
            escalations = agg.get("escalations", 0)
            conf_count = agg.get("confidence_count", 0)
            avg_conf = (agg.get("total_confidence", 0.0) / conf_count) if conf_count > 0 else 0.0

            actual_cost = agg.get("total_actual_cost", 0.0)
            baseline = agg.get("total_baseline_cost", 0.0)
            savings = agg.get("total_savings", 0.0)
            savings_pct = ((savings / baseline) * 100.0) if baseline > 0 else 0.0

            return {
                "total_requests": total,
                "gemini_requests": gemini,
                "mistral_requests": mistral,
                "escalation_rate": round(escalations / total, 4) if total > 0 else 0.0,
                "average_confidence": round(avg_conf, 4),
                "average_latency": 0.0,
                "total_cost": round(actual_cost, 10),
                "baseline_cost": round(baseline, 10),
                "total_savings": round(savings, 10),
                "savings_percentage": round(savings_pct, 2),
                "accuracy": None,
                "events": events,
            }
        except Exception as exc:
            logger.warning("MongoDB UsageRepository.get_user_dashboard_metrics failed for user %s: %s", clerk_user_id, exc)
            return None
