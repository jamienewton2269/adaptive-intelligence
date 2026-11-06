"""Pure functions for conservative, explainable learning; no Home Assistant imports."""
from collections import defaultdict
from datetime import datetime, timedelta
from math import sqrt
from zoneinfo import ZoneInfo


def classify(context, automation_context_ids, recent_service_context_ids):
    """Classify conservatively; unknown physical actions are never called manual."""
    cid = context.get("id")
    parent = context.get("parent_id")
    if cid in automation_context_ids or parent in automation_context_ids:
        return "automation"
    if context.get("user_id"):
        return "user"
    if cid in recent_service_context_ids or parent in recent_service_context_ids:
        return "service"
    return "unknown"


def make_suggestions(events, timezone="UTC", now=None):
    """Find repeated user overrides. Candidates never execute commands."""
    tz = ZoneInfo(timezone)
    now = now or datetime.now(tz)
    start = now - timedelta(days=45)
    bins = defaultdict(list)
    for event in events:
        if event.get("kind") != "light" or event.get("classification") not in ("user", "automation"):
            continue
        if event.get("new") not in ("on", "off"):
            continue
        try:
            dt = datetime.fromisoformat(event["at"]).astimezone(tz)
        except (ValueError, KeyError, TypeError):
            continue
        if dt < start or dt > now:
            continue
        key = (event["entity"], "weekend" if dt.weekday() >= 5 else "weekday", dt.hour, event["new"])
        bins[key].append((dt, event))
    findings = []
    for (entity, day_kind, hour, action), records in bins.items():
        distinct_days = {dt.date() for dt, _ in records}
        if len(distinct_days) < 10:
            continue
        overrides = [(dt, e) for dt, e in records if e["classification"] == "user" and e.get("override")]
        if len(overrides) < 6 or len({dt.date() for dt, _ in overrides}) < 4:
            continue
        if (max(distinct_days) - min(distinct_days)).days < 14:
            continue
        n, k = len(records), len(overrides)
        if k / n < 0.6:
            continue
        p = k / n
        z = 1.96
        lower = (p + z*z/(2*n) - z*sqrt((p*(1-p)+z*z/(4*n))/n))/(1+z*z/n)
        findings.append({
            "key": f"{entity}:{day_kind}:{hour}:{action}",
            "entity": entity, "day_class": day_kind, "hour": hour, "desired": action,
            "observations": n, "overrides": k, "days": len(distinct_days),
            "confidence_lower_bound": round(lower, 3), "status": "candidate",
            "explanation": f"{k}/{n} comparable {action} actions were user overrides across {len(distinct_days)} {day_kind} dates around {hour:02d}:00. Review before changing any automation.",
        })
    return sorted(findings, key=lambda item: (-item["confidence_lower_bound"], item["key"]))[:25]
