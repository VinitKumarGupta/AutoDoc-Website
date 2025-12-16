from typing import Dict, Any, Optional
from predictive import predict_breakdown_risk


def _urgency_from_risk(risk_score: float) -> str:
    if risk_score >= 0.85:
        return "critical"
    if risk_score >= 0.65:
        return "high"
    if risk_score >= 0.4:
        return "medium"
    return "low"


def _summarize_alert(alert: Optional[Dict[str, Any]]) -> str:
    if not alert:
        return "No active alerts."
    return (
        f"Active alert: {alert.get('predicted_failure_type')} "
        f"driven by {alert.get('root_cause_sensor')} at {alert.get('current_sensor_value')} "
        f"(risk {alert.get('risk_score')})."
    )


def _contextual_answer(question: str, telemetry: Dict[str, Any], model_output: Dict[str, Any], alert: Optional[Dict[str, Any]]) -> str:
    vt = telemetry.get("vehicle_type", "vehicle")
    risk_score = model_output.get("risk_score", 0)
    cause = model_output.get("predicted_failure_type", "General instability")
    root = model_output.get("root_cause_sensor", "unknown sensor")
    rec = model_output.get("repair_recommendation") or {}
    recommendation = rec.get("action") if isinstance(rec, dict) else None

    if "safe" in question and "drive" in question:
        if risk_score >= 0.85:
            return "Risk is critical; do not continue driving. Seek immediate service."
        if risk_score >= 0.65:
            return "Elevated risk. Drive only if necessary and head to service soon."
        return "Risk is low; continue driving but monitor alerts."

    if "alert" in question:
        return _summarize_alert(alert)

    if "maintenance" in question or "due" in question:
        return f"For this {vt}, address {cause}. Recommended action: {recommendation or 'Schedule inspection soon.'}"

    if "vibrat" in question:
        return f"Vibration linked to {root}. Suggested fix: {recommendation or 'Inspect mounts, bearings, and balance.'}"

    if "summarize" in question or "sensor" in question:
        return f"Top concern: {cause} via {root}. Risk {risk_score}. {_summarize_alert(alert)}"

    if "how long" in question or "until failure" in question:
        if risk_score >= 0.85:
            return "Failure could be imminent (hours). Stop and service immediately."
        if risk_score >= 0.65:
            return "Likely within days under continued stress. Prioritize service."
        return "No immediate failure expected; continue monitoring."

    return f"{cause} detected via {root}. Risk {risk_score}. {_summarize_alert(alert)}"


def generate_ai_response(question: str, telemetry: Optional[Dict[str, Any]], alert: Optional[Dict[str, Any]], rca: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    telemetry = telemetry or {}
    model_output = predict_breakdown_risk(telemetry) if telemetry else {
        "risk_score": 0,
        "predicted_failure_type": "Unknown",
        "root_cause_sensor": "unknown",
    }

    answer = _contextual_answer(question.lower(), telemetry, model_output, alert)
    urgency = _urgency_from_risk(model_output.get("risk_score", 0))

    return {
        "answer": answer,
        "risk_level": model_output.get("risk_score", 0),
        "most_likely_cause": model_output.get("predicted_failure_type"),
        "recommended_action": (rca or {}).get("action") if isinstance(rca, dict) else "See repair recommendation or schedule service soon.",
        "urgency": urgency,
        "predicted_failure_type": model_output.get("predicted_failure_type"),
        "root_cause_sensor": model_output.get("root_cause_sensor"),
    }

