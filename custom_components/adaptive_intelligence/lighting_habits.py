"""Local, conservative lighting habit discovery.

Observation only: never invokes an actuator or rewrites an automation.
JNSystems — In loving memory of Becki and Dad.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
from zoneinfo import ZoneInfo


def _read_time(value, zone):
    if not isinstance(value, str):
        return None
    try:
        at = datetime.fromisoformat(value)
        if at.tzinfo is None:  # An unqualified timestamp cannot prove local time.
            return None
        return at.astimezone(zone)
    except (TypeError, ValueError, OverflowError):
        return None


def summarise_lighting_habits(events, timezone="Europe/London", now=None,
                              min_days=5, min_span_days=10):
    """Return conservative manual habits and separate automated behaviour.

    Early patterns are evidence-only and are never user suggestions.
    Only *state* transitions of attributable user context may become
    candidates. Physical Zigbee 'unknown' events cannot train manual habits.
    All results are local, capped and contain no personal identifier.
    """
    try:
        zone = ZoneInfo(timezone)
    except (KeyError, ValueError):
        zone = ZoneInfo("UTC")
    now = now or datetime.now(zone)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(zone)
    cutoff = now - timedelta(days=45)
    groups = defaultdict(list)
    automated = defaultdict(set)
    counts = {"on_off_transitions": 0, "verified_manual": 0,
              "automation": 0, "unattributed": 0, "excluded_quality": 0}

    for event in events:
        if not isinstance(event, dict) or event.get("kind") != "light":
            continue
        entity = event.get("entity")
        old, new = event.get("old"), event.get("new")
        if not isinstance(entity, str) or not entity.startswith("light."):
            continue
        if new not in ("on", "off") or old not in ("on", "off") or new == old:
            continue
        at = _read_time(event.get("at"), zone)
        if at is None or not cutoff <= at <= now:
            continue
        counts["on_off_transitions"] += 1
        source = event.get("classification")
        if event.get("lux_quality") in ("invalid", "stale", "unavailable"):
            counts["excluded_quality"] += 1
            continue
        day_kind = "weekend" if at.weekday() >= 5 else "weekday"
        # One-hour bins, separately for each light / desired state.
        bucket = at.hour
        if source == "user":
            counts["verified_manual"] += 1
            groups[(entity, new, day_kind, bucket)].append(at)
        elif source == "automation":
            counts["automation"] += 1
            automated[(entity, new, day_kind, bucket)].add(at.date())
        else:
            counts["unattributed"] += 1

    early, suggestions = [], []
    for (entity, action, kind, hour), times in groups.items():
        days = sorted(set(t.date() for t in times))
        if len(days) < 2:
            continue
        span = (days[-1] - days[0]).days
        minute_of_hour = round(median(t.minute for t in times))
        # Distinguish "this occurred repeatedly" from likelihood that
        # the user actually wants it on any given day.
        record = {
            "entity": entity,
            "action": action,
            "day_class": kind,
            "hour": hour,
            "typical_time": f"{hour:02d}:{minute_of_hour:02d}",
            "distinct_days": len(days),
            "observations": len(times),
            "span_days": span,
            "observed_automatic_days": len(automated.get(
                (entity, action, kind, hour), set()
            )),
            "confidence": "insufficient_evidence",
            "evidence": "verified Home Assistant user context; not physical-button proof",
            "permission": "suggest_only",
        }
        if len(days) >= min_days and span >= min_span_days:
            record["confidence"] = "repeat_pattern"
            record["explanation"] = (
                f"Manual {action} observed for {entity} around "
                f"{record['typical_time']} on {len(days)} distinct {kind} dates "
                f"spanning {span} days. Review lux, presence, and energy impact "
                "before proposing any automation change."
            )
            suggestions.append(record)
        else:
            record["explanation"] = (
                f"Early observation: {len(days)} distinct {kind} dates near "
                f"{record['typical_time']}; not enough evidence for a suggestion."
            )
            early.append(record)

    def ranking(item):
        return (-item["distinct_days"], -item["span_days"],
                item["entity"], item["action"], item["hour"])
    return {
        "mode": "observe_only",
        "threshold": {"distinct_days": min_days, "span_days": min_span_days},
        "counts": counts,
        "candidates": sorted(suggestions, key=ranking)[:12],
        "early_patterns": sorted(early, key=ranking)[:12],
        "limit": "Last 45 days, bounded by local event store",
        "limitations": (
            "Missing days are not evidence of a choice; routine frequency and "
            "occupancy are not yet validated. Unidentified Zigbee physical "
            "actions never count as confirmed manual habits."
        ),
    }
