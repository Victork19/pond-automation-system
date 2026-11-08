from datetime import datetime, timedelta, timezone

STAGES = ('Discovery', 'Evaluation', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost')

def can_move_stage(current: str, proposed: str, evidence: list[dict]) -> bool:
    if proposed not in STAGES or current not in STAGES:
        return False
    if STAGES.index(proposed) < STAGES.index(current):
        return any('back' in (item.get('quote', '') or '').lower() or item.get('explicit_override') for item in evidence)
    return proposed == current or bool(evidence)

def skipped_until(days: int = 90) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)

def is_suppressed(status: str, until: datetime | None) -> bool:
    if status == 'do_not_contact':
        return True
    return bool(until and until > datetime.now(timezone.utc))
