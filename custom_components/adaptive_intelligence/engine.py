"""Evidence classification and conservative, explainable suggestions.

JNSystems — in memory of Becki and Dad.
No device control or cloud processing.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from math import sqrt
from zoneinfo import ZoneInfo


def classify(context, automation_context_ids, recent_service_context_ids):
    """Classify only verified provenance; unknown physical events are not manual."""
    cid = context.get("id")
    parent = context.get("parent_id")
    if cid in automation_context_ids or parent in automation_context_ids:
        return "automation"
    if context.get("user_id"):
        return "user"
    if cid in recent_service_context_ids or parent in recent_service_context_ids:
        return "service"
    return "unknown"


def validated_lux(state, now, max_age=timedelta(minutes=10)):
    """Return (lux, quality). Invalid and stale sensors cannot train the model."""
    if state is None:
        return None, "unconfigured"
    if getattr(state, "state", None) in ("unknown", "unavailable", None):
        return None, "unavailable"
    try:
        value = float(state.state)
        when = state.last_updated
        if not 0 <= value <= 200000:
            return None, "invalid"
        if when is None or now - when > max_age:
            return None, "stale"
        return value, "valid"
    except (ValueError, TypeError, OverflowError):
        return None, "invalid"


def make_suggestions(events, timezone="UTC", now=None):
    """Detect recurring *confirmed* user reversals; never command an actuator."""
    tz = ZoneInfo(timezone)
    now = now or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    start = now - timedelta(days=45)
    bins = defaultdict(list)
    for event in events:
        if event.get("kind") != "light":
            continue
        if event.get("classification") not in ("user", "automation"):
            continue
        if event.get("old") == event.get("new") or event.get("new") not in ("on", "off"):
            continue
        if event.get("lux_quality") in ("stale", "invalid"):
            continue
        try:
            dt = datetime.fromisoformat(event["at"]).astimezone(tz)
        except (ValueError, KeyError, TypeError):
            continue
        if not start <= dt <= now:
            continue
        key = (event["entity"], "weekend" if dt.weekday() >= 5 else "weekday",
               dt.hour, event["new"])
        bins[key].append((dt, event))
    findings = []
    for (entity, day_kind, hour, action), records in bins.items():
        days = {dt.date() for dt, _ in records}
        overrides = [(dt, e) for dt, e in records
                     if e["classification"] == "user" and e.get("override")]
        if len(days) < 10 or len(overrides) < 6:
            continue
        if len({dt.date() for dt, _ in overrides}) < 4:
            continue
        if (max(days) - min(days)).days < 14:
            continue
        n, k = len(records), len(overrides)
        if k / n < 0.6:
            continue
        p, z = k / n, 1.96
        lower = (p + z*z/(2*n) - z*sqrt((p*(1-p)+z*z/(4*n))/n))/(1+z*z/n)
        findings.append({
            "key": f"{entity}:{day_kind}:{hour}:{action}",
            "entity": entity, "day_class": day_kind, "hour": hour,
            "desired": action, "observations": n, "overrides": k,
            "days": len(days), "confidence_lower_bound": round(lower, 3),
            "status": "candidate",
            "explanation": f"{k}/{n} comparable {action} transitions were verified "
                           f"user reversals on {len(days)} {day_kind} dates around "
                           f"{hour:02d}:00. Review before changing any automation.",
        })
    return sorted(findings,
                  key=lambda item: (-item["confidence_lower_bound"], item["key"]))[:25]
