import re
import time
from typing import Dict, Any, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_SQLI = re.compile(r"(?:union|select|drop|insert|update|delete|;|--|\bor\b\s+1=1)", re.IGNORECASE)
_XSS = re.compile(r"(<script|onerror=|onload=)", re.IGNORECASE)
_FUZZ = re.compile(r"(\.\./|\%00|%2e%2e|%2f)", re.IGNORECASE)
_RATE_WINDOW = 30  # seconds
_RATE_MAX = 20
_rate_bucket: Dict[str, List[float]] = {}


def _score_payload(text: str) -> int:
    score = 0
    if _SQLI.search(text):
        score += 30
    if _XSS.search(text):
        score += 30
    if _FUZZ.search(text):
        score += 20
    if len(text) > 5000:
        score += 10
    return score


def _score_rate(ip: str) -> int:
    now = time.time()
    bucket = _rate_bucket.setdefault(ip, [])
    bucket.append(now)
    cutoff = now - _RATE_WINDOW
    _rate_bucket[ip] = [t for t in bucket if t >= cutoff]
    if len(_rate_bucket[ip]) > _RATE_MAX:
        return 20
    return 0


def analyze_request(req: Request, body_text: str) -> Dict[str, Any]:
    ip = req.client.host if req.client else "unknown"
    ua = req.headers.get("user-agent", "unknown")
    fp = req.headers.get("x-device-fingerprint", "unknown")

    score = _score_payload(body_text) + _score_rate(ip)
    findings = []
    if _SQLI.search(body_text):
        findings.append("SQLi pattern detected")
    if _XSS.search(body_text):
        findings.append("XSS pattern detected")
    if _FUZZ.search(body_text):
        findings.append("Traversal/fuzz pattern detected")
    if len(body_text) > 5000:
        findings.append("Unusually large payload")
    if _score_rate(ip) > 0:
        findings.append("Rapid request rate")

    return {
        "ip": ip,
        "user_agent": ua,
        "device_fingerprint": fp,
        "score": min(score, 100),
        "findings": findings,
        "timestamp": time.time(),
    }


class RequestSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, log_store: List[Dict[str, Any]]):
        super().__init__(app)
        self.log_store = log_store

    async def dispatch(self, request: Request, call_next):
        try:
            body_bytes = await request.body()
            body_text = body_bytes.decode(errors="ignore") if body_bytes else ""
        except Exception:
            body_text = ""

        analysis = analyze_request(request, body_text)
        request.state.request_security_score = analysis["score"]
        request.state.request_security_findings = analysis["findings"]

        if analysis["score"] >= 50 or analysis["findings"]:
            self.log_store.append({
                "path": request.url.path,
                "method": request.method,
                **analysis,
            })

        response: Response = await call_next(request)
        return response


