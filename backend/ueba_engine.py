from typing import Dict, Any, List


def _status_from_score(score: float) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "SUSPICIOUS"
    return "NORMAL"


def analyze(user_behavior: Dict[str, Any], manager_behavior: Dict[str, Any], telemetry: Dict[str, Any], web_alerts: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[str] = []
    score = 0

    # User behavior
    if user_behavior.get("failed_logins", 0) > 3:
        score += 20
        findings.append("Repeated failed logins")
    if user_behavior.get("ip_change"):
        score += 10
        findings.append("Login IP/location change")
    if user_behavior.get("odd_questions"):
        score += 10
        findings.append("Abnormal chatbot question pattern")

    # Manager behavior
    if manager_behavior.get("unauthorized_access"):
        score += 20
        findings.append("Manager accessed unauthorized data")
    if manager_behavior.get("high_freq_ops"):
        score += 10
        findings.append("High-frequency sensitive operations")

    # Telemetry behavior
    if telemetry.get("inconsistent_sensors"):
        score += 15
        findings.append("Sensor inconsistency detected")
    if telemetry.get("impossible_values"):
        score += 15
        findings.append("Impossible telemetry values")
    if telemetry.get("vehicle_type_mismatch"):
        score += 10
        findings.append("Vehicle type vs sensor mismatch")
    if telemetry.get("time_series_anomaly"):
        score += 10
        findings.append("Time-series anomaly detected")

    # Web/WAF
    waf_score = web_alerts.get("score", 0)
    if waf_score >= 50:
        score += 15
        findings.append("WAF-lite flagged suspicious pattern")
    if web_alerts.get("findings"):
        findings.extend([f"WAF: {f}" for f in web_alerts["findings"]])

    score = min(score, 100)
    status = _status_from_score(score)
    return {
        "ueba_score": score,
        "ueba_status": status,
        "ueba_findings": findings or ["No anomalies detected"],
    }


