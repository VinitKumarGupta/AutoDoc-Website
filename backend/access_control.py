from typing import Dict, Any


def apply_access_control(role: str, ueba_output: Dict[str, Any]) -> Dict[str, Any]:
    if role == "dealer":
        # Managers see everything
        return ueba_output

    # Users see simplified view
    status = ueba_output.get("ueba_status", "NORMAL")
    findings = ueba_output.get("ueba_findings", [])
    simplified = []
    for f in findings:
        if "WAF" in f or "unauthorized" in f.lower():
            continue
        simplified.append("Security check recommended." if status != "NORMAL" else "Data consistency nominal.")
        simplified.append("Data inconsistency detected." if "inconsistency" in f.lower() else "")
    simplified = [s for s in simplified if s]
    return {
        "ueba_score": ueba_output.get("ueba_score"),
        "ueba_status": status,
        "ueba_findings": simplified or ["Data consistency nominal."],
    }


