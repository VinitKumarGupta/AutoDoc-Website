from typing import Dict, Any, List, Optional


class AlertTriggerService:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.active_alerts: List[Dict[str, Any]] = []

    def evaluate(self, model_output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate a model output and store/return alert if over threshold."""
        if model_output["risk_score"] >= self.threshold:
            alert = {
                "vehicle_id": model_output["vehicle_id"],
                "predicted_failure_type": model_output["predicted_failure_type"],
                "root_cause_sensor": model_output["root_cause_sensor"],
                "current_sensor_value": model_output.get("current_sensor_value"),
                "risk_score": model_output["risk_score"],
            }
            self._upsert_alert(alert)
            return alert
        return None

    def _upsert_alert(self, alert: Dict[str, Any]):
        existing = self.get_alert_for_vehicle(alert["vehicle_id"])
        if existing:
            self.active_alerts = [a for a in self.active_alerts if a["vehicle_id"] != alert["vehicle_id"]]
        self.active_alerts.append(alert)

    def get_alert_for_vehicle(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        return next((a for a in self.active_alerts if a["vehicle_id"] == vehicle_id), None)


