from collections import defaultdict
from datetime import datetime


def ewma_degradation(payment_attempts: list, alpha: float = .25, alert_z: float = 3.5) -> list[dict]:
    """Explainable provider/method detector over observed attempts only."""
    grouped = defaultdict(list)
    for attempt in payment_attempts:
        grouped[attempt.method or "unknown"].append(attempt)
    alerts = []
    for method, rows in grouped.items():
        rows.sort(key=lambda x: x.created_at or datetime.min)
        if len(rows) < 8: continue
        ewma, values = None, []
        for row in rows:
            success = 1.0 if row.status in {"captured", "authorized"} else 0.0
            ewma = success if ewma is None else alpha * success + (1 - alpha) * ewma
            values.append(success)
        baseline = sum(values[:-1]) / max(1, len(values) - 1)
        variance = sum((v - baseline) ** 2 for v in values[:-1]) / max(1, len(values) - 2)
        z = (ewma - baseline) / max(variance ** .5, .01)
        if z <= -alert_z:
            alerts.append({"payment_method": method, "ewma_success_rate": round(ewma, 3), "baseline_success_rate": round(baseline, 3), "z_score": round(z, 2), "status": "DEGRADED"})
    return alerts
